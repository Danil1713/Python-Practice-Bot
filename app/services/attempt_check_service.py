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


async def check_attempt(
    attempt_id: int,
) -> None:
    async with async_session_factory() as session:
        attempt_repository = AttemptRepository(
            session
        )
        project_repository = ProjectRepository(
            session
        )

        attempt = await attempt_repository.get_by_id(
            attempt_id
        )

        if attempt is None:
            return

        if attempt.status != "pending":
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
                error_attempt_repository = (
                    AttemptRepository(
                        error_session
                    )
                )

                error_attempt = (
                    await error_attempt_repository
                    .get_by_id(attempt_id)
                )

                if error_attempt is not None:
                    await error_attempt_repository.mark_error(
                        error_attempt,
                        str(error),
                    )

                    await error_session.commit()

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