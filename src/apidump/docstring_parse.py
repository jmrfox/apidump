from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

# Recognized section titles (normalized key -> regex for line start).
_GOOGLE_SECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "args",
        re.compile(r"^(?:Args|Arguments|Parameters|Params)\s*:\s*(.*)$", re.I),
    ),
    (
        "other_params",
        re.compile(r"^(?:Other\s+Parameters|Other\s+Args)\s*:\s*(.*)$", re.I),
    ),
    (
        "returns",
        re.compile(r"^(?:Returns?|Return\s+values?)\s*:\s*(.*)$", re.I),
    ),
    ("yields", re.compile(r"^Yields?\s*:\s*(.*)$", re.I)),
    (
        "raises",
        re.compile(r"^(?:Raises?|Exceptions?|Errors?)\s*:\s*(.*)$", re.I),
    ),
    ("examples", re.compile(r"^(?:Examples?)\s*:\s*(.*)$", re.I)),
    ("notes", re.compile(r"^(?:Notes?|Note)\s*:\s*(.*)$", re.I)),
    ("warnings", re.compile(r"^(?:Warnings?|Warning)\s*:\s*(.*)$", re.I)),
    ("attributes", re.compile(r"^Attributes\s*:\s*(.*)$", re.I)),
    ("see_also", re.compile(r"^See\s+Also\s*:\s*(.*)$", re.I)),
)

