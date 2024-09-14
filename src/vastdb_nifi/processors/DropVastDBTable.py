# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import vastdb
from nifiapi.flowfiletransform import FlowFileTransform, FlowFileTransformResult
from nifiapi.properties import ExpressionLanguageScope, PropertyDescriptor, StandardValidators


class DropVastDBTable(FlowFileTransform):
    class Java:
        implements = ["org.apache.nifi.python.processor.FlowFileTransform"]

    class ProcessorDetails:
        dependencies = ["vastdb"]
        version = "0.0.21.dev0+g5f06b21.d20240914"  # auto generated - do not edit
        tags = ["vastdb", "arrow"]
        description = """Drop Vast DB Table."""

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
            description="The VastDB bucket.",
            required=True,
            validators=[StandardValidators.NON_EMPTY_VALIDATOR],
        )

        self.vastdb_schema = PropertyDescriptor(
            name="VastDB Database Schema",
            description="The VastDB database schema.",
            required=True,
            validators=[StandardValidators.NON_EMPTY_VALIDATOR],
        )

        self.vastdb_table = PropertyDescriptor(
            name="VastDB Table Name",
            description="The VastDB table name to drop.",
            required=True,
            expression_language_scope=ExpressionLanguageScope.FLOWFILE_ATTRIBUTES,
            validators=[StandardValidators.NON_EMPTY_VALIDATOR],
        )

        self.descriptors = [
            self.vastdb_endpoint,
            self.vastdb_credentials_provider_service,
            self.vastdb_bucket,
            self.vastdb_schema,
            self.vastdb_table,
        ]

    # Processor properties
    def getPropertyDescriptors(self):
        return self.descriptors

    def transform(self, context, flowfile):
        session = self.get_vastdb_session(context)
        self.drop_table(context, flowfile, session)

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

    def drop_table(self, context, flowfile, session):
        vastdb_bucket = context.getProperty(self.vastdb_bucket.name).getValue()
        vastdb_schema = context.getProperty(self.vastdb_schema.name).getValue()

        # Check if EL is present in the property value
        if context.getProperty(self.vastdb_table.name).isExpressionLanguagePresent():
            vastdb_table = context.getProperty(self.vastdb_table.name).evaluateAttributeExpressions(flowfile).getValue()
        else:
            vastdb_table = context.getProperty(self.vastdb_table.name).getValue()

        with session.transaction() as tx:
            bucket: vastdb.bucket.Bucket = tx.bucket(vastdb_bucket)
            schema: vastdb.schema.Schema = bucket.schema(vastdb_schema, fail_if_missing=False)
            if schema is None:
                self.logger.info(f"Database schema '{vastdb_schema}' not found, skipping.")
                return

            table: vastdb.table.Table = schema.table(vastdb_table, fail_if_missing=False)
            if table is not None:
                table.drop()
                self.logger.info(f"Dropped Table '{vastdb_table}'.")
            else:
                self.logger.info(f"Table '{vastdb_table}' not found, skipping.")
