# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""Test doubles for the `nifiapi` package.

`nifiapi` is supplied by the NiFi runtime and is not installable from PyPI, so the
handful of names the processors import from it are stubbed here. The stubs only need to
record what they were constructed with - the framework's own behaviour is not under test.
"""

import sys
import types

import pytest


class PropertyDescriptor:
    def __init__(self, name, description, **kwargs):
        self.name = name
        self.description = description
        self.required = kwargs.get("required", False)
        self.sensitive = kwargs.get("sensitive", False)
        self.default_value = kwargs.get("default_value")
        self.allowable_values = kwargs.get("allowable_values")
        self.dependencies = kwargs.get("dependencies")
        self.validators = kwargs.get("validators")
        self.controller_service_definition = kwargs.get("controller_service_definition")


class PropertyDependency:
    def __init__(self, property_descriptor, *dependent_values):
        self.property_descriptor = property_descriptor
        self.dependent_values = dependent_values


class ExpressionLanguageScope:
    NONE = "NONE"
    ENVIRONMENT = "ENVIRONMENT"
    FLOWFILE_ATTRIBUTES = "FLOWFILE_ATTRIBUTES"


class StandardValidators:
    """Validators are opaque Java objects at runtime, so any sentinel will do."""

    def __getattr__(self, name):
        return name


def _install_nifiapi_stub():
    if "nifiapi.properties" in sys.modules:
        return

    nifiapi = types.ModuleType("nifiapi")
    properties = types.ModuleType("nifiapi.properties")
    properties.PropertyDescriptor = PropertyDescriptor
    properties.PropertyDependency = PropertyDependency
    properties.ExpressionLanguageScope = ExpressionLanguageScope
    properties.StandardValidators = StandardValidators()
    nifiapi.properties = properties

    sys.modules["nifiapi"] = nifiapi
    sys.modules["nifiapi.properties"] = properties


_install_nifiapi_stub()


class FakePropertyValue:
    def __init__(self, value):
        self._value = value

    def getValue(self):  # noqa: N802 - mirrors the NiFi API
        return self._value

    def isSet(self):  # noqa: N802 - mirrors the NiFi API
        return self._value is not None

    def asControllerService(self):  # noqa: N802 - mirrors the NiFi API
        return self._value


class FakeProcessContext:
    """Stands in for the NiFi ProcessContext, backed by a plain property-name mapping."""

    def __init__(self, properties):
        self._properties = properties

    def getProperty(self, name):  # noqa: N802 - mirrors the NiFi API
        return FakePropertyValue(self._properties.get(name))


class FakeSSLContextService:
    """Stands in for the py4j proxy of an SSLContextService controller service."""

    def __init__(self, truststore=None, keystore=None):
        self._truststore = truststore or {}
        self._keystore = keystore or {}

    def isTrustStoreConfigured(self):  # noqa: N802 - mirrors the NiFi API
        return bool(self._truststore)

    def isKeyStoreConfigured(self):  # noqa: N802 - mirrors the NiFi API
        return bool(self._keystore)

    def getTrustStoreFile(self):  # noqa: N802 - mirrors the NiFi API
        return self._truststore.get("file")

    def getTrustStoreType(self):  # noqa: N802 - mirrors the NiFi API
        return self._truststore.get("type")

    def getTrustStorePassword(self):  # noqa: N802 - mirrors the NiFi API
        return self._truststore.get("password")

    def getKeyStoreFile(self):  # noqa: N802 - mirrors the NiFi API
        return self._keystore.get("file")

    def getKeyStoreType(self):  # noqa: N802 - mirrors the NiFi API
        return self._keystore.get("type")

    def getKeyStorePassword(self):  # noqa: N802 - mirrors the NiFi API
        return self._keystore.get("password")

    def getKeyPassword(self):  # noqa: N802 - mirrors the NiFi API
        return self._keystore.get("key_password")


class RecordingLogger:
    def __init__(self):
        self.messages = []

    def _record(self, message, *args):
        self.messages.append(message % args if args else message)

    info = debug = trace = warn = error = _record


@pytest.fixture
def logger():
    return RecordingLogger()
