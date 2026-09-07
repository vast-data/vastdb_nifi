## TLS

Every VastDB processor — [DeleteVastDB](./DeleteVastDB.md), [DropVastDBTable](./DropVastDBTable.md),
[ImportVastDB](./ImportVastDB.md), [PutVastDB](./PutVastDB.md), [QueryVastDBTable](./QueryVastDBTable.md)
and [UpdateVastDB](./UpdateVastDB.md) — shares the same TLS properties.

They apply when **VastDB Endpoint** uses `https`. For an `http` endpoint they are ignored.

### Properties

* **TLS Verification:** How the VastDB endpoint's certificate is verified. One of:
  * **System CA Certificates** *(default)* — verify against the CA certificates trusted by the host
    NiFi runs on. Correct when your VastDB certificate is signed by a public CA, or by an internal CA
    that has been added to the operating system trust store.
  * **SSL Context Service** — verify against the truststore of a NiFi
    [SSLContextService](https://nifi.apache.org/components/org.apache.nifi.ssl.StandardSSLContextService/).
    Use this to reuse the TLS configuration you have already set up for other processors.
  * **CA Certificate File** — verify against a PEM CA bundle on disk.
  * **No Verification** — accept any certificate. See the warning below.
* **SSL Context Service:** *(shown when **TLS Verification** is `SSL Context Service`)* The controller
  service supplying the truststore. Only the truststore is used — see
  [Mutual TLS](#mutual-tls) below.
* **CA Certificate File:** *(shown when **TLS Verification** is `CA Certificate File`)* Path to a PEM file
  holding the CA certificate(s) that signed the VastDB endpoint's certificate. The host's own CA
  certificates are **not** trusted in addition to these.

> **No Verification** accepts any certificate presented by the endpoint, which means an intercepted
> connection cannot be distinguished from a genuine one. It is useful when first bringing up a cluster
> with a self-signed certificate; prefer **CA Certificate File** or **SSL Context Service** in production.

### Which option should I use?

| Situation | TLS Verification |
| --- | --- |
| VastDB certificate signed by a public CA | System CA Certificates |
| Internal CA already in the host trust store | System CA Certificates |
| You already have an SSLContextService configured in NiFi | SSL Context Service |
| You have the CA certificate as a PEM file | CA Certificate File |
| Self-signed certificate, non-production | No Verification |

### Using an SSL Context Service

Configure a
[StandardSSLContextService](https://nifi.apache.org/components/org.apache.nifi.ssl.StandardSSLContextService/)
(or `StandardRestrictedSSLContextService`) as you would for any other processor, then select it in the
**SSL Context Service** property.

Only the **truststore** is read; it verifies the VastDB endpoint. A keystore configured on the same
service is ignored, and the processor logs a warning saying so — see [Mutual TLS](#mutual-tls).

**Supported store types are `PKCS12` and `JKS`.** `BCFKS` cannot be read from Python; convert such a store
to `PKCS12`, or use the **CA Certificate File** mode instead. The processor tells you which of these
applies if it encounters an unsupported store.

The processors read the store files directly rather than using the service's Java `SSLContext`, because
that object cannot cross into the Python process. This means the NiFi node's Python process must be able
to read the keystore and truststore files — normally true, since it runs as the same user as NiFi.

#### Converting a BCFKS store to PKCS12

```bash
keytool -importkeystore \
  -srckeystore  truststore.bcfks -srcstoretype BCFKS \
  -destkeystore truststore.p12   -deststoretype PKCS12
```

### Handling of certificates

A truststore is read and converted to PEM in memory. The resulting CA bundle is written to a file under
the system temporary directory, named after a digest of its contents, because that is the form
`vastdb.connect` accepts. Only CA certificates are written — they are public, and no private key is
involved at any point.

### Mutual TLS

Not supported, and not currently applicable: VastDB authenticates with an access key and secret (SigV4),
so it does not ask clients for a certificate. A keystore configured on the selected SSL Context Service
is therefore ignored, and the processor logs a warning rather than failing, since the service is still
perfectly usable for its truststore.

If you put VastDB behind something that *does* demand a client certificate — a TLS-terminating proxy,
API gateway, or service mesh — this would need support for the `ssl_context` argument in the `vastdb`
SDK, which no released version provides. Please raise an issue describing the setup.

### Troubleshooting

| Message | Cause |
| --- | --- |
| `certificate verify failed: unable to get local issuer certificate` | The CA that signed the VastDB certificate is not in the configured trust material. Check the truststore or CA bundle. |
| `certificate verify failed: Hostname mismatch` | The certificate does not list the hostname in **VastDB Endpoint**. Use the name in the certificate's Subject Alternative Name. |
| `Unsupported SSL Context Service truststore type 'BCFKS'` | Convert the store to `PKCS12`, or use **CA Certificate File**. |
| `No certificates found in the SSL Context Service truststore` | The truststore password is wrong, or the store holds no trusted certificate entries. |
| `The selected SSL Context Service has a keystore configured. It is not used` | Expected — see [Mutual TLS](#mutual-tls). Verification against the truststore is unaffected. |
