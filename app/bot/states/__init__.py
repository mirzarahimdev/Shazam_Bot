from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_query = State()


class RecognizeStates(StatesGroup):
    waiting_media = State()


class VideoStates(StatesGroup):
    waiting_video = State()
    waiting_category = State()
    waiting_search = State()


class AdminStates(StatesGroup):
    waiting_block_id = State()
