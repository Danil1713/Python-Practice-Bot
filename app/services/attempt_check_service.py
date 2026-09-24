from aiogram import Bot
from html import escape
from app.config import get_ai_model
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
    AI_POLICY_VERSION,
    CodeReviewResult,
    RequirementReview,
    format_review_feedback,
    resolve_review_verdict,
    review_python_code,
)
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)

from app.services.user_service import (
    AI_REVIEW_CONSENT_VERSION,
)
from app.services.code_validation_service import (
    validate_python_syntax,
)
from app.bot.views.project_card import (
    get_project_card_markup,
)
from app.services.subscription_service import (
    has_active_subscription,
)

EVALUATION_VERSION = "attempt-evaluation-v1"

def verdict_allows_xp(
    verdict: str,
) -> bool:
    return verdict == "passed"


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
        user_repository = UserRepository(
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

        user = await user_repository.get_by_id(
            attempt.user_id
        )

        if user is None:
            await attempt_repository.mark_error(
                attempt,
                "User not found",
            )

            await session.commit()
            return

        telegram_user_id = user.telegram_id

        has_ai_consent = (
                user.ai_review_consent_version
                == AI_REVIEW_CONSENT_VERSION
                and user.ai_review_consent_at
                is not None
        )

        if not has_ai_consent:
            await attempt_repository.mark_error(
                attempt,
                "AI review consent missing or outdated",
            )

            course_repository = CourseRepository(
                session
            )

            course = await course_repository.get_by_id(
                project.course_id
            )

            await session.commit()

            active_subscription = False

            if course is not None:
                active_subscription = (
                    await has_active_subscription(
                        telegram_user_id=telegram_user_id,
                        course_slug=course.slug,
                    )
                )

            if (
                    course is not None
                    and attempt.status_chat_id is not None
                    and attempt.status_message_id is not None
            ):
                await bot.edit_message_text(
                    chat_id=attempt.status_chat_id,
                    message_id=attempt.status_message_id,
                    text=(
                        "⚠️ <b>Проверка не запущена.</b>\n\n"
                        f"Project {project.number} — "
                        f"{escape(project.title)}\n\n"
                        "Нужно подтвердить актуальные "
                        "условия AI-проверки.\n\n"
                        "Открой проект и отправь "
                        "решение заново."
                    ),
                    reply_markup=get_project_card_markup(
                        project,
                        course_slug=course.slug,
                        active_subscription=active_subscription,
                    ),
                )

            return

        await attempt_repository.mark_checking(
            attempt
        )

        await session.commit()

        ai_model_used: str | None = None
        ai_policy_version_used: str | None = None
        ai_result_json: str | None = None

        syntax_check = validate_python_syntax(
            attempt.source_code
        )

        if not syntax_check.valid:
            location_parts = []

            if syntax_check.line is not None:
                location_parts.append(
                    f"строка {syntax_check.line}"
                )

            if syntax_check.column is not None:
                location_parts.append(
                    f"позиция {syntax_check.column}"
                )

            location = ", ".join(
                location_parts
            )

            problem = (
                "Синтаксическая ошибка Python"
            )

            if location:
                problem += f" ({location})"

            if syntax_check.error_message:
                problem += (
                    f": {syntax_check.error_message}"
                )

            result = CodeReviewResult(
                verdict="failed",
                requirements_complete=False,
                criteria=[
                    RequirementReview(
                        requirement=(
                            "Корректный синтаксис Python"
                        ),
                        status="failed",
                        explanation=problem,
                    )
                ],
                summary=(
                    "Код не прошёл локальную "
                    "синтаксическую проверку Python."
                ),
                strengths=[],
                problems=[
                    problem,
                ],
                recommendations=[
                    (
                        "Исправь синтаксическую "
                        "ошибку и отправь решение "
                        "повторно."
                    )
                ],
            )

            effective_verdict = "failed"

        elif (
                attempt.requirements_snapshot is None
                or not attempt.requirements_snapshot.strip()
        ):
            problem = (
                "Требования проекта для этой "
                "попытки не были зафиксированы."
            )

            result = CodeReviewResult(
                verdict="review",
                requirements_complete=False,
                criteria=[
                    RequirementReview(
                        requirement=(
                            "Зафиксированные требования "
                            "проекта"
                        ),
                        status="uncertain",
                        explanation=problem,
                    )
                ],
                summary=(
                    "Автоматическая проверка "
                    "невозможна без сохранённого "
                    "снимка требований."
                ),
                strengths=[],
                problems=[
                    problem,
                ],
                recommendations=[
                    (
                        "Отправь решение повторно, "
                        "чтобы новая попытка сохранила "
                        "актуальные требования проекта."
                    )
                ],
            )

            effective_verdict = "review"

        else:
            try:
                ai_model_used = get_ai_model()
                ai_policy_version_used = (
                    AI_POLICY_VERSION
                )

                result = await review_python_code(
                    project_title=project.title,
                    requirements=(
                        attempt.requirements_snapshot
                    ),
                    source_code=attempt.source_code,
                )

                ai_result_json = (
                    result.model_dump_json()
                )

                effective_verdict = (
                    resolve_review_verdict(
                        result
                    )
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

                    await error_attempt_repository.set_evaluation_metadata(
                        error_attempt,
                        evaluation_version=(
                            EVALUATION_VERSION
                        ),
                        ai_model=ai_model_used,
                        ai_policy_version=(
                            ai_policy_version_used
                        ),
                        ai_result_json=None,
                    )

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

                    active_subscription = (
                        await has_active_subscription(
                            telegram_user_id=telegram_user_id,
                            course_slug=error_course.slug,
                        )
                    )

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
                                f"{escape(error_project.title)}\n\n"
                                "Статус: ⚠️ Ошибка проверки\n\n"
                                "Решение сохранено. "
                                "Попробуй повторить проверку позже."
                            ),
                            reply_markup=get_project_card_markup(
                                error_project,
                                course_slug=error_course.slug,
                                active_subscription=active_subscription,
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

            await attempt_repository.set_evaluation_metadata(
                attempt,
                evaluation_version=(
                    EVALUATION_VERSION
                ),
                ai_model=ai_model_used,
                ai_policy_version=(
                    ai_policy_version_used
                ),
                ai_result_json=ai_result_json,
            )

            project = await project_repository.get_by_id(
                attempt.project_id
            )

            if project is None:
                return

            if verdict_allows_xp(
                    effective_verdict
            ):
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

            elif effective_verdict == "failed":
                await attempt_repository.mark_failed(
                    attempt,
                    feedback,
                )

            else:
                await attempt_repository.mark_review(
                    attempt,
                    feedback,
                )
            await result_session.commit()

            if effective_verdict == "passed":
                result_text = (
                    f"✅ <b>Проверка Project "
                    f"{project.number} завершена.</b>\n\n"
                    f"{escape(project.title)}\n\n"
                    "Статус: ✅ Принято\n\n"
                    "Подробный результат доступен "
                    "в разделе <b>«Мои попытки»</b>."
                )

            elif effective_verdict == "failed":
                result_text = (
                    f"❌ <b>Project "
                    f"{project.number} пока не принят.</b>\n\n"
                    f"{escape(project.title)}\n\n"
                    "Статус: ❌ Не принято\n\n"
                    "Подробный результат доступен "
                    "в разделе <b>«Мои попытки»</b>."
                )

            else:
                result_text = (
                    f"🟠 <b>Project "
                    f"{project.number} не удалось "
                    f"принять автоматически.</b>\n\n"
                    f"{escape(project.title)}\n\n"
                    "Статус: 🟠 Нужна повторная попытка\n\n"
                    "XP не начислен.\n\n"
                    "Посмотри подробный результат "
                    "в разделе <b>«Мои попытки»</b> "
                    "и можешь отправить исправленное "
                    "решение повторно."
                )

            course_repository = CourseRepository(
                result_session
            )

            course = await course_repository.get_by_id(
                project.course_id
            )

            active_subscription = False

            if course is not None:
                active_subscription = (
                    await has_active_subscription(
                        telegram_user_id=telegram_user_id,
                        course_slug=course.slug,
                    )
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
                    reply_markup=get_project_card_markup(
                        project,
                        course_slug=course.slug,
                        active_subscription=active_subscription,
                    ),
                )