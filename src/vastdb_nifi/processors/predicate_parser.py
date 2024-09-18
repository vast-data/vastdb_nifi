# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import ibis
import yaml

ALLOWED_OPS = ["<", "<=", "==", ">", ">=", "!=", "isin", "isnull", "contains"]


def parse_yaml_predicate(yaml_str):
    data = yaml.safe_load(yaml_str)

    # Extract the single predicate dictionary from the list if necessary
    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        data = data[0]

    def build_expression(predicate):
        if isinstance(predicate, dict):
            if "and" in predicate:
                return ibis.and_(*[build_expression(p) for p in predicate["and"]])
            if "or" in predicate:
                return ibis.or_(*[build_expression(p) for p in predicate["or"]])

            # Handle single column predicate without 'and' or 'or'
            column = predicate["column"]
            op = predicate.get("op")
            value = predicate["value"]

            if op is None:
                error_message = f"Missing or empty operator for column: {column}. Predicate: {predicate}"
                raise ValueError(error_message)

            op = op.strip().lower()

            if not op:
                error_message = f"Missing or empty operator for column: {column}. Predicate: {predicate}"
                raise ValueError(error_message)

            if op not in [a.lower() for a in ALLOWED_OPS]:
                error_message = f"Unsupported operator: {op}. Predicate: {predicate}"
                raise ValueError(error_message)

            table = ibis.table([(column, infer_type(value))])

            if op == "isin":
                return table[column].isin(value)
            if op == "isnull":
                return table[column].isnull()
            if op == "contains":
                return table[column].contains(value)

            # Use operator mapping for comparison operators
            op_map = {">": "__gt__", ">=": "__ge__", "<": "__lt__", "<=": "__le__", "==": "__eq__", "!=": "__ne__"}
            if op in op_map:
                return getattr(table[column], op_map[op])(value)

            error_message = f"Unhandled operator: {op}.  Predicate: {predicate}"
            raise ValueError(error_message)

        if isinstance(predicate, list):
            error_message = f"Unexpected list encountered in predicate: {predicate}"
            raise TypeError(error_message)

        error_message = f"Unsupported predicate type: {type(predicate)}"
        raise ValueError(error_message)

    def infer_type(value):
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

    return build_expression(data)
