# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""Tests for ImportVastDB's new-table path: Parquet schema inference over the S3 endpoint.

When the target table does not exist, ImportVastDB fetches each source Parquet object itself
(so the read honours the TLS Verification setting) and builds the table from the merged
schemas. The endpoint and credentials for that fetch must come from the processor's own
properties: an earlier version read them from the SDK session's private attributes, which
vastdb 2.x removed, so every import that had to create its table failed with AttributeError.
These tests drive the path against a local server with no SDK session involved at all.

The processor modules import their siblings as flat top-level modules (e.g.
`from vastdb_session import ...`), mirroring how they are laid out at runtime, so the
processors directory is placed on the path before importing.
"""

# `_read_parquet_schema` is the unit under test; calling it directly is the point.
# ruff: noqa: SLF001

import http.server
import io
import ssl
import sys
import threading
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import requests

_PROCESSORS_DIR = Path(__file__).resolve().parents[3] / "src" / "vastdb_nifi" / "processors"
if str(_PROCESSORS_DIR) not in sys.path:
    sys.path.insert(0, str(_PROCESSORS_DIR))

from ImportVastDB import ImportVastDB  # noqa: E402
from vastdb_session import TLS_CA_CERTIFICATE_FILE, TLS_SYSTEM_CA  # noqa: E402

from . import certs  # noqa: E402
from .conftest import FAKE_ACCESS_KEY, FakeCredentialsProviderService, FakeProcessContext  # noqa: E402

ORDERS = pa.table({"id": pa.array([1, 2], pa.int64()), "name": pa.array(["a", "b"], pa.string())})
EXTRA = pa.table({"id": pa.array([3], pa.int64()), "qty": pa.array([7], pa.int32())})


def parquet_bytes(table: pa.Table) -> bytes:
    buffer = io.BytesIO()
    pq.write_table(table, buffer)
    return buffer.getvalue()


class _S3Server:
    """A local server that serves Parquet objects by path and records every request's headers."""

    def __init__(self, objects, tls=None):
        self.objects = objects
        self.requests = []
        self.url = None
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                server.requests.append((self.path, dict(self.headers)))
                body = server.objects.get(self.path)
                if body is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self._server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self._scheme = "http"
        if tls is not None:
            server_certificate, tmp_path = tls
            certificate_file = tmp_path / "server.pem"
            certificate_file.write_bytes(server_certificate.private_key_pem() + server_certificate.certificate_pem())
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(str(certificate_file))
            self._server.socket = ssl_context.wrap_socket(self._server.socket, server_side=True)
            self._scheme = "https"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self):
        self._thread.start()
        self.url = f"{self._scheme}://localhost:{self._server.server_address[1]}"
        return self

    def __exit__(self, *args):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


class FakeSchema:
    """The part of a vastdb Schema that create_table_from_files needs: a name and create_table.

    Deliberately has no `tx` attribute: the new-table path must not need the SDK transaction.
    """

    name = "smoke"

    def __init__(self):
        self.created = None

    def create_table(self, name, arrow_schema):
        self.created = (name, arrow_schema)
        return f"table:{name}"


@pytest.fixture(scope="module")
def ca():
    return certs.create_ca()


@pytest.fixture(scope="module")
def server_certificate(ca):
    return certs.issue(ca, "localhost", hostname="localhost")


@pytest.fixture
def processor(logger):
    processor = ImportVastDB()
    processor.logger = logger  # injected by NiFi at runtime
    return processor


def make_context(processor, endpoint, **extra):
    properties = {
        processor.connection.endpoint.name: endpoint,
        processor.connection.credentials_provider_service.name: FakeCredentialsProviderService(),
        processor.connection.tls_verification.name: TLS_SYSTEM_CA,
        processor.schema_merge_function.name: "Union",
    }
    properties.update(extra)
    return FakeProcessContext(properties)


def test_schema_is_read_over_the_processors_own_endpoint_and_credentials(processor):
    with _S3Server({"/bucket/in/orders.parquet": parquet_bytes(ORDERS)}) as server:
        # A trailing slash on the configured endpoint must not produce a double slash in the URL.
        context = make_context(processor, server.url + "/")
        schema = processor._read_parquet_schema(context, "/bucket/in/orders.parquet")

    assert schema.names == ["id", "name"]
    assert schema.types == [pa.int64(), pa.string()]
    ((path, headers),) = server.requests
    assert path == "/bucket/in/orders.parquet"
    # Signed with the credentials from the controller service, SigV4 style.
    assert headers["Authorization"].startswith(f"AWS4-HMAC-SHA256 Credential={FAKE_ACCESS_KEY}/")


def test_new_table_schema_is_inferred_without_touching_the_sdk_session(processor):
    objects = {"/bucket/a.parquet": parquet_bytes(ORDERS), "/bucket/b.parquet": parquet_bytes(EXTRA)}
    fake_schema = FakeSchema()

    with _S3Server(objects) as server:
        context = make_context(processor, server.url)
        table = processor.create_table_from_files(context, fake_schema, "orders", list(objects))

    assert table == "table:orders"
    name, arrow_schema = fake_schema.created
    assert name == "orders"
    assert arrow_schema.names == ["id", "name", "qty"]  # Union merge of both files
    assert [path for path, _ in server.requests] == ["/bucket/a.parquet", "/bucket/b.parquet"]


def test_schema_read_verifies_https_with_the_ca_certificate_file(processor, tmp_path, ca, server_certificate):
    ca_file = tmp_path / "ca.pem"
    ca_file.write_bytes(ca.certificate_pem())

    with _S3Server({"/bucket/a.parquet": parquet_bytes(ORDERS)}, tls=(server_certificate, tmp_path)) as server:
        context = make_context(
            processor,
            server.url,
            **{
                processor.connection.tls_verification.name: TLS_CA_CERTIFICATE_FILE,
                processor.connection.ca_certificate_file.name: str(ca_file),
            },
        )
        schema = processor._read_parquet_schema(context, "/bucket/a.parquet")

    assert schema.names == ["id", "name"]


def test_schema_read_rejects_a_private_ca_under_system_ca_mode(processor, tmp_path, server_certificate):
    with (
        _S3Server({"/bucket/a.parquet": parquet_bytes(ORDERS)}, tls=(server_certificate, tmp_path)) as server,
        pytest.raises(requests.exceptions.SSLError),
    ):
        processor._read_parquet_schema(make_context(processor, server.url), "/bucket/a.parquet")


def test_processors_do_not_read_private_sdk_session_state():
    # vastdb 2.x removed `VastdbApi.url`, which an earlier ImportVastDB reached via `tx._rpc.api`.
    # The SDK's private attributes are not a stable surface, so no processor may depend on them.
    offenders = sorted(path.name for path in _PROCESSORS_DIR.glob("*.py") if "._rpc" in path.read_text())
    assert offenders == []
