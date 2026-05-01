from types import ModuleType

from apidump.extractor import deduplicate_symbols, extract_symbols


class Sample:
    def method(self):
        return 1

    def __repr__(self):
        return "Sample()"


def sample_function():
    return 1


def _private_function():
    return 0


Sample.__module__ = "fake.module"
sample_function.__module__ = "fake.module"
_private_function.__module__ = "fake.module"


UTILITY_FUNCTION_NAME = "visible_from_utils"


def visible_from_utils():
    return 1


visible_from_utils.__module__ = "fake.utils"


def test_extract_symbols_excludes_private_and_dunder_by_default():
    module = ModuleType("fake.module")
    module.Sample = Sample
    module.sample_function = sample_function
    module._private_function = _private_function

    symbols = extract_symbols(module)
    names = {symbol.name for symbol in symbols}

    assert "Sample" in names
    assert "sample_function" in names
    assert "_private_function" not in names

    sample_symbol = next(
        symbol for symbol in symbols if symbol.name == "Sample"
    )
    method_names = {method.name for method in sample_symbol.methods}
    assert "method" in method_names
    assert "__repr__" not in method_names


def test_extract_symbols_can_exclude_utility_modules():
    module = ModuleType("fake.utils")
    setattr(module, UTILITY_FUNCTION_NAME, visible_from_utils)

    symbols = extract_symbols(module, exclude_utility_modules=True)

    assert symbols == []


def test_deduplicate_symbols_collapses_same_object_identity() -> None:
    module_one = ModuleType("pkg.one")
    module_two = ModuleType("pkg.two")

    def shared():
        return 1

    shared.__module__ = "pkg.one"
    setattr(module_one, "shared", shared)
    setattr(module_two, "shared", shared)

    first = extract_symbols(module_one)
    second = [symbol for symbol in extract_symbols(module_two)]
    deduplicated = deduplicate_symbols(first + second)

    assert len(deduplicated) == 1
    assert deduplicated[0].name == "shared"


def test_deduplicate_symbols_prefers_public_alias_path() -> None:
    package_module = ModuleType("pkg")
    internal_module = ModuleType("pkg.internal.core")

    def shared():
        return 1

    shared.__module__ = "pkg.internal.core"
    setattr(package_module, "shared", shared)
    setattr(internal_module, "shared", shared)

    extracted = (
        extract_symbols(package_module)
        + extract_symbols(internal_module)
    )
    deduplicated = deduplicate_symbols(extracted)

    assert len(deduplicated) == 1
    assert deduplicated[0].module == "pkg"
    assert deduplicated[0].defined_in == "pkg.internal.core"
