from aiogram.fsm.state import (
    State,
    StatesGroup,
)


class AdminScheduleStates(StatesGroup):
    waiting_for_reschedule_datetime = State()

    choosing_post_type = State()
    choosing_project = State()
    choosing_hint = State()

    creating_project_title = State()
    creating_project_ai_requirements = State()
    confirming_project_creation = State()

    confirming_hint_creation = State()

    waiting_for_content = State()
    waiting_for_datetime = State()
    confirming = State()

    searching_subscription_user = State()
    choosing_subscription_user = State()
    waiting_for_subscription_days = State()
    confirming_subscription = State()
