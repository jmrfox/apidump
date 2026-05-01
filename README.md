# apidump

`apidump` generates a single deterministic API reference file for an installed Python package, particularly geared toward LLM agent consumption.
The goal is to provide a compact, structured reference file that helps an agent understand a package API the way a human would, without pushing it toward obscure internal symbols or unusual access paths.

## Motivation

Have you ever asked an LLM agent to generate some code using a specific Python package, only for it to confidently call methods that did not exist?
I found that providing a clear and concise static API reference file in the agent context helps mediate this issue.

However, deciding exactly what to include in the reference file can be tricky, as there are significant downsides to including too much information.
The agent may use methods that are public but not commonly used, intended to be internal, or use methods in an unconventional way, leading to obscure code.
Hence, `apidump` provides different modes to control the level of detail, and the default mode tries to strike a balance.

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

## Quick start

```bash
uv add --dev https://github.com/jmrfox/apidump.git
uv run python -m apidump -o api_reference.json numpy
```

This produces a structured JSON file like:

```json
{
  "package": "numpy",
  "mode": "standard",
  "symbols": [
    {
      "name": "numpy.array",
      "kind": "function",
      "signature": "(object, dtype=None, ...)",
      "doc": "Create an array..."
    }
  ]
}
```

## Installation & Usage

Requires Python 3.10 or higher.

If you use `uv`, install `apidump` as a dev dependency:

```bash
uv add --dev https://github.com/jmrfox/apidump.git
```

Then, run it:

```bash
uv run python -m apidump -o <output> <package>
```

Write to a specific file:

```bash
uv run python -m apidump -o .windsurf\api_references\pynapple.json pynapple
```

Generate an extended dump:

```bash
uv run python -m apidump -o .windsurf\api_references\pynapple_extended.json --mode extended pynapple
```

Generate the most complete dump:

```bash
uv run python -m apidump -o .windsurf\api_references\pynapple_complete.json --mode complete pynapple
```

Generate Markdown instead of JSON (just use `.md` suffix in the output path):

```bash
uv run python -m apidump -o .windsurf\api_references\pynapple.md --mode standard pynapple
```

## CLI options

```text
usage: apidump [-h] -o OUTPUT [--mode {compact,complete,extended,standard}] [--include-private] [--include-dunder] [--include-tests] package
```

### Positional arguments

- `package`
  - Importable package or module name

### Options

- `-o`, `--output` (required)
  - Output file path (.json or .md)

- `--mode {compact,standard,extended,complete}`
  - Controls output detail level (default = standard)

- `--include-private`
  - Include underscore-prefixed names (default = exclude)

- `--include-dunder`
  - Include dunder names such as `__enter__` (default = exclude)

- `--include-tests`
  - Include test modules (submodules named `test` or `tests`) (default = exclude)

## Modes

| Attribute | compact | standard | extended | complete |
| :---------- | :-----: | :------: | :------: | :------: |
| Public functions | ✅ | ✅ | ✅ | ✅ |
| Public classes | ✅ | ✅ | ✅ | ✅ |
| Docstrings | ❌ | ✅ | ✅ | ✅ |
| Methods | ❌ | ✅ | ✅ | ✅ |
| Utility modules (utils, helpers, internals) | ❌ | ❌ | ✅ | ✅ |
| Private names[^1] | ❌ | ❌ | ❌ | ✅ |
| Dunder methods[^2] | ❌ | ❌ | ❌ | ❌ |
| Test modules[^3] | ❌ | ❌ | ❌ | ❌ |

[^1]: Private names are those with names starting with a single underscore (e.g., `_private_function`, `_PrivateClass`).

[^2]: Dunder methods are those with names starting and ending with double underscores (e.g., `__init__`, `__enter__`).

[^3]: Test modules are those with names containing "test" or "tests" (case-insensitive).

<!-- - `compact`
  - Minimal output for token-constrained contexts
  - Includes only function and class signatures
  - Excludes class methods entirely
  - Excludes docstrings to reduce size
  - Excludes utility modules (`utils`, `helpers`, `internals`)
  - Excludes test modules (`test`, `tests`)
  - Best when you need only the callable surface with minimal overhead

- `standard` (default)
  - Balanced detail for typical agent use
  - Includes public functions and classes
  - Includes public methods defined directly on classes
  - Includes docstrings for context and usage guidance
  - Excludes private names (underscore-prefixed)
  - Excludes dunder names (`__init__`, `__enter__`, etc.)
  - Excludes utility modules to focus on main API surface
  - Excludes test modules (`test`, `tests`)
  - Recommended starting point for most packages

- `extended`
  - Broader public surface than `standard`
  - Also includes utility-style modules (`utils`, `helpers`, `internals`)
  - Excludes private names and dunder methods
  - Excludes test modules (`test`, `tests`)
  - Useful when you need access to helper functions and internal utilities
  - Good for packages where utility modules are part of the public API

- `complete`
  - Broadest introspection-oriented mode
  - Includes everything in `extended` mode
  - Also includes private names (underscore-prefixed functions and classes)
  - Excludes dunder methods unless `--include-dunder` is passed
  - Excludes test modules unless `--include-tests` is passed
  - Includes all modules including internal helpers
  - Specific use cases only: debugging, understanding internals, or exploring private APIs
  - Not recommended for typical usage due to noise from internal implementation details -->

## Canonical symbol paths

When the same underlying symbol is exposed from multiple places, `apidump` emits a single canonical entry for that symbol.

- It prefers a more public-facing path when possible
- It preserves the true defining module as `defined_in`
- This helps reduce duplicate noise without losing provenance

## Output format

The output format is determined by the file extension you provide. You must use either `.json` or `.md`:

- `.json` → JSON (structured, optimal for LLM consumption)
- `.md` → Markdown (human-readable)

### JSON

If you use `.json` as the output file extension, `apidump` writes a structured JSON document containing the same selected information for the chosen mode.

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

## Development notes

- Python requirement: `>=3.10`
- Build backend: `hatchling`
- Source layout: `src/`

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and how to submit a pull request.

Please read and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

MIT License. See [LICENSE](LICENSE) for details.
