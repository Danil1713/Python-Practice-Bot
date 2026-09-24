from html import escape
from typing import Protocol

from aiogram.types import InlineKeyboardMarkup

from app.bot.keyboards.projects import (
    get_project_card_keyboard,
)
from app.services.telegram_link_service import (
    build_channel_message_url,
)


class ProjectTaskData(Protocol):
    id: int
    telegram_channel_id: int | None
    telegram_message_id: int | None


class ProjectCardData(
    ProjectTaskData,
    Protocol,
):
    number: int
    title: str
    status: str
    awarded_xp: int
    current_xp: int
    course_slug: str


def get_project_task_url(
    project: ProjectTaskData,
    *,
    active_subscription: bool,
) -> str | None:
    if not active_subscription:
        return None

    if (
        project.telegram_channel_id is None
        or project.telegram_message_id is None
    ):
        return None

    return build_channel_message_url(
        channel_id=project.telegram_channel_id,
        message_id=project.telegram_message_id,
    )


def get_project_card_markup(
    project: ProjectTaskData,
    *,
    course_slug: str,
    active_subscription: bool,
) -> InlineKeyboardMarkup:
    task_url = get_project_task_url(
        project,
        active_subscription=active_subscription,
    )

    return get_project_card_keyboard(
        project_id=project.id,
        course_slug=course_slug,
        task_url=task_url,
    )


def render_project_card(
    project: ProjectCardData,
    *,
    active_subscription: bool,
) -> tuple[str, InlineKeyboardMarkup]:
    if project.status == "completed":
        status_text = "✅ Выполнен"

        xp_text = (
            "Получено: "
            f"<b>{project.awarded_xp} XP</b>"
        )

    elif project.status == "pending":
        status_text = "⏳ На проверке"

        xp_text = (
            "Текущая награда проекта: "
            f"<b>{project.current_xp} XP</b>"
        )

    else:
        status_text = "🟡 Не выполнен"

        xp_text = (
            "Награда сейчас: "
            f"<b>{project.current_xp} XP</b>"
        )

    keyboard = get_project_card_markup(
        project,
        course_slug=project.course_slug,
        active_subscription=active_subscription,
    )

    text = (
        f"<b>Project {project.number} — "
        f"{escape(project.title)}</b>\n\n"
        f"Статус: {status_text}\n"
        f"{xp_text}"
    )

    return text, keyboard