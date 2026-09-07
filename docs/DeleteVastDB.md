## DeleteVastDB Processor

**Description**

The `DeleteVastDB` processor facilitates the deletion of rows from a VastDB table. It accepts incoming data in either Parquet or JSON format and uses the row information to identify and delete corresponding rows within the specified VastDB table.

**Properties**

* **VastDB Endpoint:** The URL of your VastDB endpoint.  (Example: http://vip-pool.v123-xy.VastENG.lab)
* **VastDB Credentials Provider Service:** A controller service that securely provides your VastDB credentials. It must be an instance of `org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderService`.
* **TLS Verification:** How the VastDB endpoint's certificate is verified when the endpoint uses `https`: `System CA Certificates` (default), `SSL Context Service`, `CA Certificate File`, or `No Verification`. See [TLS](./TLS.md).
* **SSL Context Service:** *(when **TLS Verification** is `SSL Context Service`)* An [SSLContextService](https://nifi.apache.org/components/org.apache.nifi.ssl.StandardSSLContextService/) supplying the truststore used to verify VastDB. See [TLS](./TLS.md).
* **CA Certificate File:** *(when **TLS Verification** is `CA Certificate File`)* Path to a PEM CA bundle that signed the VastDB endpoint's certificate.
* **VastDB Bucket:** The name of the VastDB bucket where your table resides.
* **VastDB Database Schema:** The name of the VastDB schema containing the target table.
* **VastDB Table Name:** The name of the table from which rows will be deleted.
* **Data Type:** Specifies the format of the incoming data. It can be either "Parquet" or "Json".  If "Json" is selected, ensure each data row is on a separate line and terminated with a newline character.

**Usage Notes**

* Ensure your VastDB credentials are correctly configured in the Credentials Provider Service.
* The incoming data must include the internal $row_id.
* If the incoming data is from the QueryVastDBTable Processor
   * Ensure you have set `Return Internal Row ID = True`
   * Use a ConvertRecord processor with:
      * RecordReader: JsonTreeReader having the default settings
      * RecordWriter: JsonRecordSetWriter with `Output Grouping` set to `One Record per Line`
