from apidump.docstring_parse import parse_docstring, structured_doc_to_json


def test_parse_google_full_docstring():
    text = '''\
Do the thing. Second sentence ignored for summary.

Args:
    x: The input value.
    y (int): Second parameter.

Returns:
    str: The formatted result.

Raises:
    ValueError: If x is empty.

Examples:
    >>> do_thing(1)
    '1'

.. deprecated:: 2.1
    Use ``other()`` instead.
'''
    doc = parse_docstring(text)
    assert doc.summary == "Do the thing."
    assert len(doc.parameters) == 2
    assert doc.parameters[0].name == "x"
    assert doc.parameters[0].type is None
    assert "input" in doc.parameters[0].description
    assert doc.parameters[1].name == "y"
    assert doc.parameters[1].type == "int"
    assert doc.returns is not None
    assert doc.returns.type == "str"
    assert "formatted" in (doc.returns.description or "")
    assert len(doc.raises) == 1
    assert doc.raises[0].exception == "ValueError"
    assert doc.deprecated is not None
    assert doc.deprecated.version == "2.1"
    assert doc.deprecated.replacement == "other()"
    assert doc.examples


def test_parse_sphinx_when_no_args_section():
    text = """\
Short intro.

:param name: Who to greet.
:type name: str
:returns: A greeting string.
:rtype: str
:raises KeyError: if missing.
"""
    doc = parse_docstring(text)
    assert doc.summary == "Short intro."
    assert {p.name for p in doc.parameters} == {"name"}
    name_param = next(p for p in doc.parameters if p.name == "name")
    assert name_param.type == "str"
    assert doc.returns is not None
    assert doc.returns.type == "str"
    assert len(doc.raises) == 1
    assert doc.raises[0].exception == "KeyError"


def test_parse_numpy_parameters_block():
    text = """\
Compute values.

Parameters
----------
a : ndarray
    First operand.
b : float
    Second operand.

Returns
-------
ndarray
    The sum.
"""
    doc = parse_docstring(text)
    assert "Compute values" in (doc.summary or "")
    names = [p.name for p in doc.parameters]
    assert names == ["a", "b"]
    a = doc.parameters[0]
    assert a.type == "ndarray"
    assert "First operand" in a.description


def test_structured_doc_to_json_omits_empty_keys():
    doc = parse_docstring("Only a single-line doc without sections.")
    payload = structured_doc_to_json(doc)
    assert "summary" in payload
    assert "parameters" not in payload


def test_deprecated_line():
    doc = parse_docstring(":deprecated: Use something else.\n\nBody.")
    assert doc.deprecated is not None
    assert "Use something else" in doc.deprecated.message
