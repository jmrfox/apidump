from apidump.config import resolve_options


def test_resolve_options_standard_defaults():
    options = resolve_options(
        package="example_pkg",
        output=None,
        mode="standard",
        include_private=False,
        include_dunder=False,
        include_tests=False,
    )

    assert options.output_path.name == "example_pkg_api.md"
    assert options.mode == "standard"
    assert options.include_doc is True
    assert options.include_methods is True
    assert options.include_private is False
    assert options.include_dunder is False
    assert options.exclude_utility_modules is True


def test_resolve_options_extended_includes_utility_modules():
    options = resolve_options(
        package="example_pkg",
        output="custom.json",
        mode="extended",
        include_private=False,
        include_dunder=False,
        include_tests=False,
    )

    assert options.output_path.name == "custom.json"
    assert options.include_private is False
    assert options.exclude_utility_modules is False


def test_resolve_options_complete_enables_private_symbols():
    options = resolve_options(
        package="example_pkg",
        output="custom.json",
        mode="complete",
        include_private=False,
        include_dunder=False,
        include_tests=False,
    )

    assert options.output_path.name == "custom.json"
    assert options.include_private is True
    assert options.exclude_utility_modules is False
