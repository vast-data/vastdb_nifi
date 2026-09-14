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

from vastdb_nifi.processors.vastdb_session import (
    TLS_CA_CERTIFICATE_FILE,
    TLS_NO_VERIFICATION,
    TLS_SYSTEM_CA,
    VastDBConnection,
)

from . import certs
from .conftest import FakeProcessContext

HTTPS_ENDPOINT = "https://vastdb.example.com"


@pytest.fixture(scope="module")
def ca():
    return certs.create_ca()


@pytest.fixture(scope="module")
def server_certificate(ca):
    return certs.issue(ca, "localhost", hostname="localhost")


@pytest.fixture
def connection():
    return VastDBConnection()


def resolve(connection, properties, endpoint=HTTPS_ENDPOINT):
    properties.setdefault(connection.endpoint.name, endpoint)
    return connection.resolve_ssl_verify(FakeProcessContext(properties))


# --------------------------------------------------------------------------------------
# Property descriptors
# --------------------------------------------------------------------------------------


def test_property_names_are_unchanged_for_existing_flows(connection):
    # Flow configurations key on property name, so these must not drift.
    assert connection.endpoint.name == "VastDB Endpoint"
    assert connection.credentials_provider_service.name == "VastDB Credentials Provider Service"


def test_tls_defaults_to_verifying_against_system_cas(connection):
    assert connection.tls_verification.default_value == TLS_SYSTEM_CA


def test_tls_modes_are_system_ca_ca_file_and_no_verification(connection):
    # SSL Context Service was removed: CA Certificate File covers the same need (a PEM CA
    # bundle) without the native keystore-parsing dependency.
    assert set(connection.tls_verification.allowable_values) == {
        TLS_SYSTEM_CA,
        TLS_CA_CERTIFICATE_FILE,
        TLS_NO_VERIFICATION,
    }


def test_no_ssl_context_service_property_is_exposed(connection):
    names = [descriptor.name for descriptor in connection.descriptors]
    assert "SSL Context Service" not in names


def test_no_client_certificate_properties_are_exposed(connection):
    # VastDB authenticates with an access key and secret, so mutual TLS is out of scope.
    names = [descriptor.name for descriptor in connection.descriptors]
    assert not [name for name in names if "Client" in name or "Private Key" in name]


def test_ca_certificate_file_is_only_shown_for_its_own_mode(connection):
    (dependency,) = connection.ca_certificate_file.dependencies
    assert dependency.property_descriptor is connection.tls_verification
    assert dependency.dependent_values == (TLS_CA_CERTIFICATE_FILE,)


def test_descriptors_are_ordered_with_the_connection_first(connection):
    assert connection.descriptors == [
        connection.endpoint,
        connection.credentials_provider_service,
        connection.tls_verification,
        connection.ca_certificate_file,
    ]


# --------------------------------------------------------------------------------------
# Resolving TLS settings (every mode resolves to an ssl_verify value: True/False/path)
# --------------------------------------------------------------------------------------


def test_system_cas_resolve_to_true(connection):
    assert resolve(connection, {connection.tls_verification.name: TLS_SYSTEM_CA}) is True


def test_verification_can_be_disabled(connection):
    assert resolve(connection, {connection.tls_verification.name: TLS_NO_VERIFICATION}) is False


def test_ca_certificate_file_resolves_to_the_path(connection, tmp_path, ca):
    ca_file = tmp_path / "ca.pem"
    ca_file.write_bytes(ca.certificate_pem())

    verify = resolve(
        connection,
        {
            connection.tls_verification.name: TLS_CA_CERTIFICATE_FILE,
            connection.ca_certificate_file.name: str(ca_file),
        },
    )
    assert verify == str(ca_file)


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


def test_ca_certificate_file_verifies_a_real_server(connection, tmp_path, ca, server_certificate):
    # The whole path, as `vastdb.connect` (and ImportVastDB's requests read) would use it.
    ca_file = tmp_path / "ca.pem"
    ca_file.write_bytes(ca.certificate_pem())

    verify = resolve(
        connection,
        {
            connection.tls_verification.name: TLS_CA_CERTIFICATE_FILE,
            connection.ca_certificate_file.name: str(ca_file),
        },
    )

    with _TLSServer(server_certificate, tmp_path) as url:
        assert requests.get(url, verify=verify, timeout=10).text == "ok"


def test_an_untrusted_server_certificate_is_rejected(connection, tmp_path, server_certificate):
    # Trust a different CA than the one that signed the server certificate.
    ca_file = tmp_path / "stranger.pem"
    ca_file.write_bytes(certs.create_ca("Unrelated CA").certificate_pem())

    verify = resolve(
        connection,
        {
            connection.tls_verification.name: TLS_CA_CERTIFICATE_FILE,
            connection.ca_certificate_file.name: str(ca_file),
        },
    )

    with (
        _TLSServer(server_certificate, tmp_path) as url,
        pytest.raises(requests.exceptions.SSLError) as error,
    ):
        requests.get(url, verify=verify, timeout=10)

    assert "CERTIFICATE_VERIFY_FAILED" in str(error.value)
