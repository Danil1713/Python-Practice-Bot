from datetime import datetime, timezone

from aiogram import Bot

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


async def publish_scheduled_post(
    post_id: int,
    bot: Bot,
) -> None:
    async with async_session_factory() as session:
        post_repository = ScheduledPostRepository(
            session
        )
        course_repository = CourseRepository(
            session
        )

        post = await post_repository.get_by_id(
            post_id
        )

        if post is None:
            return

        if post.status != "scheduled":
            return

        course = await course_repository.get_by_id(
            post.course_id
        )

        if course is None:
            await post_repository.mark_failed(
                post,
                "Course not found",
            )
            await session.commit()
            return

        if course.telegram_channel_id is None:
            await post_repository.mark_failed(
                post,
                "Telegram channel is not configured",
            )
            await session.commit()
            return

        await post_repository.mark_publishing(
            post
        )

        await session.commit()

        channel_id = course.telegram_channel_id
        content = post.content

    try:
        message = await bot.send_message(
            chat_id=channel_id,
            text=content,
        )

    except Exception as error:
        async with async_session_factory() as session:
            repository = ScheduledPostRepository(
                session
            )

            post = await repository.get_by_id(
                post_id
            )

            if post is not None:
                await repository.mark_failed(
                    post,
                    str(error),
                )

                await session.commit()

        return

    published_at = datetime.now(
        timezone.utc
    )

    async with async_session_factory() as session:
        post_repository = ScheduledPostRepository(
            session
        )
        project_repository = ProjectRepository(
            session
        )
        hint_repository = HintRepository(
            session
        )

        post = await post_repository.get_by_id(
            post_id
        )

        if post is None:
            return

        await post_repository.mark_published(
            post=post,
            published_at=published_at,
            telegram_message_id=message.message_id,
        )

        if (
            post.post_type == "project"
            and post.project_id is not None
        ):
            project = (
                await project_repository.get_by_id(
                    post.project_id
                )
            )

            if project is not None:
                await project_repository.mark_published(
                    project=project,
                    published_at=published_at,
                    telegram_message_id=(
                        message.message_id
                    ),
                )

        elif (
            post.post_type == "hint"
            and post.hint_id is not None
        ):
            hint = await hint_repository.get_by_id(
                post.hint_id
            )

            if hint is not None:
                await hint_repository.mark_published(
                    hint=hint,
                    published_at=published_at,
                    telegram_message_id=(
                        message.message_id
                    ),
                )

        await session.commit()