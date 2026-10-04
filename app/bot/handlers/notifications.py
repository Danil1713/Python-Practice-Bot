from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(F.data == "notification:dismiss")
async def dismiss_notification_handler(
    callback: CallbackQuery,
) -> None:
    if callback.message is not None:
        await callback.message.delete()

    await callback.answer()
