from pathlib import Path

import pytest

from apidump.cli import _log_mode_guidance, _validate_output_format


def test_validate_output_format_accepts_matching_suffix():
    _validate_output_format(Path("output.json"), "json")
    _validate_output_format(Path("output.md"), "markdown")


def test_validate_output_format_rejects_mismatch():
    with pytest.raises(ValueError):
        _validate_output_format(Path("output.md"), "json")


@pytest.mark.parametrize("mode", ["compact", "complete"])
def test_log_mode_guidance_emits_warning(caplog, mode):
    with caplog.at_level("WARNING"):
        _log_mode_guidance(mode)

    assert any(record.levelname == "WARNING" for record in caplog.records)


def test_log_mode_guidance_emits_info_for_extended(caplog):
    with caplog.at_level("INFO"):
        _log_mode_guidance("extended")

    assert any(record.levelname == "INFO" for record in caplog.records)
