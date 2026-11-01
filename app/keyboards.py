import urllib.parse
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List
from app.models import Movie, RequiredChannel, Series, User, VipPlan

def get_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎬 Kinolar"))
    builder.add(KeyboardButton(text="📺 Seriallar"))
    builder.add(KeyboardButton(text="⭐ VIP"))
    builder.add(KeyboardButton(text="👥 Referal"))
    builder.add(KeyboardButton(text="ℹ️ Yordam"))
    builder.adjust(2, 2, 1)
    return builder.as_markup(resize_keyboard=True)

def get_join_channels_keyboard(channels: List[RequiredChannel], user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, chan in enumerate(channels, 1):
        sub_type = getattr(chan, "sub_type", "channel") or "channel"
        target = getattr(chan, "target_username", None) or chan.name
        url = chan.invite_link.strip() if chan.invite_link else ""
        auto_name = f"{idx}-kanal"
        
        if sub_type == "instagram":
            if not url:
                insta_user = target.replace("@", "")
                url = f"https://instagram.com/{insta_user}"
            elif not (url.startswith("http://") or url.startswith("https://")):
                url = f"https://{url}"
            builder.button(text=f"📸 {auto_name} (Instagram)", url=url)
        elif sub_type == "bot":
            if not url:
                bot_user = target.replace("@", "")
                url = f"https://t.me/{bot_user}"
            else:
                if not (url.startswith("http://") or url.startswith("https://")):
                    url = f"https://{url}"
            if user_id:
                sep = "&" if "?" in url else "?"
                if "start=" not in url:
                    url += f"{sep}start=kb_{user_id}"
            builder.button(text=f"🤖 {auto_name} (Bot)", url=url)
            builder.button(text=f"✅ {auto_name} (Start bosdim)", callback_data=f"confirm_bot_{chan.id}")
        else:
            # Telegram channel
            if url.startswith("@"):
                url = f"https://t.me/{url[1:]}"
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
                if not (url.startswith("http://") or url.startswith("https://")):
                    url = f"https://t.me/{url}"
            builder.button(text=f"📢 {auto_name}", url=url)

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
        is_vip_badge = " ⭐" if getattr(item, "is_vip", False) else ""
        if hasattr(item, "movie_code"):
            builder.row(InlineKeyboardButton(text=f"🎬 {item.title}{is_vip_badge} [{item.movie_code}]", callback_data=f"view_movie_user_{item.movie_code}"))
        else:
            builder.row(InlineKeyboardButton(text=f"📺 {item.title}{is_vip_badge} [{item.series_code}]", callback_data=f"view_series_user_{item.series_code}"))
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"movie_page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data="noop"))
        
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"movie_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data="noop"))
        
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
    builder.row(
        InlineKeyboardButton(text="👥 Adminlar", callback_data="admin_manage_admins"),
        InlineKeyboardButton(text="📝 Matnlarni tahrirlash", callback_data="admin_edit_texts")
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
        sub_type = getattr(chan, "sub_type", "channel") or "channel"
        icon = "📢" if sub_type == "channel" else ("🤖" if sub_type == "bot" else "📸")
        # Support deletion by channel_id or record id
        cb_data = f"admin_delete_sub_{chan.id}"
        builder.row(
            InlineKeyboardButton(text=f"❌ O'chirish: {icon} {chan.name}", callback_data=cb_data)
        )
    builder.row(
        InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="admin_add_channel"),
        InlineKeyboardButton(text="🤖 Bot qo'shish", callback_data="admin_add_bot")
    )
    builder.row(
        InlineKeyboardButton(text="📸 Instagram qo'shish", callback_data="admin_add_insta"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()

def get_admin_movies_keyboard(movies: List[Movie], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for movie in movies:
        is_vip_badge = " ⭐" if movie.is_vip else ""
        builder.row(InlineKeyboardButton(text=f"🎬 {movie.title}{is_vip_badge} [{movie.movie_code}]", callback_data=f"admin_movie_detail_{movie.movie_code}"))
        
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_movies_page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data="noop"))
        
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_movies_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data="noop"))
        
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()

