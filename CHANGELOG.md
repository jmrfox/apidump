# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [0.1.0] - 2026-05-01

### Added

- Initial implementation of deterministic API reference generation for installed Python packages
- Symbol extraction: public functions, classes, and class methods
- Four verbosity modes: `compact`, `standard`, `extended`, `complete`
- Markdown output format with stable, predictable section layout
- JSON output format for structured LLM/tool consumption
- Output format inferred from file extension (`.md` or `.json`)
- Hybrid canonical-path policy: prefers public-facing aliases, preserves true defining module as `defined_in` metadata
- Deduplication by underlying object identity across module aliases
- Exclusion of test modules (`test`, `tests`) by default; override with `--include-tests`
- Graceful handling of optional dependency import failures (e.g., `pytest.importorskip` skip exceptions)
- Warning when generated output exceeds 200,000 characters
- CLI with `--mode`, `--include-private`, `--include-dunder`, `--include-tests` flags
- Pytest-based unit test suite covering extraction, formatting, config resolution, and CLI behavior
