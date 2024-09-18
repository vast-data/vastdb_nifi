# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import ibis
import yaml

ALLOWED_OPS = ["<", "<=", "==", ">", ">=", "!=", "isin", "isnull", "contains"]


def parse_yaml_predicate(yaml_str):
    """
    Parses a YAML string representing a predicate.

    Args:
        yaml_str: The YAML string to parse.

    Returns:
        An Ibis expression representing the parsed predicate.

    Example:
        yaml_predicate = '''
        and:
          - or:
              - column: x
                op: <
                value: 5
              - column: x
                op: >=
                value: 10
          - column: y
            op: isin
            value: [1, 3, 5]
          - column: z
            op: isnull
        '''

        ibis_expr = parse_yaml_predicate(yaml_predicate)
        print(ibis_expr)
    """

    data = yaml.safe_load(yaml_str)

    def build_expression(predicate):
        if isinstance(predicate, dict):  # Check if it's a dictionary
            if "and" in predicate:
                return ibis.and_(*[build_expression(p) for p in predicate["and"]])
            if "or" in predicate:
                return ibis.or_(*[build_expression(p) for p in predicate["or"]])

            # Handle single column predicate without 'and' or 'or'
            column = predicate["column"]
            op = predicate["op"]
            value = predicate["value"]

            if op not in ALLOWED_OPS:
                error_message = f"Unsupported operator: {op}"
                raise ValueError(error_message)

            table = ibis.table([(column, infer_type(value))])

            if op == "isin":
                return table[column].isin(value)
            if op == "isnull":
                return table[column].isnull()
            if op == "contains":
                return table[column].contains(value)
            return getattr(table[column], op)(value)

        if isinstance(predicate, list):  # Check if it's a list
            # Iterate over the list and handle each item as a dictionary
            return [build_expression(item) for item in predicate]

        error_message = f"Unsupported predicate type: {type(predicate)}"
        raise ValueError(error_message)

    def infer_type(value):
        """Infers the Ibis data type from a Python value."""
        if isinstance(value, str):
            return "string"
        if isinstance(value, int):
            return "int64"
        if isinstance(value, float):
            return "float64"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, list):
            return "array<" + infer_type(value[0]) + ">"

        error_message = f"Unsupported value type: {type(value)}"
        raise ValueError(error_message)

    # Call build_expression and return the result
    return build_expression(data)