def get_movie_detail_keyboard(code: int, is_vip: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁️ Kinoni ko'rish", callback_data=f"admin_view_movie_file_{code}"),
        InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"admin_rename_movie_{code}")
    )
    vip_text = "🔓 VIP'dan chiqarish" if is_vip else "⭐ VIP qilish"
    builder.row(
        InlineKeyboardButton(text=vip_text, callback_data=f"admin_toggle_movie_vip_{code}"),
        InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"admin_delete_movie_{code}")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Faylni almashtirish", callback_data=f"admin_replace_movie_{code}"),
        InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_movies_page_1")
    )
    return builder.as_markup()

def get_broadcast_target_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="broadcast_target_all"))
    builder.row(InlineKeyboardButton(text="⭐ Faqat VIP foydalanuvchilar", callback_data="broadcast_target_vip"))
    builder.row(InlineKeyboardButton(text="👤 Faqat Oddiy foydalanuvchilar", callback_data="broadcast_target_oddiy"))
    builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_back"))
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
        is_vip_badge = " ⭐" if s.is_vip else ""
        builder.row(InlineKeyboardButton(text=f"📺 {s.title}{is_vip_badge} [{s.series_code}]", callback_data=f"admin_series_detail_{s.series_code}"))
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_series_page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data="noop"))
        
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_series_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data="noop"))
        
    if nav_buttons:
        builder.row(*nav_buttons)
        
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()

def get_series_detail_keyboard(code: int, is_vip: bool = False, has_link: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁️ Serialni ko'rish", callback_data=f"admin_view_series_{code}"),
        InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"admin_rename_series_{code}")
    )
    vip_text = "🔓 VIP'dan chiqarish" if is_vip else "⭐ VIP qilish"
    if has_link:
        manage_btn = InlineKeyboardButton(text="🔗 Havolani o'zgartirish", callback_data=f"admin_edit_series_link_{code}")
    else:
        manage_btn = InlineKeyboardButton(text="📁 Qismlarni boshqarish", callback_data=f"admin_series_manage_episodes_{code}")

    builder.row(
        manage_btn,
        InlineKeyboardButton(text=vip_text, callback_data=f"admin_toggle_series_vip_{code}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"admin_delete_series_{code}"),
        InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="admin_series_page_1")
    )
    return builder.as_markup()

