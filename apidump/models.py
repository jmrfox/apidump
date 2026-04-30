from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Literal

SymbolKind = Literal["function", "class"]


@dataclass(frozen=True, slots=True)
class MethodInfo:
    name: str
    signature: str
    doc: str


@dataclass(frozen=True, slots=True)
class SymbolInfo:
    name: str
    module: str
    defined_in: str
    qualname: str
    kind: SymbolKind
    signature: str
    doc: str
    object_id: int
    methods: tuple[MethodInfo, ...] = field(default_factory=tuple)

    @property
    def identifier(self) -> str:
        return f"{self.module}.{self.qualname}"


@dataclass(frozen=True, slots=True)
class ImportErrorInfo:
    module_name: str
    error_type: str
    message: str


@dataclass(frozen=True, slots=True)
class WalkResult:
    package_name: str
    modules: tuple[ModuleType, ...]
    import_errors: tuple[ImportErrorInfo, ...]


@dataclass(frozen=True, slots=True)
class DumpOptions:
    package: str
    output_path: Path
    mode: str
    include_private: bool
    include_dunder: bool
    include_doc: bool
    include_methods: bool
    exclude_utility_modules: bool
