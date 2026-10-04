from unittest.mock import AsyncMock, MagicMock

import pytest

import app.main as main_module


@pytest.mark.asyncio
async def test_startup_failure_closes_all_resources(
    monkeypatch: pytest.MonkeyPatch,
):
    bot = MagicMock()

    bot.delete_webhook = AsyncMock(side_effect=RuntimeError("Telegram unavailable"))

    bot.session.close = AsyncMock()

    storage = MagicMock()
    storage.redis.ping = AsyncMock()
    storage.close = AsyncMock()

    dispatcher = MagicMock()
    dispatcher.start_polling = AsyncMock()

    close_ai_client = AsyncMock()
    dispose_engine = AsyncMock()

    engine = MagicMock()
    engine.dispose = dispose_engine

    monkeypatch.setattr(
        main_module,
        "Bot",
        lambda **kwargs: bot,
    )

    monkeypatch.setattr(
        main_module.RedisStorage,
        "from_url",
        lambda *args, **kwargs: storage,
    )

    monkeypatch.setattr(
        main_module,
        "Dispatcher",
        lambda **kwargs: dispatcher,
    )

    monkeypatch.setattr(
        main_module,
        "engine",
        engine,
    )

    monkeypatch.setattr(
        main_module,
        "get_bot_token",
        lambda: "test-token",
    )

    monkeypatch.setattr(
        main_module,
        "get_redis_url",
        lambda: "redis://test",
    )

    monkeypatch.setattr(
        main_module,
        "close_ai_client",
        close_ai_client,
    )

    with pytest.raises(
        RuntimeError,
        match="Telegram unavailable",
    ):
        await main_module.main()

    storage.redis.ping.assert_awaited_once_with()

    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=False)

    dispatcher.start_polling.assert_not_awaited()

    storage.close.assert_awaited_once_with()
    close_ai_client.assert_awaited_once_with()
    dispose_engine.assert_awaited_once_with()
    bot.session.close.assert_awaited_once_with()
