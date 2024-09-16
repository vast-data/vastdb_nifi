## PutVastDB Processor

   * **Description:** Publishes Parquet or JSON data to a VastDB table.
   * **Properties:**
     * **VastDB Endpoint:** The URL of your VastDB endpoint.
     * **VastDB Credentials Provider Service:** An [AWSCredentialsProviderControllerService](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-aws-nar/2.0.0-M4/org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService/index.html) controller service that provides your VastDB credentials.
     * **VastDB Bucket:** The VastDB bucket to write to.
     * **VastDB Database Schema:** The VastDB schema to write to.
     * **VastDB Table Name:** The VastDB table name to write to (or create).
     * **Data Type:**  The type of incoming data ("Parquet" or "Json").  If using Json, the incoming data must consist of multiple JSON objects, one per line, representing individual data rows. For example, this file represents two rows of data with four columns “a”, “b”, “c”, “d”:

```json
{"a": 1, "b": 2.0, "c": "foo", "d": false}
{"a": 4, "b": -5.5, "c": null, "d": true}
```
   * **Note:** Processors with *Record Writers* can use the [JsonRecordSetWriter](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-record-serialization-services-nar/2.0.0-M4/org.apache.nifi.json.JsonRecordSetWriter/index.html) that has the **Output Grouping** property set to **One Line Per Object** will create the FlowFile with the correct format.