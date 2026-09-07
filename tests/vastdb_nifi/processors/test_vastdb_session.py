# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""Tests for the shared VastDB connection and its TLS configuration."""

# The TLS helpers are deliberately module-private; testing them directly is the point.
# ruff: noqa: SLF001

import http.server
import ssl
import threading

import pytest
import requests

from vastdb_nifi.processors import vastdb_session
from vastdb_nifi.processors.vastdb_session import (
    TLS_CA_CERTIFICATE_FILE,
    TLS_NO_VERIFICATION,
    TLS_SSL_CONTEXT_SERVICE,
    TLS_SYSTEM_CA,
    VastDBConnection,
)

from . import certs
from .conftest import FakeProcessContext, FakeSSLContextService

HTTPS_ENDPOINT = "https://vastdb.example.com"
HTTP_ENDPOINT = "http://vastdb.example.com"

TRUSTSTORE_PASSWORD = "truststore-secret"


@pytest.fixture(scope="module")
def ca():
    return certs.create_ca()


@pytest.fixture(scope="module")
def server_certificate(ca):
    return certs.issue(ca, "localhost", hostname="localhost")


@pytest.fixture
def connection():
    return VastDBConnection()


def build_context(connection, properties, logger, endpoint=HTTPS_ENDPOINT):
    properties.setdefault(connection.endpoint.name, endpoint)
    return connection._tls_kwargs(FakeProcessContext(properties), endpoint, logger)


def truststore_service(tmp_path, certificates, keystore_type="PKCS12", name="truststore"):
    truststore = tmp_path / f"{name}.{keystore_type.lower()}"
    if keystore_type == "PKCS12":
        certs.write_pkcs12_truststore(truststore, certificates, TRUSTSTORE_PASSWORD)
    else:
        certs.write_jks_truststore(truststore, certificates, TRUSTSTORE_PASSWORD)
    return FakeSSLContextService(
        truststore={"file": str(truststore), "type": keystore_type, "password": TRUSTSTORE_PASSWORD}
    )


# --------------------------------------------------------------------------------------
# Property descriptors
# --------------------------------------------------------------------------------------


def test_property_names_are_unchanged_for_existing_flows(connection):
    # Flow configurations key on property name, so these two must not drift.
    assert connection.endpoint.name == "VastDB Endpoint"
    assert connection.credentials_provider_service.name == "VastDB Credentials Provider Service"


def test_tls_defaults_to_verifying_against_system_cas(connection):
    assert connection.tls_verification.default_value == TLS_SYSTEM_CA


def test_ssl_context_service_references_the_nifi_interface(connection):
    assert connection.ssl_context_service.controller_service_definition == "org.apache.nifi.ssl.SSLContextService"


def test_no_client_certificate_properties_are_exposed(connection):
    # VastDB authenticates with an access key and secret, so mutual TLS is out of scope.
    names = [descriptor.name for descriptor in connection.descriptors]
    assert not [name for name in names if "Client" in name or "Private Key" in name]


def test_ssl_context_service_is_only_shown_for_its_own_mode(connection):
    (dependency,) = connection.ssl_context_service.dependencies
    assert dependency.property_descriptor is connection.tls_verification
    assert dependency.dependent_values == (TLS_SSL_CONTEXT_SERVICE,)


def test_ca_certificate_file_is_only_shown_for_its_own_mode(connection):
    (dependency,) = connection.ca_certificate_file.dependencies
    assert dependency.property_descriptor is connection.tls_verification
    assert dependency.dependent_values == (TLS_CA_CERTIFICATE_FILE,)


def test_descriptors_are_ordered_with_the_connection_first(connection):
    assert connection.descriptors == [
        connection.endpoint,
        connection.credentials_provider_service,
        connection.tls_verification,
        connection.ssl_context_service,
        connection.ca_certificate_file,
    ]


# --------------------------------------------------------------------------------------
# Resolving TLS settings
# --------------------------------------------------------------------------------------


def test_http_endpoints_skip_tls_configuration(connection, logger):
    assert build_context(connection, {}, logger, endpoint=HTTP_ENDPOINT) == {}


def test_system_cas_are_passed_through_as_ssl_verify(connection, logger):
    kwargs = build_context(connection, {connection.tls_verification.name: TLS_SYSTEM_CA}, logger)
    assert kwargs == {"ssl_verify": True}


def test_verification_can_be_disabled(connection, logger):
    kwargs = build_context(connection, {connection.tls_verification.name: TLS_NO_VERIFICATION}, logger)
    assert kwargs == {"ssl_verify": False}


def test_ca_certificate_file_is_passed_through_as_a_path(connection, logger, tmp_path, ca):
    ca_file = tmp_path / "ca.pem"
    ca_file.write_bytes(ca.certificate_pem())

    kwargs = build_context(
        connection,
        {
            connection.tls_verification.name: TLS_CA_CERTIFICATE_FILE,
            connection.ca_certificate_file.name: str(ca_file),
        },
        logger,
    )
    assert kwargs == {"ssl_verify": str(ca_file)}


def test_every_mode_resolves_to_ssl_verify(connection, logger, tmp_path, ca):
    # No mode may require an SSLContext, which the pinned vastdb SDK cannot accept.
    service = truststore_service(tmp_path, [ca])
    kwargs = build_context(
        connection,
        {
            connection.tls_verification.name: TLS_SSL_CONTEXT_SERVICE,
            connection.ssl_context_service.name: service,
        },
        logger,
    )
    assert set(kwargs) == {"ssl_verify"}