def get_admin_seasons_keyboard(series_code: int, seasons: List[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in seasons:
        builder.button(text=f"{s}-fasl", callback_data=f"admin_series_season_{series_code}_{s}")
    builder.adjust(4)
    builder.row(
        InlineKeyboardButton(text="➕ Fasl qo'shish", callback_data=f"admin_series_add_ep_{series_code}"),
        InlineKeyboardButton(text="➕ Qism qo'shish (Bittalab)", callback_data=f"admin_series_add_ep_{series_code}")
    )
    builder.row(
        InlineKeyboardButton(text="📥 Qismlar qo'shish (Birdaniga)", callback_data=f"admin_series_add_ep_bulk_{series_code}")
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_series_detail_{series_code}"))
    return builder.as_markup()

def get_admin_season_episodes_keyboard(series_code: int, season_number: int, episodes: List[Any]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ep in episodes:
        builder.button(text=f"{ep.episode_number}-qism", callback_data=f"admin_series_ep_detail_{series_code}_{ep.id}")
    builder.adjust(4)
    builder.row(
        InlineKeyboardButton(text="➕ Qism qo'shish", callback_data=f"admin_series_add_ep_{series_code}"),
        InlineKeyboardButton(text="🔙 Fasllarga", callback_data=f"admin_series_manage_episodes_{series_code}")
    )
    return builder.as_markup()

def get_admin_episode_detail_keyboard(series_code: int, episode_id: int, season_number: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👁️ Faylni ko'rish", callback_data=f"admin_series_ep_view_{episode_id}"),
        InlineKeyboardButton(text="🔄 Faylni almashtirish", callback_data=f"admin_series_ep_replace_{episode_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Qismni o'chirish", callback_data=f"admin_series_ep_delete_{episode_id}"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_series_season_{series_code}_{season_number}")
    )
    return builder.as_markup()

def get_series_episodes_keyboard(series_code: int, episodes_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, episodes_count + 1):
        builder.button(text=f"{i}-qism", callback_data=f"view_episode_{series_code}_{i}")
    builder.adjust(4)
    return builder.as_markup()

def get_series_seasons_keyboard(series_code: int, seasons: List[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in seasons:
        builder.button(text=f"{s}-fasl", callback_data=f"view_season_{series_code}_{s}")
    builder.adjust(3)
    return builder.as_markup()

def get_series_season_episodes_keyboard(series_code: int, season_number: int, episodes: List[Any]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ep in episodes:
        builder.button(text=f"{ep.episode_number}-qism", callback_data=f"view_episode_{series_code}_{ep.episode_number}_{season_number}")
    builder.adjust(4)
    builder.row(InlineKeyboardButton(text="🔙 Fasllarga", callback_data=f"view_series_user_{series_code}"))
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

def get_bulk_finish_upload_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💾 Yuklashni yakunlash", callback_data="series_bulk_finish_upload"))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_back"))
    return builder.as_markup()

# --- ADMIN DYNAMIC ADMINS KEYBOARDS ---
def get_admin_manage_admins_keyboard(admins: List[Any]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for admin in admins:
        username_str = f" (@{admin.username})" if admin.username else ""
        builder.row(
            InlineKeyboardButton(text=f"❌ O'chirish: {admin.full_name}{username_str}", callback_data=f"admin_delete_admin_{admin.id}")
        )
    builder.row(
        InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="admin_add_admin_prompt"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")
    )
    return builder.as_markup()

# --- ADMIN EDIT TEXTS KEYBOARDS ---
def get_admin_edit_texts_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Start xabari", callback_data="admin_edit_text_start_message"))
    builder.row(InlineKeyboardButton(text="ℹ️ Yordam xabari", callback_data="admin_edit_text_help_message"))
    builder.row(InlineKeyboardButton(text="⭐ VIP xabari", callback_data="admin_edit_text_vip_message"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()


def get_series_list_keyboard(items: List[Series], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        is_vip_badge = " ⭐" if getattr(item, "is_vip", False) else ""
        builder.row(InlineKeyboardButton(text=f"📺 {item.title}{is_vip_badge} [{item.series_code}]", callback_data=f"view_series_user_{item.series_code}"))
    
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"series_page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data="noop"))
        
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"series_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data="noop"))
        
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="❌ Yopish", callback_data="close_movies"))
    return builder.as_markup()

def get_admin_stats_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎬 Filmlar qidiruv statistikasi", callback_data="admin_movie_stats_page_1"),
        InlineKeyboardButton(text="📺 Seriallar statistikasi", callback_data="admin_series_stats_page_1")
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back"))
    return builder.as_markup()

def get_admin_movie_stats_keyboard(movies: List[Movie], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for movie in movies:
        is_vip_badge = " ⭐" if movie.is_vip else ""
        builder.row(
            InlineKeyboardButton(
                text=f"🎬 {movie.title}{is_vip_badge} [{movie.movie_code}] — 👁️ {movie.search_count}",
                callback_data=f"admin_movie_detail_{movie.movie_code}"
            )
        )
        
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_movie_stats_page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data="noop"))
        
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_movie_stats_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data="noop"))
        
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Statistikaga qaytish", callback_data="admin_stats"))
    return builder.as_markup()

def get_admin_series_stats_keyboard(series: List[Series], page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in series:
        is_vip_badge = " ⭐" if s.is_vip else ""
        builder.row(
            InlineKeyboardButton(
                text=f"📺 {s.title}{is_vip_badge} [{s.series_code}] — 👁️ {s.search_count}",
                callback_data=f"admin_series_detail_{s.series_code}"
            )
        )
        
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_series_stats_page_{page-1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data="noop"))
        
    nav_buttons.append(InlineKeyboardButton(text=f"📄 {page}/{max(1, total_pages)}", callback_data="noop"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_series_stats_page_{page+1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data="noop"))
        
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🔙 Statistikaga qaytish", callback_data="admin_stats"))
    return builder.as_markup()


def get_referral_keyboard(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_text = f"🍿 Kinolar va seriallarni eng yaxshi sifatda tomosha qiling!\n\nBotga kirish: {ref_link}"
    share_url = f"https://t.me/share/url?url={ref_link}&text={urllib.parse.quote_plus(share_text)}"
    builder.row(InlineKeyboardButton(text="📤 Do'stlarga ulashish", url=share_url))
    builder.row(InlineKeyboardButton(text="🏆 Top referallar reytingi", callback_data="top_referrers"))
    return builder.as_markup()
