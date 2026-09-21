from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.database.models.attempt import Attempt


ACTIVE_STATUSES = (
    "pending",
    "checking",
)


class AttemptRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def lock_attempt_creation(
            self,
            user_id: int,
            project_id: int,
    ) -> None:
        statement = select(
            func.pg_advisory_xact_lock(
                user_id,
                project_id,
            )
        )

        await self.session.execute(
            statement
        )

    async def get_next_attempt_number(
        self,
        user_id: int,
        project_id: int,
    ) -> int:
        statement = select(
            func.coalesce(
                func.max(Attempt.attempt_number),
                0,
            )
        ).where(
            Attempt.user_id == user_id,
            Attempt.project_id == project_id,
        )

        result = await self.session.execute(
            statement
        )

        current_max = result.scalar_one()

        return current_max + 1

    async def create(
        self,
        user_id: int,
        project_id: int,
        attempt_number: int,
        filename: str,
        source_code: str,
        xp_snapshot: int,
    ) -> Attempt:
        attempt = Attempt(
            user_id=user_id,
            project_id=project_id,
            attempt_number=attempt_number,
            filename=filename,
            source_code=source_code,
            status="pending",
            xp_snapshot=xp_snapshot,
        )

        self.session.add(attempt)

        await self.session.flush()

        return attempt

    async def get_active_for_project(
        self,
        user_id: int,
        project_id: int,
    ) -> Attempt | None:
        statement = select(Attempt).where(
            Attempt.user_id == user_id,
            Attempt.project_id == project_id,
            Attempt.status.in_(
                ACTIVE_STATUSES
            ),
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def get_pending_project_ids(
        self,
        user_id: int,
        project_ids: list[int],
    ) -> set[int]:
        if not project_ids:
            return set()

        statement = select(
            Attempt.project_id
        ).where(
            Attempt.user_id == user_id,
            Attempt.project_id.in_(
                project_ids
            ),
            Attempt.status.in_(
                ACTIVE_STATUSES
            ),
        )

        result = await self.session.execute(
            statement
        )

        return set(
            result.scalars().all()
        )

    async def get_by_project_for_user(
        self,
        user_id: int,
        project_id: int,
    ) -> list[Attempt]:
        statement = (
            select(Attempt)
            .where(
                Attempt.user_id == user_id,
                Attempt.project_id == project_id,
            )
            .order_by(
                Attempt.attempt_number.desc()
            )
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def get_by_id_for_user(
        self,
        attempt_id: int,
        user_id: int,
    ) -> Attempt | None:
        statement = select(Attempt).where(
            Attempt.id == attempt_id,
            Attempt.user_id == user_id,
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def get_by_id(
            self,
            attempt_id: int,
    ) -> Attempt | None:
        statement = select(Attempt).where(
            Attempt.id == attempt_id
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def mark_checking(
            self,
            attempt: Attempt,
    ) -> None:
        attempt.status = "checking"

        await self.session.flush()

    async def mark_passed(
            self,
            attempt: Attempt,
            feedback: str,
    ) -> None:
        attempt.status = "passed"
        attempt.ai_feedback = feedback
        attempt.error_message = None
        attempt.checking_started_at = None
        attempt.checked_at = datetime.now(
            timezone.utc
        )

        await self.session.flush()

    async def mark_failed(
            self,
            attempt: Attempt,
            feedback: str,
    ) -> None:
        attempt.status = "failed"
        attempt.ai_feedback = feedback
        attempt.error_message = None
        attempt.checking_started_at = None
        attempt.checked_at = datetime.now(
            timezone.utc
        )

        await self.session.flush()

    async def mark_error(
            self,
            attempt: Attempt,
            error_message: str,
    ) -> None:
        attempt.status = "error"
        attempt.error_message = error_message
        attempt.checking_started_at = None
        attempt.checked_at = datetime.now(
            timezone.utc
        )

        await self.session.flush()

    async def get_pending(
            self,
            limit: int = 10,
    ) -> list[Attempt]:
        statement = (
            select(Attempt)
            .where(
                Attempt.status == "pending"
            )
            .order_by(
                Attempt.submitted_at.asc()
            )
            .limit(limit)
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def set_status_message(
            self,
            attempt: Attempt,
            chat_id: int,
            message_id: int,
    ) -> None:
        attempt.status_chat_id = chat_id
        attempt.status_message_id = message_id

        await self.session.flush()

    async def claim_pending(
            self,
            attempt_id: int,
    ) -> bool:
        statement = (
            update(Attempt)
            .where(
                Attempt.id == attempt_id,
                Attempt.status == "pending",
            )
            .values(
                status="checking",
                checking_started_at=datetime.now(
                    timezone.utc
                ),
            )
            .returning(
                Attempt.id
            )
        )

        result = await self.session.execute(
            statement
        )

        claimed_id = result.scalar_one_or_none()

        return claimed_id is not None

    async def recover_stuck_checking(
            self,
            before: datetime,
    ) -> int:
        statement = select(
            Attempt
        ).where(
            Attempt.status == "checking",
            Attempt.checking_started_at.is_not(
                None
            ),
            Attempt.checking_started_at <= before,
        )

        result = await self.session.execute(
            statement
        )

        attempts = list(
            result.scalars().all()
        )

        for attempt in attempts:
            attempt.status = "pending"
            attempt.checking_started_at = None

        await self.session.flush()

        return len(attempts)