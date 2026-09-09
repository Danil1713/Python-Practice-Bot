from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionPlan:
    course_slug: str
    stars_price: int
    days: int


PLANS = {
    "python_start": SubscriptionPlan(
        course_slug="python-start",
        stars_price=350,
        days=30,
    ),
    "python_practice": SubscriptionPlan(
        course_slug="python-practice",
        stars_price=500,
        days=30,
    ),
}


def get_subscription_plan(
    course_slug: str,
) -> SubscriptionPlan | None:
    return PLANS.get(
        course_slug
    )