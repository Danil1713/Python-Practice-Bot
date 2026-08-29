from aiogram.fsm.state import (
    State,
    StatesGroup,
)


class SolutionStates(StatesGroup):
    waiting_for_file = State()