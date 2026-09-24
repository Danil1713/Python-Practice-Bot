from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionPlan:
    course_slug: str
    stars_price: int
    days: int


_SUBSCRIPTION_PLANS = (
    SubscriptionPlan(
        course_slug="python_start",
        stars_price=350,
        days=30,
    ),
    SubscriptionPlan(
        course_slug="python_practice",
        stars_price=500,
        days=30,
    ),
)


PLANS = {
    plan.course_slug: plan
    for plan in _SUBSCRIPTION_PLANS
}


def get_subscription_plan(
    course_slug: str,
) -> SubscriptionPlan | None:
    return PLANS.get(
        course_slug
    )