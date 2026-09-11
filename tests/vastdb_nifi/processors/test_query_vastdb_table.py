# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""Tests for QueryVastDBTable's 'Data Endpoints' parsing and QueryConfig wiring.

The processor modules import their siblings as flat top-level modules (e.g.
`from vastdb_session import ...`), mirroring how they are laid out at runtime, so the
processors directory is placed on the path before importing.
"""

import sys
from pathlib import Path

import pytest
from vastdb.config import QueryConfig

_PROCESSORS_DIR = Path(__file__).resolve().parents[3] / "src" / "vastdb_nifi" / "processors"
if str(_PROCESSORS_DIR) not in sys.path:
    sys.path.insert(0, str(_PROCESSORS_DIR))

from QueryVastDBTable import QueryVastDBTable  # noqa: E402

from .conftest import FakeProcessContext  # noqa: E402

DATA_ENDPOINTS = "Data Endpoints"


@pytest.fixture
def processor():
    return QueryVastDBTable()


def _extract(processor, value):
    context = FakeProcessContext({DATA_ENDPOINTS: value})
    return processor.extract_data_endpoints(context, flowfile=None)


@pytest.mark.parametrize("value", [None, "", "   ", "\n", " , \n ,"])
def test_blank_data_endpoints_returns_none(processor, value):
    # Empty / whitespace-only input must fall back to the single endpoint (None).
    assert _extract(processor, value) is None


def test_single_endpoint(processor):
    assert _extract(processor, "https://s3.nifi.test") == ["https://s3.nifi.test"]


def test_comma_separated_endpoints_are_split_and_stripped(processor):
    value = "https://11.0.0.2, https://11.0.0.3 ,https://11.0.0.4"
    assert _extract(processor, value) == [
        "https://11.0.0.2",
        "https://11.0.0.3",
        "https://11.0.0.4",
    ]


def test_newline_separated_endpoints(processor):
    value = "https://11.0.0.2\nhttps://11.0.0.3\n"
    assert _extract(processor, value) == ["https://11.0.0.2", "https://11.0.0.3"]


def test_duplicates_are_preserved(processor):
    # Repeating one VIP-pool DNS name N times is the documented way to get N worker
    # threads, so duplicates must NOT be de-duplicated.
    value = "https://s3.nifi.test\nhttps://s3.nifi.test"
    assert _extract(processor, value) == ["https://s3.nifi.test", "https://s3.nifi.test"]


def test_parsed_endpoints_are_accepted_by_queryconfig(processor):
    # The parsed list must be usable as vastdb QueryConfig.data_endpoints.
    endpoints = _extract(processor, "https://11.0.0.2,https://11.0.0.3")
    config = QueryConfig(data_endpoints=endpoints)
    assert config.data_endpoints == ["https://11.0.0.2", "https://11.0.0.3"]


def test_data_endpoints_descriptor_is_registered(processor):
    names = [descriptor.name for descriptor in processor.getPropertyDescriptors()]
    assert DATA_ENDPOINTS in names
