# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""Shared VastDB connection handling for the VastDB NiFi processors.

Owns the endpoint, credentials and TLS property descriptors that every processor
exposes, and turns them into a `vastdb` session.

VastDB authenticates with an access key and secret, so TLS here is one-way: the
endpoint's certificate is verified, and no client certificate is presented. Every
verification mode resolves to the `ssl_verify` argument of `vastdb.connect` - either a
boolean or the path to a PEM CA bundle - so no particular SDK version is required, and
verification depends only on operator-supplied material (a PEM file) rather than on the
host OS trust store or any native library.
"""

import vastdb
from nifiapi.properties import (
    PropertyDependency,
    PropertyDescriptor,
    StandardValidators,
)

AWS_CREDENTIALS_PROVIDER_SERVICE = (
    "org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderService"
)

TLS_SYSTEM_CA = "System CA Certificates"
TLS_CA_CERTIFICATE_FILE = "CA Certificate File"
TLS_NO_VERIFICATION = "No Verification"


class VastDBConnection:
    """The endpoint, credentials and TLS properties shared by every VastDB processor.

    A processor creates one of these in its constructor, splices `descriptors` into the
    list it returns from `getPropertyDescriptors`, and calls `connect` to obtain a
    session. `resolve_ssl_verify` exposes the same verification setting so a processor
    that opens its own connection (e.g. ImportVastDB reading a Parquet source over S3)
    verifies exactly the way the database connection does.
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
                f"'{TLS_CA_CERTIFICATE_FILE}' verifies against a PEM CA bundle on disk - the "
                "recommended option for an internal/private CA, since it needs nothing from the "
                "host OS trust store.\n"
                f"'{TLS_SYSTEM_CA}' verifies against the CA certificates trusted by the host - use "
                "this when the endpoint's CA is public, or already installed in the host trust store.\n"
                f"'{TLS_NO_VERIFICATION}' disables verification entirely and is not safe for production, "
                "because it accepts any certificate and so cannot detect an intercepted connection.\n"
                "This property is ignored for http endpoints."
            ),
            required=True,
            default_value=TLS_SYSTEM_CA,
            allowable_values=[
                TLS_SYSTEM_CA,
                TLS_CA_CERTIFICATE_FILE,
                TLS_NO_VERIFICATION,
            ],
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
            self.ca_certificate_file,
        ]

    def connect(self, context, logger):
        """Open a VastDB session using the configured endpoint, credentials and TLS settings."""
        endpoint = context.getProperty(self.endpoint.name).getValue()
        credentials_provider_service = context.getProperty(self.credentials_provider_service.name).asControllerService()
        credentials = credentials_provider_service.getAwsCredentialsProvider().resolveCredentials()

        tls_kwargs = {}
        if endpoint.lower().startswith("https"):
            tls_kwargs["ssl_verify"] = self.resolve_ssl_verify(context)

        try:
            session = vastdb.connect(
                endpoint=endpoint,
                access=credentials.accessKeyId(),
                secret=credentials.secretAccessKey(),
                **tls_kwargs,
            )
            logger.info("Connected to VastDB")
        except Exception as e:
            error_message = f"Failed to connect to VastDB: {e}"
            raise RuntimeError(error_message) from e
        else:
            return session

    def resolve_ssl_verify(self, context):
        """Return the `ssl_verify` value for the configured mode: False, True, or a PEM CA path.

        This is what `vastdb.connect` accepts, and it is equally valid as the `verify` argument to
        `requests`/`urllib3`, so a processor that must read directly over S3 (rather than through
        the VastDB RPC) can verify the endpoint with the same operator-supplied trust material.
        """
        mode = context.getProperty(self.tls_verification.name).getValue()
        if mode == TLS_NO_VERIFICATION:
            return False
        if mode == TLS_CA_CERTIFICATE_FILE:
            return context.getProperty(self.ca_certificate_file.name).getValue()
        return True  # System CA Certificates
