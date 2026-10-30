from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_query = State()


class AdminStates(StatesGroup):
    waiting_block_id = State()
