from app.services.ai_check_limit_service import (
    MAX_AI_CHECKS_PER_PROJECT,
    AICheckUsage,
)


def test_ai_check_limit_is_five():
    assert (
        MAX_AI_CHECKS_PER_PROJECT
        == 5
    )


def test_four_ai_checks_leave_one():
    usage = AICheckUsage(
        used=4,
        limit=MAX_AI_CHECKS_PER_PROJECT,
    )

    assert usage.used == 4
    assert usage.remaining == 1
    assert usage.exhausted is False


def test_five_ai_checks_exhaust_limit():
    usage = AICheckUsage(
        used=5,
        limit=MAX_AI_CHECKS_PER_PROJECT,
    )

    assert usage.remaining == 0
    assert usage.exhausted is True


def test_usage_never_has_negative_remaining():
    usage = AICheckUsage(
        used=6,
        limit=MAX_AI_CHECKS_PER_PROJECT,
    )

    assert usage.remaining == 0
    assert usage.exhausted is True