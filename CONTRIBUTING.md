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

### Pull Requests

We use a standard pull request (PR) workflow to facilitate code reviews and ensure the quality of contributions.

**Process**

1. **Fork the repository:** Create your own copy of the repository on GitHub.
2. **Create a branch:**  From your forked repository, create a new branch for your feature or bug fix. Follow the branching strategy outlined above (e.g., `feature/new-processor` or `fix/query-bug`).
3. **Make your changes:**  Implement your changes on your branch, ensuring that the code adheres to the coding standards and passes all tests.
4. **Commit and push:**  Commit your changes with clear and descriptive commit messages. Push your branch to your forked repository.
5. **Open a pull request:**  From your forked repository, open a pull request against the `main` branch of the original repository.
6. **Code review and testing:** The maintainers will review your code and provide feedback. Automated tests will also be run to ensure the changes don't introduce any regressions.
7. **Address feedback:**  Address any feedback or requested changes from the code review.
8. **Merge:** Once the code review is complete and all tests pass, your pull request will be merged into the `main` branch.

**Guidelines**

* **Clear and descriptive PR titles:**  Use a concise and informative title that summarizes the changes in your pull request.
* **Detailed descriptions:** Provide a detailed description of the changes, including the motivation behind them and any relevant implementation details.
* **Reference issues:** If your pull request addresses a specific issue, reference it in the description.
* **Small and focused PRs:** Keep your pull requests small and focused on a single feature or bug fix. This makes them easier to review and reduces the risk of conflicts.
* **Tests:** Include tests for any new code or changes to existing code.
* **Documentation:** Update any relevant documentation to reflect your changes.

## Contributing

- Create a GitHub issue to report bugs, suggest features.
- Submit code changes as a pull request.

## Troubleshooting

Coming soon ...

## License

`vastdb_nifi` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Contact

chris.snow@vastdata.com
