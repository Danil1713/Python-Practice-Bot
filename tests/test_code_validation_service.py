from app.services.code_validation_service import (
    validate_python_syntax,
)


def test_valid_python_source() -> None:
    result = validate_python_syntax("value = 10\nprint(value)\n")

    assert result.valid is True
    assert result.error_message is None
    assert result.line is None
    assert result.column is None


def test_invalid_python_source() -> None:
    result = validate_python_syntax("if True\n    print('hello')\n")

    assert result.valid is False
    assert result.error_message is not None
    assert result.line == 1
    assert result.column is not None


def test_validation_does_not_execute_code(
    tmp_path,
) -> None:
    marker_file = tmp_path / "should_not_exist.txt"

    source_code = (
        f"from pathlib import Path\nPath({str(marker_file)!r}).write_text('executed')\n"
    )

    result = validate_python_syntax(source_code)

    assert result.valid is True
    assert marker_file.exists() is False
