from aiogram.fsm.state import State, StatesGroup

class AddMovieState(StatesGroup):
    waiting_for_title = State()
    waiting_for_file = State()

class AddSeriesState(StatesGroup):
    waiting_for_title = State()
    waiting_for_type = State()
    waiting_for_link = State()
    waiting_for_episodes_count = State()
    waiting_for_file = State()
    waiting_for_rename = State()
    waiting_for_edit_link = State()

class VIPState(StatesGroup):
    waiting_for_receipt = State()

class AddVipPlanState(StatesGroup):
    waiting_for_name = State()
    waiting_for_months = State()
    waiting_for_price = State()

class ManageVipUserState(StatesGroup):
    waiting_for_extend_months = State()

class AdminState(StatesGroup):
    waiting_for_card = State()
    waiting_for_broadcast = State()
    waiting_for_broadcast_button = State()
    waiting_for_add_channel = State()
    waiting_for_add_bot = State()
    waiting_for_add_insta = State()
    waiting_for_rename_movie = State()
    waiting_for_replace_movie_file = State()
    waiting_for_manual_vip_id = State()
    waiting_for_reject_reason = State()

class AddAdminState(StatesGroup):
    waiting_for_admin_id = State()

class EditTextState(StatesGroup):
    waiting_for_new_text = State()

class ManageSeriesEpisodesState(StatesGroup):
    waiting_for_season = State()
    waiting_for_episode = State()
    waiting_for_file = State()
    waiting_for_replace_file = State()
    waiting_for_bulk_season = State()
    waiting_for_bulk_files = State()

