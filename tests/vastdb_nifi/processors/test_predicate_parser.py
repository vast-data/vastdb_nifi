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
        self.assertEqual(str(ibis_expr), expected_expr)

# if __name__ == '__main__':
#     unittest.main()