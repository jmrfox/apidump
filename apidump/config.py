from __future__ import annotations

from pathlib import Path

from .models import DumpOptions

MODES = {
    "compact": {
        "include_doc": False,
        "include_methods": False,
        "include_private": False,
        "include_dunder": False,
        "exclude_utility_modules": True,
        "exclude_tests": True,
    },
    "standard": {
        "include_doc": True,
        "include_methods": True,
        "include_private": False,
        "include_dunder": False,
        "exclude_utility_modules": True,
        "exclude_tests": True,
    },
    "extended": {
        "include_doc": True,
        "include_methods": True,
        "include_private": False,
        "include_dunder": False,
        "exclude_utility_modules": False,
        "exclude_tests": True,
    },
    "complete": {
        "include_doc": True,
        "include_methods": True,
        "include_private": True,
        "include_dunder": False,
        "exclude_utility_modules": False,
        "exclude_tests": True,
    },
}


def resolve_options(
    package: str,
    output: str | None,
    mode: str,
    include_private: bool,
    include_dunder: bool,
    include_tests: bool,
) -> DumpOptions:
    if mode not in MODES:
        valid_modes = ", ".join(sorted(MODES))
        raise ValueError(
            f"Unsupported mode '{mode}'. " f"Expected one of: {valid_modes}"
        )

    mode_config = MODES[mode]
    output_path = Path(output) if output else Path(f"{package}_api.md")

    resolved_include_private = mode_config["include_private"] or include_private
    resolved_include_dunder = mode_config["include_dunder"] or include_dunder
    resolved_exclude_tests = not include_tests and mode_config["exclude_tests"]

    return DumpOptions(
        package=package,
        output_path=output_path,
        mode=mode,
        include_private=resolved_include_private,
        include_dunder=resolved_include_dunder,
        include_doc=mode_config["include_doc"],
        include_methods=mode_config["include_methods"],
        exclude_utility_modules=mode_config["exclude_utility_modules"],
        exclude_tests=resolved_exclude_tests,
    )
