from app.bot.keyboards.main_menu import (
    get_main_menu_keyboard,
)


def get_callback_data(keyboard) -> list[str]:
    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


def test_free_course_with_channel_has_channel_access_button():
    keyboard = get_main_menu_keyboard(
        course_slug="demo",
        requires_subscription=False,
        has_channel=True,
    )

    callback_data = get_callback_data(keyboard)

    assert "subscription:channel:demo" in callback_data
    assert "menu:subscription:demo" not in callback_data


def test_free_course_without_channel_has_no_channel_access_button():
    keyboard = get_main_menu_keyboard(
        course_slug="demo",
        requires_subscription=False,
        has_channel=False,
    )

    callback_data = get_callback_data(keyboard)

    assert "subscription:channel:demo" not in callback_data
    assert "menu:subscription:demo" not in callback_data


def test_paid_course_keeps_subscription_button():
    keyboard = get_main_menu_keyboard(
        course_slug="python_start",
        requires_subscription=True,
        has_channel=True,
    )

    callback_data = get_callback_data(keyboard)

    assert "menu:subscription:python_start" in callback_data
    assert "subscription:channel:python_start" not in callback_data
