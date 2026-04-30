from __future__ import annotations

import inspect
from types import ModuleType
from typing import Any

from .models import MethodInfo, SymbolInfo


UTILITY_MODULE_PARTS = {
    "utils",
    "util",
    "helpers",
    "helper",
}


def _is_dunder_name(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _is_public_name(
    name: str,
    include_private: bool,
    include_dunder: bool,
) -> bool:
    if include_dunder and _is_dunder_name(name):
        return True
    if include_private:
        return True
    return not name.startswith("_")


def _is_utility_module(module_name: str) -> bool:
    parts = set(module_name.split("."))
    return any(part in parts for part in UTILITY_MODULE_PARTS)


def _should_include_method(
    name: str,
    include_private: bool,
    include_dunder: bool,
) -> bool:
    if name == "__init__":
        return False
    if _is_dunder_name(name):
        return include_dunder
    if include_private:
        return True
    return not name.startswith("_")


def _should_include_symbol(
    module_name: str,
    name: str,
    include_private: bool,
    include_dunder: bool,
    exclude_utility_modules: bool,
) -> bool:
    if exclude_utility_modules and _is_utility_module(module_name):
        return False
    return _is_public_name(name, include_private, include_dunder)


def _canonical_rank(symbol: SymbolInfo) -> tuple[int, int, int, str, str]:
    module_parts = symbol.module.split(".")
    defining_parts = symbol.defined_in.split(".")
    is_root_like = 0 if len(module_parts) <= 2 else 1
    is_alias = 0 if symbol.module != symbol.defined_in else 1
    definition_depth = len(defining_parts)
    return (
        is_root_like,
        is_alias,
        definition_depth,
        symbol.module,
        symbol.qualname,
    )


def _safe_signature(obj: Any) -> str:
    try:
        return str(inspect.signature(obj))
    except Exception:
        return "(...)"


def _safe_doc(obj: Any) -> str:
    return inspect.getdoc(obj) or ""


def _is_supported_function(obj: Any) -> bool:
    return bool(
        inspect.isfunction(obj)
        or inspect.isbuiltin(obj)
        or inspect.iscoroutinefunction(obj)
    )


def _extract_methods(
    cls: type[Any],
    include_private: bool,
    include_dunder: bool,
) -> tuple[MethodInfo, ...]:
    methods: list[MethodInfo] = []

    for name, value in sorted(cls.__dict__.items()):
        if not _should_include_method(
            name,
            include_private,
            include_dunder,
        ):
            continue

        unwrapped = value
        if isinstance(value, (staticmethod, classmethod)):
            unwrapped = value.__func__

        if not _is_supported_function(unwrapped):
            continue

        methods.append(
            MethodInfo(
                name=name,
                signature=_safe_signature(unwrapped),
                doc=_safe_doc(unwrapped),
            )
        )

    return tuple(methods)


def _class_signature(cls: type[Any]) -> str:
    try:
        return str(inspect.signature(cls))
    except Exception:
        init = cls.__dict__.get("__init__")
        if init is None:
            return "(...)"
        return _safe_signature(init)


def extract_symbols(
    module: ModuleType,
    include_private: bool = False,
    include_dunder: bool = False,
    include_methods: bool = True,
    exclude_utility_modules: bool = False,
) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []

    for name, obj in sorted(
        inspect.getmembers(module),
        key=lambda item: item[0],
    ):
        if not _should_include_symbol(
            module.__name__,
            name,
            include_private,
            include_dunder,
            exclude_utility_modules,
        ):
            continue

        object_module = getattr(obj, "__module__", None)
        if object_module is None:
            continue

        if inspect.isclass(obj):
            methods: tuple[MethodInfo, ...] = ()
            if include_methods:
                methods = _extract_methods(
                    obj,
                    include_private,
                    include_dunder,
                )
            symbols.append(
                SymbolInfo(
                    name=name,
                    module=module.__name__,
                    defined_in=object_module,
                    qualname=getattr(obj, "__qualname__", name),
                    kind="class",
                    signature=_class_signature(obj),
                    doc=_safe_doc(obj),
                    object_id=id(obj),
                    methods=methods,
                )
            )
            continue

        if _is_supported_function(obj):
            symbols.append(
                SymbolInfo(
                    name=name,
                    module=module.__name__,
                    defined_in=object_module,
                    qualname=getattr(obj, "__qualname__", name),
                    kind="function",
                    signature=_safe_signature(obj),
                    doc=_safe_doc(obj),
                    object_id=id(obj),
                )
            )

    return symbols


def deduplicate_symbols(symbols: list[SymbolInfo]) -> list[SymbolInfo]:
    by_identifier: dict[str, SymbolInfo] = {}
    by_object: dict[tuple[str, str, int], list[SymbolInfo]] = {}

    for symbol in sorted(
        symbols,
        key=lambda item: (item.module, item.kind, item.name, item.qualname),
    ):
        by_identifier.setdefault(symbol.identifier, symbol)

    for symbol in by_identifier.values():
        object_key = (symbol.kind, symbol.name, symbol.object_id)
        by_object.setdefault(object_key, []).append(symbol)

    deduplicated: list[SymbolInfo] = []
    for candidates in by_object.values():
        canonical = min(candidates, key=_canonical_rank)
        deduplicated.append(canonical)

    return sorted(
        deduplicated,
        key=lambda item: (item.module, item.kind, item.name, item.qualname),
    )
