from aiogram.fsm.state import State, StatesGroup

class AddMovieState(StatesGroup):
    waiting_for_title = State()
    waiting_for_file = State()

class VIPState(StatesGroup):
    waiting_for_receipt = State()

class AdminState(StatesGroup):
    waiting_for_card = State()
    waiting_for_broadcast = State()
    waiting_for_add_channel = State()
    waiting_for_rename_movie = State()
    waiting_for_replace_movie_file = State()
    waiting_for_manual_vip_id = State()
