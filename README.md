# apidump

`apidump` generates a single deterministic Markdown API reference for an installed Python package.

By default, it writes Markdown. It can also optionally emit the same reference information as JSON for structured ingestion.

The intended consumer is an LLM coding agent. The goal is to provide a compact, structured reference file that helps an agent understand a package API the way a human would, without pushing it toward obscure internal symbols or unusual access paths.

## What it does

- Walks an importable Python package and its submodules
- Extracts classes, functions, and class methods
- Filters out private names by default
- Reduces duplicate exposure by choosing one canonical public-facing path per symbol
- Preserves the true defining module as metadata when it differs from the canonical path
- Writes a single reference file with stable ordering in either Markdown or JSON

## Current scope

The current implementation focuses on a conservative callable surface.

- Includes public functions
- Includes public classes
- Includes public methods defined directly on those classes
- Excludes inherited methods
- Excludes properties and non-callable attributes
- Excludes private names by default
- Excludes dunder names by default

## Installation

### With `uv`

Install the project in editable mode:

```bash
uv pip install -e .
```

If you want a build backend configured first, this project uses `hatchling`.

## Usage

Run via module:

```bash
uv run python -m apidump <package>
```

Write to a specific file:

```bash
uv run python -m apidump -o .\outputs\pynapple.md pynapple
```

Generate an extended dump:

```bash
uv run python -m apidump -o .\outputs\pynapple_extended.md --mode extended pynapple
```

Generate the most complete dump:

```bash
uv run python -m apidump -o .\outputs\pynapple_complete.md --mode complete pynapple
```

Generate JSON instead of Markdown:

```bash
uv run python -m apidump -o .\outputs\pynapple.json --mode standard --output-format json pynapple
```

If the console script is installed, you can also run:

```bash
apidump pynapple -o .\outputs\pynapple.md
```

## CLI options

```text
usage: apidump [-h] [-o OUTPUT] [--mode {compact,complete,extended,standard}] [--include-private] [--include-dunder] [--output-format {markdown,json}] package
```

### Positional arguments

- `package`
  - Importable package or module name

### Options

- `-o`, `--output`
  - Output file path

- `--mode {compact,standard,extended,complete}`
  - Controls output detail level

- `--include-private`
  - Include underscore-prefixed names

- `--include-dunder`
  - Include dunder names such as `__enter__`

- `--output-format {markdown,json}`
  - Select the output format
  - Default is `markdown`

## Modes

- `compact`
  - signatures only
  - no methods
  - no docstrings

- `standard`
  - public functions and classes
  - public methods
  - docstrings included

- `extended`
  - broader public surface than `standard`
  - includes utility-style modules
  - still excludes private names

- `complete`
  - broadest introspection-oriented mode
  - includes private names

## Canonical symbol paths

When the same underlying symbol is exposed from multiple places, `apidump` emits a single canonical entry for that symbol.

- It prefers a more public-facing path when possible
- It preserves the true defining module as `defined_in`
- This helps reduce duplicate noise without losing provenance

## Output format

Markdown is the default output format.

### Markdown

The generated Markdown file uses a predictable section layout like this:

```md
# API REFERENCE: <package_name>

## FUNCTION: <name>
module: <module.path>
defined_in: <defining.module.path>
signature: <signature>

<docstring>

---

## CLASS: <name>
module: <module.path>
defined_in: <defining.module.path>
signature: <signature>

<docstring>

### METHODS

- <method_name><signature>
  <docstring>

---
```

### JSON

If you pass `--output-format json`, `apidump` writes a structured JSON document containing the same selected information for the chosen mode.

The JSON includes:

- top-level run metadata such as package name and doc inclusion
- a `symbols` array
- for each symbol:
  - `name`
  - `module`
  - `defined_in`
  - `qualname`
  - `kind`
  - `signature`
  - `doc` when enabled (full cleaned docstring; always present when docs are enabled)
  - `doc_structured` when enabled and parsing finds any structured fields (summary, parameters, returns, raises, examples, deprecated); omitted when empty
  - `methods` for classes (each method may include `doc` and `doc_structured` the same way)

## Logging

`apidump` currently emits basic `INFO`-level logging during a run.

Example:

```text
INFO Generating API reference for pynapple in standard mode
INFO Imported 42 modules
INFO Extracted 187 symbols (192 before deduplication)
INFO Wrote API reference to outputs\pynapple.md
```

If a submodule import fails during traversal, `apidump` logs a warning and continues.

## Example

Generate a reference for `apidump` itself:

```bash
uv run python -m apidump -o .\outputs\apidump.md apidump
```

## Development notes

- Python requirement: `>=3.12`
- Build backend: `hatchling`
- Dev dependency example in this repo: `pynapple`

## Status

This is an early implementation. The current focus is deterministic extraction and clean LLM-oriented formatting rather than exhaustive Python object modeling.
