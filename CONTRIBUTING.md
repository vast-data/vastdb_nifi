# VastDB NiFi 2.x Processors Developer Documentation

Welcome to the developer documentation for VastDB NiFi 2.x Processors! This guide will help you get started with contributing to the project.

## Table of Contents

- [Project Overview](#project-overview)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
- [Development Workflow](#development-workflow)
    - [Branching Strategy](#branching-strategy)
    - [Coding Standards](#coding-standards)
    - [Testing](#testing)
    - [Pull Requests](#pull-requests)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)
- [Contact](#contact)

## Project Overview

This is a **community supported** project containing NiFi 2.0.0 Python Processors for Vast DataBase:

- **DeleteVastDB**: Deletes Vast DataBase Table rows ([docs](./docs/DeleteVastDB.md))
- **DropVastDBTable**: Drop a Vast DataBase Table ([docs](./docs/DropVastDBTable.md))
- **ImportVastDB**: Imports parquet files from Vast S3 ([docs](./docs/ImportVastDB.md))
- **PutVastDB**: Writes Parquet or JSON data to a Vast DataBase Table ([docs](./docs/PutVastDB.md))
- **QueryVastDBTable**: Queries a Vast DataBase Table ([docs](./docs/QueryVastDBTable.md))

**Features**

- Automatic database schema creation and table creation.
- Automatic table schema discovery and table evolution.

## Getting Started

### Prerequisites

- [NiFi Standard 2.0.0-M4](https://nifi.apache.org/download/) [or later] installed
- Python 3.9+

### Installation

- [NiFi Standard 2.0.0-M4](https://nifi.apache.org/download/) [or later] installed ([install docs](https://nifi.apache.org/docs/nifi-docs/html/getting-started.html#downloading-and-installing-nifi)).  The installation directory will be referred to as `$NIFI_HOME`.
 - Uncomment `nifi.python.command=python3` in `$NIFI_HOME/conf/nifi.properties`

## Development Workflow

### Branching Strategy

### Branching Strategy

We primarily follow a simplified **GitHub Flow** branching strategy with the addition of release tagging on the `main` branch.

* **Main Branch (`main`)**: The `main` branch represents the latest stable release. It should always be in a deployable state.
* **Feature Branches**: All new features and bug fixes are developed on separate feature branches. These branches are created from `main` and named descriptively (e.g., `feature/new-processor` or `fix/query-bug`).
* **Pull Requests**: Once development on a feature branch is complete, a pull request is opened to merge the changes back into `main`. Code reviews and automated tests are conducted before merging.
* **Release Tagging**: When a new version is ready for release, we create a tag on the `main` branch using the format `vX.X.X` (e.g., `v1.2.0`). This tag serves as a reference point for specific releases.

**Additional Notes**

* **Hotfix Branches**: In case of urgent bug fixes on a released version, a hotfix branch can be created from the corresponding release tag. After the fix is applied and tested, it is merged back into both `main` and the release branch.
* **Avoid Direct Commits to `main`**:  Direct commits to `main` should be avoided to maintain its stability. All changes should go through the pull request process. 

### Coding Standards

**Code Formatting**

We use `hatch fmt` to automatically format our code. This helps maintain a consistent style across the project. 

* **Before Committing:**  Run `hatch fmt` to format your code changes. 
* **Pre-commit Hook:**  A pre-commit hook is set up to run `hatch fmt --check` before each commit. This ensures that only correctly formatted code is committed.  Make sure to run `pip install pre-commit` and `pre-commit install` after cloning the repository to enable this hook. 

**Additional Notes on Style:**

* We adhere to the PEP 8 style guide with some minor exceptions configured in the `[tool.ruff]` section of `pyproject.toml`.
* `ruff` is used to enforce code style and catch potential issues. You can run `ruff check .` to lint your code locally. 

**Example:**

```bash
# Format your code
hatch fmt

# Check for style issues 
ruff check .
```

### Testing

- Tests are run with `hatch test`

### Pull Requests

[Describe the process for submitting pull requests and any specific guidelines that developers should follow.]

## Contributing

- Create a GitHub issue to report bugs, suggest features.
- Submit code changes as a pull request.

## Troubleshooting

Coming soon ...

## License

`vastdb_nifi` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Contact

chris.snow@vastdata.com