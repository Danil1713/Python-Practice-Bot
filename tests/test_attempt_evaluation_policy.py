from app.database.repositories.attempt_repository import (
    ACTIVE_STATUSES,
)
from app.services.attempt_check_service import (
    verdict_allows_xp,
)


def test_only_passed_verdict_allows_xp() -> None:
    assert verdict_allows_xp("passed") is True

    assert verdict_allows_xp("failed") is False

    assert verdict_allows_xp("review") is False


def test_review_does_not_block_new_attempt() -> None:
    assert "pending" in ACTIVE_STATUSES
    assert "checking" in ACTIVE_STATUSES
    assert "review" not in ACTIVE_STATUSES


def test_review_verdict_does_not_allow_xp() -> None:
    assert verdict_allows_xp("review") is False
