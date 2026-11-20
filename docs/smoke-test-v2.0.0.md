# VastDB NiFi — v2.0.0 release smoke test (vastdb SDK 2.4.0) on a live cluster

Smoke test of the **v2.0.0 release NAR** (first release built on the **vastdb 2.4.0** SDK and **pyarrow 23**,
Python 3.9 dropped) against a real VAST cluster, through NiFi itself: every FlowFile went through the released
Python processors inside `apache/nifi:2.12.0`, not through the SDK directly. The repo's unit tests stub NiFi and
never talk to a database, so this is the first time the 2.4.0 wire behaviour has been exercised end-to-end.

> No credentials appear in this report; the cluster and bucket were throwaway lab resources.

## TL;DR

- **5 of 6 processors PASS** on `release-5-5-0-sp6`: PutVastDB (JSON and Parquet, table auto-create, column
  add on both paths), QueryVastDBTable (with and without `Data Endpoints`, YAML predicates, `$row_id`),
  UpdateVastDB, DeleteVastDB and DropVastDBTable all behave exactly as on v1.3.x.
- **ImportVastDB FAILS** whenever the target table does not exist yet: the schema-inference step reads
  `tx._rpc.api.url`, a private SDK attribute that **no longer exists in vastdb 2.4.0**
  (`AttributeError: 'VastdbApi' object has no attribute 'url'`). Import into an **existing** table passes, so
  the import RPC itself is fine; only the "create table from the Parquet schema" path is broken. This is a
  regression introduced by the SDK bump, not caught by the unit tests because they stub the SDK session.
- The NAR loads cleanly: all six processors discovered at startup, zero `ERROR` lines in `nifi-app.log` until the
  first FlowFile, no dependency or GLIBC problems on the Debian 12 / Python 3.11 image.

## Environment

