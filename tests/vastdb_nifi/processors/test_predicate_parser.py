# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import ibis
import pytest
from ibis import _

from vastdb_nifi.processors.predicate_parser import parse_yaml_predicate


def test_datestring():
    yaml_predicate = """
    and:
    - column: tpep_pickup_datetime
      op: ">="
      value: "2019-01-01T00:00:00+0000"
      datatype: "timestamp"
    - column: tpep_pickup_datetime
      op: "<="
      value: "2019-01-02T00:00:00+0000"
      datatype: "timestamp"
    """

    date_from = ibis.literal("2019-01-01T00:00:00+0000", type=ibis.dtype("timestamp"))
    date_to = ibis.literal("2019-01-02T00:00:00+0000", type=ibis.dtype("timestamp"))

    actual = parse_yaml_predicate(yaml_predicate)
    expected = (_["tpep_pickup_datetime"] >= date_from) & (_["tpep_pickup_datetime"] <= date_to)

    assert repr(actual) == repr(expected)


def test_single_column_predicate():
    yaml_predicate = """
    - column: extra
      op: ">"
      value: 2
      datatype: "int32"
    """
    ibis_expr = parse_yaml_predicate(yaml_predicate)
    assert repr(ibis_expr) == "(_['extra'] > <scalar[int32]>)"


def test_integer_value_predicate():
    yaml_predicate = """
    - column: vendor_id
      op: "=="
      value: 3
      datatype: "int64"
    """
    ibis_expr = parse_yaml_predicate(yaml_predicate)
    assert repr(ibis_expr) == "(_['vendor_id'] == <scalar[int64]>)"


def test_empty_operator():
    yaml_predicate = """
    - column: extra
      op:
      value: 2
      datatype: "int32"
    """
    with pytest.raises(ValueError, match="Missing or empty operator for column: extra"):
        parse_yaml_predicate(yaml_predicate)


def test_missing_operator():
    yaml_predicate = """
    - column: extra
      value: 2
      datatype: "int32"
    """
    with pytest.raises(ValueError, match="Missing or empty operator for column: extra"):
        parse_yaml_predicate(yaml_predicate)


if __name__ == "__main__":
    pytest.main()
