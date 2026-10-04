from dataclasses import dataclass

from app.bot.views.project_card import (
    get_project_card_markup,
)


@dataclass(frozen=True)
class ProjectTask:
    id: int
    telegram_message_id: int | None


def test_project_markup_uses_explicit_course_channel() -> None:
    project = ProjectTask(
        id=7,
        telegram_message_id=42,
    )

    markup = get_project_card_markup(
        project,
        course_slug="demo",
        telegram_channel_id=-1004325612238,
        active_subscription=True,
    )

    task_button = markup.inline_keyboard[0][0]

    assert task_button.url == "https://t.me/c/4325612238/42"
    assert task_button.callback_data is None


def test_project_markup_without_access_uses_callback() -> None:
    project = ProjectTask(
        id=7,
        telegram_message_id=42,
    )

    markup = get_project_card_markup(
        project,
        course_slug="demo",
        telegram_channel_id=-1004325612238,
        active_subscription=False,
    )

    task_button = markup.inline_keyboard[0][0]

    assert task_button.url is None
    assert task_button.callback_data == "project:task:7"
