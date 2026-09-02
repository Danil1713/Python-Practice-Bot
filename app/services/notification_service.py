from aiogram import Bot


async def notify_attempt_checked(
    bot: Bot,
    telegram_user_id: int,
    project_number: int,
    project_title: str,
    passed: bool,
) -> None:
    if passed:
        text = (
            f"✅ <b>Проверка Project {project_number} "
            f"завершена.</b>\n\n"
            f"{project_title}\n\n"
            "Результат доступен в разделе "
            "<b>«Мои попытки»</b>."
        )
    else:
        text = (
            f"❌ <b>Project {project_number} "
            f"пока не принят.</b>\n\n"
            f"{project_title}\n\n"
            "Результат проверки доступен "
            "в разделе <b>«Мои попытки»</b>."
        )

    await bot.send_message(
        chat_id=telegram_user_id,
        text=text,
    )

async def notify_attempt_error(
    bot: Bot,
    telegram_user_id: int,
    project_number: int,
    project_title: str,
) -> None:
    await bot.send_message(
        chat_id=telegram_user_id,
        text=(
            f"⚠️ <b>Не удалось проверить "
            f"Project {project_number}.</b>\n\n"
            f"{project_title}\n\n"
            "Решение сохранено. "
            "Попробуй повторить проверку позже."
        ),
    )