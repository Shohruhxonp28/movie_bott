from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List
from app.models import Movie, RequiredChannel

def get_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎬 Movies"))
    builder.add(KeyboardButton(text="⭐ VIP"))
    builder.add(KeyboardButton(text="ℹ️ Help"))
    return builder.as_markup(resize_keyboard=True)

def get_join_channels_keyboard(channels: List[RequiredChannel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, chan in enumerate(channels, 1):
        builder.button(text=f"📢 {chan.name}", url=chan.invite_link)
    
    # Grid adjustment: place join buttons, then check & vip on their own rows
    builder.adjust(1)
    
    # Action buttons
    builder.row(
        InlineKeyboardButton(text="🔄 Check Subscription", callback_data="check_subscription"),
        InlineKeyboardButton(text="⭐ Buy VIP", callback_data="buy_vip")
    )
    return builder.as_markup()

def get_vip_plans_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 Month", callback_data="vip_plan_1"),
        InlineKeyboardButton(text="3 Months", callback_data="vip_plan_3"),
        InlineKeyboardButton(text="12 Months", callback_data="vip_plan_12")
    )
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="vip_back"))
    return builder.as_markup()

def get_share_keyboard(bot_username: str, movie_code: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    share_url = f"https://t.me/{bot_username}?start=movie_{movie_code}"
    builder.button(text="📤 Share", url=f"https://t.me/share/url?url={share_url}")
    return builder.as_markup()

def get_movie_list_keyboard(movies: List[Movie], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for movie in movies:
        builder.row(InlineKeyboardButton(text=f"🎬 {movie.title} [{movie.movie_code}]", callback_data=f"view_movie_user_{movie.movie_code}"))
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"movie_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"movie_page_{page+1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text="❌ Close", callback_data="close_movies"))
    return builder.as_markup()

def get_admin_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Add Movie", callback_data="admin_add_movie"),
        InlineKeyboardButton(text="🎬 Movies", callback_data="admin_movies_page_1")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ VIP", callback_data="admin_vip_plans"),
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="📺 Required Channels", callback_data="admin_channels"),
        InlineKeyboardButton(text="💳 Bank Card", callback_data="admin_bank_card")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats")
    )
    return builder.as_markup()

def get_receipt_approval_keyboard(user_id: int, months: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_vip_{user_id}_{months}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_vip_{user_id}")
    )
    return builder.as_markup()

def get_admin_channels_keyboard(channels: List[RequiredChannel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for chan in channels:
        builder.row(
            InlineKeyboardButton(text=f"❌ Delete {chan.name}", callback_data=f"admin_delete_channel_{chan.channel_id}")
        )
    builder.row(
        InlineKeyboardButton(text="➕ Add Channel", callback_data="admin_add_channel"),
        InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")
    )
    return builder.as_markup()

def get_admin_movies_keyboard(movies: List[Movie], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for movie in movies:
        builder.row(InlineKeyboardButton(text=f"🎬 {movie.title} [{movie.movie_code}]", callback_data=f"admin_movie_detail_{movie.movie_code}"))
        
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"admin_movies_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"admin_movies_page_{page+1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_back"))
    return builder.as_markup()

def get_movie_detail_keyboard(code: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁️ View Movie", callback_data=f"admin_view_movie_file_{code}"),
        InlineKeyboardButton(text="✏️ Rename", callback_data=f"admin_rename_movie_{code}")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Replace File", callback_data=f"admin_replace_movie_{code}"),
        InlineKeyboardButton(text="🗑️ Delete", callback_data=f"admin_delete_movie_{code}")
    )
    builder.row(InlineKeyboardButton(text="🔙 Back to List", callback_data="admin_movies_page_1"))
    return builder.as_markup()

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Confirm", callback_data="admin_confirm_broadcast"),
        InlineKeyboardButton(text="❌ Cancel", callback_data="admin_back")
    )
    return builder.as_markup()
