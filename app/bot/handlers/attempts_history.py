from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.callbacks import (
    parse_callback_int,
)
from app.bot.keyboards.attempts import (
    get_attempt_detail_keyboard,
    get_attempts_keyboard,
)
from app.services.attempt_service import (
    get_attempt_detail,
    get_project_attempts,
)

router = Router()

@router.callback_query(
    F.data.startswith("project:attempts:")
)
async def attempts_list_handler(
    callback: CallbackQuery,
) -> None:
    project_id = parse_callback_int(
        callback.data,
        "project:attempts",
    )

    if project_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    view = await get_project_attempts(
        telegram_user_id=callback.from_user.id,
        project_id=project_id,
    )

    if view is None:
        await callback.answer(
            "Проект не найден.",
            show_alert=True,
        )
        return

    if not view.attempts:
        text = (
            f"<b>🧾 Мои попытки — "
            f"Project {view.project_number}</b>\n\n"
            "Ты ещё не отправлял "
            "решения этого проекта."
        )

    else:
        text = (
            f"<b>🧾 Мои попытки — "
            f"Project {view.project_number}</b>\n\n"
            "⏳ — проверяется\n"
            "❌ — не принято\n"
            "✅ — принято\n"
            "🟠 — не принято автоматически\n"
            "⚠️ — ошибка проверки"
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_attempts_keyboard(
            attempts=view.attempts,
            project_id=view.project_id,
        ),
    )

    await callback.answer()

async def show_attempt_detail(
    callback: CallbackQuery,
    attempt_id: int,
) -> None:
    attempt = await get_attempt_detail(
        telegram_user_id=callback.from_user.id,
        attempt_id=attempt_id,
    )

    if attempt is None:
        await callback.answer(
            "Попытка не найдена.",
            show_alert=True,
        )
        return

    icons = {
        "pending": "⏳ Проверяется",
        "checking": "⏳ Проверяется",
        "failed": "❌ Не принято",
        "passed": "✅ Принято",
        "review": "🟠 Не принято автоматически",
        "error": "⚠️ Ошибка проверки",
    }

    status = icons.get(
        attempt.status,
        "❔ Неизвестно",
    )

    filename = escape(
        attempt.filename
    )

    project_title = escape(
        attempt.project_title
    )

    text = (
        f"<b>Попытка №"
        f"{attempt.number}</b>\n\n"
        f"Project {attempt.project_number} — "
        f"{project_title}\n\n"
        f"Статус: {status}\n"
        f"Файл: <code>{filename}</code>\n"
    )

    if attempt.xp_snapshot > 0:
        text += (
            "Награда при успешной проверке: "
            f"<b>{attempt.xp_snapshot} XP</b>"
        )
    else:
        text += (
            "Повторная проверка "
            "без дополнительного XP."
        )

    await callback.message.answer(
        text=text,
        reply_markup=get_attempt_detail_keyboard(
            attempt_id=attempt.id,
            project_id=attempt.project_id,
        ),
    )


@router.callback_query(
    F.data.startswith("attempt:open:")
)
async def attempt_detail_handler(
    callback: CallbackQuery,
) -> None:
    attempt_id = parse_callback_int(
        callback.data,
        "attempt:open",
    )

    if attempt_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    await show_attempt_detail(
        callback=callback,
        attempt_id=attempt_id,
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("attempt:code:")
)
async def attempt_code_handler(
    callback: CallbackQuery,
) -> None:
    attempt_id = parse_callback_int(
        callback.data,
        "attempt:code",
    )

    if attempt_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    attempt = await get_attempt_detail(
        telegram_user_id=callback.from_user.id,
        attempt_id=attempt_id,
    )

    if attempt is None:
        await callback.answer(
            "Попытка не найдена.",
            show_alert=True,
        )
        return

    raw_code = attempt.source_code

    chunks = [
        raw_code[index:index + 3000]
        for index in range(
            0,
            len(raw_code),
            3000,
        )
    ]

    for chunk in chunks:
        await callback.message.answer(
            "<pre><code>"
            f"{escape(chunk)}"
            "</code></pre>"
        )

    await show_attempt_detail(
        callback=callback,
        attempt_id=attempt.id,
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("attempt:feedback:")
)
async def attempt_feedback_handler(
    callback: CallbackQuery,
) -> None:
    attempt_id = parse_callback_int(
        callback.data,
        "attempt:feedback",
    )

    if attempt_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    attempt = await get_attempt_detail(
        telegram_user_id=callback.from_user.id,
        attempt_id=attempt_id,
    )

    if attempt is None:
        await callback.answer(
            "Попытка не найдена.",
            show_alert=True,
        )
        return

    if attempt.status in (
        "pending",
        "checking",
    ):
        await callback.answer(
            "⏳ Решение ещё проверяется.",
            show_alert=True,
        )
        return

    if attempt.status == "error":
        await callback.answer(
            "⚠️ Во время проверки "
            "произошла техническая ошибка.",
            show_alert=True,
        )
        return

    if not attempt.ai_feedback:
        await callback.answer(
            "Результат проверки пока "
            "не сохранён.",
            show_alert=True,
        )
        return

    await callback.message.answer(
        "<b>🤖 Результат проверки</b>\n\n"
        f"{escape(attempt.ai_feedback)}"
    )

    await callback.answer()