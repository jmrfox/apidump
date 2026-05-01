from pathlib import Path

import pytest

from apidump.cli import _infer_output_format, _log_mode_guidance


def test_infer_output_format_from_json_suffix():
    assert _infer_output_format(Path("output.json")) == "json"


def test_infer_output_format_from_md_suffix():
    assert _infer_output_format(Path("output.md")) == "markdown"


def test_infer_output_format_defaults_to_markdown():
    assert _infer_output_format(Path("output.txt")) == "markdown"
    assert _infer_output_format(Path("output")) == "markdown"


@pytest.mark.parametrize("mode", ["compact", "complete"])
def test_log_mode_guidance_emits_warning(caplog, mode):
    with caplog.at_level("WARNING"):
        _log_mode_guidance(mode)

    assert any(record.levelname == "WARNING" for record in caplog.records)


def test_log_mode_guidance_emits_info_for_extended(caplog):
    with caplog.at_level("INFO"):
        _log_mode_guidance("extended")

    assert any(record.levelname == "INFO" for record in caplog.records)