_NUMPY_PARAMETERS_HEADER = re.compile(
    r"^\s*Parameters\s*\n\s*-{3,}\s*$",
    re.MULTILINE | re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ParamInfo:
    name: str
    type: str | None
    description: str


@dataclass(frozen=True, slots=True)
class ReturnInfo:
    type: str | None
    description: str


@dataclass(frozen=True, slots=True)
class RaiseInfo:
    exception: str
    description: str


@dataclass(frozen=True, slots=True)
class DeprecatedInfo:
    message: str
    version: str | None
    replacement: str | None


@dataclass(frozen=True, slots=True)
class StructuredDoc:
    summary: str | None
    parameters: tuple[ParamInfo, ...]
    returns: ReturnInfo | None
    raises: tuple[RaiseInfo, ...]
    examples: tuple[str, ...]
    deprecated: DeprecatedInfo | None


_DEPRECATED_BLOCK = re.compile(
    r"^\s*\.\.\s*deprecated::\s*([^\n]*)\n((?:^[ \t]+.*\n?)*)",
    re.MULTILINE | re.IGNORECASE,
)

# Inline / short Sphinx deprecation on its own line
_DEPRECATED_LINE = re.compile(
    r"^\s*:deprecated:\s*(.+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def _strip_blank_edges(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _dedent_block(lines: list[str]) -> str:
    lines = _strip_blank_edges([line.rstrip() for line in lines])
    if not lines:
        return ""
    indents = [
        len(line) - len(line.lstrip()) for line in lines if line.strip()
    ]
    margin = min(indents) if indents else 0
    trimmed = [
        line[margin:] if len(line) >= margin else line for line in lines
    ]
    return "\n".join(trimmed).strip()


def _extract_deprecated(text: str) -> tuple[str, DeprecatedInfo | None]:
    """Remove deprecated directives from *text* and return (cleaned, info)."""
    dep: DeprecatedInfo | None = None

    def repl_block(match: re.Match[str]) -> str:
        nonlocal dep
        first = match.group(1).strip()
        body_lines = match.group(2).splitlines()
        body = _dedent_block(body_lines)
        version, replacement, message = _parse_deprecated_content(first, body)
        dep = DeprecatedInfo(
            message=message.strip(),
            version=version,
            replacement=replacement,
        )
        return ""

    cleaned = _DEPRECATED_BLOCK.sub(repl_block, text)

    mline = _DEPRECATED_LINE.search(cleaned)
    if mline and dep is None:
        dep = DeprecatedInfo(
            message=mline.group(1).strip(),
            version=None,
            replacement=None,
        )
        cleaned = cleaned[:mline.start()] + cleaned[mline.end():]

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, dep


def _parse_deprecated_content(
    first_line: str,
    body: str,
) -> tuple[str | None, str | None, str]:
    """
    Parse Sphinx-style '.. deprecated:: X.Y' plus optional body with
    'Use :func:`other` instead.' patterns into (version, replacement, message).
    """
    version = first_line.strip() or None
    message_parts: list[str] = []
    if version:
        message_parts.append(version)
    replacement: str | None = None

    text = body.strip()
    if text:
        message_parts.append(text)
        repl_m = re.search(
            r"(?:Use|Replace(?:d)?\s+with)\s+[`:A-Za-z0-9_.]+\s*`([^`]+)`",
            text,
            re.IGNORECASE,
        )
        if repl_m:
            replacement = repl_m.group(1).strip()
        repl_m2 = re.search(
            r"Use\s+``([^`]+)``\s+instead",
            text,
            re.IGNORECASE,
        )
        if repl_m2:
            replacement = repl_m2.group(1).strip()

    message = "\n".join(message_parts).strip()
    if not message:
        message = "deprecated"
    return version, replacement, message


def _first_paragraph(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    return text.split("\n\n", 1)[0].strip()


def _first_sentence(paragraph: str) -> str:
    paragraph = re.sub(r"\s+", " ", paragraph).strip()
    if not paragraph:
        return ""
    # Prefer sentence boundary before space + capital / quote / digit.
    match = re.match(
        r"^(.+?[.!?])(?:\s+(?=[\d\"'(\[]|[A-Z])|\s*$)",
        paragraph,
    )
    if match:
        return match.group(1).strip()
    return paragraph


def _summary_from_preamble(preamble: str) -> str | None:
    para = _first_paragraph(preamble)
    if not para:
        return None
    sent = _first_sentence(para)
    return sent or None


def _split_google_sections(text: str) -> tuple[str, dict[str, str]]:
    """Split *text* into preamble and Google-style section bodies."""
    lines = text.splitlines()
    preamble_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in lines:
        matched_key: str | None = None
        inline_rest: str | None = None
        for key, pattern in _GOOGLE_SECTION_PATTERNS:
            m = pattern.match(line.strip())
            if m:
                matched_key = key
                inline_rest = m.group(1)
                break

        if matched_key:
            if matched_key == "other_params":
                matched_key = "args"
            current = matched_key
            if inline_rest and inline_rest.strip():
                sections.setdefault(current, []).append(inline_rest)
            continue

        if current is None:
            preamble_lines.append(line)
        else:
            sections.setdefault(current, []).append(line)

    preamble = "\n".join(preamble_lines).strip()
    joined = {k: "\n".join(v).rstrip() for k, v in sections.items()}
    return preamble, joined


def _parse_numpy_parameters(block: str) -> list[ParamInfo]:
    """Parse a NumPy-style ``name : type`` parameter block (body only)."""
    lines = block.splitlines()
    params: list[ParamInfo] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        m = re.match(r"^(\S+)\s*:\s*(.*)$", stripped)
        if not m:
            i += 1
            continue
        name, first_rest = m.group(1), m.group(2).strip()
        if name.lower() == "parameters":
            i += 1
            continue
        base_indent = len(line) - len(line.lstrip())
        i += 1
        cont_lines: list[str] = []
        while i < len(lines):
            cont = lines[i]
            if not cont.strip():
                cont_lines.append("")
                i += 1
                continue
            indent = len(cont) - len(cont.lstrip())
            if indent > base_indent:
                cont_lines.append(cont.rstrip())
                i += 1
                continue
            break
        desc = _dedent_block(cont_lines) if cont_lines else ""
        if cont_lines:
            params.append(
                ParamInfo(name=name, type=first_rest or None, description=desc)
            )
        else:
            params.append(
                ParamInfo(name=name, type=None, description=first_rest)
            )
    return params


def _extract_numpy_parameters(text: str) -> tuple[str, list[ParamInfo]]:
    m = _NUMPY_PARAMETERS_HEADER.search(text)
    if not m:
        return text, []
    start, end = m.span()
    raw_lines = text[end:].splitlines()
    body_lines: list[str] = []
    i = 0
    while i < len(raw_lines):
        stripped = raw_lines[i].strip()
        if (
            i + 1 < len(raw_lines)
            and re.match(r"^[A-Za-z][A-Za-z0-9_ ]*$", stripped)
            and re.match(r"^-{3,}$", raw_lines[i + 1].strip())
        ):
            break
        body_lines.append(raw_lines[i])
        i += 1
    block = "\n".join(body_lines)
    params = _parse_numpy_parameters(block)
    tail = "\n".join(raw_lines[i:])
    head = text[:start].rstrip()
    tail_stripped = tail.lstrip()
    if head and tail_stripped:
        cleaned = f"{head}\n\n{tail_stripped}"
    else:
        cleaned = head + tail_stripped
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, params


_GOOGLE_PARAM_LINE = re.compile(
    r"^(\s*)(?P<name>(?:\*{1,2})?\w+)\s*(?:\((?P<type>[^)]+)\))?"
    r"\s*:\s*(?P<desc>.*)$",
)


def _parse_google_parameters(block: str) -> list[ParamInfo]:
    lines = block.splitlines()
    params: list[ParamInfo] = []
    current_name: str | None = None
    current_type: str | None = None
    current_desc: list[str] = []
    current_indent: int | None = None

    def flush() -> None:
        nonlocal current_name, current_type, current_desc, current_indent
        if current_name is not None:
            desc = "\n".join(current_desc).strip()
            params.append(
                ParamInfo(
                    name=current_name,
                    type=current_type,
                    description=desc,
                )
            )
        current_name = None
        current_type = None
        current_desc = []
        current_indent = None

    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip():
            if current_name is not None:
                current_desc.append("")
            continue
        m = _GOOGLE_PARAM_LINE.match(line)
        if m and m.group("name"):
            indent = len(m.group(1))
            if (
                current_indent is not None
                and indent > current_indent
                and current_name
            ):
                current_desc.append(line.strip())
                continue
            flush()
            current_name = m.group("name").strip()
            typ = m.group("type")
            current_type = typ.strip() if typ else None
            desc = m.group("desc") or ""
            current_desc = [desc] if desc.strip() else []
            current_indent = indent
            continue
        if current_name is not None:
            current_desc.append(line)
    flush()
    return params


_SPHINX_PARAM = re.compile(
    r"^\s*:param\s+(?P<name>[\w.]+):\s*(?P<desc>.*)\s*$",
    re.IGNORECASE,
)
_SPHINX_TYPE = re.compile(
    r"^\s*:type\s+(?P<name>[\w.]+):\s*(?P<type>.+)\s*$",
    re.IGNORECASE,
)
_SPHINX_RETURNS = re.compile(
    r"^\s*:returns?:\s*(?P<desc>.*)\s*$",
    re.IGNORECASE,
)
_SPHINX_RTYPE = re.compile(
    r"^\s*:rtype:\s*(?P<type>.+)\s*$",
    re.IGNORECASE,
)
_SPHINX_RAISES = re.compile(
    r"^\s*:raises\s+(?P<exc>[\w.]+):\s*(?P<desc>.*)\s*$",
    re.IGNORECASE,
)


def _parse_sphinx_fields(
    text: str,
) -> tuple[list[ParamInfo], ReturnInfo | None, list[RaiseInfo]]:
    param_types: dict[str, str | None] = {}
    param_descs: dict[str, list[str]] = defaultdict(list)
    return_desc: list[str] = []
    return_type: str | None = None
    raises: list[RaiseInfo] = []

    for line in text.splitlines():
        mp = _SPHINX_PARAM.match(line)
        if mp:
            name = mp.group("name")
            desc = mp.group("desc").strip()
            if desc:
                param_descs[name].append(desc)
            continue
        mt = _SPHINX_TYPE.match(line)
        if mt:
            name = mt.group("name")
            typ = mt.group("type").strip()
            param_types[name] = typ
            continue
        mr = _SPHINX_RETURNS.match(line)
        if mr:
            d = mr.group("desc").strip()
            if d:
                return_desc.append(d)
            continue
        mrt = _SPHINX_RTYPE.match(line)
        if mrt:
            return_type = mrt.group("type").strip()
            continue
        mrz = _SPHINX_RAISES.match(line)
        if mrz:
            raises.append(
                RaiseInfo(
                    exception=mrz.group("exc").strip(),
                    description=mrz.group("desc").strip(),
                )
            )
            continue

    params: list[ParamInfo] = []
    for name in sorted(set(param_types) | set(param_descs)):
        typ = param_types.get(name)
        desc = "\n".join(param_descs.get(name, [])).strip()
        params.append(ParamInfo(name=name, type=typ, description=desc))

    ret: ReturnInfo | None = None
    if return_desc or return_type:
        ret = ReturnInfo(
            type=return_type,
            description="\n".join(return_desc).strip(),
        )
    return params, ret, raises


_GOOGLE_RAISE_LINE = re.compile(
    r"^\s*(?P<exc>[\w.]+)\s*:\s*(?P<desc>.*)\s*$",
)


def _parse_raises_block(block: str) -> list[RaiseInfo]:
    raises: list[RaiseInfo] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = _GOOGLE_RAISE_LINE.match(line)
        if m:
            raises.append(
                RaiseInfo(
                    exception=m.group("exc"),
                    description=m.group("desc").strip(),
                )
            )
    return raises


def _looks_like_return_type(token: str) -> bool:
    if not token or len(token) > 120:
        return False
    t = token.strip()
    if t.lower() in {
        "note",
        "notes",
        "warning",
        "warnings",
        "see",
        "todo",
    }:
        return False
    if "[" in t or "|" in t:
        return True
    builtins = {
        "str",
        "int",
        "float",
        "bool",
        "bytes",
        "dict",
        "list",
        "set",
        "tuple",
        "type",
        "object",
        "None",
    }
    if t in builtins:
        return True
    return bool(t[0].isupper())


def _parse_returns_block(block: str) -> ReturnInfo | None:
    block = block.strip()
    if not block:
        return None
    lines = block.splitlines()
    first = lines[0].strip()
    m = re.match(r"^([^\s:]+?)\s*:\s*(.+)$", first)
    if m:
        left, right = m.group(1).strip(), m.group(2).strip()
        if right and _looks_like_return_type(left):
            body = "\n".join(
                [right, *[ln.rstrip() for ln in lines[1:]]]
            ).strip()
            return ReturnInfo(type=left, description=body)
    return ReturnInfo(type=None, description=block)


def _split_example_blocks(body: str) -> tuple[str, ...]:
    body = body.strip()
    if not body:
        return ()
    parts = re.split(r"\n\s*\n", body)
    blocks = [p.strip() for p in parts if p.strip()]
    return tuple(blocks) if blocks else (body,)


def parse_docstring(doc: str) -> StructuredDoc:
    """
    Parse a cleaned docstring (e.g. from inspect.getdoc) into
    structured fields.

    Supports Google-style sections, a subset of NumPy parameter blocks, and
    common Sphinx :param / :returns / :raises lines when no Google Args section
    is present.
    """
    raw = (doc or "").strip()
    if not raw:
        return StructuredDoc(
            summary=None,
            parameters=(),
            returns=None,
            raises=(),
            examples=(),
            deprecated=None,
        )

    text, deprecated = _extract_deprecated(raw)
    numpy_params: list[ParamInfo] = []
    text, numpy_params = _extract_numpy_parameters(text)

    preamble, sections = _split_google_sections(text)

    params: list[ParamInfo] = list(numpy_params)
    if "args" in sections:
        params.extend(_parse_google_parameters(sections["args"]))
    sphinx_params, sphinx_returns, sphinx_raises = _parse_sphinx_fields(text)
    if not params and sphinx_params:
        params = sphinx_params

    raises_list = _parse_raises_block(sections.get("raises", ""))
    if not raises_list and sphinx_raises:
        raises_list = sphinx_raises

    returns = _parse_returns_block(sections.get("returns", ""))
    if returns is None and sphinx_returns is not None:
        returns = sphinx_returns
    elif returns is not None and sphinx_returns is not None:
        if not returns.description and sphinx_returns.description:
            returns = ReturnInfo(
                type=returns.type or sphinx_returns.type,
                description=sphinx_returns.description,
            )
        elif sphinx_returns.type and returns.type is None:
            returns = ReturnInfo(
                type=sphinx_returns.type,
                description=returns.description or sphinx_returns.description,
            )

    examples_body = sections.get("examples", "").strip()
    examples = _split_example_blocks(examples_body) if examples_body else ()

    summary = _summary_from_preamble(preamble)

    return StructuredDoc(
        summary=summary,
        parameters=tuple(params),
        returns=returns,
        raises=tuple(raises_list),
        examples=examples,
        deprecated=deprecated,
    )


def structured_doc_to_json(doc: StructuredDoc) -> dict[str, object]:
    """Serialize StructuredDoc to a JSON-ready dict; omit empty keys."""
    out: dict[str, object] = {}
    if doc.summary:
        out["summary"] = doc.summary
    if doc.parameters:
        out["parameters"] = [
            {
                "name": p.name,
                **({"type": p.type} if p.type else {}),
                "description": p.description,
            }
            for p in doc.parameters
        ]
    if doc.returns is not None and (
        doc.returns.description or doc.returns.type
    ):
        r: dict[str, object] = {}
        if doc.returns.type:
            r["type"] = doc.returns.type
        if doc.returns.description:
            r["description"] = doc.returns.description
        out["returns"] = r
    if doc.raises:
        out["raises"] = [
            {"exception": r.exception, "description": r.description}
            for r in doc.raises
        ]
    if doc.examples:
        out["examples"] = list(doc.examples)
    if doc.deprecated is not None:
        d: dict[str, object] = {"message": doc.deprecated.message}
        if doc.deprecated.version:
            d["version"] = doc.deprecated.version
        if doc.deprecated.replacement:
            d["replacement"] = doc.deprecated.replacement
        out["deprecated"] = d
    return out


def format_structured_markdown(doc: StructuredDoc) -> str:
    """Emit Markdown fragments for non-empty structured fields."""
    lines: list[str] = []
    if doc.summary:
        lines.append("summary:")
        lines.append(doc.summary)
        lines.append("")
    if doc.parameters:
        lines.append("### PARAMETERS")
        lines.append("")
        for p in doc.parameters:
            type_part = f" (`{p.type}`)" if p.type else ""
            lines.append(f"- `{p.name}`{type_part}: {p.description}".rstrip())
        lines.append("")
    if doc.returns is not None and (
        doc.returns.description or doc.returns.type
    ):
        lines.append("### RETURNS")
        lines.append("")
        if doc.returns.type:
            lines.append(f"type: `{doc.returns.type}`")
        if doc.returns.description:
            lines.append(doc.returns.description)
        lines.append("")
    if doc.raises:
        lines.append("### RAISES")
        lines.append("")
        for r in doc.raises:
            lines.append(f"- `{r.exception}`: {r.description}".rstrip())
        lines.append("")
    if doc.examples:
        lines.append("### EXAMPLES")
        lines.append("")
        for block in doc.examples:
            lines.append("```")
            lines.append(block)
            lines.append("```")
            lines.append("")
    if doc.deprecated is not None:
        lines.append("### DEPRECATED")
        lines.append("")
        if doc.deprecated.version:
            lines.append(f"version: {doc.deprecated.version}")
        if doc.deprecated.replacement:
            lines.append(f"replacement: {doc.deprecated.replacement}")
        lines.append(doc.deprecated.message)
        lines.append("")
    return "\n".join(lines).rstrip()
