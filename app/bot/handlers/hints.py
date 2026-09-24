from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.callbacks import (
    parse_callback_int,
)
from app.bot.keyboards.hints import (
    get_hints_keyboard,
)
from app.services.hint_service import (
    get_hint_open_view,
    get_project_hints,
)
from app.services.project_service import (
    get_project_card,
)
from app.services.subscription_service import (
    has_active_subscription,
)

router = Router()


@router.callback_query(
    F.data.startswith("project:hints:")
)
async def hints_list_handler(
    callback: CallbackQuery,
) -> None:
    project_id = parse_callback_int(
        callback.data,
        "project:hints",
    )

    if project_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    project = await get_project_card(
        telegram_user_id=callback.from_user.id,
        project_id=project_id,
    )

    if project is None:
        await callback.answer(
            "Проект не найден.",
            show_alert=True,
        )
        return

    active = await has_active_subscription(
        telegram_user_id=callback.from_user.id,
        course_slug=project.course_slug,
    )

    if not active:
        await callback.answer(
            "🔒 Подсказки доступны только "
            "при активной подписке.",
            show_alert=True,
        )
        return

    view = await get_project_hints(
        project_id
    )

    if view is None:
        await callback.answer(
            "Проект не найден.",
            show_alert=True,
        )
        return

    if not view.hints:
        await callback.answer(
            "Для этого проекта пока "
            "нет подсказок.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        text=(
            f"<b>💡 Подсказки — "
            f"Project {view.project_number}</b>\n\n"
            "Подсказки становятся доступны "
            "после публикации в канале."
        ),
        reply_markup=get_hints_keyboard(
            hints=view.hints,
            project_id=view.project_id,
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("hint:open:")
)
async def hint_open_handler(
    callback: CallbackQuery,
) -> None:
    hint_id = parse_callback_int(
        callback.data,
        "hint:open",
    )

    if hint_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    view = await get_hint_open_view(
        hint_id
    )

    if view is None:
        await callback.answer(
            "Подсказка не найдена.",
            show_alert=True,
        )
        return

    active = await has_active_subscription(
        telegram_user_id=callback.from_user.id,
        course_slug=view.course_slug,
    )

    if not active:
        await callback.answer(
            "🔒 Подсказки доступны только "
            "при активной подписке.",
            show_alert=True,
        )
        return

    if not view.is_published:
        await callback.answer(
            "🔒 Эта подсказка ещё "
            "не опубликована.",
            show_alert=True,
        )
        return

    if view.telegram_url is None:
        await callback.answer(
            "Не удалось открыть публикацию.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Открой подсказку из списка.",
        show_alert=True,
    )