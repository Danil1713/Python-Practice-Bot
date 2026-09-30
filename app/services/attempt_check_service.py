from html import escape

from aiogram import Bot

from app.bot.views.project_card import (
    get_project_card_markup,
)
from app.config import get_ai_model
from app.database.repositories.attempt_repository import (
    AttemptRepository,
)
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.repositories.user_project_repository import (
    UserProjectRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.repositories.xp_repository import (
    XPRepository,
)
from app.database.session import (
    async_session_factory,
)
from app.services.ai_check_limit_service import (
    MAX_AI_CHECKS_PER_PROJECT,
)
from app.services.ai_service import (
    AI_POLICY_VERSION,
    CodeReviewResult,
    RequirementReview,
    format_review_feedback,
    resolve_review_verdict,
    review_python_code,
)
from app.services.code_validation_service import (
    validate_python_syntax,
)
from app.services.subscription_service import (
    has_active_subscription,
)
from app.services.user_service import (
    AI_REVIEW_CONSENT_VERSION,
)

EVALUATION_VERSION = "attempt-evaluation-v1"


def verdict_allows_xp(
    verdict: str,
) -> bool:
    return verdict == "passed"


def _build_local_review_result(
    source_code: str,
    requirements_snapshot: str | None,
) -> tuple[CodeReviewResult, str] | None:
    syntax_check = validate_python_syntax(source_code)

    if not syntax_check.valid:
        location_parts = []

        if syntax_check.line is not None:
            location_parts.append(f"строка {syntax_check.line}")

        if syntax_check.column is not None:
            location_parts.append(f"позиция {syntax_check.column}")

        location = ", ".join(location_parts)

        problem = "Синтаксическая ошибка Python"

        if location:
            problem += f" ({location})"

        if syntax_check.error_message:
            problem += f": {syntax_check.error_message}"

        result = CodeReviewResult(
            verdict="failed",
            requirements_complete=False,
            criteria=[
                RequirementReview(
                    requirement=("Корректный синтаксис Python"),
                    status="failed",
                    explanation=problem,
                )
            ],
            summary=("Код не прошёл локальную синтаксическую проверку Python."),
            strengths=[],
            problems=[
                problem,
            ],
            recommendations=[
                ("Исправь синтаксическую ошибку и отправь решение повторно.")
            ],
        )

        return result, "failed"

    if requirements_snapshot is None or not requirements_snapshot.strip():
        problem = "Требования проекта для этой попытки не были зафиксированы."

        result = CodeReviewResult(
            verdict="review",
            requirements_complete=False,
            criteria=[
                RequirementReview(
                    requirement=("Зафиксированные требования проекта"),
                    status="uncertain",
                    explanation=problem,
                )
            ],
            summary=(
                "Автоматическая проверка невозможна без сохранённого снимка требований."
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

        return result, "review"

    return None


async def _handle_ai_review_error(
    *,
    attempt_id: int,
    telegram_user_id: int,
    bot: Bot,
    error: Exception,
    ai_model: str | None,
    ai_policy_version: str | None,
) -> None:
    async with async_session_factory() as error_session:
        attempt_repository = AttemptRepository(error_session)
        project_repository = ProjectRepository(error_session)
        course_repository = CourseRepository(error_session)

        attempt = await attempt_repository.get_by_id(attempt_id)

        if attempt is None:
            return

        await attempt_repository.set_evaluation_metadata(
            attempt,
            evaluation_version=(EVALUATION_VERSION),
            ai_model=ai_model,
            ai_policy_version=(ai_policy_version),
            ai_result_json=None,
        )

        await attempt_repository.mark_error(
            attempt,
            str(error),
        )

        project = await project_repository.get_by_id(attempt.project_id)

        await error_session.commit()

        if project is None:
            return

        course = await course_repository.get_by_id(project.course_id)

        if course is None:
            return

        active_subscription = await has_active_subscription(
            telegram_user_id=telegram_user_id,
            course_slug=course.slug,
        )

        if attempt.status_chat_id is None or attempt.status_message_id is None:
            return

        await bot.edit_message_text(
            chat_id=attempt.status_chat_id,
            message_id=attempt.status_message_id,
            text=(
                f"⚠️ <b>Не удалось проверить "
                f"Project {project.number}.</b>\n\n"
                f"{escape(project.title)}\n\n"
                "Статус: ⚠️ Ошибка проверки\n\n"
                "Решение сохранено. "
                "Попробуй повторить проверку позже."
            ),
            reply_markup=get_project_card_markup(
                project,
                course_slug=course.slug,
                active_subscription=(active_subscription),
            ),
        )


async def _apply_attempt_result(
    *,
    attempt_repository: AttemptRepository,
    user_project_repository: UserProjectRepository,
    xp_repository: XPRepository,
    attempt,
    project,
    effective_verdict: str,
    feedback: str,
    ai_model: str | None,
    ai_policy_version: str | None,
    ai_result_json: str | None,
) -> None:
    await attempt_repository.set_evaluation_metadata(
        attempt,
        evaluation_version=(EVALUATION_VERSION),
        ai_model=ai_model,
        ai_policy_version=(ai_policy_version),
        ai_result_json=ai_result_json,
    )

    if verdict_allows_xp(effective_verdict):
        await attempt_repository.mark_passed(
            attempt,
            feedback,
        )

        completed = await user_project_repository.complete_project(
            user_id=attempt.user_id,
            project_id=project.id,
            awarded_xp=attempt.xp_snapshot,
        )

        if completed is not None and attempt.xp_snapshot > 0:
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


def _build_attempt_result_text(
    *,
    effective_verdict: str,
    project_number: int,
    project_title: str,
) -> str:
    safe_title = escape(project_title)

    if effective_verdict == "passed":
        return (
            f"✅ <b>Проверка Project "
            f"{project_number} завершена.</b>\n\n"
            f"{safe_title}\n\n"
            "Статус: ✅ Принято\n\n"
            "Подробный результат доступен "
            "в разделе <b>«Мои попытки»</b>."
        )

    if effective_verdict == "failed":
        return (
            f"❌ <b>Project "
            f"{project_number} пока не принят.</b>\n\n"
            f"{safe_title}\n\n"
            "Статус: ❌ Не принято\n\n"
            "Подробный результат доступен "
            "в разделе <b>«Мои попытки»</b>."
        )

    return (
        f"🟠 <b>Project "
        f"{project_number} не удалось "
        f"принять автоматически.</b>\n\n"
        f"{safe_title}\n\n"
        "Статус: 🟠 Нужна повторная попытка\n\n"
        "XP не начислен.\n\n"
        "Посмотри подробный результат "
        "в разделе <b>«Мои попытки»</b> "
        "и можешь отправить исправленное "
        "решение повторно."
    )


async def _notify_attempt_result(
    *,
    session,
    attempt,
    project,
    telegram_user_id: int,
    effective_verdict: str,
    bot: Bot,
) -> None:
    if attempt.status_chat_id is None or attempt.status_message_id is None:
        return

    course_repository = CourseRepository(session)

    course = await course_repository.get_by_id(project.course_id)

    if course is None:
        return

    active_subscription = await has_active_subscription(
        telegram_user_id=telegram_user_id,
        course_slug=course.slug,
    )

    result_text = _build_attempt_result_text(
        effective_verdict=effective_verdict,
        project_number=project.number,
        project_title=project.title,
    )

    await bot.edit_message_text(
        chat_id=attempt.status_chat_id,
        message_id=attempt.status_message_id,
        text=result_text,
        reply_markup=get_project_card_markup(
            project,
            course_slug=course.slug,
            active_subscription=(active_subscription),
        ),
    )


async def check_attempt(
    attempt_id: int,
    bot: Bot,
) -> None:
    async with async_session_factory() as session:
        attempt_repository = AttemptRepository(session)
        project_repository = ProjectRepository(session)
        user_repository = UserRepository(session)

        claimed = await attempt_repository.claim_pending(attempt_id)

        if not claimed:
            await session.rollback()
            return

        await session.commit()

        attempt = await attempt_repository.get_by_id(attempt_id)

        if attempt is None:
            return

        project = await project_repository.get_by_id(attempt.project_id)

        if project is None:
            await attempt_repository.mark_error(
                attempt,
                "Project not found",
            )

            await session.commit()
            return

        user = await user_repository.get_by_id(attempt.user_id)

        if user is None:
            await attempt_repository.mark_error(
                attempt,
                "User not found",
            )

            await session.commit()
            return

        telegram_user_id = user.telegram_id

        has_ai_consent = (
            user.ai_review_consent_version == AI_REVIEW_CONSENT_VERSION
            and user.ai_review_consent_at is not None
        )

        if not has_ai_consent:
            await attempt_repository.mark_error(
                attempt,
                ("AI review consent missing or outdated"),
            )

            course_repository = CourseRepository(session)

            course = await course_repository.get_by_id(project.course_id)

            await session.commit()

            active_subscription = False

            if course is not None:
                active_subscription = await has_active_subscription(
                    telegram_user_id=(telegram_user_id),
                    course_slug=course.slug,
                )

            if (
                course is not None
                and attempt.status_chat_id is not None
                and attempt.status_message_id is not None
            ):
                await bot.edit_message_text(
                    chat_id=attempt.status_chat_id,
                    message_id=(attempt.status_message_id),
                    text=(
                        "⚠️ <b>Проверка "
                        "не запущена.</b>\n\n"
                        f"Project {project.number} — "
                        f"{escape(project.title)}\n\n"
                        "Нужно подтвердить актуальные "
                        "условия AI-проверки.\n\n"
                        "Открой проект и отправь "
                        "решение заново."
                    ),
                    reply_markup=(
                        get_project_card_markup(
                            project,
                            course_slug=course.slug,
                            active_subscription=(active_subscription),
                        )
                    ),
                )

            return

        await attempt_repository.mark_checking(attempt)

        await session.commit()

        ai_model_used: str | None = None
        ai_policy_version_used: str | None = None
        ai_result_json: str | None = None

        local_review = _build_local_review_result(
            source_code=attempt.source_code,
            requirements_snapshot=(attempt.requirements_snapshot),
        )

        if local_review is not None:
            result, effective_verdict = local_review

        else:
            try:
                ai_model_used = get_ai_model()
                ai_policy_version_used = AI_POLICY_VERSION

                ai_checks_used = await attempt_repository.count_ai_checks(
                    user_id=attempt.user_id,
                    project_id=attempt.project_id,
                )

                if ai_checks_used >= MAX_AI_CHECKS_PER_PROJECT:
                    await attempt_repository.mark_error(
                        attempt,
                        "AI check limit reached",
                    )

                    await session.commit()

                    course_repository = CourseRepository(session)

                    course = await course_repository.get_by_id(project.course_id)

                    if (
                        course is not None
                        and attempt.status_chat_id is not None
                        and attempt.status_message_id is not None
                    ):
                        active_subscription = await has_active_subscription(
                            telegram_user_id=telegram_user_id,
                            course_slug=course.slug,
                        )

                        await bot.edit_message_text(
                            chat_id=attempt.status_chat_id,
                            message_id=attempt.status_message_id,
                            text=(
                                "🤖 <b>Проверка не запущена.</b>\n\n"
                                f"Project {project.number} — "
                                f"{escape(project.title)}\n\n"
                                "Лимит AI-проверок "
                                "для этого задания исчерпан: "
                                f"<b>{MAX_AI_CHECKS_PER_PROJECT} "
                                f"из {MAX_AI_CHECKS_PER_PROJECT}</b>."
                            ),
                            reply_markup=get_project_card_markup(
                                project,
                                course_slug=course.slug,
                                active_subscription=(active_subscription),
                            ),
                        )

                    return

                await attempt_repository.set_evaluation_metadata(
                    attempt,
                    evaluation_version=(EVALUATION_VERSION),
                    ai_model=ai_model_used,
                    ai_policy_version=(ai_policy_version_used),
                    ai_result_json=None,
                )

                await session.commit()

                result = await review_python_code(
                    project_title=project.title,
                    requirements=(attempt.requirements_snapshot),
                    source_code=attempt.source_code,
                )

                ai_result_json = result.model_dump_json()

                effective_verdict = resolve_review_verdict(result)

            except Exception as error:
                await _handle_ai_review_error(
                    attempt_id=attempt_id,
                    telegram_user_id=(telegram_user_id),
                    bot=bot,
                    error=error,
                    ai_model=ai_model_used,
                    ai_policy_version=(ai_policy_version_used),
                )

                return

        feedback = format_review_feedback(result)

        async with async_session_factory() as result_session:
            attempt_repository = AttemptRepository(result_session)
            user_project_repository = UserProjectRepository(result_session)
            xp_repository = XPRepository(result_session)
            project_repository = ProjectRepository(result_session)

            attempt = await attempt_repository.get_by_id(attempt_id)

            if attempt is None:
                return

            project = await project_repository.get_by_id(attempt.project_id)

            if project is None:
                return

            await _apply_attempt_result(
                attempt_repository=attempt_repository,
                user_project_repository=(user_project_repository),
                xp_repository=xp_repository,
                attempt=attempt,
                project=project,
                effective_verdict=(effective_verdict),
                feedback=feedback,
                ai_model=ai_model_used,
                ai_policy_version=(ai_policy_version_used),
                ai_result_json=ai_result_json,
            )

            await result_session.commit()

            await _notify_attempt_result(
                session=result_session,
                attempt=attempt,
                project=project,
                telegram_user_id=(telegram_user_id),
                effective_verdict=(effective_verdict),
                bot=bot,
            )
