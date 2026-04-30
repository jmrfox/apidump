from __future__ import annotations

import json

from .docstring_parse import format_structured_markdown, parse_docstring, structured_doc_to_json
from .models import SymbolInfo


def _append_doc(lines: list[str], doc: str, include_doc: bool) -> None:
    if include_doc and doc:
        structured = format_structured_markdown(parse_docstring(doc))
        if structured:
            lines.append(structured)
            lines.append("")
        lines.append(doc)
        lines.append("")


def _doc_structured_json(raw: str) -> dict[str, object] | None:
    payload = structured_doc_to_json(parse_docstring(raw))
    return payload if payload else None


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


def _serialize_method(method, include_doc: bool) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": method.name,
        "signature": method.signature,
    }
    if include_doc:
        payload["doc"] = method.doc
        extra = _doc_structured_json(method.doc)
        if extra:
            payload["doc_structured"] = extra
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
            extra = _doc_structured_json(symbol.doc)
            if extra:
                payload["doc_structured"] = extra
        serialized_symbols.append(payload)

    document = {
        "package": package_name,
        "format": "apidump.v1",
        "include_doc": include_doc,
        "symbols": serialized_symbols,
    }
    return json.dumps(document, indent=2) + "\n"
