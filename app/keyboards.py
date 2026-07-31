from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List
from app.models import Movie, RequiredChannel

def get_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎬 Kinolar"))
    builder.add(KeyboardButton(text="⭐ VIP"))
    builder.add(KeyboardButton(text="ℹ️ Yordam"))
    return builder.as_markup(resize_keyboard=True)

def get_join_channels_keyboard(channels: List[RequiredChannel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, chan in enumerate(channels, 1):
        url = chan.invite_link.strip()
        # Ensure URL starts with http:// or https:// to prevent BUTTON_URL_INVALID
        if not (url.startswith("http://") or url.startswith("https://")):
            clean_url = url.replace("@", "")
            url = f"https://t.me/{clean_url}"
        builder.button(text=f"📢 {chan.name}", url=url)
    
    builder.adjust(1)
    
    # Action buttons
    builder.row(
        InlineKeyboardButton(text="🔄 A'zolikni tekshirish", callback_data="check_subscription"),
        InlineKeyboardButton(text="⭐ VIP sotib olish", callback_data="buy_vip")
    )
    return builder.as_markup()

def get_vip_plans_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 Oylik", callback_data="vip_plan_1"),
        InlineKeyboardButton(text="3 Oylik", callback_data="vip_plan_3"),
        InlineKeyboardButton(text="12 Oylik", callback_data="vip_plan_12")
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_back"))
    return builder.as_markup()

def get_share_keyboard(bot_username: str, movie_code: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    share_url = f"https://t.me/{bot_username}?start=movie_{movie_code}"
    builder.button(text="📤 Ulashish", url=f"https://t.me/share/url?url={share_url}")
    return builder.as_markup()

def get_movie_list_keyboard(movies: List[Movie], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for movie in movies:
        builder.row(InlineKeyboardButton(text=f"🎬 {movie.title} [{movie.movie_code}]", callback_data=f"view_movie_user_{movie.movie_code}"))
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"movie_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"movie_page_{page+1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text="❌ Yopish", callback_data="close_movies"))
    return builder.as_markup()

def get_admin_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="admin_add_movie"),
        InlineKeyboardButton(text="🎬 Kinolar", callback_data="admin_movies_page_1")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ VIP", callback_data="admin_vip_plans"),
        InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="📺 Majburiy kanallar", callback_data="admin_channels"),
        InlineKeyboardButton(text="💳 Bank kartasi", callback_data="admin_bank_card")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")
    )
    return builder.as_markup()

def get_receipt_approval_keyboard(user_id: int, months: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_vip_{user_id}_{months}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_vip_{user_id}")
    )
    return builder.as_markup()

def get_admin_channels_keyboard(channels: List[RequiredChannel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for chan in channels:
        builder.row(
            InlineKeyboardButton(text=f"❌ O'chirish {chan.name}", callback_data=f"admin_delete_channel_{chan.channel_id}")
        )
    builder.row(
        InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin_add_channel"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()

def get_admin_movies_keyboard(movies: List[Movie], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for movie in movies:
        builder.row(InlineKeyboardButton(text=f"🎬 {movie.title} [{movie.movie_code}]", callback_data=f"admin_movie_detail_{movie.movie_code}"))
        
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_movies_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_movies_page_{page+1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()

def get_movie_detail_keyboard(code: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁️ Kinoni ko'rish", callback_data=f"admin_view_movie_file_{code}"),
        InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"admin_rename_movie_{code}")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Faylni almashtirish", callback_data=f"admin_replace_movie_{code}"),
        InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"admin_delete_movie_{code}")
    )
    builder.row(InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_movies_page_1"))
    return builder.as_markup()

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="admin_confirm_broadcast"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_back")
    )
    return builder.as_markup()

def get_admin_vip_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ VIP qo'shish (Manual)", callback_data="admin_add_vip"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()

def get_admin_manual_vip_plans_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1 Oylik", callback_data=f"admin_manual_vip_1_{user_id}"),
        InlineKeyboardButton(text="3 Oylik", callback_data=f"admin_manual_vip_3_{user_id}"),
        InlineKeyboardButton(text="12 Oylik", callback_data=f"admin_manual_vip_12_{user_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_vip_plans"))
    return builder.as_markup()