| | |
|---|---|
| VAST cluster | `release-5-5-0-sp6-2750428` (sw `5.5.0.1`), devvm loopback cluster `loop1141724-oo`, 2 data VIPs |
| Endpoint under test | `http://<data-vip-1>:9090` (plain HTTP; TLS modes were covered in [tls-test-report.md](./tls-test-report.md) and are not re-tested here) |
| `Data Endpoints` | `http://<data-vip-1>:9090,http://<data-vip-2>:9090` |
| NiFi | `apache/nifi:2.12.0` (image `sha256:a0b4fe3a…`), single-user mode, Debian 12, OpenJDK 21.0.12.1, **Python 3.11.2** in-image, `nifi.python.command=python3` |
| NAR | `vastdb_nifi-2.0.0-linux-x86_64-py311.nar` from the [v2.0.0 release](https://github.com/vast-data/vastdb_nifi/releases/tag/v2.0.0), sha256 `f83e36b8…14f0d1` (matches the release asset digest), dropped in `nar_extensions/` (the autoload directory) |
| Processor bundle as seen by NiFi | `org.apache.nifi:python-extensions:2.0.0` for all six processors |
| Bundled deps (from `NAR-INF/bundled-dependencies`) | vastdb 2.4.0, pyarrow 23.0.1, pandas 2.2.2, numpy 2.4.6, ibis-framework 12.0.0, requests 2.34.2, aws-requests-auth 0.4.3, cryptography 50.0.1, pyjks 20.0.0 |
| Bucket / schema | S3+DATABASE view `nifi-smoke` (policy `s3_default_policy`), schema `smoke_v200`; the S3 user is an `s3_superuser` with an access/secret key in an `AWSCredentialsProviderControllerService` |
| Driver | NiFi REST API from the devvm host: one process group per step, `GenerateFlowFile`/`FetchFile` as the source, the processor under test, and one stopped `LogAttribute` sink per relationship so the script can read what each processor emitted |

## Startup: do the six processors load?

`nifi-app.log` at container start (13:12 UTC):

```
NarClassLoaders Loaded NAR file: …/work/nar/extensions/vastdb_nifi-2.0.0-linux-x86_64-py311.nar-unpacked …
StandardExtensionDiscoveringManager Discovered Python Processor DeleteVastDB
StandardExtensionDiscoveringManager Discovered Python Processor DropVastDBTable
StandardExtensionDiscoveringManager Discovered Python Processor ImportVastDB
StandardExtensionDiscoveringManager Discovered Python Processor PutVastDB
StandardExtensionDiscoveringManager Discovered Python Processor QueryVastDBTable
StandardExtensionDiscoveringManager Discovered Python Processor UpdateVastDB
StandardExtensionDiscoveringManager Discovered or updated 6 Python Processors in 170 millis
```

Zero `ERROR` lines before the first FlowFile. The first `PutVastDB` instance launched its Python process and
reported `Loaded module PutVastDB` / `Successfully loaded Python Processor` 3 s after creation; every later
instance validated in 0–2 s. One benign `WARN` (`StandardNarLoader Found existing bundle with coordinate
vastdb-nifi:vastdb-nifi-nar:2.0.0, will not load …`) is NiFi's autoloader noticing the NAR it already loaded at
boot.

## Result matrix (verified end-to-end through the NiFi processors)

| Processor | Verdict | Notes |
|---|:--:|---|
| PutVastDB | ✅ PASS | JSON lines → table auto-created (schema `smoke_v200` auto-created too); second JSON write added column `region`; Parquet write into the same table; second Parquet write added `ts` (timestamp[us]) and `flag` (bool). All rows read back with correct nulls in rows that predate each column. |
| QueryVastDBTable | ✅ PASS | YAML predicates `>=`, `>`, `==`, `isin`, `and`; `Columns` list; `Return internal row ID` gives `$row_id`; identical 10-row result with `Data Endpoints` empty and with both VIPs listed (`QueryConfig(data_endpoints=[…])`); correct `MissingTable` failure after the drop. |
| UpdateVastDB | ✅ PASS | Fed by QueryVastDBTable output (rows carrying `$row_id`); `status` changed on 2 rows, verified by a follow-up query. |
| DeleteVastDB | ✅ PASS | Fed by QueryVastDBTable output (rows carrying `$row_id`); 2 rows deleted, verified by a follow-up query (10 → 8 rows). |
| ImportVastDB | ❌ FAIL | **New-table path fails** with `AttributeError: 'VastdbApi' object has no attribute 'url'` in `_read_parquet_schema`; the FlowFile is routed to `failure`, no table is created. Import into an *existing* table (seeded with PutVastDB) **passes** and the 4 Parquet rows read back. |
| DropVastDBTable | ✅ PASS | Dropped `orders`, `imported2`; a drop of a never-created table (`imported`) routes to `success` with "not found, skipping", as designed. |

Pass/fail is binary and taken from which relationship the FlowFile left on, plus the processor's bulletins,
corroborated by the next QueryVastDBTable step reading the data back.

## What was run (in order, each step its own process group)

| # | Step | Processor | Input | Result |
|--:|---|---|---|---|
| 1 | put-json-create | PutVastDB (`Json Line Delimited`) | 3 rows `id,name,qty,price,status` | PASS — schema and table created |
| 2 | put-json-addcol | PutVastDB (`Json Line Delimited`) | 2 rows with extra `region` | PASS — `add_column(region)` |
| 3 | put-parquet | PutVastDB (`Parquet`) | 3 rows, same 5 columns | PASS |
| 4 | put-parquet-addcol | PutVastDB (`Parquet`) | 2 rows with extra `ts`, `flag` | PASS — two `add_column` calls |
| 5 | query-all | QueryVastDBTable, no `Data Endpoints` | `id >= 0` (int64) | PASS — 10 rows; `region`/`ts`/`flag` populated only where written |
| 6 | query-data-endpoints | QueryVastDBTable, `Data Endpoints` = both VIPs | same | PASS — same 10 rows |
| 7 | query-predicate | QueryVastDBTable | `qty > 20` and `status == new` (utf8) | PASS — the expected 7 ids |
| 8 | query-rowid | QueryVastDBTable, `Return internal row ID = True` | `id isin [2, 102]` | PASS — `$row_id` 1 and 6 |
| 9 | update | Query(rowid) → ReplaceText ×3 → UpdateVastDB (`Json`) | 2 rows, `status` → `updated` | PASS |
| 10 | query-after-update | QueryVastDBTable | `id isin [2, 102]` | PASS — both `updated` |
| 11 | delete | Query(rowid) → ReplaceText ×2 → DeleteVastDB (`Json`) | rows `id isin [3, 103]` | PASS |
| 12 | query-after-delete | QueryVastDBTable | `id >= 0` | PASS — 8 rows, 3 and 103 gone |
| 13 | import | ImportVastDB (`Schema Merge = Union`) into **new** table `imported` | `[{"key":"in/import1.parquet","bucket":"nifi-smoke"}]` | **FAIL** — see below |
| 14 | query-imported | QueryVastDBTable on `imported` | `id >= 0` | FAIL — `MissingTable` (consequence of 13) |
| 15 | drop-orders | DropVastDBTable | — | PASS |
| 16 | drop-imported | DropVastDBTable (table never existed) | — | PASS — "not found, skipping" |
| 17 | query-after-drop | QueryVastDBTable on `orders` (negative) | `id >= 0` | PASS — routed to `failure` with `vastdb.errors.MissingTable` |
| 18 | put-seed-for-import | PutVastDB (`Json Line Delimited`) into `imported2` | 1 row `id,name,score` | PASS |
| 19 | import-existing-table | ImportVastDB into **existing** `imported2` | same Parquet object | **PASS** |
| 20 | query-imported2 | QueryVastDBTable on `imported2` | `id >= 0` | PASS — 5 rows (4 imported + 1 seeded) |
| 21 | drop-imported2 | DropVastDBTable | — | PASS |

The ReplaceText processors in steps 9 and 11 only reshape QueryVastDBTable's JSON array into the one-object-per-line
form the write processors read; they are NiFi standard processors, not part of this NAR.

## The failure: ImportVastDB on a table that does not exist yet

Processor bulletin (identical text in `nifi-app.log`, `ERROR … FlowFileTransformProxy PythonProcessor[type=ImportVastDB …] Failed to transform …`):

```
py4j.Py4JException: An exception was raised by the Python Proxy. Return Message: Traceback (most recent call last):
  File ".../ImportVastDB.py", line 95, in transform
    self.import_tables(context, session, parquet_file_list)
  File ".../ImportVastDB.py", line 121, in import_tables
    table = self.create_table_from_files(context, schema, vastdb_table, parquet_file_list)
  File ".../ImportVastDB.py", line 146, in create_table_from_files
    file_schema = self._read_parquet_schema(context, tx, prq_file)
  File ".../ImportVastDB.py", line 166, in _read_parquet_schema
    endpoint = tx._rpc.api.url.rstrip("/")
               ^^^^^^^^^^^^^^^
AttributeError: 'VastdbApi' object has no attribute 'url'
```

**Where it comes from.** `ImportVastDB._read_parquet_schema` (added by the TLS fix in v1.3.0 so schema
inference honours `TLS Verification`) fetches the source Parquet over S3 with `requests` and signs it with
`aws_requests_auth`. It gets the endpoint and keys from the SDK's private session object:
`tx._rpc.api.url`, `tx._rpc.api.access_key`, `tx._rpc.api.secret_key`. In vastdb 1.3.1 `VastdbApi` had a `url`
attribute. In vastdb 2.4.0 the session (`vastdb.session.Session`) keeps a *list* of endpoints on
`VastdbApi.endpoints` and the configured base endpoint on `Session._context.endpoint`; `VastdbApi.url` is gone
(`access_key`/`secret_key` still exist). The processor therefore raises before `schema.create_table` and before
`table.import_files`, and the FlowFile is routed to `failure`.

**Impact.** Every ImportVastDB flow that relies on table auto-creation fails on v2.0.0, for every TLS mode, on every
cluster. Flows that import into a table created beforehand (by PutVastDB, by an earlier import, or out of band)
are unaffected; `Table.import_files(files)` itself works on 2.4.0 (step 19).

**Suggested fix.** The processor already knows the endpoint (its own `VastDB Endpoint` property) and the
credentials (the resolved `AWSCredentialsProvider`), so `_read_parquet_schema` should take them from the
processor context rather than from SDK internals; that also removes the last dependency on private SDK
attributes. A unit test that drives `_read_parquet_schema` with a real `vastdb.Session` object (not a stub) would
have caught the attribute change at the SDK bump.

## Observations that are not failures

- QueryVastDBTable serialises timestamps as epoch integers (`"ts": 1795176000` for `2026-11-20T12:00:00`), the
  pandas `to_json` default; unchanged from v1.3.x.
- The only other `ERROR`/`WARN` lines in `nifi-app.log` were the expected `MissingTable` failures (steps 14 and
  17), their `vastdb.transaction rolling back txid=…` companions, and a harness mistake (`GetFile` refuses a
  read-only directory even with `Keep Source File`; the driver was switched to `FetchFile`).

## Not covered

TLS modes (`System CA` / `CA Certificate File` / `No Verification`) were not re-run — the endpoint under test is
plain HTTP; `Flatten Nested Json`, `Max Input Size`, `Schema Merge = Strict|Child`, the `Json Array` data type, the
`darwin-arm64` NARs and the `py310`/`py312` Linux NARs were not exercised.

## Verification artefacts

- The REST driver (`smoke.py`, `smoke_extra.py`), its per-step JSON results (FlowFile contents, attributes,
  bulletins, matching `nifi-app.log` blocks) and `nifi-app.log` are on the devvm under `~/nifi-smoke/`
  (`results/20261120T132332Z.*` for steps 1–17, `results/20261120T132743Z.*` for 18–21). The NiFi canvas with all
  21 process groups was left running in container `nifi-smoke` (port 8444 on the devvm) for inspection.
- Left behind on the cluster: view/bucket `nifi-smoke` (empty schema `smoke_v200`, object
  `in/import1.parquet`); drop them when the devvm is no longer needed.

## Follow-ups

1. **Fix `ImportVastDB._read_parquet_schema` for vastdb ≥ 2.x** (endpoint and keys from the processor context, or
   at least `tx._rpc._context.endpoint` / `tx._rpc.access` / `tx._rpc.secret`) and release a `v2.0.1`; v2.0.0
   should be flagged in the release notes as "ImportVastDB cannot create tables".
2. Add a live-cluster integration test (this driver is a reasonable seed) to CI or to the release checklist, so
   SDK bumps are exercised through NiFi before a NAR is published.
3. Re-run the TLS matrix from [tls-test-report.md](./tls-test-report.md) once on 2.4.0, since `_read_parquet_schema`
   is also the TLS-sensitive path in ImportVastDB.

## Re-test with the ImportVastDB fix (#18)

Same cluster, NiFi image, bucket and schema. The v2.0.0 NAR was replaced by the Build artifact from the fix
branch (`vastdb_nifi-0.1.dev1+g200a2726a-linux-x86_64-py311.nar`, commit `200a272`, the commit merged in #18),
and the container restarted. NiFi discovered all six processors from the new bundle with zero `ERROR` lines.

| Step | Processor | Result |
|---|---|:--:|
| Import into a table that does not exist yet (`Schema Merge = Union`) | ImportVastDB | ✅ PASS - routed to `success`, no bulletins |
| Query the new table | QueryVastDBTable | ✅ PASS - the 4 imported rows |
| Seed a second table with one row | PutVastDB | ✅ PASS |
| Import into that existing table | ImportVastDB | ✅ PASS |
| Query the existing table | QueryVastDBTable | ✅ PASS - 5 rows (4 imported + 1 seeded) |
| Drop both tables | DropVastDBTable | ✅ PASS |

With the fix, all six processors pass end-to-end on the vastdb 2.4.0 build. The fix ships in v2.0.1.
