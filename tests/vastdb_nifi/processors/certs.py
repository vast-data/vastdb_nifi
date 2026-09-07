# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""Throwaway PKI for the TLS tests: a CA and a server certificate.

Everything is generated in-process, so the tests never depend on checked-in key material.
"""

import datetime
import ipaddress

import jks
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

# Deliberately small: these keys exist for the duration of a test run only, and 2048-bit
# generation noticeably slows the suite down.
KEY_SIZE = 2048
VALIDITY = datetime.timedelta(days=1)


class Certificate:
    def __init__(self, certificate, private_key):
        self.certificate = certificate
        self.private_key = private_key

    def certificate_pem(self):
        return self.certificate.public_bytes(serialization.Encoding.PEM)

    def private_key_pem(self):
        return self.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _builder(subject, issuer, public_key):
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(_now() - VALIDITY)
        .not_valid_after(_now() + VALIDITY)
    )


def _name(common_name):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def create_ca(common_name="VastDB Test CA"):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=KEY_SIZE)
    subject = _name(common_name)
    certificate = (
        _builder(subject, subject, private_key.public_key())
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    return Certificate(certificate, private_key)


def issue(ca, common_name, *, hostname=None):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=KEY_SIZE)
    builder = _builder(_name(common_name), ca.certificate.subject, private_key.public_key()).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True
    )
    if hostname:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(hostname), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
    certificate = builder.sign(ca.private_key, hashes.SHA256())
    return Certificate(certificate, private_key)


def write_pkcs12_truststore(path, certificates, password):
    """Write a PKCS12 file holding only trusted certificates, as NiFi truststores do."""
    path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            name=b"truststore",
            key=None,
            cert=None,
            cas=[certificate.certificate for certificate in certificates],
            encryption_algorithm=_encryption(password),
        )
    )


def write_jks_truststore(path, certificates, password):
    entries = [
        jks.TrustedCertEntry.new(f"ca-{index}", certificate.certificate.public_bytes(serialization.Encoding.DER))
        for index, certificate in enumerate(certificates)
    ]
    jks.KeyStore.new("jks", entries).save(str(path), password)


def _encryption(password):
    return serialization.BestAvailableEncryption(password.encode("utf-8")) if password else serialization.NoEncryption()
