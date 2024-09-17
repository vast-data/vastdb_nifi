# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import ibis
import yaml

ALLOWED_OPS = ["<", "<=", "==", ">", ">=", "!=", "isin", "isnull", "contains"]


def parse_yaml_predicate(yaml_str, context=None):
    """
    Parses a YAML string representing a predicate, allowing for dynamic constants
    by directly substituting values from the context.

    Args:
        yaml_str: The YAML string to parse.
        context: A dictionary containing the dynamic values to substitute.

    Returns:
        An Ibis expression representing the parsed predicate.

    Example:
        yaml_predicate = '''
        and:
          - or:
              - column: x
                op: <
                value: ${max_value}
              - column: x
                op: >=
                value: ${min_value}
          - column: y
            op: isin
            value: ${allowed_values}
          - column: z
            op: isnull
        '''

        context = {
            'max_value': 5,
            'min_value': 10,
            'allowed_values': [1, 3, 5]
        }

        ibis_expr = parse_yaml_predicate(yaml_predicate, context)
        print(ibis_expr)
    """

    def substitute_constants(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    var_name = value[2:-1]
                    if var_name in context:
                        data[key] = context[var_name]
                else:
                    substitute_constants(value)
        elif isinstance(data, list):
            for i in range(len(data)):
                substitute_constants(data[i])

    data = yaml.safe_load(yaml_str)
    substitute_constants(data)

    def build_expression(predicate):
        if "and" in predicate:
            return ibis.and_(*[build_expression(p) for p in predicate["and"]])
        if "or" in predicate:
            return ibis.or_(*[build_expression(p) for p in predicate["or"]])
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

    return build_expression(data)


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
