## PutVastDB Processor

   * **Description:** Publishes Parquet or JSON data to a VastDB table.
   * **Properties:**
     * **VastDB Endpoint:** The URL of your VastDB endpoint.
     * **VastDB Credentials Provider Service:** An [AWSCredentialsProviderControllerService](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-aws-nar/2.0.0-M4/org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService/index.html) controller service that provides your VastDB credentials.
     * **TLS Verification:** How the VastDB endpoint's certificate is verified when the endpoint uses `https`: `System CA Certificates` (default), `CA Certificate File`, or `No Verification`. See [TLS](./TLS.md).
     * **CA Certificate File:** *(when **TLS Verification** is `CA Certificate File`)* Path to a PEM CA bundle that signed the VastDB endpoint's certificate.
     * **VastDB Bucket:** The VastDB bucket to write to.
     * **VastDB Database Schema:** The VastDB schema to write to.
     * **VastDB Table Name:** The VastDB table name to write to (or create).
     * **Data Type:**  The type of incoming data ("Parquet", "Json Array", or "Json Line Delimited").
       * If using Parquet, the incoming flowfile must represent a single Parquet file.
       * If using Json, the incoming flowfile must consist of multiple JSON objects, one per line, representing individual data rows.
         * PutVastDB will save all incoming json records in the flowfile as a batch.
         * Example Json, this file represents two rows of data with four columns “a”, “b”, “c”, “d”:

```json
{"a": 1, "b": 2.0, "c": "foo", "d": false}
{"a": 4, "b": -5.5, "c": null, "d": true}
```

   * **Max Input Size:** *(optional)* A data-size ceiling on the incoming FlowFile's content, e.g.
     `500 MB` or `2 GB`. Leave it empty to disable the check (the default).

### Guarding against large inputs

PutVastDB reads the **entire** FlowFile into memory (`getContentsAsBytes`) and decodes it into an
in-memory Arrow table before writing. A large enough FlowFile therefore exhausts the NiFi Python
process and gets it **OOM-killed** — an unrecoverable crash of the Python side, not a routed failure.
(The write itself is safe: the `vastdb` SDK already splits the insert into small RPCs, so the limit is
client-side memory, not a server limit.)

**Max Input Size** turns that crash into a routed FlowFile. When set, if the FlowFile's content size
exceeds the limit, the FlowFile is routed to **failure** with a `vastdb.error` attribute **before any
content is read** (the check uses the FlowFile's size metadata only — it never calls
`getContentsAsBytes`). It is deliberately **operator-set and not inferred**: the safe size depends on
the node's Python memory budget, its concurrency, and the format's decode expansion, none of which the
processor can reliably know. Note the value is compared against the **on-disk** size, which for Parquet
is much smaller than the decoded size — set it conservatively. Treat it as a safety tripwire, not a
precise memory gauge.

For **bulk loads**, don't rely on the guard — keep the large payload out of the Python process
entirely: split upstream (e.g. [SplitRecord](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-standard-nar/2.0.0-M4/org.apache.nifi.processors.standard.SplitRecord/index.html),
which streams on the JVM side and does not load the whole content into heap) so each FlowFile is a
bounded size, or use [ImportVastDB](./ImportVastDB.md), where VAST reads the Parquet **server-side** and
nothing is materialised in the Python process.

  **Note:**
   * Processors with *Record Writers* can use the [JsonRecordSetWriter](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-record-serialization-services-nar/2.0.0-M4/org.apache.nifi.json.JsonRecordSetWriter/index.html) that has the **Output Grouping** property set to **One Line Per Object** will create the FlowFile with the correct format.
