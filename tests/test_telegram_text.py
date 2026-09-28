import pytest

from app.utils.telegram_text import (
    split_telegram_lines,
    split_telegram_text,
)


def test_short_text_is_not_split():
    text = "Hello"

    assert split_telegram_text(
        text
    ) == [
        "Hello"
    ]


def test_long_text_is_split():
    text = "a" * 8000

    chunks = split_telegram_text(
        text,
        max_chars=3000,
    )

    assert len(chunks) == 3

    assert all(
        len(chunk) <= 3000
        for chunk in chunks
    )

    assert "".join(chunks) == text


def test_prefers_newline_boundary():
    text = (
        "a" * 100
        + "\n"
        + "b" * 100
    )

    chunks = split_telegram_text(
        text,
        max_chars=150,
    )

    assert chunks[0] == (
        "a" * 100
        + "\n"
    )

    assert "".join(chunks) == text


def test_empty_text_returns_empty_list():
    assert split_telegram_text(
        ""
    ) == []


def test_invalid_limit_is_rejected():
    with pytest.raises(
        ValueError,
        match="greater than 0",
    ):
        split_telegram_text(
            "text",
            max_chars=0,
        )


def test_telegram_lines_stay_under_limit():
    lines = [
        f"Project {index} — "
        + "a" * 100
        for index in range(100)
    ]

    chunks = split_telegram_lines(
        lines,
        max_chars=500,
    )

    assert len(chunks) > 1

    assert all(
        len(chunk) <= 500
        for chunk in chunks
    )

    assert "\n".join(
        chunks
    ) == "\n".join(
        lines
    )


def test_short_lines_are_not_split():
    lines = [
        "Line 1",
        "Line 2",
        "Line 3",
    ]

    assert split_telegram_lines(
        lines
    ) == [
        (
            "Line 1\n"
            "Line 2\n"
            "Line 3"
        )
    ]