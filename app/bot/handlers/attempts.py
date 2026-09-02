from io import BytesIO
from html import escape
import asyncio

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.attempts import (
    get_attempt_detail_keyboard,
    get_attempts_keyboard,
    get_cancel_submission_keyboard,
)
from app.bot.keyboards.projects import (
    get_project_card_keyboard,
)
from app.bot.states.attempts import (
    SolutionStates,
)
from app.exceptions.attempts import (
    AttemptAlreadyPending,
    AttemptError,
)
from app.services.attempt_service import (
    create_attempt,
    get_attempt_detail,
    get_project_attempts,
)
from app.services.project_service import (
    get_project_card,
)
from app.services.subscription_service import (
    has_active_subscription,
)
from app.services.attempt_check_service import (
    check_attempt,
)


router = Router()


MAX_SOLUTION_FILE_SIZE = 200 * 1024

@router.callback_query(
    F.data.startswith("project:submit:")
)
async def start_submission_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    project_id = int(
        callback.data.split(":")[2]
    )

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

    if project.status == "locked":
        await callback.answer(
            "🔒 Проект ещё не опубликован.",
            show_alert=True,
        )
        return

    if project.status == "pending":
        await callback.answer(
            "⏳ У тебя уже есть решение "
            "на проверке.",
            show_alert=True,
        )
        return

    active = await has_active_subscription(
        telegram_user_id=callback.from_user.id,
        course_slug=project.course_slug,
    )

    if not active:
        await callback.answer(
            "🔒 Для отправки решения "
            "нужен доступ к уровню.",
            show_alert=True,
        )
        return

    await state.set_state(
        SolutionStates.waiting_for_file
    )

    await state.update_data(
        project_id=project.id
    )

    await callback.message.edit_text(
        text=(
            f"<b>📤 Project "
            f"{project.number} — "
            f"{project.title}</b>\n\n"
            "Отправь Python-файл "
            "с решением.\n\n"
            "Формат: <code>.py</code>"
        ),
        reply_markup=(
            get_cancel_submission_keyboard(
                project.id
            )
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("attempt:cancel:")
)
async def cancel_submission_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    project_id = int(
        callback.data.split(":")[2]
    )

    await state.clear()

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

    if project.status == "completed":
        status_text = "✅ Выполнен"
        xp_text = (
            f"Получено: "
            f"<b>{project.awarded_xp} XP</b>"
        )

    elif project.status == "pending":
        status_text = "⏳ На проверке"
        xp_text = (
            f"Текущая награда: "
            f"<b>{project.current_xp} XP</b>"
        )

    else:
        status_text = "🟡 Не выполнен"
        xp_text = (
            f"Награда сейчас: "
            f"<b>{project.current_xp} XP</b>"
        )

    await callback.message.edit_text(
        text=(
            f"<b>Project {project.number} — "
            f"{project.title}</b>\n\n"
            f"Статус: {status_text}\n"
            f"{xp_text}"
        ),
        reply_markup=get_project_card_keyboard(
            project_id=project.id,
            course_slug=project.course_slug,
        ),
    )

    await callback.answer(
        "Отправка отменена."
    )


@router.message(
    SolutionStates.waiting_for_file,
    F.document,
)
async def solution_file_handler(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    document = message.document

    if document is None:
        return

    filename = document.file_name or ""

    if not filename.lower().endswith(".py"):
        await message.answer(
            "❌ Нужен файл с расширением "
            "<code>.py</code>."
        )
        return

    if (
        document.file_size is not None
        and document.file_size
        > MAX_SOLUTION_FILE_SIZE
    ):
        await message.answer(
            "❌ Файл слишком большой.\n"
            "Максимальный размер: 200 KB."
        )
        return

    data = await state.get_data()

    project_id = data.get("project_id")

    if project_id is None:
        await state.clear()

        await message.answer(
            "Не удалось определить проект. "
            "Выбери его заново."
        )
        return

    project = await get_project_card(
        telegram_user_id=message.from_user.id,
        project_id=project_id,
    )

    if project is None:
        await state.clear()

        await message.answer(
            "Проект не найден."
        )
        return

    active = await has_active_subscription(
        telegram_user_id=message.from_user.id,
        course_slug=project.course_slug,
    )

    if not active:
        await state.clear()

        await message.answer(
            "🔒 Доступ к уровню закончился."
        )
        return

    buffer = BytesIO()

    await bot.download(
        document,
        destination=buffer,
    )

    raw_code = buffer.getvalue()

    try:
        source_code = raw_code.decode(
            "utf-8-sig"
        )

    except UnicodeDecodeError:
        await message.answer(
            "❌ Не удалось прочитать файл.\n"
            "Сохрани его в UTF-8 "
            "и отправь снова."
        )
        return

    if not source_code.strip():
        await message.answer(
            "❌ Файл пустой."
        )
        return

    try:
        attempt = await create_attempt(
            telegram_user_id=(
                message.from_user.id
            ),
            project_id=project_id,
            filename=filename,
            source_code=source_code,
        )

    except AttemptAlreadyPending:
        await state.clear()

        await message.answer(
            "⏳ У тебя уже есть решение "
            "на проверке."
        )
        return

    except AttemptError:
        await state.clear()

        await message.answer(
            "Не удалось сохранить решение."
        )
        return

    await state.clear()

    project = await get_project_card(
        telegram_user_id=message.from_user.id,
        project_id=project_id,
    )

    if project is None:
        return

    status_message = await message.answer(
        text=(
            "✅ <b>Решение получено.</b>\n\n"
            f"Попытка №{attempt.number}\n\n"
            "Результат проверки появится "
            "в разделе "
            "<b>«Мои попытки»</b>.\n\n"
            f"<b>Project "
            f"{project.number} — "
            f"{project.title}</b>\n\n"
            "Статус: ⏳ На проверке"
        ),
        reply_markup=get_project_card_keyboard(
            project_id=project.id,
            course_slug=project.course_slug,
        ),
    )

    asyncio.create_task(
        check_attempt(
            attempt_id=attempt.id,
            bot=bot,
            chat_id=message.chat.id,
            status_message_id=status_message.message_id,
        )
    )


@router.message(
    SolutionStates.waiting_for_file
)
async def wrong_solution_message_handler(
    message: Message,
) -> None:
    await message.answer(
        "Отправь Python-файл "
        "<code>.py</code> или нажми "
        "«Отмена»."
    )


@router.callback_query(
    F.data.startswith("project:attempts:")
)
async def attempts_list_handler(
    callback: CallbackQuery,
) -> None:
    project_id = int(
        callback.data.split(":")[2]
    )

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
        "error": "⚠️ Ошибка проверки",
    }

    status = icons.get(
        attempt.status,
        "❔ Неизвестно",
    )

    filename = escape(
        attempt.filename
    )

    text = (
        f"<b>Попытка №"
        f"{attempt.number}</b>\n\n"
        f"Project {attempt.project_number} — "
        f"{attempt.project_title}\n\n"
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
    attempt_id = int(
        callback.data.split(":")[2]
    )

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
    attempt_id = int(
        callback.data.split(":")[2]
    )

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
    attempt_id = int(
        callback.data.split(":")[2]
    )

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