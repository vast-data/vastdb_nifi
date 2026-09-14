# SPDX-FileCopyrightText: 2024-present VASTDATA <www.vastdata.com>
#
# SPDX-License-Identifier: MIT

"""An opt-in ceiling on the size of a FlowFile a write processor will accept.

PutVastDB, UpdateVastDB and DeleteVastDB read the whole FlowFile into memory
(`getContentsAsBytes`) and decode it into an Arrow table, so a large enough FlowFile can
exhaust the NiFi Python process and get it OOM-killed - an unrecoverable crash rather than a
routed failure.

This guard checks the FlowFile's declared content length (cheap metadata, not a content read)
*before* anything is read, and lets a processor route an over-large FlowFile to `failure`
instead. The ceiling is deliberately operator-set rather than inferred: the safe size depends
on the node's Python memory budget, its concurrency, and the data format's decode expansion
(Parquet in particular decompresses to many times its on-disk size), none of which the
processor can reliably know. For bulk loads, split upstream (e.g. SplitRecord) or use
ImportVastDB, which reads Parquet server-side and never materialises it in the Python process.
"""

import re

from nifiapi.properties import PropertyDescriptor, StandardValidators

_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4, "PB": 1024**5}
_DATA_SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([A-Za-z]+)\s*$")


def max_input_size_descriptor():
    """The shared 'Max Input Size' property descriptor. Empty value disables the guard."""
    return PropertyDescriptor(
        name="Max Input Size",
        description=(
            "Maximum size of an incoming FlowFile's content, e.g. '500 MB' or '2 GB'. The whole "
            "content is read into memory and decoded, so an over-large FlowFile can crash the NiFi "
            "Python process; when set, a FlowFile larger than this is routed to 'failure' without "
            "being read. Leave empty to disable. Note the value is compared against the on-disk "
            "size, which for Parquet is much smaller than the decoded size - set it conservatively. "
            "For bulk loads, split upstream (e.g. SplitRecord) or use ImportVastDB, which reads "
            "Parquet server-side."
        ),
        required=False,
        validators=[StandardValidators.DATA_SIZE_VALIDATOR],
    )


def parse_data_size(value):
    """Parse a NiFi data-size string (e.g. '500 MB') into a byte count. Empty/None -> None."""
    if value is None or not str(value).strip():
        return None
    match = _DATA_SIZE_RE.match(str(value))
    if not match:
        error_message = f"Invalid data size: {value!r}"
        raise ValueError(error_message)
    number, unit = float(match.group(1)), match.group(2).upper()
    if unit == "BYTES":
        unit = "B"
    if unit not in _UNITS:
        error_message = f"Unknown data size unit '{unit}' in {value!r}"
        raise ValueError(error_message)
    return int(number * _UNITS[unit])


def oversize_reason(context, flowfile, descriptor):
    """If the FlowFile exceeds the configured Max Input Size, return an explanatory string;
    otherwise return None. Reads only the FlowFile's size, never its content."""
    limit = parse_data_size(context.getProperty(descriptor.name).getValue())
    if limit is None:
        return None
    size = flowfile.getSize()
    if size > limit:
        return (
            f"FlowFile content is {size} bytes, exceeding the configured Max Input Size of "
            f"{limit} bytes; routing to failure to avoid an out-of-memory crash. Split the input "
            f"upstream (e.g. SplitRecord) or use ImportVastDB for bulk loads."
        )
    return None
