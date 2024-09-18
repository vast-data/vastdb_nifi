# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import vastdb
from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.properties import ExpressionLanguageScope, PropertyDescriptor, StandardValidators
from predicate_parser import parse_yaml_predicate


class QueryVastDBTable(FlowFileTransform):
    class Java:
        implements = ["org.apache.nifi.python.processor.FlowFileTransform"]

    class ProcessorDetails:
        dependencies = ["vastdb", "pyarrow"]
        version = "{{version}}"  # auto generated - do not edit
        tags = ["vastdb", "yaml"]
        description = """Publishes Parquet or JSON data to a Vast DB."""

    # ruff: noqa: ARG002
    def __init__(self, **kwargs):
        self.vastdb_endpoint = PropertyDescriptor(
            name="VastDB Endpoint",
            description="AWS_S3_ENDPOINT_URL",
            required=True,
            default_value="http://vip-pool.v123-xy.VastENG.lab",
            validators=[StandardValidators.URL_VALIDATOR],
        )

        self.vastdb_credentials_provider_service = PropertyDescriptor(
            name="VastDB Credentials Provider Service",
            description="The Controller Service that is used to obtain VastDB credentials.",
            required=True,
            controller_service_definition="org.apache.nifi.processors.aws.credentials.provider.service.AWSCredentialsProviderService",
        )

        self.vastdb_bucket = PropertyDescriptor(
            name="VastDB Bucket",
            description="The VastDB bucket to write to",
            required=True,
            validators=[StandardValidators.NON_EMPTY_VALIDATOR],
        )

        self.vastdb_schema = PropertyDescriptor(
            name="VastDB Database Schema",
            description="The VastDB database schema to write to",
            required=True,
            validators=[StandardValidators.NON_EMPTY_VALIDATOR],
        )

        self.vastdb_table = PropertyDescriptor(
            name="VastDB Table Name",
            description="The VastDB table name to write to (or create)",
            required=True,
            validators=[StandardValidators.NON_EMPTY_VALIDATOR],
        )

        self.vastdb_columns = PropertyDescriptor(
            name="Columns",
            description="List of Columns to select (seperated by commas), or leave blank to select all columns",
            required=True,
            default_value=None,
            expression_language_scope=ExpressionLanguageScope.FLOWFILE_ATTRIBUTES,
            # TODO: use REGULAR_EXPRESSION_WITH_EL_VALIDATOR
        )

        self.vastdb_predicates = PropertyDescriptor(
            name="Predicates",
            description="Predicates yaml",
            required=True,
            default_value="""and:
  - column: c2
    op: >
    value: ${c2_value}
  - column: c3
    op: isnull
""",
            expression_language_scope=ExpressionLanguageScope.FLOWFILE_ATTRIBUTES,
            # TODO: use REGULAR_EXPRESSION_WITH_EL_VALIDATOR
        )

        self.descriptors = [
            self.vastdb_endpoint,
            self.vastdb_credentials_provider_service,
            self.vastdb_bucket,
            self.vastdb_schema,
            self.vastdb_table,
            self.vastdb_columns,
            self.vastdb_predicates,
        ]

    # Processor properties
    def getPropertyDescriptors(self):
        return self.descriptors

    def get_el_property(self, context, flowfile, property_name) -> str:
        # Check if EL is present in the property value
        if context.getProperty(property_name).isExpressionLanguagePresent():
            return context.getProperty(property_name).evaluateAttributeExpressions(flowfile).getValue()
        return context.getProperty(property_name).getValue()

    def transform(self, context, flowfile):
        session = self.get_vastdb_session(context)
        rows = self.query_vastdb(context, flowfile, session)
        return FlowFileTransformResult(relationship="success", contents=rows)

    def get_vastdb_session(self, context):
        vastdb_endpoint = context.getProperty(self.vastdb_endpoint.name).getValue()
        credentials_provider_service = context.getProperty(
            self.vastdb_credentials_provider_service.name
        ).asControllerService()
        credentials = credentials_provider_service.getAwsCredentialsProvider().resolveCredentials()

        try:
            session = vastdb.connect(
                endpoint=vastdb_endpoint, access=credentials.accessKeyId(), secret=credentials.secretAccessKey()
            )
            self.logger.info("Connected to VastDB")
        except Exception as e:
            error_message = f"Failed to connect to VastDB: {e}"
            raise RuntimeError(error_message) from e
        else:
            return session

    def extract_column_list(self, context, flowfile):
        vastdb_columns_data = self.get_el_property(context, flowfile, self.vastdb_columns.name)

        # Split, filter out empty columns, and strip whitespace
        column_list = [col.strip() for col in vastdb_columns_data.split(",") if col.strip()]

        # Return None if the list is empty
        if not column_list:
            return None
        return column_list

    def query_vastdb(self, context, flowfile, session):
        vastdb_bucket = context.getProperty(self.vastdb_bucket.name).getValue()
        vastdb_schema = context.getProperty(self.vastdb_schema.name).getValue()
        vastdb_table = context.getProperty(self.vastdb_table.name).getValue()
        vastdb_column_list = self.extract_column_list(context, flowfile)
        vastdb_predicate = self.get_el_property(context, flowfile, self.vastdb_predicates.name)

        ibis_expr = parse_yaml_predicate(vastdb_predicate)

        with session.transaction() as tx:
            bucket: vastdb.bucket.Bucket = tx.bucket(vastdb_bucket)
            schema: vastdb.schema.Schema = bucket.schema(vastdb_schema, fail_if_missing=True)
            table: vastdb.table.Table = schema.table(vastdb_table, fail_if_missing=True)

            reader = table.select(columns=vastdb_column_list, predicate=ibis_expr)
            table = reader.read_all()
            df = table.to_pandas()
            return df.to_json(orient="records")
