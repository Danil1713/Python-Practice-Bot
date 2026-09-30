from dataclasses import dataclass

from app.database.repositories.attempt_repository import (
    AttemptRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.session import (
    async_session_factory,
)

MAX_AI_CHECKS_PER_PROJECT = 5


@dataclass(frozen=True)
class AICheckUsage:
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(
            0,
            self.limit - self.used,
        )

    @property
    def exhausted(self) -> bool:
        return self.used >= self.limit


async def get_ai_check_usage(
    *,
    telegram_user_id: int,
    project_id: int,
) -> AICheckUsage | None:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        attempt_repository = AttemptRepository(session)

        user = await user_repository.get_by_telegram_id(telegram_user_id)

        if user is None:
            return None

        used = await attempt_repository.count_ai_checks(
            user_id=user.id,
            project_id=project_id,
        )

        return AICheckUsage(
            used=used,
            limit=MAX_AI_CHECKS_PER_PROJECT,
        )
