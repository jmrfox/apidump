from __future__ import annotations

import json

from .models import SymbolInfo


def _append_doc(lines: list[str], doc: str, include_doc: bool) -> None:
    if include_doc and doc:
        lines.append(doc)
        lines.append("")


def format_reference(
    package_name: str,
    symbols: list[SymbolInfo],
    include_doc: bool = True,
) -> str:
    lines: list[str] = [f"# API REFERENCE: {package_name}", ""]

    for symbol in sorted(
        symbols,
        key=lambda item: (
            item.module,
            item.kind,
            item.name,
            item.qualname,
        ),
    ):
        lines.append(f"## {symbol.kind.upper()}: {symbol.name}")
        lines.append(f"module: {symbol.module}")
        if symbol.defined_in != symbol.module:
            lines.append(f"defined_in: {symbol.defined_in}")
        lines.append(f"signature: {symbol.signature}")
        lines.append("")

        _append_doc(lines, symbol.doc, include_doc)

        if symbol.kind == "class" and symbol.methods:
            lines.append("### METHODS")
            lines.append("")
            for method in symbol.methods:
                lines.append(f"- {method.name}{method.signature}")
                if include_doc and method.doc:
                    lines.append(f"  {method.doc}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _serialize_method(method, include_doc: bool) -> dict[str, str]:
    payload = {
        "name": method.name,
        "signature": method.signature,
    }
    if include_doc:
        payload["doc"] = method.doc
    return payload


def format_reference_json(
    package_name: str,
    symbols: list[SymbolInfo],
    include_doc: bool = True,
) -> str:
    serialized_symbols: list[dict[str, object]] = []

    for symbol in sorted(
        symbols,
        key=lambda item: (
            item.module,
            item.kind,
            item.name,
            item.qualname,
        ),
    ):
        payload: dict[str, object] = {
            "name": symbol.name,
            "module": symbol.module,
            "defined_in": symbol.defined_in,
            "qualname": symbol.qualname,
            "kind": symbol.kind,
            "signature": symbol.signature,
            "methods": [
                _serialize_method(
                    method,
                    include_doc,
                )
                for method in symbol.methods
            ],
        }
        if include_doc:
            payload["doc"] = symbol.doc
        serialized_symbols.append(payload)

    document = {
        "package": package_name,
        "format": "apidump.v1",
        "include_doc": include_doc,
        "symbols": serialized_symbols,
    }
    return json.dumps(document, indent=2) + "\n"
