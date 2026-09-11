## QueryVastDBTable Processor

**Description:**

Queries a specified table from a VastDB schema using Ibis expressions defined in YAML format and returns the results as JSON.

**Properties:**

* **VastDB Endpoint:** The URL of your VastDB endpoint.
* **VastDB Credentials Provider Service:** An [AWSCredentialsProviderControllerService](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-aws-nar/2.0.0-M4/org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService/index.html) controller service that provides your VastDB credentials.
* **TLS Verification:** How the VastDB endpoint's certificate is verified when the endpoint uses `https`: `System CA Certificates` (default), `SSL Context Service`, `CA Certificate File`, or `No Verification`. See [TLS](./TLS.md).
* **SSL Context Service:** *(when **TLS Verification** is `SSL Context Service`)* An [SSLContextService](https://nifi.apache.org/components/org.apache.nifi.ssl.StandardSSLContextService/) supplying the truststore used to verify VastDB. See [TLS](./TLS.md).
* **CA Certificate File:** *(when **TLS Verification** is `CA Certificate File`)* Path to a PEM CA bundle that signed the VastDB endpoint's certificate.
* **VastDB Bucket:** The VastDB bucket containing your data.
* **VastDB Database Schema:** The VastDB schema containing the table to query.
* **VastDB Table Name:** The name of the table to query. This can be an Expression Language expression that references FlowFile attributes.
* **Columns:** A comma-separated list of columns to select. Leave blank to select all columns. This can include Expression Language expressions.
* **Predicates:** A YAML string defining the filter predicates for the query. The YAML should adhere to the following structure:

```yaml
and:
- column: <column_name>
  op: <operator> 
  value: <value>
  datatype: <pyarrow_datatype>
# ... more predicates can be added under 'and'
```

See [here](https://github.com/vast-data/vastdb_sdk/blob/main/docs/predicate.md) for the supported datatype values.

* **Return internal row ID:** A boolean value indicating whether to include the internal row ID in the query results.
* **Data Endpoints:** *(optional)* A comma- or newline-separated list of VastDB data endpoint URLs used to parallelize the query across CNodes — each endpoint is serviced by its own worker thread. When left empty, the query is served only by the single **VastDB Endpoint**. Following VAST's [load-balancing guidance](https://github.com/vast-data/vastdb_sdk/blob/main/README.md), you may list the same VIP-pool DNS name once per VIP (for example, the same `https` URL repeated 16 times for a 16-VIP pool). `https` endpoints are verified using the same **TLS Verification** setting as **VastDB Endpoint** — see [TLS](./TLS.md). This maps to the VastDB SDK's `QueryConfig.data_endpoints`. This property supports Expression Language referencing FlowFile attributes.

**Supported Operators:**

* `<`, `<=`, `==`, `>`, `>=`, `!=` (comparison operators)
* `isin` (check if a value is in a list)
* `isnull` (check for null values)
* `contains` (substring match)

**Example YAML Predicates:**

Example 1.

```yaml
and:
- column: c2
  op: ">"
  value: 2
  datatype: "int64"
- column: c3
  op: isnull
```

Example 2.

```yaml
- column: c2
  op: ">"
  value: 2
  datatype: "int64"
```

**Usage Notes:**

* The processor establishes a connection to VastDB using the provided endpoint and credentials.
* It extracts the column list and parses the YAML predicate to construct an Ibis expression.
* The query is executed on the specified table, and the results are converted to a Pandas DataFrame and then to JSON.
* If `Return internal row ID` is set to `True`, the internal row IDs will be included in the JSON output under the key `_rowid`.
* The JSON output is written to the FlowFile content and routed to the 'success' relationship.
* Ensure that the YAML predicate adheres to the specified structure and uses supported operators.
* Use Expression Language in the `VastDB Table Name` and `Columns` properties to reference FlowFile attributes for dynamic behavior. 