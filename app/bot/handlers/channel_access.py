import logging

from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    ChatJoinRequest,
)

from app.bot.callbacks import (
    parse_callback_str,
)
from app.bot.handlers.course_context import (
    check_current_course,
)
from app.bot.keyboards.subscription import (
    get_channel_join_keyboard,
)
from app.services.channel_access_service import (
    ChannelAccessError,
    create_course_join_request_link,
    get_course_by_channel_id,
)
from app.services.subscription_service import (
    has_active_subscription,
)

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("subscription:channel:"))
async def subscription_channel_handler(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    course_slug = parse_callback_str(
        callback.data,
        "subscription:channel",
    )

    if course_slug is None:
        await callback.answer(
            "Некорректная команда.",
            show_alert=True,
        )
        return

    if not await check_current_course(
        callback,
        course_slug,
    ):
        return

    try:
        invite_link = await create_course_join_request_link(
            bot=bot,
            telegram_user_id=(callback.from_user.id),
            course_slug=course_slug,
        )

    except ChannelAccessError as error:
        await callback.answer(
            str(error),
            show_alert=True,
        )
        return

    await callback.message.answer(
        text=(
            "📢 <b>Доступ к каналу</b>\n\n"
            "Нажми кнопку ниже и отправь "
            "заявку на вступление.\n\n"
            "Бот автоматически проверит "
            "твою подписку и подтвердит "
            "заявку.\n\n"
            "Ссылка действует ограниченное "
            "время."
        ),
        reply_markup=get_channel_join_keyboard(
            invite_link=invite_link,
            course_slug=course_slug,
        ),
    )

    await callback.answer()


@router.chat_join_request()
async def course_join_request_handler(
    request: ChatJoinRequest,
    bot: Bot,
) -> None:
    course = await get_course_by_channel_id(request.chat.id)

    if course is None:
        return

    allowed = True

    if course.requires_subscription:
        allowed = await has_active_subscription(
            telegram_user_id=(request.from_user.id),
            course_slug=course.slug,
        )

    if allowed:
        try:
            await bot.approve_chat_join_request(
                chat_id=request.chat.id,
                user_id=request.from_user.id,
            )

        except Exception:
            logger.exception(
                "Could not approve "
                "channel join request "
                "telegram_user_id=%s "
                "course_slug=%s",
                request.from_user.id,
                course.slug,
            )

        return

    try:
        await bot.decline_chat_join_request(
            chat_id=request.chat.id,
            user_id=request.from_user.id,
        )

    except Exception:
        logger.exception(
            "Could not decline channel join request telegram_user_id=%s course_slug=%s",
            request.from_user.id,
            course.slug,
        )
