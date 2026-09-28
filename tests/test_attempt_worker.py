import asyncio

import pytest

from app.scheduler import attempt_checks


@pytest.mark.asyncio
async def test_attempt_batch_respects_concurrency(
    monkeypatch,
):
    active = 0
    max_active = 0
    processed: list[int] = []

    lock = asyncio.Lock()

    async def fake_check_attempt(
        *,
        attempt_id: int,
        bot,
    ) -> None:
        nonlocal active
        nonlocal max_active

        async with lock:
            active += 1

            max_active = max(
                max_active,
                active,
            )

        await asyncio.sleep(
            0.03
        )

        processed.append(
            attempt_id
        )

        async with lock:
            active -= 1

    monkeypatch.setattr(
        attempt_checks,
        "check_attempt",
        fake_check_attempt,
    )

    await attempt_checks.process_attempt_batch(
        attempt_ids=[
            1,
            2,
            3,
            4,
            5,
        ],
        bot=object(),
        max_concurrency=2,
    )

    assert max_active == 2

    assert sorted(processed) == [
        1,
        2,
        3,
        4,
        5,
    ]


@pytest.mark.asyncio
async def test_attempt_failure_does_not_stop_batch(
    monkeypatch,
):
    processed: list[int] = []

    async def fake_check_attempt(
        *,
        attempt_id: int,
        bot,
    ) -> None:
        if attempt_id == 2:
            raise RuntimeError(
                "Test failure"
            )

        processed.append(
            attempt_id
        )

    monkeypatch.setattr(
        attempt_checks,
        "check_attempt",
        fake_check_attempt,
    )

    await attempt_checks.process_attempt_batch(
        attempt_ids=[
            1,
            2,
            3,
        ],
        bot=object(),
        max_concurrency=2,
    )

    assert sorted(processed) == [
        1,
        3,
    ]


@pytest.mark.asyncio
async def test_attempt_batch_rejects_zero_concurrency():
    with pytest.raises(
        ValueError,
        match="greater than 0",
    ):
        await attempt_checks.process_attempt_batch(
            attempt_ids=[1],
            bot=object(),
            max_concurrency=0,
        )