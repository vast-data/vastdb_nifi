# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING

from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.properties import ExpressionLanguageScope, PropertyDescriptor, StandardValidators
from predicate_parser import parse_yaml_predicate
from vastdb_session import VastDBConnection

if TYPE_CHECKING:
    import vastdb


class QueryVastDBTable(FlowFileTransform):
    class Java:
        implements = ["org.apache.nifi.python.processor.FlowFileTransform"]

    class ProcessorDetails:
        dependencies = ["vastdb", "pyarrow", "cryptography", "pyjks"]
        version = "{{version}}"  # auto generated - do not edit
        tags = ["vastdb", "yaml"]
        description = """Publishes Parquet or JSON data to a Vast DB."""

    # ruff: noqa: ARG002
    def __init__(self, **kwargs):
        self.connection = VastDBConnection()

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
    datatype: "int64"
  - column: c3
    op: isnull
""",
            expression_language_scope=ExpressionLanguageScope.FLOWFILE_ATTRIBUTES,
            # TODO: use REGULAR_EXPRESSION_WITH_EL_VALIDATOR
        )

        self.return_row_id = PropertyDescriptor(
            name="Return internal row ID",
            description=("Return the internal row ID."),
            allowable_values=["True", "False"],
            required=True,
            default_value="False",
        )

        self.data_endpoints = PropertyDescriptor(
            name="Data Endpoints",
            description=(
                "Optional comma- or newline-separated list of VastDB data endpoint URLs used to "
                "parallelize the query across CNodes; each endpoint is handled by its own worker "
                "thread. When left empty the query is served only by the single 'VastDB Endpoint'. "
                "Per VAST's load-balancing guidance you may list the same VIP-pool DNS name once per "
                "VIP (e.g. the same https URL repeated 16 times for a 16-VIP pool). https endpoints "
                "are verified using the same 'TLS Verification' setting as 'VastDB Endpoint'."
            ),
            required=False,
            expression_language_scope=ExpressionLanguageScope.FLOWFILE_ATTRIBUTES,
        )

        self.descriptors = [
            *self.connection.descriptors,
            self.vastdb_bucket,
            self.vastdb_schema,
            self.vastdb_table,
            self.vastdb_columns,
            self.vastdb_predicates,
            self.return_row_id,
            self.data_endpoints,
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
        return self.connection.connect(context, self.logger)

    def extract_column_list(self, context, flowfile):
        vastdb_columns_data = self.get_el_property(context, flowfile, self.vastdb_columns.name)

        # Split, filter out empty columns, and strip whitespace
        column_list = [col.strip() for col in vastdb_columns_data.split(",") if col.strip()]

        # Return None if the list is empty
        if not column_list:
            return None
        return column_list

    def extract_data_endpoints(self, context, flowfile):
        data_endpoints_data = self.get_el_property(context, flowfile, self.data_endpoints.name)

        # Nothing configured: fall back to the single 'VastDB Endpoint'.
        if not data_endpoints_data:
            return None

        # Accept commas and/or newlines as separators, strip whitespace, drop blanks.
        endpoints = [
            endpoint.strip()
            for line in data_endpoints_data.splitlines()
            for endpoint in line.split(",")
            if endpoint.strip()
        ]
        return endpoints or None

    def parse_bool_string(self, s):
        """Parses a "True" or "False" string into a Python bool.

        Args:
            s: The string to parse.

        Returns:
            True if the string is "True", False if the string is "False".
            Raises a ValueError if the string is neither "True" nor "False".
        """
        if s.lower() == "true":
            return True
        if s.lower() == "false":
            return False

        error_message = f"Invalid bool string: {s}"
        raise ValueError(error_message)

    def query_vastdb(self, context, flowfile, session):
        vastdb_bucket = context.getProperty(self.vastdb_bucket.name).getValue()
        vastdb_schema = context.getProperty(self.vastdb_schema.name).getValue()
        vastdb_table = context.getProperty(self.vastdb_table.name).getValue()
        vastdb_column_list = self.extract_column_list(context, flowfile)
        vastdb_predicate = self.get_el_property(context, flowfile, self.vastdb_predicates.name)
        vastdb_ret_row_id = self.parse_bool_string(context.getProperty(self.return_row_id.name).getValue())
        vastdb_data_endpoints = self.extract_data_endpoints(context, flowfile)

        self.logger.info(f"Received predicate {vastdb_predicate}")

        with session.transaction() as tx:
            bucket: vastdb.bucket.Bucket = tx.bucket(vastdb_bucket)
            schema: vastdb.schema.Schema = bucket.schema(vastdb_schema, fail_if_missing=True)
            table: vastdb.table.Table = schema.table(vastdb_table, fail_if_missing=True)

            # FUTURE: retrieve datatype from table column definition so
            #         so the user doesn't have to manually specify.
            ibis_expr = parse_yaml_predicate(vastdb_predicate)

            # Only build a QueryConfig when data endpoints are set; passing None keeps the
            # SDK's default single-endpoint behaviour unchanged.
            query_config = None
            if vastdb_data_endpoints:
                from vastdb.config import QueryConfig  # noqa: PLC0415

                query_config = QueryConfig(data_endpoints=vastdb_data_endpoints)

            log_message = (
                f"Selecting from table '{table.name}' columns '{vastdb_column_list}' "
                f"with yaml: '{vastdb_predicate}' translated to ibis '{ibis_expr!s}' "
                f"across data endpoints '{vastdb_data_endpoints}'"
            )
            self.logger.info(log_message)

            try:
                reader = table.select(
                    columns=vastdb_column_list,
                    predicate=ibis_expr,
                    config=query_config,
                    internal_row_id=vastdb_ret_row_id,
                )
                table = reader.read_all()
                df = table.to_pandas()
                return df.to_json(orient="records")
            except Exception as e:
                error_message = (
                    f"Error from table '{table.name}' columns '{vastdb_column_list}' "
                    f"with yaml: '{vastdb_predicate}' translated to ibis '{ibis_expr!s}': {e}"
                )
                raise RuntimeError(error_message) from e
