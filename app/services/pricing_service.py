from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionPlan:
    course_slug: str
    price: int
    days: int


PLANS = {
    "python-start": SubscriptionPlan(
        course_slug="python-start",
        price=69900,
        days=30,
    ),
    "python-practice": SubscriptionPlan(
        course_slug="python-practice",
        price=99900,
        days=30,
    ),
}


def get_subscription_plan(
    course_slug: str,
) -> SubscriptionPlan | None:
    return PLANS.get(
        course_slug
    )