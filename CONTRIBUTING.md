# Contributing

Thank you for your interest in contributing to `apidump`.

## Development setup

This project uses [uv](https://docs.astral.sh/uv/) for environment and dependency management.

1. Clone the repository:

   ```bash
   git clone https://github.com/jmrfox/apidump.git
   cd apidump
   ```

2. Install the package and dev dependencies:

   ```bash
   uv sync
   ```

3. Run the test suite to verify your setup:

   ```bash
   uv run pytest
   ```

## Code style

- Python 3.10+ syntax
- Lines must be 79 characters or fewer (Flake8 default)
- No `any` type annotations or intentional type degradation
- Do not add or remove comments without good reason
- Run Flake8 before submitting:

  ```bash
  uv run flake8 src/ tests/
  ```

## Submitting a pull request

1. Fork the repository and create a feature branch from `main`
2. Make your changes with focused, minimal commits
3. Ensure all tests pass: `uv run pytest`
4. Open a pull request with a clear description of what changed and why

## Reporting issues

Please open an issue at <https://github.com/jmrfox/apidump/issues> with:

- A clear description of the problem
- The package name you were running `apidump` against
- The command you ran and the full error output

## Code of Conduct

All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
