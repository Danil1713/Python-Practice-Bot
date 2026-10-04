from app.bot.keyboards.hints import (
    get_hint_open_keyboard,
    get_hints_keyboard,
)
from app.services.hint_service import (
    HintListItem,
)


def test_published_hint_is_opened_directly_by_url():
    keyboard = get_hints_keyboard(
        hints=[
            HintListItem(
                id=15,
                number=1,
                is_published=True,
                telegram_url="https://t.me/c/123/456",
            )
        ],
        project_id=7,
    )

    button = keyboard.inline_keyboard[0][0]

    assert button.url == "https://t.me/c/123/456"
    assert button.callback_data is None


def test_unpublished_hint_uses_callback():
    keyboard = get_hints_keyboard(
        hints=[
            HintListItem(
                id=16,
                number=2,
                is_published=False,
                telegram_url=None,
            )
        ],
        project_id=7,
    )

    button = keyboard.inline_keyboard[0][0]

    assert button.callback_data == "hint:open:16"
    assert button.url is None


def test_hint_url_is_shown_after_validation():
    keyboard = get_hint_open_keyboard(
        telegram_url="https://t.me/c/123/456",
        project_id=7,
    )

    open_button = keyboard.inline_keyboard[0][0]
    back_button = keyboard.inline_keyboard[1][0]

    assert open_button.url == "https://t.me/c/123/456"
    assert back_button.callback_data == "project:hints:7"
