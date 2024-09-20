## QueryVastDBTable Processor

**Description:**

Queries a specified table from a VastDB schema using Ibis expressions defined in YAML format and returns the results as JSON.

**Properties:**

* **VastDB Endpoint:** The URL of your VastDB endpoint.
* **VastDB Credentials Provider Service:** An [AWSCredentialsProviderControllerService](https://nifi.apache.org/docs/nifi-docs/components/org.apache.nifi/nifi-aws-nar/2.0.0-M4/org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderControllerService/index.html) controller service that provides your VastDB credentials.
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