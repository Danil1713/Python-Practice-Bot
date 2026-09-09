import asyncio

from app.database.repositories.payment_repository import (
    PaymentRepository,
)
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.user_repository import (
    UserRepository,
)
from app.database.session import (
    async_session_factory,
    engine,
)
from app.services.payment_service import (
    process_successful_payment,
)


TELEGRAM_USER_ID = 8730251621
COURSE_SLUG = "python_start"
EXTERNAL_PAYMENT_ID = "test_payment_001"


async def create_test_payment() -> None:
    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        course_repository = CourseRepository(session)
        payment_repository = PaymentRepository(session)

        user = await user_repository.get_by_telegram_id(
            TELEGRAM_USER_ID
        )

        if user is None:
            raise RuntimeError(
                "Пользователь не найден"
            )

        course = await course_repository.get_by_slug(
            COURSE_SLUG
        )

        if course is None:
            raise RuntimeError(
                "Курс не найден"
            )

        payment = await payment_repository.create(
            user_id=user.id,
            course_id=course.id,
            provider="test",
            amount=69900,
            currency="RUB",
            subscription_days=30,
        )

        await payment_repository.set_external_id(
            payment,
            EXTERNAL_PAYMENT_ID,
        )

        await session.commit()

        print(
            f"Создан Payment #{payment.id}"
        )


async def main() -> None:
    await create_test_payment()

    print("\nПервое подтверждение:")

    first_result = await process_successful_payment(
        external_payment_id=EXTERNAL_PAYMENT_ID
    )

    print(
        "Результат:",
        first_result,
    )

    print("\nВторое подтверждение:")

    second_result = await process_successful_payment(
        external_payment_id=EXTERNAL_PAYMENT_ID
    )

    print(
        "Результат:",
        second_result,
    )


async def run() -> None:
    try:
        await main()

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())