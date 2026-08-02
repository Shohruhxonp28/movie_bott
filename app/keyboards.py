from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List
from app.models import Movie, RequiredChannel, Series, User, VipPlan

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
        # Handle username starting with @
        if url.startswith("@"):
            url = f"https://t.me/{url[1:]}"
        # Handle typos containing telegram domains
        elif "t.me" in url or "telegram.me" in url:
            if url.startswith("ttps://"):
                url = "h" + url
            elif url.startswith("tps://"):
                url = "ht" + url
            elif url.startswith("ps://"):
                url = "htt" + url
            elif not (url.startswith("http://") or url.startswith("https://")):
                url = f"https://{url}"
        else:
            # Fallback if no protocol and no t.me domain
            if not (url.startswith("http://") or url.startswith("https://")):
                url = f"https://t.me/{url}"
        
        builder.button(text=f"📢 {chan.name}", url=url)
    
    builder.adjust(1)
    
    # Action buttons
    builder.row(
        InlineKeyboardButton(text="🔄 A'zolikni tekshirish", callback_data="check_subscription"),
        InlineKeyboardButton(text="⭐ VIP sotib olish", callback_data="buy_vip")
    )
    return builder.as_markup()

def get_user_vip_plans_keyboard(plans: List[VipPlan]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.row(
            InlineKeyboardButton(text=f"⭐ {plan.name} ({plan.price})", callback_data=f"vip_plan_{plan.months}")
        )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_back"))
    return builder.as_markup()

def get_vip_plans_keyboard() -> InlineKeyboardMarkup:
    # Deprecated: use get_user_vip_plans_keyboard instead
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

def get_share_series_keyboard(bot_username: str, series_code: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    share_url = f"https://t.me/{bot_username}?start=movie_{series_code}"
    builder.button(text="📤 Ulashish", url=f"https://t.me/share/url?url={share_url}")
    return builder.as_markup()

def get_movie_list_keyboard(items: List[Any], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        # Check if item is Movie or Series dynamically using attributes
        if hasattr(item, "movie_code"):
            builder.row(InlineKeyboardButton(text=f"🎬 {item.title} [{item.movie_code}]", callback_data=f"view_movie_user_{item.movie_code}"))
        else:
            builder.row(InlineKeyboardButton(text=f"📺 {item.title} [{item.series_code}]", callback_data=f"view_series_user_{item.series_code}"))
    
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
        InlineKeyboardButton(text="➕ Serial qo'shish", callback_data="admin_add_series")
    )
    builder.row(
        InlineKeyboardButton(text="🎬 Kinolar", callback_data="admin_movies_page_1"),
        InlineKeyboardButton(text="📺 Seriallar", callback_data="admin_series_page_1")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ VIP", callback_data="admin_vip_plans"),
        InlineKeyboardButton(text="📢 Reklama yuborish", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="📺 Majburiy kanallar", callback_data="admin_channels"),
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

def get_admin_vip_keyboard(vip_users: List[User], plans: List[VipPlan]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # 1. VIP Users List buttons
    if vip_users:
        builder.row(InlineKeyboardButton(text="👥 VIP Foydalanuvchilar (Boshqarish):", callback_data="noop"))
        for u in vip_users:
            builder.row(
                InlineKeyboardButton(
                    text=f"👤 {u.full_name[:20]} [ID: {u.id}]",
                    callback_data=f"admin_manage_vip_user_{u.id}"
                )
            )
            
    # 2. VIP Plans List buttons (to delete)
    if plans:
        builder.row(InlineKeyboardButton(text="📋 VIP Tariflar (O'chirish):", callback_data="noop"))
        for p in plans:
            builder.row(
                InlineKeyboardButton(
                    text=f"❌ O'chirish: {p.name} ({p.price})",
                    callback_data=f"admin_delete_vip_plan_{p.id}"
                )
            )
            
    # 3. Operations buttons
    builder.row(
        InlineKeyboardButton(text="➕ VIP qo'shish (Manual)", callback_data="admin_add_vip"),
        InlineKeyboardButton(text="➕ Tarif qo'shish", callback_data="admin_add_vip_plan")
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()

def get_admin_vip_user_manage_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Obunani uzaytirish", callback_data=f"admin_vip_user_extend_{user_id}"),
        InlineKeyboardButton(text="❌ Obunani bekor qilish", callback_data=f"admin_vip_user_cancel_{user_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 VIP bo'limiga qaytish", callback_data="admin_vip_plans"))
    return builder.as_markup()

def get_admin_manual_vip_plans_keyboard(user_id: int, plans: List[VipPlan]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.row(
            InlineKeyboardButton(
                text=f"{plan.name} ({plan.months} oy)",
                callback_data=f"admin_manual_vip_{plan.months}_{user_id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_vip_plans"))
    return builder.as_markup()

# --- NEW SERIES KEYBOARDS ---
def get_series_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔗 Kanal havolasi orqali", callback_data="series_type_link"),
        InlineKeyboardButton(text="📁 Qismlarni yuklash orqali", callback_data="series_type_upload")
    )
    builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_back"))
    return builder.as_markup()

def get_admin_series_keyboard(series: List[Series], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in series:
        builder.row(InlineKeyboardButton(text=f"📺 {s.title} [{s.series_code}]", callback_data=f"admin_series_detail_{s.series_code}"))
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_series_page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_series_page_{page+1}"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()

def get_series_detail_keyboard(code: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁️ Serialni ko'rish", callback_data=f"admin_view_series_{code}"),
        InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"admin_rename_series_{code}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"admin_delete_series_{code}"),
        InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_series_page_1")
    )
    return builder.as_markup()

def get_series_episodes_keyboard(series_code: int, episodes_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, episodes_count + 1):
        builder.button(text=f"{i}-qism", callback_data=f"view_episode_{series_code}_{i}")
    builder.adjust(4)
    return builder.as_markup()

def get_series_link_keyboard(channel_link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    url = channel_link.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = f"https://t.me/{url.replace('@', '')}"
    builder.button(text="🍿 Serialni ko'rish (Kanal)", url=url)
    return builder.as_markup()

def get_finish_upload_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💾 Yakunlash", callback_data="series_finish_upload"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_back"))
    return builder.as_markup()
