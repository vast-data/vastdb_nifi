## ImportVastDB Processor

   * **Description:** Imports Parquet files from Vast S3 into a VastDB table.
   * **Properties:**
     * **VastDB Endpoint:** The URL of your VastDB endpoint.
     * **VastDB Credentials Provider Service:** An [AWSCredentialsProviderControllerService](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-aws-nar/2.0.0-M4/org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService/index.html) controller service that provides your VastDB credentials.
     * **VastDB Bucket:** The VastDB bucket to write to.
     * **VastDB Database Schema:** The VastDB schema to write to.
     * **VastDB Table Name:** The VastDB table name to write to (or create).
     * **Schema Merge:**  How to handle schema differences between Parquet files and the target table ("Union", "Strict", or "Child").
        * **Union** This schema merge function returns a unified schema from potentially two different schemas.
        * **Strict** This schema merge function validates two Schemas are identical.
        * **Child** This schema merge function validates a schema is contained in another schema.
   * **Incoming Data Requirements:** The incoming FlowFile's content must be a JSON array with each element in the array is a JSON object with the following keys:
        * **key:** The S3 key (path) to the Parquet file.
        * **bucket:** The S3 bucket where the Parquet file is located.
	
    
   * **Example of Incoming FlowFile Content:**
```json
    [
        {"key": "path/to/file1.parquet", "bucket": "my-vast-bucket"},
        {"key": "path/to/file2.parquet", "bucket": "my-vast-bucket"}
    ]
```
   * **Note:** The [ListS3](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-aws-nar/2.0.0-M4/org.apache.nifi.processors.aws.s3.ListS3/index.html) processor configured with a [JsonRecordSetWriter](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-record-serialization-services-nar/2.0.0-M4/org.apache.nifi.json.JsonRecordSetWriter/index.html) that has the **Output Grouping** property set to **Array** will create the FlowFile with the correct content and format.