# --------------------------------------------------------------------------------------
# SSL Context Service truststores
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("keystore_type", ["PKCS12", "JKS"])
def test_truststore_is_converted_to_trusted_pem(tmp_path, ca, keystore_type):
    service = truststore_service(tmp_path, [ca], keystore_type)
    pem = vastdb_session._truststore_to_pem(service)

    assert "BEGIN CERTIFICATE" in pem
    # The converted PEM is usable as trust material, which is the point of the exercise.
    assert ssl.create_default_context(cadata=pem).cert_store_stats()["x509_ca"] == 1


def test_truststore_becomes_a_ca_bundle_on_disk(connection, logger, tmp_path, ca):
    service = truststore_service(tmp_path, [ca])
    kwargs = build_context(
        connection,
        {
            connection.tls_verification.name: TLS_SSL_CONTEXT_SERVICE,
            connection.ssl_context_service.name: service,
        },
        logger,
    )

    assert vastdb_session.Path(kwargs["ssl_verify"]).read_bytes() == ca.certificate_pem()


def test_unsupported_truststore_type_explains_the_alternatives(tmp_path, ca):
    service = truststore_service(tmp_path, [ca])
    service._truststore["type"] = "BCFKS"

    with pytest.raises(RuntimeError, match="Unsupported SSL Context Service truststore type 'BCFKS'"):
        vastdb_session._truststore_to_pem(service)


def test_a_keystore_only_service_falls_back_to_system_cas(logger):
    service = FakeSSLContextService(keystore={"file": "/tmp/unused", "type": "PKCS12"})
    assert vastdb_session._resolve_verify(TLS_SSL_CONTEXT_SERVICE, service, None, logger) is True


def test_an_unused_keystore_is_called_out(tmp_path, ca, logger):
    # A user who configured a keystore may be expecting mutual TLS; they should be told.
    service = truststore_service(tmp_path, [ca])
    service._keystore = {"file": "/tmp/client.p12", "type": "PKCS12"}

    vastdb_session._resolve_verify(TLS_SSL_CONTEXT_SERVICE, service, None, logger)

    assert any("keystore configured" in message for message in logger.messages)


def test_no_warning_when_the_service_has_only_a_truststore(tmp_path, ca, logger):
    service = truststore_service(tmp_path, [ca])

    vastdb_session._resolve_verify(TLS_SSL_CONTEXT_SERVICE, service, None, logger)

    assert not [message for message in logger.messages if "keystore" in message]


# --------------------------------------------------------------------------------------
# Caching
# --------------------------------------------------------------------------------------


def test_tls_configuration_is_cached_between_flowfiles(connection, logger, tmp_path, ca):
    service = truststore_service(tmp_path, [ca])
    properties = {
        connection.tls_verification.name: TLS_SSL_CONTEXT_SERVICE,
        connection.ssl_context_service.name: service,
    }

    first = build_context(connection, dict(properties), logger)
    second = build_context(connection, dict(properties), logger)

    assert first is second


def test_replacing_a_truststore_invalidates_the_cache(connection, logger, tmp_path, ca):
    service = truststore_service(tmp_path, [ca])
    properties = {
        connection.tls_verification.name: TLS_SSL_CONTEXT_SERVICE,
        connection.ssl_context_service.name: service,
    }

    first = build_context(connection, dict(properties), logger)

    # Rotate the CA behind the same path, as a certificate renewal would.
    certs.write_pkcs12_truststore(
        vastdb_session.Path(service.getTrustStoreFile()),
        [certs.create_ca("Renewed CA")],
        TRUSTSTORE_PASSWORD,
    )
    second = build_context(connection, dict(properties), logger)

    assert first is not second


# --------------------------------------------------------------------------------------
# End to end against a real TLS server
# --------------------------------------------------------------------------------------


class _TLSServer:
    """A local HTTPS server presenting a certificate from a private CA."""

    def __init__(self, server_certificate, tmp_path):
        certificate_file = tmp_path / "server.pem"
        certificate_file.write_bytes(server_certificate.private_key_pem() + server_certificate.certificate_pem())

        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(str(certificate_file))

        self._server = http.server.HTTPServer(("127.0.0.1", 0), _QuietHandler)
        self._server.socket = ssl_context.wrap_socket(self._server.socket, server_side=True)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        return f"https://localhost:{self._server.server_address[1]}/"

    def __exit__(self, *args):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


class _QuietHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


def test_a_converted_truststore_verifies_a_real_server(connection, logger, tmp_path, ca, server_certificate):
    # The whole path, as `vastdb.connect` would use it: truststore -> PEM -> requests.
    service = truststore_service(tmp_path, [ca])
    kwargs = build_context(
        connection,
        {
            connection.tls_verification.name: TLS_SSL_CONTEXT_SERVICE,
            connection.ssl_context_service.name: service,
        },
        logger,
    )

    with _TLSServer(server_certificate, tmp_path) as url:
        assert requests.get(url, verify=kwargs["ssl_verify"], timeout=10).text == "ok"


def test_an_untrusted_server_certificate_is_rejected(connection, logger, tmp_path, server_certificate):
    # Trust a different CA than the one that signed the server certificate.
    service = truststore_service(tmp_path, [certs.create_ca("Unrelated CA")], name="stranger")
    kwargs = build_context(
        connection,
        {
            connection.tls_verification.name: TLS_SSL_CONTEXT_SERVICE,
            connection.ssl_context_service.name: service,
        },
        logger,
    )

    with _TLSServer(server_certificate, tmp_path) as url, pytest.raises(requests.exceptions.SSLError) as error:
        requests.get(url, verify=kwargs["ssl_verify"], timeout=10)

    assert "CERTIFICATE_VERIFY_FAILED" in str(error.value)
