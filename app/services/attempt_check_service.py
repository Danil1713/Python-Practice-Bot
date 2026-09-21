from aiogram import Bot
from app.database.repositories.attempt_repository import (
    AttemptRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.repositories.user_project_repository import (
    UserProjectRepository,
)
from app.database.repositories.xp_repository import (
    XPRepository,
)
from app.database.session import (
    async_session_factory,
)
from app.services.ai_service import (
    format_review_feedback,
    review_python_code,
)
from app.bot.keyboards.projects import (
    get_project_card_keyboard,
)
from app.database.repositories.course_repository import (
    CourseRepository,
)


async def check_attempt(
    attempt_id: int,
    bot: Bot,
) -> None:
    async with async_session_factory() as session:
        attempt_repository = AttemptRepository(
            session
        )
        project_repository = ProjectRepository(
            session
        )

        claimed = await attempt_repository.claim_pending(
            attempt_id
        )

        if not claimed:
            await session.rollback()
            return

        await session.commit()

        attempt = await attempt_repository.get_by_id(
            attempt_id
        )

        if attempt is None:
            return

        project = await project_repository.get_by_id(
            attempt.project_id
        )

        if project is None:
            await attempt_repository.mark_error(
                attempt,
                "Project not found",
            )

            await session.commit()
            return

        await attempt_repository.mark_checking(
            attempt
        )

        await session.commit()

        try:
            result = await review_python_code(
                project_title=project.title,
                requirements=(
                    project.ai_requirements or ""
                ),
                source_code=attempt.source_code,
            )


        except Exception as error:
            async with async_session_factory() as error_session:
                error_attempt_repository = AttemptRepository(
                    error_session
                )

                error_project_repository = ProjectRepository(
                    error_session
                )

                error_course_repository = CourseRepository(
                    error_session
                )

                error_attempt = (
                    await error_attempt_repository.get_by_id(
                        attempt_id
                    )
                )

                if error_attempt is None:
                    return

                await error_attempt_repository.mark_error(
                    error_attempt,
                    str(error),
                )

                error_project = (
                    await error_project_repository.get_by_id(
                        error_attempt.project_id
                    )
                )

                await error_session.commit()

                if error_project is None:
                    return

                error_course = (
                    await error_course_repository.get_by_id(
                        error_project.course_id
                    )
                )

                if error_course is None:
                    return

                if (
                        error_attempt.status_chat_id is not None
                        and error_attempt.status_message_id is not None
                ):
                    await bot.edit_message_text(
                        chat_id=error_attempt.status_chat_id,
                        message_id=error_attempt.status_message_id,
                        text=(
                            f"⚠️ <b>Не удалось проверить "
                            f"Project {error_project.number}.</b>\n\n"
                            f"{error_project.title}\n\n"
                            "Статус: ⚠️ Ошибка проверки\n\n"
                            "Решение сохранено. "
                            "Попробуй повторить проверку позже."
                        ),
                        reply_markup=get_project_card_keyboard(
                            project_id=error_project.id,
                            course_slug=error_course.slug,
                        ),
                    )

            return

        feedback = format_review_feedback(
            result
        )

        async with async_session_factory() as result_session:
            attempt_repository = AttemptRepository(
                result_session
            )
            user_project_repository = (
                UserProjectRepository(
                    result_session
                )
            )
            xp_repository = XPRepository(
                result_session
            )
            project_repository = ProjectRepository(
                result_session
            )

            attempt = await attempt_repository.get_by_id(
                attempt_id
            )

            if attempt is None:
                return

            project = await project_repository.get_by_id(
                attempt.project_id
            )

            if project is None:
                return

            if result.passed:
                await attempt_repository.mark_passed(
                    attempt,
                    feedback,
                )

                completed = (
                    await user_project_repository
                    .complete_project(
                        user_id=attempt.user_id,
                        project_id=project.id,
                        awarded_xp=attempt.xp_snapshot,
                    )
                )

                if (
                    completed is not None
                    and attempt.xp_snapshot > 0
                ):
                    await xp_repository.add_project_reward(
                        user_id=attempt.user_id,
                        course_id=project.course_id,
                        project_id=project.id,
                        amount=attempt.xp_snapshot,
                    )

            else:
                await attempt_repository.mark_failed(
                    attempt,
                    feedback,
                )

            await result_session.commit()

            if result.passed:
                result_text = (
                    f"✅ <b>Проверка Project "
                    f"{project.number} завершена.</b>\n\n"
                    f"{project.title}\n\n"
                    f"Статус: ✅ Принято\n\n"
                    "Подробный результат доступен "
                    "в разделе <b>«Мои попытки»</b>."
                )
            else:
                result_text = (
                    f"❌ <b>Project "
                    f"{project.number} пока не принят.</b>\n\n"
                    f"{project.title}\n\n"
                    f"Статус: ❌ Не принято\n\n"
                    "Подробный результат доступен "
                    "в разделе <b>«Мои попытки»</b>."
                )

            course_repository = CourseRepository(
                result_session
            )

            course = await course_repository.get_by_id(
                project.course_id
            )

            if (
                    course is not None
                    and attempt.status_chat_id is not None
                    and attempt.status_message_id is not None
            ):
                await bot.edit_message_text(
                    chat_id=attempt.status_chat_id,
                    message_id=attempt.status_message_id,
                    text=result_text,
                    reply_markup=get_project_card_keyboard(
                        project_id=project.id,
                        course_slug=course.slug,
                    ),
                )