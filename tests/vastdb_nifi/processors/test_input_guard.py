# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""Tests for the shared Max Input Size guard."""

import sys
from pathlib import Path

import pytest

_PROCESSORS_DIR = Path(__file__).resolve().parents[3] / "src" / "vastdb_nifi" / "processors"
if str(_PROCESSORS_DIR) not in sys.path:
    sys.path.insert(0, str(_PROCESSORS_DIR))

import input_guard  # noqa: E402

from .conftest import FakeProcessContext, RecordingLogger  # noqa: E402

KB, MB, GB = 1024, 1024**2, 1024**3


class FakeFlowFile:
    def __init__(self, size):
        self._size = size

    def getSize(self):  # noqa: N802 - mirrors the NiFi API
        return self._size


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("500 MB", 500 * MB),
        ("1GB", GB),
        ("1024 B", 1024),
        ("2 gb", 2 * GB),
        ("1.5 KB", int(1.5 * KB)),
        ("10 BYTES", 10),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_parse_data_size(text, expected):
    assert input_guard.parse_data_size(text) == expected


@pytest.mark.parametrize("bad", ["abc", "10 XB", "MB", "10", "GB 10"])
def test_parse_data_size_rejects_garbage(bad):
    with pytest.raises(ValueError, match="data size"):
        input_guard.parse_data_size(bad)


def _guard(limit):
    descriptor = input_guard.max_input_size_descriptor()
    return FakeProcessContext({descriptor.name: limit}), descriptor


def test_no_limit_allows_any_size():
    context, descriptor = _guard(None)
    assert input_guard.oversize_reason(context, FakeFlowFile(10**12), descriptor) is None


def test_empty_limit_disables_the_guard():
    context, descriptor = _guard("")
    assert input_guard.oversize_reason(context, FakeFlowFile(10**12), descriptor) is None


def test_under_the_limit_is_allowed():
    context, descriptor = _guard("1 GB")
    assert input_guard.oversize_reason(context, FakeFlowFile(500 * MB), descriptor) is None


def test_at_the_limit_is_allowed():
    context, descriptor = _guard("100 MB")
    assert input_guard.oversize_reason(context, FakeFlowFile(100 * MB), descriptor) is None


def test_over_the_limit_returns_a_reason():
    context, descriptor = _guard("100 MB")
    reason = input_guard.oversize_reason(context, FakeFlowFile(200 * MB), descriptor)
    assert reason is not None
    assert str(200 * MB) in reason
    assert "failure" in reason


def test_putvastdb_routes_oversize_flowfile_to_failure():
    from PutVastDB import PutVastDB  # noqa: PLC0415

    processor = PutVastDB()
    processor.logger = RecordingLogger()
    context = FakeProcessContext({processor.max_input_size.name: "1 MB"})

    result = processor.transform(context, FakeFlowFile(5 * MB))

    assert result.relationship == "failure"
    assert result.attributes["vastdb.error"]
    assert any("Max Input Size" in message for message in processor.logger.messages)
