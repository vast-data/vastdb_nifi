# VastDB NiFi — TLS Verification: test, fixes, and results

Interop test of the **TLS Verification** modes (see [TLS.md](./TLS.md)) exercised against a live
VAST S3 + DATABASE endpoint secured with a **private CA**, across **all six** VastDB processors,
plus the fixes this change set makes so that a private-CA endpoint can be verified on any customer
NiFi/Python/OS — without disabling hostname verification.

> No credentials appear in this report; the test cluster was a throwaway.

## TL;DR

- **`CA Certificate File` is the recommended, environment-independent mode.** The operator supplies
  one PEM bundle; it is passed straight to `vastdb.connect(ssl_verify=<path>)` (pure-Python `ssl`) —
  no OS trust-store change, no keystore parsing, no native libraries, works on the oldest supported
  NiFi.
- After the fixes below, **all six processors pass in `CA Certificate File` and `No Verification`**,
  and **`System CA Certificates` is the correct negative** (a private CA is not in the host store).
- Three problems were found and addressed in this change set: an ImportVastDB TLS gap, an
  UpdateVastDB bug, and a fragile/redundant SSL Context Service mode.

## Environment

| | |
|---|---|
| VAST cluster | `release-5-5-0-sp1`, S3/DATABASE endpoint `https://<data-vip>:9091` |
| NiFi | `apache/nifi:2.0.0-M4` (single-user), Python 3.9 in-image |
| Processors | `vastdb_nifi` v1.3.0 (`org.apache.nifi:python-extensions:1.3.0`), linux-x86_64-py39 NAR |
| Server certificate | `CN=s3.nifi.test`, SAN includes the data-VIP IPs + DNS names, 2048-bit, EKU serverAuth |
| Signing CA | private 4096-bit root; installed via `PATCH /api/clusters/1/` (`s3_certificate` + `s3_private_key`) |

## Result matrix (verified end-to-end through the NiFi processors)

| Processor | CA Certificate File | No Verification | System CA (negative) |
|---|:--:|:--:|:--:|
| PutVastDB | ✅ PASS | ✅ PASS | ❌ FAIL (cert) |
| QueryVastDBTable | ✅ PASS | ✅ PASS | ❌ FAIL |
| UpdateVastDB | ✅ PASS *(fixed)* | ✅ PASS | ❌ FAIL |
| DeleteVastDB | ✅ PASS | ✅ PASS | ❌ FAIL |
| ImportVastDB | ✅ PASS *(fixed)* | ✅ PASS | ❌ FAIL |
| DropVastDBTable | ✅ PASS | ✅ PASS | ❌ FAIL |

Pass/fail is binary and taken from processor error bulletins (the full server responses),
corroborated with out-of-band `aws s3` / SDK checks. `System CA` fails because the private CA is not
in the container's OS trust store — the intended behaviour and correct negative control.

## What was broken, and the fix

### 1. ImportVastDB — Parquet schema read ignored TLS Verification *(fixed)*
`import_files()` is an SDK RPC (VAST reads the Parquet server-side over the verified session), but the
processor first read the Parquet **schema** client-side via pyarrow `S3FileSystem` to create the
table. pyarrow's `S3FileSystem` (v16) exposes no CA/verify option and only trusts the OS store, so a
private-CA endpoint failed with `curlCode 60` in **every** mode (including No Verification).

**Fix:** read the schema over `requests` (SigV4 via `aws_requests_auth`) with `verify=` set to the
resolved `ssl_verify`, so schema inference honours the processor's TLS Verification exactly like the
import RPC. The redundant schema read on the existing-table branch was removed.

### 2. UpdateVastDB — `$row_id` schema conflict *(fixed)*
Updates connect fine over TLS but failed with `TabularColumnNameConflict`: the schema-evolution step
tried to `add_column("$row_id")`, VAST's reserved internal column.

**Fix:** exclude `$row_id` from the columns considered for addition.

### 3. SSL Context Service — fragile and redundant *(removed)*
It resolved to the *same* `ssl_verify = <PEM path>` as `CA Certificate File`, but got there by parsing
a keystore with the bundled `cryptography` wheel, which requires **GLIBC_2.33** and fails to load on
`apache/nifi:2.0.0-M4`. It added no verification capability over CA File.

**Fix:** removed the mode. This eliminates the keystore-parsing code path — so `cryptography` is no
longer imported at runtime and the GLIBC failure cannot occur. (`cryptography`/`pyjks` remain declared
only because the test suite uses them to synthesise certificates; they are never imported at runtime.)

## Verification

- **End-to-end:** the matrix above was produced by building a NiFi flow (one source per processor,
  an AWS credentials controller service, real operations: create/write/query/update/delete/import/drop)
  and running every processor in each mode against the live endpoint.
- **Unit:** `hatch test` — 28 passed, including the real-TLS-server checks for `CA Certificate File`
  (trusted CA verifies, unrelated CA is rejected with `CERTIFICATE_VERIFY_FAILED`).
- **Import RPC over CA-File TLS** was additionally proven directly against the SDK
  (`vastdb.connect(ssl_verify=ca.pem)` + `table.import_files(...)`).

> CI should validate the full `hatch test` matrix (py39/310/311) and the platform NAR build; the
> runtime behaviour was verified on the live cluster with the linux-x86_64-py39 NAR.
