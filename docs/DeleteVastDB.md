## DeleteVastDB Processor

**Description**

The `DeleteVastDB` processor facilitates the deletion of rows from a VastDB table. It accepts incoming data in either Parquet or JSON format and uses the row information to identify and delete corresponding rows within the specified VastDB table.

**Properties**

* **VastDB Endpoint:** The URL of your VastDB endpoint.  (Example: http://vip-pool.v123-xy.VastENG.lab)
* **VastDB Credentials Provider Service:** A controller service that securely provides your VastDB credentials. It must be an instance of `org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderService`.
* **VastDB Bucket:** The name of the VastDB bucket where your table resides.
* **VastDB Database Schema:** The name of the VastDB schema containing the target table.
* **VastDB Table Name:** The name of the table from which rows will be deleted.
* **Data Type:** Specifies the format of the incoming data. It can be either "Parquet" or "Json".  If "Json" is selected, ensure each data row is on a separate line and terminated with a newline character.

**Usage Notes**

1. **Configuration:**
    * Provide the correct VastDB endpoint and credentials.
    * Specify the bucket, schema, and table name accurately.
    * Choose the appropriate "Data Type" based on your incoming data format.

2. **Incoming Data:**
    * The incoming FlowFile should contain either Parquet or JSON data.
    * The data structure within the FlowFile should align with the schema of the VastDB table.
    * For JSON data, each row must be on a separate line and end with a newline.

3. **Functionality:**
    * The processor reads the incoming data and extracts the relevant row information.
    * It connects to VastDB using the provided credentials.
    * It constructs a delete operation based on the incoming data and executes it on the specified table.
    * The FlowFile is then routed to the 'success' relationship, indicating successful deletion.

4. **Error Handling:**
    * The processor includes error handling to manage potential issues like invalid data formats or connection failures.
    * Error messages are logged to assist in troubleshooting.

**Important Considerations:**

* Ensure your VastDB credentials are correctly configured in the Credentials Provider Service.
* The incoming data structure must match the table schema for accurate row deletion.
* For large datasets, consider optimizing performance by adjusting NiFi settings or using partitioning techniques in VastDB.
