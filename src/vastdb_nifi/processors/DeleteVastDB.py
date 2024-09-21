# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import io

import pyarrow.parquet as pq
import vastdb
from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.properties import PropertyDescriptor, StandardValidators
from pyarrow import json as pa_json


class DeleteVastDB(FlowFileTransform):
    class Java:
        implements = ["org.apache.nifi.python.processor.FlowFileTransform"]

    class ProcessorDetails:
        dependencies = ["vastdb", "pyarrow"]
        version = "{{version}}"  # auto generated - do not edit
        tags = ["vastdb", "arrow"]
        description = """Deletes Vast DB table rows."""

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
            description="The VastDB table name with rows to delete.",
            required=True,
            validators=[StandardValidators.NON_EMPTY_VALIDATOR],
        )

        self.incoming_data_type = PropertyDescriptor(
            name="Data Type",
            description=(
                "Data Type.  Parquet or Json.\n"
                "If Json, each data row must be on one line terminated by a newline character."
            ),
            allowable_values=["Parquet", "Json"],
            required=True,
            default_value="Parquet",
        )

        self.descriptors = [
            self.vastdb_endpoint,
            self.vastdb_credentials_provider_service,
            self.vastdb_bucket,
            self.vastdb_schema,
            self.vastdb_table,
            self.incoming_data_type,
        ]

    # Processor properties
    def getPropertyDescriptors(self):
        return self.descriptors

    def transform(self, context, flowfile):
        incoming_data_type = context.getProperty(self.incoming_data_type.name).getValue()

        session = self.get_vastdb_session(context)
        pa_table = self.read_json(flowfile) if incoming_data_type == "Json" else self.read_parquet(flowfile)

        self.write_to_vastdb(context, session, pa_table)
        return FlowFileTransformResult(relationship="success")

    def read_parquet(self, flowfile):
        try:
            # Read the FlowFile contents into a byte array
            file_contents = flowfile.getContentsAsBytes()

            # Create a BytesIO object from the byte array
            buffer = io.BytesIO(file_contents)

            # Read the Parquet data from the buffer
            return pq.read_table(buffer)
        except Exception as e:
            error_message = (
                f"{e}.  Ensure your parquet is valid and meets pyarrow's requirements."
                f"\nSee: https://arrow.apache.org/docs/python/json.html#reading-json-files"
            )
            raise RuntimeError(error_message) from e

    def read_json(self, flowfile):
        try:
            return pa_json.read_json(io.BytesIO(flowfile.getContentsAsBytes()))
        except Exception as e:
            error_message = (
                f"{e}.  Ensure your json is valid and meets pyarrow's requirements."
                f"\nSee: https://arrow.apache.org/docs/python/json.html#reading-json-files"
            )
            raise RuntimeError(error_message) from e

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

    def write_to_vastdb(self, context, session, pa_table):
        vastdb_bucket = context.getProperty(self.vastdb_bucket.name).getValue()
        vastdb_schema = context.getProperty(self.vastdb_schema.name).getValue()
        vastdb_table = context.getProperty(self.vastdb_table.name).getValue()

        with session.transaction() as tx:
            bucket: vastdb.bucket.Bucket = tx.bucket(vastdb_bucket)
            schema: vastdb.schema.Schema = bucket.schema(vastdb_schema, fail_if_missing=False)
            if schema is None:
                self.logger.info(f"Creating schema {vastdb_schema}")
                schema = bucket.create_schema(vastdb_schema)

            table: vastdb.table.Table = schema.table(vastdb_table, fail_if_missing=False)
            if table is None:
                self.logger.info(f"Creating table {vastdb_table}")
                try:
                    table = schema.create_table(vastdb_table, pa_table.schema)
                except Exception as e:
                    error_message = f"Error creating table '{vastdb_table}' with schema {pa_table.schema}: {e}"
                    raise RuntimeError(error_message) from e

            self.logger.info(f"Deleting '{pa_table.num_rows}' from table '{vastdb_table}'.")
            table.delete(pa_table)
            self.logger.info(f"Deleted '{pa_table.num_rows}' from table '{vastdb_table}'.")
