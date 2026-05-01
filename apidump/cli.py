from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from .config import MODES, resolve_options
from .extractor import deduplicate_symbols, extract_symbols
from .formatter import format_reference, format_reference_json
from .walker import walk_package


LOGGER = logging.getLogger(__name__)
OUTPUT_SUFFIXES = {
    ".md": "markdown",
    ".json": "json",
}
LARGE_OUTPUT_WARNING_THRESHOLD = 200_000


def _infer_output_format(output_path: Path) -> str:
    """Infer output format from file suffix. Defaults to markdown."""
    suffix = output_path.suffix.lower()
    return OUTPUT_SUFFIXES.get(suffix, "markdown")


def _log_mode_guidance(mode: str) -> None:
    if mode == "compact":
        LOGGER.warning(
            "Compact mode is not usually the optimal setting for agent use: "
            "it omits docstrings and methods, so it is best when compactness "
            "matters more than guidance. Standard mode is usually recommended."
        )
    elif mode == "extended":
        LOGGER.info(
            "Extended mode includes additional public helper-oriented surface "
            "beyond standard mode while still avoiding private internals."
        )
    elif mode == "complete":
        LOGGER.warning(
            "Complete mode is not usually the optimal setting for agent use: "
            "it "
            "includes more internal and private API surface, which can make "
            "the "
            "reference noisier. Standard mode is usually recommended."
        )


def _warn_if_output_is_large(reference: str) -> None:
    if len(reference) >= LARGE_OUTPUT_WARNING_THRESHOLD:
        LOGGER.warning(
            "Generated output is very large (%d characters). "
            "Consider using standard mode or a narrower target package if you "
            "want a smaller reference.",
            len(reference),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apidump",
        description=(
            "Generate a deterministic Markdown API reference for an "
            "installed Python package."
        ),
    )
    parser.add_argument("package", help="Importable package or module name")
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path",
    )
    parser.add_argument(
        "--mode",
        default="standard",
        choices=sorted(MODES),
        help="Detail level for the generated reference",
    )
    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include names beginning with an underscore",
    )
    parser.add_argument(
        "--include-dunder",
        action="store_true",
        help="Include dunder names such as __enter__",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = build_parser()
    args = parser.parse_args(argv)
    options = resolve_options(
        package=args.package,
        output=args.output,
        mode=args.mode,
        include_private=args.include_private,
        include_dunder=args.include_dunder,
    )
    output_format = _infer_output_format(options.output_path)

    LOGGER.info(
        "Generating API reference for %s in %s mode",
        options.package,
        options.mode,
    )
    _log_mode_guidance(options.mode)

    walk_result = walk_package(
        package_name=options.package,
        include_private=options.include_private,
    )

    LOGGER.info(
        "Imported %d modules",
        len(walk_result.modules),
    )

    for import_error in walk_result.import_errors:
        LOGGER.warning(
            "Skipped module %s due to %s: %s",
            import_error.module_name,
            import_error.error_type,
            import_error.message,
        )

    symbols = []
    for module in walk_result.modules:
        symbols.extend(
            extract_symbols(
                module=module,
                include_private=options.include_private,
                include_dunder=options.include_dunder,
                include_methods=options.include_methods,
                exclude_utility_modules=options.exclude_utility_modules,
            )
        )

    deduplicated_symbols = deduplicate_symbols(symbols)
    LOGGER.info(
        "Extracted %d symbols (%d before deduplication)",
        len(deduplicated_symbols),
        len(symbols),
    )

    if output_format == "json":
        reference = format_reference_json(
            package_name=options.package,
            symbols=deduplicated_symbols,
            include_doc=options.include_doc,
        )
    else:
        reference = format_reference(
            package_name=options.package,
            symbols=deduplicated_symbols,
            include_doc=options.include_doc,
        )
    _warn_if_output_is_large(reference)
    options.output_path.write_text(reference, encoding="utf-8")
    LOGGER.info("Wrote API reference to %s", options.output_path)
    return 0
