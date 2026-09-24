import pytest

from app.services.telegram_post_validation_service import (
    TelegramPostValidationError,
    build_telegram_post_preview,
    validate_telegram_post_content,
)


def test_plain_text_is_valid() -> None:
    validate_telegram_post_content(
        "Обычный Telegram-пост."
    )


def test_valid_html_is_valid() -> None:
    validate_telegram_post_content(
        "<b>Заголовок</b>\n\n"
        "<i>Описание</i>"
    )


def test_4096_visible_characters_are_valid() -> None:
    validate_telegram_post_content(
        "a" * 4096
    )


def test_4097_visible_characters_are_rejected() -> None:
    with pytest.raises(
        TelegramPostValidationError
    ):
        validate_telegram_post_content(
            "a" * 4097
        )


def test_html_tags_do_not_count_toward_limit() -> None:
    content = (
        "<b>"
        + ("a" * 4096)
        + "</b>"
    )

    assert len(content) > 4096

    validate_telegram_post_content(
        content
    )


def test_unclosed_html_tag_is_rejected() -> None:
    with pytest.raises(
        TelegramPostValidationError
    ):
        validate_telegram_post_content(
            "<b>Текст"
        )


def test_mismatched_html_tags_are_rejected() -> None:
    with pytest.raises(
        TelegramPostValidationError
    ):
        validate_telegram_post_content(
            "<b><i>Текст</b></i>"
        )


def test_unsupported_html_tag_is_rejected() -> None:
    with pytest.raises(
        TelegramPostValidationError
    ):
        validate_telegram_post_content(
            "<script>text</script>"
        )


def test_preview_removes_html_markup() -> None:
    preview = build_telegram_post_preview(
        "<b>Привет</b>",
        max_chars=100,
    )

    assert preview == "Привет"


def test_preview_is_limited() -> None:
    preview = build_telegram_post_preview(
        "a" * 100,
        max_chars=20,
    )

    assert len(preview) == 20
    assert preview.endswith("…")