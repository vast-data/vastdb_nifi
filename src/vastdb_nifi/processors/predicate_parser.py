# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

import ibis
import yaml

ALLOWED_OPS = ["<", "<=", "==", ">", ">=", "!=", "isin", "isnull", "contains"]


def cast_to_ibis_type(value, type_str):
    type_map = {
        "int8": "int8",
        "int16": "int16",
        "int32": "int32",
        "int64": "int64",
        "float32": "float32",
        "float64": "float64",
        "utf8": "string",
        "bool": "boolean",
        "decimal128": "decimal",
        "binary": "binary",
        "date32": "date",
        "time32": "time",
        "time64": "time",
        "timestamp": "timestamp",
    }

    if type_str not in type_map:
        error_message = f"Unsupported type: {type_str}"
        raise ValueError(error_message)

    ibis_type = ibis.dtype(type_map[type_str])
    return ibis.literal(value, type=ibis_type)


def parse_yaml_predicate(yaml_str):
    data = yaml.safe_load(yaml_str)

    if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
        data = data[0]

    def build_expression(predicate):
        from ibis import _

        if isinstance(predicate, dict):
            if "and" in predicate:
                return ibis.and_(*[build_expression(p) for p in predicate["and"]])
            if "or" in predicate:
                return ibis.or_(*[build_expression(p) for p in predicate["or"]])

            column = predicate["column"]
            op = predicate.get("op")
            value = predicate["value"]
            datatype = predicate.get("datatype")

            if datatype:
                value = cast_to_ibis_type(value, datatype)

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

            column_expr = _[column]

            if op == "isin":
                return column_expr.isin(value)
            if op == "isnull":
                return column_expr.isnull()
            if op == "contains":
                return column_expr.contains(value)

            op_map = {">": "__gt__", ">=": "__ge__", "<": "__lt__", "<=": "__le__", "==": "__eq__", "!=": "__ne__"}
            if op in op_map:
                return getattr(column_expr, op_map[op])(value)

            error_message = f"Unhandled operator: {op}.  Predicate: {predicate}"
            raise ValueError(error_message)

        if isinstance(predicate, list):
            error_message = f"Unexpected list encountered in predicate: {predicate}"
            raise TypeError(error_message)

        error_message = f"Unsupported predicate type: {type(predicate)}"
        raise ValueError(error_message)

    return build_expression(data)
