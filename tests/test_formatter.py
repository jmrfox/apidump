from apidump.formatter import format_reference_md, format_reference_json
from apidump.models import MethodInfo, SymbolInfo


SYMBOLS = [
    SymbolInfo(
        name="Example",
        module="pkg.module",
        defined_in="pkg.impl",
        qualname="Example",
        kind="class",
        signature="()",
        doc="Example class",
        object_id=1,
        methods=(MethodInfo(name="run", signature="(self)", doc="Run it"),),
    ),
    SymbolInfo(
        name="helper",
        module="pkg.module",
        defined_in="pkg.module",
        qualname="helper",
        kind="function",
        signature="()",
        doc="Helper doc",
        object_id=2,
    ),
]


def test_format_reference_contains_expected_sections():
    output = format_reference_md("pkg", SYMBOLS, include_doc=True)

    assert "# API REFERENCE: pkg" in output
    assert "## CLASS: Example" in output
    assert "defined_in: pkg.impl" in output
    assert "### METHODS" in output
    assert "- run(self)" in output
    assert "## FUNCTION: helper" in output


def test_format_reference_json_contains_expected_fields():
    output = format_reference_json("pkg", SYMBOLS, include_doc=True)

    assert '"package": "pkg"' in output
    assert '"format": "apidump.v1"' in output
    assert '"name": "Example"' in output
    assert '"defined_in": "pkg.impl"' in output
    assert '"methods": [' in output
    assert '"doc": "Run it"' in output
    assert '"doc_structured"' in output
    assert '"summary"' in output


def test_format_reference_includes_structured_markdown_before_raw_doc():
    output = format_reference_md("pkg", SYMBOLS, include_doc=True)
    idx_summary = output.find("summary:")
    idx_example = output.find("Example class")
    assert idx_summary != -1 and idx_example != -1
    assert idx_summary < idx_example
