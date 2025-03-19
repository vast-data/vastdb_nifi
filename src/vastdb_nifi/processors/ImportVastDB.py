# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: SLF001

import json

import pyarrow as pa
import pyarrow.parquet as pq
import vastdb
from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.properties import PropertyDescriptor, StandardValidators


class ImportVastDB(FlowFileTransform):
    class Java:
        implements = ["org.apache.nifi.python.processor.FlowFileTransform"]

    class ProcessorDetails:
        dependencies = ["vastdb", "pyarrow"]
        version = "{{version}}"  # auto generated - do not edit
        tags = ["vastdb", "arrow"]
        description = """Imports parquet files from Vast S3."""

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

        self.schema_merge_function = PropertyDescriptor(
            name="Schema Merge",
            description="Schema Merge",
            allowable_values=["Union", "Strict", "Child"],
            required=True,
            default_value="Union",
        )

        self.descriptors = [
            self.vastdb_endpoint,
            self.vastdb_credentials_provider_service,
            self.vastdb_bucket,
            self.vastdb_schema,
            self.vastdb_table,
            self.schema_merge_function,
        ]

    # Processor properties
    def getPropertyDescriptors(self):
        return self.descriptors

    def transform(self, context, flowfile):
        json_content = json.loads(flowfile.getContentsAsBytes())

        parquet_file_list = []

        for item in json_content:
            if "key" in item and "bucket" in item:
                transformed_key = f"/{item['bucket']}/{item['key']}"
                parquet_file_list.append(transformed_key)
            else:
                error_message = "Incoming JSON must have 'key' and 'bucket'"
                raise ValueError(error_message)

        self.logger.info(f"Received parquet_file_list: {parquet_file_list}")

        session = self.get_vastdb_session(context)
        self.import_tables(context, session, parquet_file_list)

        return FlowFileTransformResult(relationship="success")

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

    def import_tables(self, context, session, parquet_file_list):
        vastdb_bucket = context.getProperty(self.vastdb_bucket.name).getValue()
        vastdb_schema = context.getProperty(self.vastdb_schema.name).getValue()
        vastdb_table = context.getProperty(self.vastdb_table.name).getValue()

        with session.transaction() as tx:
            bucket: vastdb.bucket.Bucket = tx.bucket(vastdb_bucket)
            schema: vastdb.schema.Schema = bucket.schema(vastdb_schema, fail_if_missing=False)
            if schema is None:
                self.logger.info(f"Creating schema {vastdb_schema}")
                try:
                    schema = bucket.create_schema(vastdb_schema)
                except Exception as e:
                    error_message = f"Couldn't create schema: {vastdb_schema}"
                    raise RuntimeError(error_message) from e

            table: vastdb.table.Table = schema.table(vastdb_table, fail_if_missing=False)
            if table is None:
                table = self.create_table_from_files(context, schema, vastdb_table, parquet_file_list)
                
            # the following two lines are redundant and can be removed?
            else:
                self.create_table_from_files(context, schema, vastdb_table, parquet_file_list, table.arrow_schema)

            num_parquet_files = len(parquet_file_list)
            self.logger.info(f"Starting import of {num_parquet_files} files to table: {vastdb_table}")
            table.import_files(parquet_file_list)
            self.logger.info(f"Finished import of {num_parquet_files} files to table: {vastdb_table}")

    def create_table_from_files(self, context, schema, table_name: str, parquet_file_list: list[str], pa_schema=None):
        vastdb_schema_merge_function = context.getProperty(self.schema_merge_function.name).getValue()

        if vastdb_schema_merge_function == "Strict":
            schema_merge_function = self.strict_schema_merge
        elif vastdb_schema_merge_function == "Child":
            schema_merge_function = self.child_schema_merge
        else:
            schema_merge_function = self.union_schema_merge

        tx = schema.tx
        current_schema = pa.schema([]) if pa_schema is None else pa_schema
        s3fs = pa.fs.S3FileSystem(
            access_key=tx._rpc.api.access_key, secret_key=tx._rpc.api.secret_key, endpoint_override=tx._rpc.api.url
        )

        for prq_file in parquet_file_list:
            if not prq_file.startswith("/"):
                error_message = f"Path {prq_file} must start with a '/'"
                raise ValueError(error_message)
            parquet_ds = pq.ParquetDataset(prq_file.lstrip("/"), filesystem=s3fs)
            current_schema = schema_merge_function(current_schema, parquet_ds.schema)

        if pa_schema is None:
            try:
                self.logger.info(f"Creating schema.table '{schema.name}.{table_name}'")
                return schema.create_table(table_name, current_schema)
            except Exception as e:
                error_message = (
                    f"Failed to create schema.table '{schema.name}.{table_name}' with pyarrow schema '{current_schema}'"
                )
                raise RuntimeError(error_message) from e
        return None

    def child_schema_merge(self, current_schema: pa.Schema, new_schema: pa.Schema) -> pa.Schema:
        """
        This function validates a schema is contained in another schema
        Raises an ValueError if a certain field does not exist in the target schema
        """
        if not current_schema.names:
            return new_schema
        s1 = set(current_schema)
        s2 = set(new_schema)

        if len(s1) > len(s2):
            s1, s2 = s2, s1
            result = current_schema  # We need this variable in order to preserve the original fields order
        else:
            result = new_schema

        if not s1.issubset(s2):
            self.logger.error("Schema mismatch. schema: %s isn't contained in schema: %s.", s1, s2)
            error_message = "Found mismatch in parquet files schemas."
            raise ValueError(error_message)
        return result

    def strict_schema_merge(self, current_schema: pa.Schema, new_schema: pa.Schema) -> pa.Schema:
        """
        This function validates two Schemas are identical.
        Raises an ValueError if schemas aren't identical.
        """
        if current_schema.names and current_schema != new_schema:
            error_message = f"Schemas are not identical. \n {current_schema} \n vs \n {new_schema}"
            raise ValueError(error_message)

        return new_schema

    def union_schema_merge(self, current_schema: pa.Schema, new_schema: pa.Schema) -> pa.Schema:
        """
        This function returns a unified schema from potentially two different schemas.
        """
        return pa.unify_schemas([current_schema, new_schema])
