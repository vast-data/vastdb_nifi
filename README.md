# VastDB NiFi 2.x Processors

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/vast-data/vastdb_nifi?style=flat-square)](https://github.com/vast-data/vastdb_nifi/releases)
[![Build Status](https://github.com/vast-data/vastdb_nifi/actions/workflows/main.yml/badge.svg)](https://github.com/vast-data/vastdb_nifi/actions/workflows/main.yml)
[![Supported Python versions](https://img.shields.io/badge/Python-3.9%20|%203.10%20|%203.11-blue)](https://www.python.org/)
[![Supported Platforms](https://img.shields.io/badge/platform-MacOS%20ARM64%20|%20linux%20AMD64-lightgrey)](https://www.python.org/)
[![code style: ruff](https://img.shields.io/badge/code%20style-ruff-4B4483.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub issues](https://img.shields.io/github/issues/vast-data/vastdb_nifi)](https://github.com/vast-data/vastdb_nifi/issues)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)

-----

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Contributing](#contributing)
- [License](#license)

## Overview

This is a **community supported** project containing NiFi 2.0.0 Python Processors for Vast DataBase:

- **DeleteVastDB**: Deletes Vast DataBase Table rows ([docs](./docs/DeleteVastDB.md))
- **DropVastDBTable**: Drop a Vast DataBase Table ([docs](./docs/DropVastDBTable.md))
- **ImportVastDB**: High performance import of parquet files from Vast S3 ([docs](./docs/ImportVastDB.md))
- **PutVastDB**: Writes data to a Vast DataBase Table ([docs](./docs/PutVastDB.md))
- **QueryVastDBTable**: Queries a Vast DataBase Table ([docs](./docs/QueryVastDBTable.md))
- **UpdateVastDB**: Updates a Vast DataBase Table ([docs](./docs/UpdateVastDB.md))

**Features**

- Automatic database schema creation and table creation.
- Automatic table schema discovery and table evolution.

### Quickstart using Docker

See here: https://vast-data.github.io/data-platform-field-docs/vast_database/nifi/quickstart.html

## Contributing

We welcome contributions from the community!  Please see our [CONTRIBUTING.md](./CONTRIBUTING.md) guide for details on how to get involved. 

## License

`vastdb_nifi` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
