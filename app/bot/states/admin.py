from aiogram.fsm.state import (
    State,
    StatesGroup,
)


class AdminScheduleStates(StatesGroup):
    waiting_for_reschedule_datetime = State()

    choosing_post_type = State()
    choosing_project = State()
    choosing_hint = State()
    waiting_for_content = State()
    waiting_for_datetime = State()
    confirming = State()