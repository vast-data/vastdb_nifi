# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""Shared VastDB connection handling for the VastDB NiFi processors.

Owns the endpoint, credentials and TLS property descriptors that every processor
exposes, and turns them into a `vastdb` session.

VastDB authenticates with an access key and secret, so TLS here is one-way: the
endpoint's certificate is verified, and no client certificate is presented. Every
verification mode resolves to the `ssl_verify` argument of `vastdb.connect` - either a
boolean or the path to a PEM CA bundle - so no particular SDK version is required.
"""

import hashlib
import tempfile
from pathlib import Path

import vastdb
from nifiapi.properties import PropertyDependency, PropertyDescriptor, StandardValidators

AWS_CREDENTIALS_PROVIDER_SERVICE = (
    "org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderService"
)
SSL_CONTEXT_SERVICE = "org.apache.nifi.ssl.SSLContextService"

TLS_SYSTEM_CA = "System CA Certificates"
TLS_SSL_CONTEXT_SERVICE = "SSL Context Service"
TLS_CA_CERTIFICATE_FILE = "CA Certificate File"
TLS_NO_VERIFICATION = "No Verification"

KEYSTORE_TYPE_PKCS12 = "PKCS12"
KEYSTORE_TYPE_JKS = "JKS"


class VastDBConnection:
    """The endpoint, credentials and TLS properties shared by every VastDB processor.

    A processor creates one of these in its constructor, splices `descriptors` into the
    list it returns from `getPropertyDescriptors`, and calls `connect` to obtain a
    session.
    """

    def __init__(self):
        self.endpoint = PropertyDescriptor(
            name="VastDB Endpoint",
            description="AWS_S3_ENDPOINT_URL",
            required=True,
            default_value="http://vip-pool.v123-xy.VastENG.lab",
            validators=[StandardValidators.URL_VALIDATOR],
        )

        self.credentials_provider_service = PropertyDescriptor(
            name="VastDB Credentials Provider Service",
            description="The Controller Service that is used to obtain VastDB credentials.",
            required=True,
            controller_service_definition=AWS_CREDENTIALS_PROVIDER_SERVICE,
        )

        self.tls_verification = PropertyDescriptor(
            name="TLS Verification",
            description=(
                "How the VastDB endpoint's certificate is verified when the endpoint uses https.\n"
                f"'{TLS_SYSTEM_CA}' verifies against the CA certificates trusted by the host.\n"
                f"'{TLS_SSL_CONTEXT_SERVICE}' verifies against the truststore of an SSL Context Service.\n"
                f"'{TLS_CA_CERTIFICATE_FILE}' verifies against a PEM CA bundle on disk.\n"
                f"'{TLS_NO_VERIFICATION}' disables verification entirely and is not safe for production, "
                "because it accepts any certificate and so cannot detect an intercepted connection.\n"
                "This property is ignored for http endpoints."
            ),
            required=True,
            default_value=TLS_SYSTEM_CA,
            allowable_values=[
                TLS_SYSTEM_CA,
                TLS_SSL_CONTEXT_SERVICE,
                TLS_CA_CERTIFICATE_FILE,
                TLS_NO_VERIFICATION,
            ],
        )

        self.ssl_context_service = PropertyDescriptor(
            name="SSL Context Service",
            description=(
                "The Controller Service supplying the truststore used to verify the VastDB endpoint. "
                "Only the truststore is used: VastDB authenticates with an access key and secret, so "
                "a keystore configured on the service is not used as a client certificate."
            ),
            required=True,
            controller_service_definition=SSL_CONTEXT_SERVICE,
            dependencies=[PropertyDependency(self.tls_verification, TLS_SSL_CONTEXT_SERVICE)],
        )

        self.ca_certificate_file = PropertyDescriptor(
            name="CA Certificate File",
            description=(
                "Path to a PEM file holding the CA certificate(s) that signed the VastDB endpoint's "
                "certificate. The host's own CA certificates are not trusted in addition to these."
            ),
            required=True,
            validators=[StandardValidators.FILE_EXISTS_VALIDATOR],
            dependencies=[PropertyDependency(self.tls_verification, TLS_CA_CERTIFICATE_FILE)],
        )

        self.descriptors = [
            self.endpoint,
            self.credentials_provider_service,
            self.tls_verification,
            self.ssl_context_service,
            self.ca_certificate_file,
        ]

        self._cached_tls_fingerprint = None
        self._cached_tls_kwargs = None

    def connect(self, context, logger):
        """Open a VastDB session using the configured endpoint, credentials and TLS settings."""
        endpoint = context.getProperty(self.endpoint.name).getValue()
        credentials_provider_service = context.getProperty(self.credentials_provider_service.name).asControllerService()
        credentials = credentials_provider_service.getAwsCredentialsProvider().resolveCredentials()

        try:
            session = vastdb.connect(
                endpoint=endpoint,
                access=credentials.accessKeyId(),
                secret=credentials.secretAccessKey(),
                **self._tls_kwargs(context, endpoint, logger),
            )
            logger.info("Connected to VastDB")
        except Exception as e:
            error_message = f"Failed to connect to VastDB: {e}"
            raise RuntimeError(error_message) from e
        else:
            return session

    def _tls_kwargs(self, context, endpoint, logger):
        """Build the TLS keyword arguments for `vastdb.connect`.

        Reading and converting a truststore is not free, so the result is cached against a
        fingerprint of the configuration that produced it. The cached value is a plain
        `ssl_verify` setting, which is safe to share across concurrent tasks.
        """
        if not endpoint.lower().startswith("https"):
            return {}

        mode = context.getProperty(self.tls_verification.name).getValue()
        ca_certificate_file = context.getProperty(self.ca_certificate_file.name).getValue()

        ssl_context_service = None
        if mode == TLS_SSL_CONTEXT_SERVICE:
            ssl_context_service = context.getProperty(self.ssl_context_service.name).asControllerService()

        fingerprint = _fingerprint(
            mode,
            _file_fingerprint(ca_certificate_file),
            _ssl_context_service_fingerprint(ssl_context_service),
        )
        if fingerprint == self._cached_tls_fingerprint:
            return self._cached_tls_kwargs

        tls_kwargs = {"ssl_verify": _resolve_verify(mode, ssl_context_service, ca_certificate_file, logger)}

        self._cached_tls_fingerprint = fingerprint
        self._cached_tls_kwargs = tls_kwargs
        return tls_kwargs


def _resolve_verify(mode, ssl_context_service, ca_certificate_file, logger):
    """Return the `ssl_verify` value: False, True, or the path to a PEM CA bundle."""
    if mode == TLS_NO_VERIFICATION:
        return False

    if mode == TLS_CA_CERTIFICATE_FILE:
        return ca_certificate_file

    if mode == TLS_SSL_CONTEXT_SERVICE:
        if ssl_context_service.isKeyStoreConfigured():
            # Say so rather than failing: the service is still perfectly usable for its
            # truststore, but a user who configured a keystore may be expecting mutual TLS.
            # NiFi's logger exposes warn(), not warning() - G010 must not "fix" this.
            logger.warn(  # noqa: G010
                "The selected SSL Context Service has a keystore configured. It is not used: "
                "VastDB authenticates with an access key and secret, not a client certificate."
            )
        if not ssl_context_service.isTrustStoreConfigured():
            # Nothing to verify against, so fall back to the host's CA certificates.
            return True
        return _ca_bundle_file(_truststore_to_pem(ssl_context_service))

    return True


def _ca_bundle_file(cadata):
    """Write CA certificates to a PEM file, which is what `ssl_verify` accepts.

    The file is named after a digest of its contents, so repeated calls reuse one file per
    distinct truststore instead of accumulating temporary files. Only CA certificates are
    written - they are public, and no private key is ever involved.
    """
    directory = Path(tempfile.gettempdir()) / "vastdb-nifi-ca"
    directory.mkdir(exist_ok=True)
    pem_bytes = cadata.encode("ascii")
    path = directory / f"{hashlib.sha256(pem_bytes).hexdigest()}.pem"
    if not path.exists():
        path.write_bytes(pem_bytes)
    return str(path)


def _truststore_to_pem(ssl_context_service):
    """Convert an SSL Context Service truststore into PEM text."""
    certificates = _load_keystore_certificates(
        Path(ssl_context_service.getTrustStoreFile()).read_bytes(),
        _keystore_type(ssl_context_service.getTrustStoreType()),
        ssl_context_service.getTrustStorePassword(),
    )
    if not certificates:
        error_message = (
            f"No certificates found in the SSL Context Service truststore '{ssl_context_service.getTrustStoreFile()}'."
        )
        raise RuntimeError(error_message)

    from cryptography.hazmat.primitives.serialization import Encoding  # noqa: PLC0415

    return "".join(certificate.public_bytes(Encoding.PEM).decode("ascii") for certificate in certificates)


def _load_keystore_certificates(keystore_bytes, keystore_type, password):
    if keystore_type == KEYSTORE_TYPE_PKCS12:
        from cryptography.hazmat.primitives.serialization import pkcs12  # noqa: PLC0415

        _, certificate, additional = pkcs12.load_key_and_certificates(keystore_bytes, _password_bytes(password))
        certificates = list(additional or [])
        if certificate is not None:
            certificates.insert(0, certificate)
        return certificates

    import jks  # noqa: PLC0415
    from cryptography import x509  # noqa: PLC0415

    keystore = jks.KeyStore.loads(keystore_bytes, password)
    return [x509.load_der_x509_certificate(entry.cert) for entry in keystore.certs.values()]


def _keystore_type(keystore_type):
    normalized = (keystore_type or "").upper()
    if normalized in (KEYSTORE_TYPE_PKCS12, KEYSTORE_TYPE_JKS):
        return normalized
    error_message = (
        f"Unsupported SSL Context Service truststore type '{keystore_type}'. "
        f"Only {KEYSTORE_TYPE_PKCS12} and {KEYSTORE_TYPE_JKS} can be read from Python; "
        f"convert the truststore to {KEYSTORE_TYPE_PKCS12}, or use the "
        f"'{TLS_CA_CERTIFICATE_FILE}' verification mode with a PEM CA bundle."
    )
    raise RuntimeError(error_message)


def _password_bytes(password):
    return password.encode("utf-8") if password else None


def _ssl_context_service_fingerprint(ssl_context_service):
    """Summarise an SSL Context Service so configuration changes invalidate the cache."""
    if ssl_context_service is None:
        return None
    return (
        _file_fingerprint(ssl_context_service.getTrustStoreFile()),
        ssl_context_service.getTrustStoreType(),
        ssl_context_service.getTrustStorePassword(),
    )


def _file_fingerprint(path):
    """Digest a file's contents, so replacing a certificate invalidates the cached TLS setup."""
    if not path:
        return None
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        # Let the failure surface later, with the context of what was being loaded.
        return path


def _fingerprint(*values):
    """Hash the TLS configuration, so passwords are not retained in the cache key."""
    digest = hashlib.sha256()
    for value in values:
        digest.update(repr(value).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()
