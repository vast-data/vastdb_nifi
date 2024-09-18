# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import unittest

from vastdb_nifi.processors.predicate_parser import parse_yaml_predicate


class TestPredicateParser(unittest.TestCase):
    def test_single_column_predicate(self):
        yaml_predicate = """
- column: extra
  op: >
  value: 2
"""
        expected_expr = "extra > 2"

        ibis_expr = parse_yaml_predicate(yaml_predicate)
        assert str(ibis_expr) == expected_expr  # Replace self.assertEqual with assert


if __name__ == "__main__":
    unittest.main()
