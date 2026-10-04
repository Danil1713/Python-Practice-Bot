import logging
from datetime import datetime, timezone
from html import escape

from aiogram import Bot

from app.bot.keyboards.notifications import (
    get_dismiss_notification_keyboard,
)
from app.config import get_admin_telegram_ids
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.hint_repository import (
    HintRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.repositories.scheduled_post_repository import (
    ScheduledPostRepository,
)
from app.database.session import (
    async_session_factory,
)
from app.services.telegram_post_validation_service import (
    TelegramPostValidationError,
    validate_telegram_post_content,
)

logger = logging.getLogger(__name__)


async def notify_admins_about_publication_failure(
    *,
    bot: Bot,
    post_id: int,
    post_type: str,
    course_slug: str | None,
    error_message: str,
) -> None:
    try:
        admin_ids = sorted(get_admin_telegram_ids())
    except Exception:
        logger.exception(
            "Failed to load admin ids for publication failure notification"
        )
        return

    safe_course_slug = escape(course_slug or "неизвестен")
    safe_post_type = escape(post_type)
    safe_error_message = escape(error_message[:1000] or "Неизвестная ошибка")

    text = (
        "🚨 <b>Ошибка публикации</b>\n\n"
        f"Курс: <code>{safe_course_slug}</code>\n"
        f"Публикация: <b>#{post_id}</b>\n"
        f"Тип: <code>{safe_post_type}</code>\n\n"
        f"<b>Ошибка:</b>\n"
        f"<code>{safe_error_message}</code>\n\n"
        "⛔ Последующие публикации этого курса приостановлены.\n"
        "Открой админ-панель → «Расписание» и обработай ошибку."
    )

    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=get_dismiss_notification_keyboard(),
            )
        except Exception:
            logger.exception(
                "Failed to notify admin about publication failure "
                "admin_id=%s post_id=%s",
                admin_id,
                post_id,
            )


async def publish_scheduled_post(
    post_id: int,
    bot: Bot,
) -> bool:
    async with async_session_factory() as session:
        post_repository = ScheduledPostRepository(session)
        course_repository = CourseRepository(session)

        claimed = await post_repository.claim_scheduled(post_id)

        if not claimed:
            await session.rollback()
            return False

        await session.commit()

        post = await post_repository.get_by_id(post_id)

        if post is None:
            return False

        course = await course_repository.get_by_id(post.course_id)

        if course is None:
            error_message = "Course not found"

            await post_repository.mark_failed(
                post,
                error_message,
            )
            await session.commit()

            await notify_admins_about_publication_failure(
                bot=bot,
                post_id=post_id,
                post_type=post.post_type,
                course_slug=None,
                error_message=error_message,
            )
            return False

        if course.telegram_channel_id is None:
            error_message = "Telegram channel is not configured"

            await post_repository.mark_failed(
                post,
                error_message,
            )
            await session.commit()

            await notify_admins_about_publication_failure(
                bot=bot,
                post_id=post_id,
                post_type=post.post_type,
                course_slug=course.slug,
                error_message=error_message,
            )
            return False

        channel_id = course.telegram_channel_id
        content = post.content
        course_slug = course.slug
        post_type = post.post_type

        try:
            validate_telegram_post_content(content)

        except TelegramPostValidationError as error:
            error_message = str(error)

            logger.warning(
                "Invalid scheduled post content post_id=%s error=%s",
                post_id,
                error,
            )

            await post_repository.mark_failed(
                post,
                error_message,
            )

            await session.commit()

            await notify_admins_about_publication_failure(
                bot=bot,
                post_id=post_id,
                post_type=post.post_type,
                course_slug=course.slug,
                error_message=error_message,
            )

            return False

    try:
        message = await bot.send_message(
            chat_id=channel_id,
            text=content,
        )

    except Exception as error:
        error_message = str(error)
        logger.exception(
            "Failed to publish scheduled post post_id=%s channel_id=%s",
            post_id,
            channel_id,
        )

        failure_saved = False

        async with async_session_factory() as session:
            repository = ScheduledPostRepository(session)

            post = await repository.get_by_id(post_id)

            if post is not None:
                await repository.mark_failed(
                    post,
                    error_message,
                )

                await session.commit()

                failure_saved = True

        if failure_saved:
            await notify_admins_about_publication_failure(
                bot=bot,
                post_id=post_id,
                post_type=post_type,
                course_slug=course_slug,
                error_message=error_message,
            )

        return False

    published_at = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        post_repository = ScheduledPostRepository(session)
        project_repository = ProjectRepository(session)
        hint_repository = HintRepository(session)

        post = await post_repository.get_by_id(post_id)

        if post is None:
            return False

        await post_repository.mark_published(
            post=post,
            published_at=published_at,
            telegram_message_id=message.message_id,
        )

        if post.post_type == "project" and post.project_id is not None:
            project = await project_repository.get_by_id(post.project_id)

            if project is not None:
                await project_repository.mark_published(
                    project=project,
                    published_at=published_at,
                    telegram_message_id=(message.message_id),
                )

        elif post.post_type == "hint" and post.hint_id is not None:
            hint = await hint_repository.get_by_id(post.hint_id)

            if hint is not None:
                await hint_repository.mark_published(
                    hint=hint,
                    published_at=published_at,
                    telegram_message_id=(message.message_id),
                )

        await session.commit()

    logger.info(
        "Published scheduled post post_id=%s channel_id=%s message_id=%s",
        post_id,
        channel_id,
        message.message_id,
    )

    return True
