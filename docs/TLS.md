## TLS

Every VastDB processor — [DeleteVastDB](./DeleteVastDB.md), [DropVastDBTable](./DropVastDBTable.md),
[ImportVastDB](./ImportVastDB.md), [PutVastDB](./PutVastDB.md), [QueryVastDBTable](./QueryVastDBTable.md)
and [UpdateVastDB](./UpdateVastDB.md) — shares the same TLS properties.

They apply when **VastDB Endpoint** uses `https`. For an `http` endpoint they are ignored.

Verification depends only on operator-supplied trust material (a PEM CA bundle) or the host trust
store — it needs nothing installed into NiFi beyond the processors themselves, and works on any
supported NiFi/Python version.

### Properties

* **TLS Verification:** How the VastDB endpoint's certificate is verified. One of:
  * **System CA Certificates** *(default)* — verify against the CA certificates trusted by the host
    NiFi runs on. Correct when your VastDB certificate is signed by a public CA, or by an internal CA
    that has been added to the operating system trust store.
  * **CA Certificate File** — verify against a PEM CA bundle on disk. **Recommended for an internal
    or private CA:** the operator supplies a single PEM file and nothing needs to be installed into
    the host trust store.
  * **No Verification** — accept any certificate. See the warning below.
* **CA Certificate File:** *(shown when **TLS Verification** is `CA Certificate File`)* Path to a PEM file
  holding the CA certificate(s) that signed the VastDB endpoint's certificate. The host's own CA
  certificates are **not** trusted in addition to these.

> **No Verification** accepts any certificate presented by the endpoint, which means an intercepted
> connection cannot be distinguished from a genuine one. It is useful when first bringing up a cluster
> with a self-signed certificate; prefer **CA Certificate File** in production.

### Which option should I use?

| Situation | TLS Verification |
| --- | --- |
| VastDB certificate signed by a public CA | System CA Certificates |
| Internal CA already in the host trust store | System CA Certificates |
| Internal / private CA, certificate available as a PEM file | **CA Certificate File** |
| Self-signed certificate, non-production | No Verification |

The **CA Certificate File** path is the one PEM file that signed the endpoint's certificate. The same
file is used to verify every connection the processor makes — including ImportVastDB's read of its
Parquet source over S3 — so a private CA works without touching the host trust store.

### Handling of certificates

The **CA Certificate File** path is passed directly as the `ssl_verify` argument of `vastdb.connect`
(and as the `verify` argument to `requests` for ImportVastDB's Parquet-source read). Only CA
certificates are involved — they are public, and no private key is used at any point.

### Mutual TLS

Not supported, and not currently applicable: VastDB authenticates with an access key and secret
(SigV4), so it does not ask clients for a certificate.

If you put VastDB behind something that *does* demand a client certificate — a TLS-terminating proxy,
API gateway, or service mesh — this would need support for the `ssl_context` argument in the `vastdb`
SDK, which no released version provides. Please raise an issue describing the setup.

### Troubleshooting

| Message | Cause |
| --- | --- |
| `certificate verify failed: unable to get local issuer certificate` | The CA that signed the VastDB certificate is not in the configured trust material. Check the **CA Certificate File** path, or that the CA is in the host trust store for **System CA Certificates**. |
| `certificate verify failed: Hostname mismatch` | The certificate does not list the hostname/IP in **VastDB Endpoint**. Use a name or IP present in the certificate's Subject Alternative Name. |
