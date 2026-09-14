## DeleteVastDB Processor

**Description**

The `DeleteVastDB` processor facilitates the deletion of rows from a VastDB table. It accepts incoming data in either Parquet or JSON format and uses the row information to identify and delete corresponding rows within the specified VastDB table.

**Properties**

* **VastDB Endpoint:** The URL of your VastDB endpoint.  (Example: http://vip-pool.v123-xy.VastENG.lab)
* **VastDB Credentials Provider Service:** A controller service that securely provides your VastDB credentials. It must be an instance of `org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderService`.
* **TLS Verification:** How the VastDB endpoint's certificate is verified when the endpoint uses `https`: `System CA Certificates` (default), `CA Certificate File`, or `No Verification`. See [TLS](./TLS.md).
* **CA Certificate File:** *(when **TLS Verification** is `CA Certificate File`)* Path to a PEM CA bundle that signed the VastDB endpoint's certificate.
* **VastDB Bucket:** The name of the VastDB bucket where your table resides.
* **VastDB Database Schema:** The name of the VastDB schema containing the target table.
* **VastDB Table Name:** The name of the table from which rows will be deleted.
* **Data Type:** Specifies the format of the incoming data. It can be either "Parquet" or "Json".  If "Json" is selected, ensure each data row is on a separate line and terminated with a newline character.
* **Max Input Size:** *(optional)* A data-size ceiling on the incoming FlowFile's content, e.g. `500 MB` or `2 GB`. Leave it empty to disable the check (the default). See [Guarding against large inputs](#guarding-against-large-inputs).

**Usage Notes**

* Ensure your VastDB credentials are correctly configured in the Credentials Provider Service.
* The incoming data must include the internal $row_id.
* If the incoming data is from the QueryVastDBTable Processor
   * Ensure you have set `Return Internal Row ID = True`
   * Use a ConvertRecord processor with:
      * RecordReader: JsonTreeReader having the default settings
      * RecordWriter: JsonRecordSetWriter with `Output Grouping` set to `One Record per Line`

### Guarding against large inputs

DeleteVastDB reads the **entire** FlowFile into memory (`getContentsAsBytes`) and decodes it into an
in-memory Arrow table before issuing the delete, so a large enough FlowFile can exhaust the NiFi Python
process and get it **OOM-killed** — an unrecoverable crash rather than a routed failure. When
**Max Input Size** is set, a FlowFile whose content exceeds it is routed to **failure** with a
`vastdb.error` attribute **before any content is read** (the check uses the FlowFile's size metadata
only). It is deliberately **operator-set and not inferred** — the safe size depends on the node's Python
memory budget, its concurrency, and the format's decode expansion — and it is compared against the
**on-disk** size (for Parquet much smaller than the decoded size), so set it conservatively; treat it as
a safety tripwire, not a precise memory gauge. For large deletes, split the input upstream (e.g.
[SplitRecord](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-standard-nar/2.0.0-M4/org.apache.nifi.processors.standard.SplitRecord/index.html))
so each FlowFile is a bounded size.
