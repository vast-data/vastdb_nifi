## UpdateVastDB Processor

* **Description:**  Publishes Parquet or JSON data to a VastDB table, existing rows based on the data provided in the FlowFile.  The table is created if it doesn't already exist.

* **Properties:**
   * **VastDB Endpoint:** The URL of your VastDB endpoint.
   * **VastDB Credentials Provider Service:** An [AWSCredentialsProviderControllerService](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-aws-nar/2.0.0-M4/org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService/index.html) controller service that provides your VastDB credentials.
   * **TLS Verification:** How the VastDB endpoint's certificate is verified when the endpoint uses `https`: `System CA Certificates` (default), `CA Certificate File`, or `No Verification`. See [TLS](./TLS.md).
   * **CA Certificate File:** *(when **TLS Verification** is `CA Certificate File`)* Path to a PEM CA bundle that signed the VastDB endpoint's certificate.
   * **VastDB Bucket:** The VastDB bucket to write to.
   * **VastDB Database Schema:** The VastDB schema to write to.
   * **VastDB Table Name:** The VastDB table name to write to (or create).
   * **Data Type:**  The type of incoming data ("Parquet" or "Json").  If using Json, the incoming data must consist of multiple JSON objects, one per line, representing individual data rows. For example, this file represents two rows of data with four columns “a”, “b”, “c”, “d”:

```json
{"a": 1, "b": 2.0, "c": "foo", "d": false, "$row_id": 12345}
{"a": 4, "b": -5.5, "c": null, "d": true, "$row_id": 23456}
```

   * **Max Input Size:** *(optional)* A data-size ceiling on the incoming FlowFile's content, e.g.
     `500 MB` or `2 GB`. Leave it empty to disable the check (the default).

### Guarding against large inputs

UpdateVastDB reads the **entire** FlowFile into memory (`getContentsAsBytes`) and decodes it into an
in-memory Arrow table before writing, so a large enough FlowFile can exhaust the NiFi Python process and
get it **OOM-killed** — an unrecoverable crash rather than a routed failure. When **Max Input Size** is
set, a FlowFile whose content exceeds it is routed to **failure** with a `vastdb.error` attribute
**before any content is read** (the check uses the FlowFile's size metadata only). It is deliberately
**operator-set and not inferred** — the safe size depends on the node's Python memory budget, its
concurrency, and the format's decode expansion — and it is compared against the **on-disk** size (for
Parquet much smaller than the decoded size), so set it conservatively; treat it as a safety tripwire,
not a precise memory gauge. For large updates, split the input upstream (e.g.
[SplitRecord](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-standard-nar/2.0.0-M4/org.apache.nifi.processors.standard.SplitRecord/index.html))
so each FlowFile is a bounded size.

* **Note:** Processors with *Record Writers* can use the [JsonRecordSetWriter](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-record-serialization-services-nar/2.0.0-M4/org.apache.nifi.json.JsonRecordSetWriter/index.html) that has the **Output Grouping** property set to **One Line Per Object** will create the FlowFile with the correct format. 
