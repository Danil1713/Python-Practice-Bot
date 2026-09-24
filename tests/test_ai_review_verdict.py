from app.services.ai_service import (
    CodeReviewResult,
    RequirementReview,
    resolve_review_verdict,
)


def make_criterion(
    status: str,
) -> RequirementReview:
    return RequirementReview(
        requirement="Требование",
        status=status,
        explanation="Причина",
    )


def test_all_requirements_passed() -> None:
    result = CodeReviewResult(
        verdict="passed",
        requirements_complete=True,
        criteria=[
            make_criterion("passed"),
            make_criterion("passed"),
        ],
        summary="Всё выполнено.",
        strengths=[],
        problems=[],
        recommendations=[],
    )

    assert (
        resolve_review_verdict(result)
        == "passed"
    )


def test_failed_requirement_fails() -> None:
    result = CodeReviewResult(
        verdict="failed",
        requirements_complete=True,
        criteria=[
            make_criterion("passed"),
            make_criterion("failed"),
        ],
        summary="Есть ошибка.",
        strengths=[],
        problems=[
            "Требование не выполнено."
        ],
        recommendations=[],
    )

    assert (
        resolve_review_verdict(result)
        == "failed"
    )


def test_uncertain_requirement_requires_review() -> None:
    result = CodeReviewResult(
        verdict="review",
        requirements_complete=True,
        criteria=[
            make_criterion("passed"),
            make_criterion("uncertain"),
        ],
        summary="Не всё можно определить.",
        strengths=[],
        problems=[],
        recommendations=[],
    )

    assert (
        resolve_review_verdict(result)
        == "review"
    )


def test_incomplete_requirements_require_review() -> None:
    result = CodeReviewResult(
        verdict="review",
        requirements_complete=False,
        criteria=[
            make_criterion("passed"),
        ],
        summary="Проверены не все требования.",
        strengths=[],
        problems=[],
        recommendations=[],
    )

    assert (
        resolve_review_verdict(result)
        == "review"
    )


def test_contradictory_ai_result_requires_review() -> None:
    result = CodeReviewResult(
        verdict="passed",
        requirements_complete=True,
        criteria=[
            make_criterion("failed"),
        ],
        summary="Противоречивый результат.",
        strengths=[],
        problems=[
            "Есть невыполненное требование."
        ],
        recommendations=[],
    )

    assert (
        resolve_review_verdict(result)
        == "review"
    )


def test_passed_with_problems_requires_review() -> None:
    result = CodeReviewResult(
        verdict="passed",
        requirements_complete=True,
        criteria=[
            make_criterion("passed"),
        ],
        summary="Есть противоречие.",
        strengths=[],
        problems=[
            "Почему-то указана ошибка."
        ],
        recommendations=[],
    )

    assert (
        resolve_review_verdict(result)
        == "review"
    )