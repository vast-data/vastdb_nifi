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
- **ImportVastDB**: Imports parquet files from Vast S3 ([docs](./docs/ImportVastDB.md))
- **PutVastDB**: Writes data to a Vast DataBase Table ([docs](./docs/PutVastDB.md))
- **QueryVastDBTable**: Queries a Vast DataBase Table ([docs](./docs/QueryVastDBTable.md))
- **UpdateVastDB**: Updates a Vast DataBase Table ([docs](./docs/UpdateVastDB.md))

**Features**

- Automatic database schema creation and table creation.
- Automatic table schema discovery and table evolution.

## Installation

There are two main options:

- [Docker Run](#docker-run)
- [Apache NiFi Install](#apache-nifi-install)

### Docker Run

First download this extension:

```
mkdir nifi_extensions
cd nifi_extensions

## CHANGE 1.0.8 to the latest release number:
wget https://github.com/vast-data/vastdb_nifi/releases/download/v1.0.8/vastdb_nifi-1.0.8-linux-x86_64-py39.nar
```

Then run docker:

```
cd nifi_extension
docker run --name nifi \
   -p 8443:8443 \
   -d \
   -e SINGLE_USER_CREDENTIALS_USERNAME=admin \
   -e SINGLE_USER_CREDENTIALS_PASSWORD=123456123456 \
   -v .:/opt/nifi/nifi-current/nar_extensions \
   --platform linux/amd64 \
   apache/nifi:2.0.0-M4
```

Then visit: https://localhost:8443 and login with `username: admin` and `password: 123456123456`

Note:
- Due to security requirements with Apache NiFi 2.x these instructions will only work using the localhost (or 127.0.0.1) url.
- The `--platform linux/amd64` is a hard requirement. 

### Apache NiFi Install

 - [NiFi Standard 2.0.0-M4](https://nifi.apache.org/download/) [or later] installed ([install docs](https://nifi.apache.org/docs/nifi-docs/html/getting-started.html#downloading-and-installing-nifi)).  The installation directory will be referred to as `$NIFI_HOME`.
 - Uncomment `nifi.python.command=python3` in `$NIFI_HOME/conf/nifi.properties`
 - Download the [nar file](https://github.com/vast-data/vastdb_nifi/releases/latest) for your platform and Python version
 - Add the nar file to `$NIFI_HOME/extensions`

## Contributing

We welcome contributions from the community!  Please see our [CONTRIBUTING.md](./CONTRIBUTING.md) guide for details on how to get involved. 

## License

`vastdb_nifi` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
