from html import escape
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import (
    parse_callback_int,
)
from app.bot.keyboards.attempts import (
    get_ai_review_consent_keyboard,
    get_cancel_submission_keyboard,
)
from app.bot.states.attempts import (
    SolutionStates,
)
from app.bot.views.project_card import (
    render_project_card,
)
from app.exceptions.attempts import (
    AttemptAlreadyPending,
    AttemptError,
)
from app.services.attempt_service import (
    create_attempt,
    save_attempt_status_message,
)
from app.services.project_service import (
    get_project_card,
)
from app.services.subscription_service import (
    has_active_subscription,
)
from app.services.user_service import (
    accept_ai_review_consent,
    has_current_ai_review_consent,
)

router = Router()


MAX_SOLUTION_FILE_SIZE = 200 * 1024

@router.callback_query(
    F.data.startswith(
        "attempt:ai-consent:"
    )
)
async def ai_review_consent_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    project_id = parse_callback_int(
        callback.data,
        "attempt:ai-consent",
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
            "🔒 Для отправки решения "
            "нужен доступ к уровню.",
            show_alert=True,
        )
        return

    accepted = await accept_ai_review_consent(
        callback.from_user.id
    )

    if not accepted:
        await callback.answer(
            "Не удалось сохранить согласие.",
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
            f"{escape(project.title)}</b>\n\n"
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

    await callback.answer(
        "✅ Согласие сохранено."
    )

@router.callback_query(
    F.data.startswith("project:submit:")
)
async def start_submission_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    project_id = parse_callback_int(
        callback.data,
        "project:submit",
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

    has_consent = (
        await has_current_ai_review_consent(
            callback.from_user.id
        )
    )

    if not has_consent:
        await callback.message.edit_text(
            text=(
                "🤖 <b>Автоматическая проверка</b>\n\n"
                "Для проверки содержимое "
                "Python-файла будет передано "
                "внешнему AI-сервису.\n\n"
                "Не отправляй в решении:\n"
                "• пароли;\n"
                "• API-ключи и токены;\n"
                "• персональные данные;\n"
                "• другие секретные данные.\n\n"
                "Нажимая <b>«Согласен»</b>, "
                "ты разрешаешь передать "
                "содержимое файла для "
                "автоматической проверки."
            ),
            reply_markup=(
                get_ai_review_consent_keyboard(
                    project.id
                )
            ),
        )

        await callback.answer()
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
            f"{escape(project.title)}</b>\n\n"
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
    project_id = parse_callback_int(
        callback.data,
        "attempt:cancel",
    )

    if project_id is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

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

    active = await has_active_subscription(
        telegram_user_id=callback.from_user.id,
        course_slug=project.course_slug,
    )

    text, keyboard = render_project_card(
        project,
        active_subscription=active,
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
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

    has_consent = (
        await has_current_ai_review_consent(
            message.from_user.id
        )
    )

    if not has_consent:
        await state.clear()

        await message.answer(
            "⚠️ Условия AI-проверки изменились.\n\n"
            "Открой проект и нажми "
            "«Отправить решение» заново."
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

    project_text, project_keyboard = (
        render_project_card(
            project,
            active_subscription=active,
        )
    )

    status_message = await message.answer(
        text=(
            "✅ <b>Решение получено.</b>\n\n"
            f"Попытка №{attempt.number}\n\n"
            "Результат проверки появится "
            "в разделе "
            "<b>«Мои попытки»</b>.\n\n"
            f"{project_text}"
        ),
        reply_markup=project_keyboard,
    )

    await save_attempt_status_message(
        attempt_id=attempt.id,
        chat_id=message.chat.id,
        message_id=status_message.message_id,
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