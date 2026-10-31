import logging
import datetime
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from app.utils import extract_movie_title
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramForbiddenError
from app.config import ADMIN_IDS, STORAGE_CHANNEL_ID
from app.states import (
    AdminState, AddMovieState, AddSeriesState, AddVipPlanState, ManageVipUserState,
    AddAdminState, EditTextState, ManageSeriesEpisodesState
)
from app.database import (
    get_statistics, get_setting, set_setting, get_required_channels,
    add_required_channel, delete_required_channel, delete_required_channel_by_id, add_movie,
    get_all_movies, get_movie_count, get_movie_by_code, rename_movie,
    replace_movie_file, delete_movie, update_vip_until,
    add_series, add_series_episode, get_all_series, get_series_count,
    get_series_by_code, rename_series, delete_series, get_active_vip_users,
    get_vip_plans, add_vip_plan, delete_vip_plan, remove_user_vip, get_user,
    is_admin_db, add_admin_user, delete_admin_user, get_all_admins,
    replace_series_episode_file, delete_series_episode, toggle_movie_vip,
    toggle_series_vip, get_user_ids_by_target, get_top_10_movies, update_series_link,
    get_movies_search_stats, get_series_search_stats, set_user_active, set_user_inactive
)
from app.keyboards import (
    get_admin_panel, get_admin_channels_keyboard, get_admin_movies_keyboard,
    get_movie_detail_keyboard, get_broadcast_confirm_keyboard,
    get_receipt_approval_keyboard, get_series_type_keyboard,
    get_admin_series_keyboard, get_series_detail_keyboard,
    get_admin_vip_keyboard, get_admin_vip_user_manage_keyboard,
    get_admin_manual_vip_plans_keyboard, get_admin_seasons_keyboard,
    get_admin_season_episodes_keyboard, get_admin_episode_detail_keyboard,
    get_admin_manage_admins_keyboard, get_admin_edit_texts_keyboard,
    get_broadcast_target_keyboard, get_admin_stats_menu_keyboard,
    get_admin_movie_stats_keyboard, get_admin_series_stats_keyboard
)

logger = logging.getLogger(__name__)
admin_router = Router()

def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS or is_admin_db(message.from_user.id)

def is_admin_callback(callback: CallbackQuery) -> bool:
    return callback.from_user.id in ADMIN_IDS or is_admin_db(callback.from_user.id)

@admin_router.callback_query(F.data == "noop")
async def admin_noop(callback: CallbackQuery):
    await callback.answer()

@admin_router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await state.clear()
    await message.answer("🛠️ Admin panelga xush kelibsiz. Amalni tanlang:", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data == "admin_back")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text("🛠️ Admin panelga xush kelibsiz. Amalni tanlang:", reply_markup=get_admin_panel())
    await callback.answer()

# --- STATISTICS ---
@admin_router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    stats = await get_statistics()
    text = (
        "📊 **Bot statistikasi**\n\n"
        f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
        f"⚡ Faol foydalanuvchilar (24 soat): {stats.get('active_24h', 0)}\n"
        f"⚡ Faol foydalanuvchilar (7 kun): {stats.get('active_7d', 0)}\n"
        f"⚡ Faol foydalanuvchilar (30 kun): {stats.get('active_30d', 0)}\n"
        f"🚫 Botni bloklaganlar: {stats.get('blocked_users', 0)}\n"
        f"⭐ VIP foydalanuvchilar: {stats['vip_users']}\n"
        f"🎬 Jami filmlar: {stats['movies']}\n"
        f"📺 Jami seriallar: {stats['series']}\n"
        f"🔍 Jami qidiruvlar: {stats['searches']}\n"
        f"🔍 Bugungi qidiruvlar: {stats['today_searches']}\n"
        f"📅 Bugungi ro'yxatdan o'tganlar: {stats['today_users']}\n"
        f"📅 Oxirgi 30 kundagi yangi a'zolar: {stats['thirty_days_users']}\n\n"
        "🏆 **Top 10 Eng Ko'p Qidirilgan Filmlar:**\n"
    )
    
    top_movies = await get_top_10_movies()
    if top_movies:
        for idx, m in enumerate(top_movies, 1):
            text += f"{idx}. {m.title} [{m.movie_code}] — 👁️ {m.search_count} marta\n"
    else:
        text += "Hozircha ma'lumot yo'q.\n"

    try:
        await callback.message.edit_text(text, reply_markup=get_admin_stats_menu_keyboard())
    except TelegramBadRequest:
        pass
    
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_movie_stats_page_"))
async def show_movie_stats_page(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    page = int(callback.data.replace("admin_movie_stats_page_", ""))
    limit = 10
    offset = (page - 1) * limit
    
    movies, total_count = await get_movies_search_stats(offset=offset, limit=limit)
    total_pages = (total_count + limit - 1) // limit
    
    await callback.message.edit_text(
        f"🎬 **Filmlar qidiruv statistikasi ({page}/{max(1, total_pages)}-sahifa)**\n\n"
        f"Jami filmlar: {total_count} ta\n"
        "Qidiruvlar sonini ko'rish yoki tahrirlash uchun film ustiga bosing:",
        reply_markup=get_admin_movie_stats_keyboard(movies, page, total_pages)
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_series_stats_page_"))
async def show_series_stats_page(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    page = int(callback.data.replace("admin_series_stats_page_", ""))
    limit = 10
    offset = (page - 1) * limit
    
    series, total_count = await get_series_search_stats(offset=offset, limit=limit)
    total_pages = (total_count + limit - 1) // limit
    
    await callback.message.edit_text(
        f"📺 **Seriallar qidiruv statistikasi ({page}/{max(1, total_pages)}-sahifa)**\n\n"
        f"Jami seriallar: {total_count} ta\n"
        "Qidiruvlar sonini ko'rish yoki tahrirlash uchun serial ustiga bosing:",
        reply_markup=get_admin_series_stats_keyboard(series, page, total_pages)
    )
    await callback.answer()

# --- REQUIRED CHANNELS & SUBSCRIPTIONS ---
@admin_router.callback_query(F.data == "admin_channels")
async def view_required_channels(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    channels = await get_required_channels()
    text = "📺 **Foydalanuvchilar uchun majburiy obunalar:**\n\n"
    if not channels:
        text += "Hech qanday majburiy obuna qo'shilmagan. Foydalanuvchilar to'g'ridan-to'g'ri foydalanishi mumkin."
    else:
        for idx, chan in enumerate(channels, 1):
            sub_type = getattr(chan, "sub_type", "channel") or "channel"
            if sub_type == "bot":
                text += f"{idx}. 🤖 Bot: {chan.name} (`@{chan.target_username or ''}`)\n"
            elif sub_type == "instagram":
                text += f"{idx}. 📸 Instagram: {chan.name} (`@{chan.target_username or ''}`)\n"
            else:
                text += f"{idx}. 📢 Kanal: {chan.name} (ID: `{chan.channel_id or ''}`)\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_channels_keyboard(channels))
    await callback.answer()

@admin_router.callback_query(F.data == "admin_add_channel")
async def add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AdminState.waiting_for_add_channel)
    await callback.message.edit_text(
        "📢 **Telegram Kanal qo'shish**\n\n"
        "Iltimos, kanal ma'lumotlarini quyidagi formatda yuboring:\n\n"
        "`channel_id|taklif_linki|kanal_nomi`\n\n"
        "Masalan:\n"
        "`-1001234567890|https://t.me/+AbCdEf|Mening Kanalim`"
    )
    await callback.answer()

@admin_router.message(AdminState.waiting_for_add_channel)
async def add_channel_save(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    parts = message.text.split("|")
    if len(parts) != 3:
        await message.answer("❌ Noto'g'ri format. Foydalaning: `channel_id|taklif_linki|kanal_nomi`")
        return
    
    try:
        channel_id = int(parts[0].strip())
        invite_link = parts[1].strip()
        name = parts[2].strip()
        
        await add_required_channel(channel_id, invite_link, name, sub_type="channel")
        await state.clear()
        await message.answer("✅ Telegram kanal muvaffaqiyatli qo'shildi!", reply_markup=get_admin_panel())
    except ValueError:
        await message.answer("❌ Kanal ID raqam (integer) bo'lishi kerak. Qayta urinib ko'ring.")

@admin_router.callback_query(F.data == "admin_add_bot")
async def add_bot_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AdminState.waiting_for_add_bot)
    await callback.message.edit_text(
        "🤖 **Telegram Bot qo'shish**\n\n"
        "Iltimos, bot ma'lumotlarini quyidagi formatda yuboring:\n\n"
        "`@bot_username|taklif_linki|bot_nomi`\n\n"
        "Masalan:\n"
        "`@kinobot_partnyor|https://t.me/kinobot_partnyor|Hamkor Botimiz`"
    )
    await callback.answer()

@admin_router.message(AdminState.waiting_for_add_bot)
async def add_bot_save(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    parts = message.text.split("|")
    if len(parts) < 2:
        await message.answer("❌ Noto'g'ri format. Foydalaning: `@bot_username|taklif_linki|bot_nomi`")
        return
        
    bot_user = parts[0].strip().replace("@", "")
    invite_link = parts[1].strip() if len(parts) >= 2 else f"https://t.me/{bot_user}"
    name = parts[2].strip() if len(parts) >= 3 else parts[1].strip()
    
    await add_required_channel(None, invite_link, name, sub_type="bot", target_username=bot_user)
    await state.clear()
    await message.answer(f"✅ Telegram bot (@{bot_user}) muvaffaqiyatli qo'shildi!", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data == "admin_add_insta")
async def add_insta_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AdminState.waiting_for_add_insta)
    await callback.message.edit_text(
        "📸 **Instagram Sahifa qo'shish**\n\n"
        "Iltimos, Instagram ma'lumotlarini quyidagi formatda yuboring:\n\n"
        "`@insta_username|taklif_linki|sahifa_nomi`\n\n"
        "Masalan:\n"
        "`@kinotime_uz|https://instagram.com/kinotime_uz|Instagram Sahifamiz`"
    )
    await callback.answer()

@admin_router.message(AdminState.waiting_for_add_insta)
async def add_insta_save(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    parts = message.text.split("|")
    if len(parts) < 2:
        await message.answer("❌ Noto'g'ri format. Foydalaning: `@insta_username|taklif_linki|sahifa_nomi`")
        return
        
    insta_user = parts[0].strip().replace("@", "")
    invite_link = parts[1].strip() if len(parts) >= 2 else f"https://instagram.com/{insta_user}"
    name = parts[2].strip() if len(parts) >= 3 else parts[1].strip()
    
    await add_required_channel(None, invite_link, name, sub_type="instagram", target_username=insta_user)
    await state.clear()
    await message.answer(f"✅ Instagram sahifasi (@{insta_user}) muvaffaqiyatli qo'shildi!", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data.startswith("admin_delete_sub_"))
async def delete_sub_action(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    rec_id = int(callback.data.replace("admin_delete_sub_", ""))
    success = await delete_required_channel_by_id(rec_id)
    if success:
        await callback.answer("✅ Obuna o'chirildi.")
        channels = await get_required_channels()
        await callback.message.edit_text("📺 Majburiy obunalar ro'yxati yangilandi:", reply_markup=get_admin_channels_keyboard(channels))
    else:
        await callback.answer("❌ Obuna topilmadi.")

@admin_router.callback_query(F.data.startswith("admin_delete_channel_"))
async def delete_channel_action(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    channel_id = int(callback.data.replace("admin_delete_channel_", ""))
    success = await delete_required_channel(channel_id)
    if success:
        await callback.answer("✅ Kanal o'chirildi.")
        channels = await get_required_channels()
        await callback.message.edit_text("📺 Majburiy obunalar ro'yxati yangilandi:", reply_markup=get_admin_channels_keyboard(channels))
    else:
        await callback.answer("❌ Kanal not found.")

# --- BROADCAST ---
@admin_router.callback_query(F.data == "admin_broadcast")
async def broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await callback.message.edit_text(
        "📢 **Reklama tarqatish**\n\nQaysi foydalanuvchilarga reklama yubormoqchisiz? Tanlang:",
        reply_markup=get_broadcast_target_keyboard()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("broadcast_target_"))
async def broadcast_target_selected(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    target = callback.data.replace("broadcast_target_", "")
    await state.update_data(broadcast_target=target)
    await state.set_state(AdminState.waiting_for_broadcast)
    
    target_names = {
        "all": "👥 Barcha foydalanuvchilar",
        "vip": "⭐ Faqat VIP foydalanuvchilar",
        "oddiy": "👤 Faqat Oddiy foydalanuvchilar"
    }
    t_name = target_names.get(target, "👥 Barcha foydalanuvchilar")
    
    await callback.message.edit_text(
        f"🎯 **Tanlangan auditoriya:** {t_name}\n\n"
        "📢 Iltimos, yubormoqchi bo'lgan xabaringizni yuboring (matn, rasm, video va h.k.):"
    )
    await callback.answer()

@admin_router.message(AdminState.waiting_for_broadcast)
async def broadcast_receive_msg(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await state.update_data(
        broadcast_msg_id=message.message_id,
        broadcast_chat_id=message.chat.id
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ O'tkazib yuborish", callback_data="broadcast_skip_button")
    
    await state.set_state(AdminState.waiting_for_broadcast_button)
    await message.answer(
        "✅ Xabar qabul qilindi.\n\n"
        "Agar xabarga inline tugma (button) qo'shmoqchi bo'lsangiz, uni quyidagi formatda yuboring:\n"
        "`Tugma nomi | https://silka.com`\n\n"
        "Agar tugma qo'shish kerak bo'lmasa, **O'tkazib yuborish** tugmasini bosing.",
        reply_markup=builder.as_markup()
    )

@admin_router.callback_query(F.data == "broadcast_skip_button")
async def broadcast_skip_button(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await callback.message.edit_text("Tugma qo'shilmaydi.")
    await broadcast_confirm_prompt(callback.message, state)
    await callback.answer()

@admin_router.message(AdminState.waiting_for_broadcast_button)
async def broadcast_receive_button(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    text = message.text.strip()
    if "|" not in text:
        await message.answer("❌ Noto'g'ri format! Iltimos, `Tugma nomi | https://silka.com` shaklida yuboring yoki 'O'tkazib yuborish' tugmasini bosing.")
        return
        
    parts = text.split("|", 1)
    btn_text = parts[0].strip()
    btn_url = parts[1].strip()
    
    if not (btn_url.startswith("http://") or btn_url.startswith("https://") or btn_url.startswith("t.me")):
        await message.answer("❌ Noto'g'ri URL! Link http:// yoki https:// bilan boshlanishi kerak.")
        return
        
    await state.update_data(broadcast_btn_text=btn_text, broadcast_btn_url=btn_url)
    await message.answer(f"✅ Tugma qo'shildi: [{btn_text}]({btn_url})")
    await broadcast_confirm_prompt(message, state)

async def broadcast_confirm_prompt(message: Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("broadcast_target", "all")
    
    target_names = {
        "all": "barcha foydalanuvchilarga",
        "vip": "faqat VIP foydalanuvchilarga",
        "oddiy": "faqat oddiy foydalanuvchilarga"
    }
    t_name = target_names.get(target, "barcha foydalanuvchilarga")
    
    await message.answer(
        f"❓ Haqiqatan ham ushbu xabarni **{t_name}** yuborishni tasdiqlaysizmi?",
        reply_markup=get_broadcast_confirm_keyboard()
    )

@admin_router.callback_query(F.data == "admin_confirm_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin_callback(callback):
        return
    data = await state.get_data()
    msg_id = data.get("broadcast_msg_id")
    chat_id = data.get("broadcast_chat_id")
    target = data.get("broadcast_target", "all")
    
    if not msg_id or not chat_id:
        await callback.answer("❌ Reklama tafsilotlari topilmadi. Qayta urinib ko'ring.", show_alert=True)
        await state.clear()
        return
        
    await callback.answer("🚀 Reklama yuborilmoqda...")
    await callback.message.edit_text("📤 Yuborish jarayoni boshlandi...")
    
    user_ids = await get_user_ids_by_target(target)
    
    success_count = 0
    fail_count = 0
    
    btn_text = data.get("broadcast_btn_text")
    btn_url = data.get("broadcast_btn_url")
    
    reply_markup = None
    if btn_text and btn_url:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text=btn_text, url=btn_url)
        reply_markup = builder.as_markup()
    
    for uid in user_ids:
        try:
            await bot.copy_message(
                chat_id=uid, 
                from_chat_id=chat_id, 
                message_id=msg_id,
                reply_markup=reply_markup
            )
            success_count += 1
            await set_user_active(uid)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.copy_message(
                    chat_id=uid, 
                    from_chat_id=chat_id, 
                    message_id=msg_id,
                    reply_markup=reply_markup
                )
                success_count += 1
                await set_user_active(uid)
            except Exception:
                fail_count += 1
                await set_user_inactive(uid)
        except (TelegramForbiddenError, Exception) as e:
            fail_count += 1
            err_msg = str(e).lower()
            if "blocked" in err_msg or "deactivated" in err_msg or "not found" in err_msg or "forbidden" in err_msg:
                await set_user_inactive(uid)
                
        # Small delay to respect Telegram rate limits
        await asyncio.sleep(0.035)
            
    target_titles = {
        "all": "Barcha foydalanuvchilar",
        "vip": "Faqat VIP foydalanuvchilar",
        "oddiy": "Faqat Oddiy foydalanuvchilar"
    }
    t_title = target_titles.get(target, "Barcha foydalanuvchilar")
            
    await state.clear()
    await callback.message.answer(
        f"📢 **Reklama yuborish yakunlandi**\n\n"
        f"🎯 Auditoriya: {t_title}\n"
        f"👥 Maqsadli foydalanuvchilar: {len(user_ids)} ta\n"
        f"✅ Muvaffaqiyatli yuborilganlar: {success_count} ta\n"
        f"❌ Yuborilmaganlar (botni bloklaganlar/xatolik): {fail_count} ta",
        reply_markup=get_admin_panel()
    )

# --- ADD MOVIE (CONCURRENCY & FLOOD PROTECTED) ---
_storage_forward_lock = asyncio.Lock()

async def safe_forward_to_storage(bot: Bot, from_chat_id: int, message_id: int, max_retries: int = 5):
    """
    Kanalga bir vaqtda 20+ ta kino tashlanganda Telegram flood limitiga tushib qolmaslik
    uchun asinxron navbat va avtomatik retry mexanizmi.
    """
    async with _storage_forward_lock:
        for attempt in range(max_retries):
            try:
                forwarded = await bot.forward_message(
                    chat_id=STORAGE_CHANNEL_ID,
                    from_chat_id=from_chat_id,
                    message_id=message_id
                )
                await asyncio.sleep(0.08)  # Telegram limitiga tushmaslik uchun qisqa oraliq
                return forwarded
            except TelegramRetryAfter as e:
                logger.warning(f"Telegram flood limit: sleeping {e.retry_after}s before retry")
                await asyncio.sleep(e.retry_after + 0.5)
            except Exception:
                try:
                    forwarded = await bot.copy_message(
                        chat_id=STORAGE_CHANNEL_ID,
                        from_chat_id=from_chat_id,
                        message_id=message_id
                    )
                    await asyncio.sleep(0.08)
                    return forwarded
                except TelegramRetryAfter as e:
                    logger.warning(f"Telegram flood limit: sleeping {e.retry_after}s before retry")
                    await asyncio.sleep(e.retry_after + 0.5)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(0.2)

async def safe_admin_answer(message: Message, text: str, reply_markup=None):
    try:
        await message.answer(text, reply_markup=reply_markup)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after + 0.5)
        try:
            await message.answer(text, reply_markup=reply_markup)
        except Exception as err:
            logger.error(f"safe_admin_answer failed after retry: {err}")
    except Exception as e:
        logger.error(f"safe_admin_answer failed: {e}")

@admin_router.callback_query(F.data == "admin_add_movie")
async def add_movie_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.clear()
    await state.set_state(AddMovieState.waiting_for_title)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Bekor qilish", callback_data="admin_back")
    
    text = (
        "🎬 **Kino qo'shish**\n\n"
        "Kino faylini (video yoki hujjat) yuboring yoki postni to'g'ridan-to'g'ri forward qiling.\n"
        "⚡ _Post matnida kino nomi bo'lsa (masalan: `#🎥 Kino nomi`), bot uni avtomatik aniqlaydi va qo'shadi._\n"
        "💡 _Bir vaqtning o'zida 20+ ta filmni ham bemalol tashlashingiz mumkin, barchasi navbat bilan to'liq qo'shiladi._\n\n"
        "Yoki avval kino nomini matn sifatida yuborishingiz ham mumkin:"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.message(
    StateFilter(None, AddMovieState.waiting_for_title, AddMovieState.waiting_for_file),
    F.video | F.document | F.animation | F.audio
)
async def process_movie_media_upload(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
        
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.animation:
        file_id = message.animation.file_id
    elif message.audio:
        file_id = message.audio.file_id
        
    if not file_id:
        await safe_admin_answer(message, "❌ Iltimos, yaroqli video, hujjat, animatsiya yoki audio fayl yuboring.")
        return
        
    # Avval yuborilgan videoning o'z matnidan (caption) nomni aniqlashga harakat qilamiz
    caption = message.caption or message.text
    title = extract_movie_title(caption)
    
    # Agar post matnida nom bo'lmasa, state'da avval kiritilgan nom bor-yo'qligini tekshiramiz
    if not title:
        data = await state.get_data()
        title = data.get("movie_title")
        
    if title:
        # Nom aniqlandi -> darhol saqlash kanaliga va DB ga qo'shamiz
        try:
            forwarded = await safe_forward_to_storage(
                bot=bot,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
                
            movie = await add_movie(
                title=title,
                channel_id=STORAGE_CHANNEL_ID,
                message_id=forwarded.message_id,
                file_id=file_id
            )
            
            # Agar oldin biror state ochilgan bo'lsa, tozalaymiz
            curr = await state.get_state()
            if curr in [AddMovieState.waiting_for_title, AddMovieState.waiting_for_file]:
                await state.clear()

            await safe_admin_answer(
                message,
                f"✅ **Kino muvaffaqiyatli qo'shildi!**\n\n"
                f"🎬 Nomi: {movie.title}\n"
                f"🆔 Kodi: `{movie.movie_code}`",
                reply_markup=get_admin_panel()
            )
        except Exception as e:
            logger.error(f"Error adding movie automatically: {e}")
            await safe_admin_answer(
                message,
                f"❌ Kino qo'shishda xatolik: {e}\nSaqlash kanali ID'si to'g'ri ekanligini va bot u yerda admin ekanligini tekshiring."
            )
    else:
        # Nomni aniqlab bo'lmadi -> faylni vaqtinchalik saqlab, admindan nom so'raymiz
        await state.update_data(
            pending_file_id=file_id,
            pending_message_id=message.message_id,
            pending_chat_id=message.chat.id
        )
        await state.set_state(AddMovieState.waiting_for_title)
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Bekor qilish", callback_data="admin_back")
        
        await safe_admin_answer(
            message,
            "❓ **Videodan kino nomini avtomatik aniqlab bo'lmadi.**\n\n"
            "✍️ Iltimos, ushbu kino nomini yuboring:",
            reply_markup=builder.as_markup()
        )

@admin_router.message(AddMovieState.waiting_for_title, F.text)
async def process_movie_title_text(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
        
    title = message.text.strip()
    if not title:
        await safe_admin_answer(message, "❌ Kino nomi bo'sh bo'lishi mumkin emas. Iltimos, nomni yuboring:")
        return
        
    data = await state.get_data()
    pending_file_id = data.get("pending_file_id")
    pending_message_id = data.get("pending_message_id")
    pending_chat_id = data.get("pending_chat_id")
    
    if pending_file_id and pending_message_id and pending_chat_id:
        # Fayl avval yuborilgan, endi unga nom berildi
        try:
            forwarded = await safe_forward_to_storage(
                bot=bot,
                from_chat_id=pending_chat_id,
                message_id=pending_message_id
            )
                
            movie = await add_movie(
                title=title,
                channel_id=STORAGE_CHANNEL_ID,
                message_id=forwarded.message_id,
                file_id=pending_file_id
            )
            
            await state.clear()
            await safe_admin_answer(
                message,
                f"✅ **Kino muvaffaqiyatli qo'shildi!**\n\n"
                f"🎬 Nomi: {movie.title}\n"
                f"🆔 Kodi: `{movie.movie_code}`",
                reply_markup=get_admin_panel()
            )
        except Exception as e:
            logger.error(f"Error adding movie with manual title: {e}")
            await safe_admin_answer(
                message,
                f"❌ Kino qo'shishda xatolik: {e}\nSaqlash kanali ID'si to'g'ri ekanligini va bot u yerda admin ekanligini tekshiring."
            )
    else:
        # Admin avval nom yubordi, endi fayl kutamiz
        await state.update_data(movie_title=title)
        await state.set_state(AddMovieState.waiting_for_file)
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Bekor qilish", callback_data="admin_back")
        
        await safe_admin_answer(
            message,
            f"🎬 Kino nomi: **{title}**\n\n"
            "📁 Endi kino faylini yuboring (Video, Hujjat va h.k.):",
            reply_markup=builder.as_markup()
        )

# --- MOVIE LIST PAGINATION (ADMIN) ---
@admin_router.callback_query(F.data.startswith("admin_movies_page_"))
async def admin_list_movies(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    page = int(callback.data.replace("admin_movies_page_", ""))
    limit = 10
    offset = (page - 1) * limit
    
    movies = await get_all_movies(offset=offset, limit=limit)
    total_count = await get_movie_count()
    total_pages = (total_count + limit - 1) // limit
    
    await callback.message.edit_text(
        f"🎬 **Kinolar ro'yxati (Admin) - Sahifa {page}/{max(1, total_pages)}**\n"
        "Bosib boshqarishingiz mumkin:",
        reply_markup=get_admin_movies_keyboard(movies, page, total_pages)
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_movie_detail_"))
async def admin_movie_detail(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_movie_detail_", ""))
    movie = await get_movie_by_code(code)
    if not movie:
        await callback.answer("❌ Kino topilmadi.", show_alert=True)
        return
        
    vip_status = "Ha ⭐" if movie.is_vip else "Yo'q"
    await callback.message.edit_text(
        f"🎬 **Kino tafsilotlari**\n\n"
        f"🆔 Kodi: `{movie.movie_code}`\n"
        f"📌 Nomi: {movie.title}\n"
        f"👁️ Qidiruvlar soni: {movie.search_count}\n"
        f"⭐ VIP: {vip_status}",
        reply_markup=get_movie_detail_keyboard(code, is_vip=movie.is_vip)
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_toggle_movie_vip_"))
async def admin_toggle_movie_vip_handler(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_toggle_movie_vip_", ""))
    new_status = await toggle_movie_vip(code)
    if new_status is None:
        await callback.answer("❌ Kino topilmadi.", show_alert=True)
        return
    
    movie = await get_movie_by_code(code)
    vip_status = "Ha ⭐" if movie.is_vip else "Yo'q"
    await callback.message.edit_text(
        f"🎬 **Kino tafsilotlari**\n\n"
        f"🆔 Kodi: `{movie.movie_code}`\n"
        f"📌 Nomi: {movie.title}\n"
        f"👁️ Qidiruvlar soni: {movie.search_count}\n"
        f"⭐ VIP: {vip_status}",
        reply_markup=get_movie_detail_keyboard(code, is_vip=movie.is_vip)
    )
    await callback.answer("✅ VIP holati o'zgartirildi.")

@admin_router.callback_query(F.data.startswith("admin_view_movie_file_"))
async def admin_view_movie_file(callback: CallbackQuery, bot: Bot):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_view_movie_file_", ""))
    movie = await get_movie_by_code(code)
    if not movie:
        await callback.answer("❌ Kino topilmadi.", show_alert=True)
        return
        
    try:
        await bot.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=movie.channel_id,
            message_id=movie.message_id
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Xabar nusxalashda xatolik: {e}", show_alert=True)

@admin_router.callback_query(F.data.startswith("admin_rename_movie_"))
async def admin_rename_movie_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_rename_movie_", ""))
    await state.set_state(AdminState.waiting_for_rename_movie)
    await state.update_data(edit_movie_code=code)
    await callback.message.edit_text("✏️ Iltimos, kino uchun yangi nom yuboring:")
    await callback.answer()

@admin_router.message(AdminState.waiting_for_rename_movie)
async def admin_rename_movie_save(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    data = await state.get_data()
    code = data.get("edit_movie_code")
    new_title = message.text.strip()
    
    success = await rename_movie(code, new_title)
    await state.clear()
    if success:
        await message.answer(f"✅ Kino nomi muvaffaqiyatli '{new_title}'ga o'zgartirildi!", reply_markup=get_admin_panel())
    else:
        await message.answer("❌ Kino nomini o'zgartirish muvaffaqiyatsiz tugadi.", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data.startswith("admin_replace_movie_"))
async def admin_replace_movie_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_replace_movie_", ""))
    await state.set_state(AdminState.waiting_for_replace_movie_file)
    await state.update_data(edit_movie_code=code)
    await callback.message.edit_text("🔄 Iltimos, yangi kino faylini yuboring:")
    await callback.answer()

@admin_router.message(AdminState.waiting_for_replace_movie_file)
async def admin_replace_movie_save(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
    
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.animation:
        file_id = message.animation.file_id
    else:
        await message.answer("❌ Iltimos, yaroqli fayl yuboring.")
        return
        
    data = await state.get_data()
    code = data.get("edit_movie_code")
    
    try:
        # Forward to storage channel
        forwarded = await bot.forward_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        
        success = await replace_movie_file(
            code=code,
            channel_id=STORAGE_CHANNEL_ID,
            message_id=forwarded.message_id,
            file_id=file_id
        )
        
        await state.clear()
        if success:
            await message.answer("✅ Kino fayli muvaffaqiyatli almashtirildi!", reply_markup=get_admin_panel())
        else:
            await message.answer("❌ Kino faylini almashtirish muvaffaqiyatsiz yakunlandi.", reply_markup=get_admin_panel())
    except Exception as e:
        await message.answer(f"❌ Kino faylini almashtirishda xatolik: {e}")

@admin_router.callback_query(F.data.startswith("admin_delete_movie_"))
async def admin_delete_movie_action(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_delete_movie_", ""))
    success = await delete_movie(code)
    if success:
        await callback.answer("✅ Kino o'chirildi.")
        await callback.message.edit_text("✅ Kino muvaffaqiyatli o'chirildi.", reply_markup=get_admin_panel())
    else:
        await callback.answer("❌ Kinoni o'chirishda xatolik.", show_alert=True)

# --- VIP APPROVAL SYSTEM ---
@admin_router.callback_query(F.data.startswith("approve_vip_"))
async def approve_vip(callback: CallbackQuery, bot: Bot):
    if not is_admin_callback(callback):
        return
    parts = callback.data.replace("approve_vip_", "").split("_")
    user_id = int(parts[0])
    months = int(parts[1])
    
    new_expiry = await update_vip_until(user_id, months)
    
    if new_expiry:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🎉 **VIP Obuna muvaffaqiyatli faollashtirildi!**\n\nSizning obunangiz {months} oyga faollashtirildi. VIP muddati: {new_expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC gacha."
            )
        except Exception as e:
            logger.error(f"Error sending notification to user: {e}")
            
        success_text = f"✅ Foydalanuvchi `{user_id}` uchun VIP muvaffaqiyatli faollashtirildi ({months} oy). Muddat: {new_expiry.strftime('%Y-%m-%d')}"
        try:
            if callback.message.caption is not None:
                await callback.message.edit_caption(caption=success_text)
            else:
                await callback.message.edit_text(text=success_text)
        except Exception as e:
            logger.error(f"Error updating admin message: {e}")
            
        await callback.answer("✅ VIP muvaffaqiyatli qo'shildi!", show_alert=True)
    else:
        try:
            if callback.message.caption is not None:
                await callback.message.edit_caption(caption="❌ Foydalanuvchi topilmadi.")
            else:
                await callback.message.edit_text(text="❌ Foydalanuvchi topilmadi.")
        except Exception:
            pass
        await callback.answer("❌ Foydalanuvchi topilmadi.", show_alert=True)

@admin_router.callback_query(F.data.startswith("reject_vip_confirm_default_"))
async def reject_vip_default(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin_callback(callback):
        return
    user_id = int(callback.data.replace("reject_vip_confirm_default_", ""))
    await state.clear()
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ **VIP obuna so'rovi rad etildi**\n\nYuborgan to'lov chekingiz rad etildi. Agar xatolik deb o'ylasangiz, administrator bilan bog'laning."
        )
    except Exception as e:
        logger.error(f"Failed to send rejection to user {user_id}: {e}")
        
    reject_text = f"❌ Foydalanuvchi `{user_id}` uchun VIP so'rovi rad etildi."
    try:
        if callback.message.caption is not None:
            await callback.message.edit_caption(caption=reject_text)
        else:
            await callback.message.edit_text(text=reject_text)
    except Exception:
        pass
    await callback.answer("❌ So'rov rad etildi.", show_alert=True)

@admin_router.callback_query(F.data.startswith("reject_vip_"))
async def reject_vip_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    user_id = int(callback.data.replace("reject_vip_", ""))
    await state.update_data(
        reject_vip_user_id=user_id,
        reject_vip_msg_id=callback.message.message_id,
        reject_vip_chat_id=callback.message.chat.id,
        has_caption=(callback.message.caption is not None)
    )
    await state.set_state(AdminState.waiting_for_reject_reason)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➡️ Sababsiz rad etish", callback_data=f"reject_vip_confirm_default_{user_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_back"))
    
    msg_text = (
        f"❌ **VIP obuna so'rovini rad etish** (User ID: `{user_id}`)\n\n"
        "Iltimos, foydalanuvchiga yuboriladigan **rad etish sababini** yozing:\n"
        "(masalan: *To'lov summasi kam*, *Chek tasviri aniq emas*)\n\n"
        "Yoki sababsiz rad etish uchun **Sababsiz rad etish** tugmasini bosing."
    )
    
    if callback.message.caption is not None:
        await callback.message.edit_caption(caption=msg_text, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text(text=msg_text, reply_markup=builder.as_markup())
    await callback.answer()

@admin_router.message(AdminState.waiting_for_reject_reason)
async def process_reject_vip_reason(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
    
    data = await state.get_data()
    user_id = data.get("reject_vip_user_id")
    orig_msg_id = data.get("reject_vip_msg_id")
    orig_chat_id = data.get("reject_vip_chat_id")
    has_caption = data.get("has_caption", False)
    
    reason = message.text.strip()
    await state.clear()
    
    if user_id:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"❌ **VIP obuna so'rovi rad etildi**\n\n"
                     f"📝 **Sabab:** {reason}\n\n"
                     f"Agar xatolik deb o'ylasangiz, administrator bilan bog'laning."
            )
        except Exception as e:
            logger.error(f"Failed to send rejection reason to user {user_id}: {e}")
            
        reject_text = f"❌ Foydalanuvchi `{user_id}` uchun VIP so'rovi rad etildi.\n📝 **Sabab:** {reason}"
        if orig_msg_id and orig_chat_id:
            try:
                if has_caption:
                    await bot.edit_message_caption(chat_id=orig_chat_id, message_id=orig_msg_id, caption=reject_text)
                else:
                    await bot.edit_message_text(chat_id=orig_chat_id, message_id=orig_msg_id, text=reject_text)
            except Exception:
                pass
                
        await message.answer(f"✅ Foydalanuvchi `{user_id}` so'rovi rad etildi va sababi yuborildi.", reply_markup=get_admin_panel())

# --- VIP MANAGEMENT & PLANS (ADMIN) ---
@admin_router.callback_query(F.data == "admin_vip_plans")
async def admin_vip_menu(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    vip_users = await get_active_vip_users()
    plans = await get_vip_plans()
    
    text = "⭐ **VIP bo'limi (Admin)**\n\n"
    text += "👥 **VIP obunaga ega foydalanuvchilar:**\n"
    if not vip_users:
        text += "Hozircha VIP foydalanuvchilar mavjud emas.\n"
    else:
        for idx, u in enumerate(vip_users, 1):
            username_str = f" (@{u.username})" if u.username else ""
            expiry_str = u.vip_until.strftime("%Y-%m-%d %H:%M")
            text += f"{idx}. {u.full_name}{username_str} [ID: `{u.id}`] - {expiry_str} gacha\n"
            
    text += "\n⭐ **Hozirgi faol VIP tariflari:**\n"
    if not plans:
        text += "Tariflar mavjud emas. Iltimos, tarif qo'shing."
    else:
        for p in plans:
            text += f"- {p.name} ({p.months} oy) - {p.price}\n"
            
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_vip_keyboard(vip_users, plans)
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_add_vip")
async def admin_add_vip_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AdminState.waiting_for_manual_vip_id)
    await callback.message.edit_text("👤 Iltimos, VIP bermoqchi bo'lgan foydalanuvchining ID raqamini (User ID) yuboring:")
    await callback.answer()

@admin_router.message(AdminState.waiting_for_manual_vip_id)
async def admin_save_manual_vip_id(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    user_id_str = message.text.strip()
    if not user_id_str.isdigit():
        await message.answer("❌ Noto'g'ri ID. User ID faqat raqamlardan iborat bo'lishi kerak. Qayta yuboring:")
        return
    
    user_id = int(user_id_str)
    plans = await get_vip_plans()
    
    if not plans:
        await message.answer("❌ VIP tariflar topilmadi. Avval tarif qo'shing.", reply_markup=get_admin_panel())
        await state.clear()
        return
        
    await state.clear()
    await message.answer(
        f"👤 Tanlangan foydalanuvchi ID: `{user_id}`\n\nUshbu foydalanuvchiga qancha muddatga VIP obuna bermoqchisiz?",
        reply_markup=get_admin_manual_vip_plans_keyboard(user_id, plans)
    )

@admin_router.callback_query(F.data.startswith("admin_manual_vip_"))
async def admin_grant_manual_vip(callback: CallbackQuery, bot: Bot):
    if not is_admin_callback(callback):
        return
    parts = callback.data.replace("admin_manual_vip_", "").split("_")
    months = int(parts[0])
    user_id = int(parts[1])
    
    new_expiry = await update_vip_until(user_id, months)
    
    if new_expiry:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🎉 **VIP Obunangiz faollashtirildi!**\n\nAdministrator sizga qo'lda {months} oylik VIP obuna taqdim etdi. Muddat: {new_expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC gacha."
            )
        except Exception:
            pass
        await callback.message.edit_text(
            f"✅ Foydalanuvchi (`{user_id}`) uchun {months} oylik VIP muvaffaqiyatli faollashtirildi!\n"
            f"Muddat: {new_expiry.strftime('%Y-%m-%d')}",
            reply_markup=get_admin_panel()
        )
    else:
        await callback.message.edit_text("❌ Foydalanuvchi topilmadi. U kamida bir marta botni start qilgan bo'lishi kerak.", reply_markup=get_admin_panel())
    await callback.answer()

# --- VIP USER MANAGEMENT ---
@admin_router.callback_query(F.data.startswith("admin_manage_vip_user_"))
async def admin_manage_vip_user(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    user_id = int(callback.data.replace("admin_manage_vip_user_", ""))
    user = await get_user(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return
        
    username_str = f" (@{user.username})" if user.username else ""
    expiry_str = user.vip_until.strftime("%Y-%m-%d %H:%M") if user.vip_until else "Yo'q"
    
    text = f"👤 **VIP Foydalanuvchi Boshqaruvi**\n\n" \
           f"Ismi: {user.full_name}{username_str}\n" \
           f"ID: `{user.id}`\n" \
           f"VIP muddati: {expiry_str} UTC gacha"
           
    await callback.message.edit_text(text, reply_markup=get_admin_vip_user_manage_keyboard(user_id))
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_vip_user_cancel_"))
async def admin_vip_user_cancel(callback: CallbackQuery, bot: Bot):
    if not is_admin_callback(callback):
        return
    user_id = int(callback.data.replace("admin_vip_user_cancel_", ""))
    success = await remove_user_vip(user_id)
    if success:
        try:
            await bot.send_message(
                chat_id=user_id,
                text="❌ **Sizning VIP obunangiz bekor qilindi.**"
            )
        except Exception:
            pass
        await callback.answer("VIP obuna bekor qilindi.")
        # Go back to VIP menu
        await admin_vip_menu(callback)
    else:
        await callback.answer("Xatolik yuz berdi.", show_alert=True)

@admin_router.callback_query(F.data.startswith("admin_vip_user_extend_"))
async def admin_vip_user_extend(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    user_id = int(callback.data.replace("admin_vip_user_extend_", ""))
    plans = await get_vip_plans()
    
    if not plans:
        await callback.answer("Tariflar topilmadi. Avval tarif qo'shing.", show_alert=True)
        return
        
    await callback.message.edit_text(
        f"👤 User ID: `{user_id}`\n\nVIP obunani necha oyga uzaytirmoqchisiz?",
        reply_markup=get_admin_manual_vip_plans_keyboard(user_id, plans)
    )
    await callback.answer()

# --- VIP PLANS MANAGEMENT ---
@admin_router.callback_query(F.data == "admin_add_vip_plan")
async def admin_add_vip_plan_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AddVipPlanState.waiting_for_name)
    await callback.message.edit_text("📋 Tarif nomini kiriting (masalan: 1 Oylik):")
    await callback.answer()

@admin_router.message(AddVipPlanState.waiting_for_name)
async def admin_add_vip_plan_name(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    name = message.text.strip()
    await state.update_data(plan_name=name)
    await state.set_state(AddVipPlanState.waiting_for_months)
    await message.answer("📅 Ushbu tarif necha oy amal qiladi? (Faqat raqam yozing, masalan: 1):")

@admin_router.message(AddVipPlanState.waiting_for_months)
async def admin_add_vip_plan_months(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    months_str = message.text.strip()
    if not months_str.isdigit():
        await message.answer("❌ Xato! Iltimos faqat raqam yozing:")
        return
        
    months = int(months_str)
    await state.update_data(plan_months=months)
    await state.set_state(AddVipPlanState.waiting_for_price)
    await message.answer("💳 Tarif narxini yoki tavsifini yozing (masalan: 50,000 UZS):")

@admin_router.message(AddVipPlanState.waiting_for_price)
async def admin_add_vip_plan_price(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    price = message.text.strip()
    data = await state.get_data()
    name = data.get("plan_name")
    months = data.get("plan_months")
    
    await add_vip_plan(name, months, price)
    await state.clear()
    await message.answer("✅ VIP Tarif muvaffaqiyatli qo'shildi!", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data.startswith("admin_delete_vip_plan_"))
async def admin_delete_vip_plan(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    plan_id = int(callback.data.replace("admin_delete_vip_plan_", ""))
    success = await delete_vip_plan(plan_id)
    if success:
        await callback.answer("Tarif o'chirildi.")
        await admin_vip_menu(callback)
    else:
        await callback.answer("Tarifni o'chirishda xatolik yuz berdi.", show_alert=True)

# --- ADD SERIES FLOW (ADMIN) ---
@admin_router.callback_query(F.data == "admin_add_series")
async def admin_add_series_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AddSeriesState.waiting_for_title)
    await callback.message.edit_text("📺 Iltimos, serial nomini kiriting:")
    await callback.answer()

@admin_router.message(AddSeriesState.waiting_for_title)
async def admin_add_series_title(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    title = message.text.strip()
    await state.update_data(series_title=title)
    await state.set_state(AddSeriesState.waiting_for_type)
    await message.answer(
        "Ushbu serial qanday taqdim etiladi?\n\n"
        "1. 🔗 Kanal havolasi orqali\n"
        "2. 📁 Qismlarni yuklash orqali",
        reply_markup=get_series_type_keyboard()
    )

@admin_router.callback_query(F.data == "series_type_link")
async def admin_series_type_link(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AddSeriesState.waiting_for_link)
    await callback.message.edit_text("🔗 Kanal havolasini kiriting (masalan, https://t.me/kanal):")
    await callback.answer()

@admin_router.message(AddSeriesState.waiting_for_link)
async def admin_save_series_link(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    link = message.text.strip()
    data = await state.get_data()
    title = data.get("series_title")
    
    series = await add_series(title=title, channel_link=link)
    await state.clear()
    await message.answer(
        f"✅ **Serial muvaffaqiyatli qo'shildi!**\n\n"
        f"📺 Nomi: {series.title}\n"
        f"🆔 Kodi: `{series.series_code}`",
        reply_markup=get_admin_panel()
    )

@admin_router.callback_query(F.data == "series_type_upload")
async def admin_series_type_upload(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    from app.keyboards import get_finish_upload_keyboard
    await state.update_data(episodes_list=[])
    await state.set_state(AddSeriesState.waiting_for_file)
    await callback.message.edit_text(
        "📁 Iltimos, serial qismlarini yuboring (fayllarni birdaniga guruhlab yoki ketma-ket yuborishingiz mumkin).\n\n"
        "Yuklashni tugatganingizdan so'ng, quyidagi **💾 Yakunlash** tugmasini bosing:",
        reply_markup=get_finish_upload_keyboard()
    )
    await callback.answer()

@admin_router.message(AddSeriesState.waiting_for_file)
async def admin_save_series_file(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
        
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.animation:
        file_id = message.animation.file_id
    else:
        await message.answer("❌ Iltimos, yaroqli fayl (video, hujjat, audio, animatsiya) yuboring.")
        return
        
    data = await state.get_data()
    ep_list = data.get("episodes_list", [])
    
    try:
        # Forward to storage channel
        forwarded = await bot.forward_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        
        # Save episode details
        ep_list.append({
            "channel_id": STORAGE_CHANNEL_ID,
            "message_id": forwarded.message_id,
            "file_id": file_id
        })
        await state.update_data(episodes_list=ep_list)
        
        from app.keyboards import get_finish_upload_keyboard
        await message.answer(
            f"✅ {len(ep_list)}-qism qabul qilindi.\n"
            "Yana qismlar yuborishingiz mumkin yoki yuklashni yakunlash uchun **💾 Yakunlash** tugmasini bosing:",
            reply_markup=get_finish_upload_keyboard()
        )
    except Exception as e:
        logger.error(f"Error saving series episode: {e}")
        await message.answer(f"❌ Faylni saqlashda xatolik: {e}")

@admin_router.callback_query(F.data == "series_finish_upload")
async def admin_series_finish_upload(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    data = await state.get_data()
    title = data.get("series_title")
    ep_list = data.get("episodes_list", [])
    
    if not ep_list:
        await callback.answer("⚠️ Iltimos, avval kamida 1 ta qism yuklang!", show_alert=True)
        return
        
    try:
        # Save Series in DB
        episodes_count = len(ep_list)
        series = await add_series(title=title, episodes_count=episodes_count)
        
        # Save SeriesEpisodes sequentially
        for idx, ep in enumerate(ep_list, 1):
            await add_series_episode(
                series_code=series.series_code,
                episode_number=idx,
                channel_id=ep["channel_id"],
                message_id=ep["message_id"],
                file_id=ep["file_id"]
            )
            
        await state.clear()
        await callback.message.edit_text(
            f"✅ **Serial va barcha {episodes_count} qismlari muvaffaqiyatli qo'shildi!**\n\n"
            f"📺 Nomi: {series.title}\n"
            f"🆔 Kodi: `{series.series_code}`",
            reply_markup=get_admin_panel()
        )
    except Exception as e:
        logger.error(f"Error finishing series upload: {e}")
        await callback.message.answer(f"❌ Serialni saqlashda xatolik: {e}")
    await callback.answer()

# --- SERIES LIST & DETAIL MANAGEMENT (ADMIN) ---
@admin_router.callback_query(F.data.startswith("admin_series_page_"))
async def admin_list_series(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    page = int(callback.data.replace("admin_series_page_", ""))
    limit = 10
    offset = (page - 1) * limit
    
    series_list = await get_all_series(offset=offset, limit=limit)
    total_count = await get_series_count()
    total_pages = (total_count + limit - 1) // limit
    
    await callback.message.edit_text(
        f"📺 **Seriallar ro'yxati (Admin) - Sahifa {page}/{max(1, total_pages)}**\n"
        "Bosib boshqarishingiz mumkin:",
        reply_markup=get_admin_series_keyboard(series_list, page, total_pages)
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_series_detail_"))
async def admin_series_detail(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_series_detail_", ""))
    series = await get_series_by_code(code)
    if not series:
        await callback.answer("❌ Serial topilmadi.", show_alert=True)
        return
        
    vip_status = "Ha ⭐" if series.is_vip else "Yo'q"
    info = f"📺 **Serial tafsilotlari**\n\n" \
           f"🆔 Kodi: `{series.series_code}`\n" \
           f"📌 Nomi: {series.title}\n" \
           f"👁️ Qidiruvlar soni: {series.search_count}\n" \
           f"⭐ VIP: {vip_status}\n"
    
    if series.channel_link:
        info += f"🔗 Havola: {series.channel_link}"
    else:
        info += f"📁 Qismlar soni: {series.episodes_count}"
        
    await callback.message.edit_text(info, reply_markup=get_series_detail_keyboard(code, is_vip=series.is_vip, has_link=bool(series.channel_link)))
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_toggle_series_vip_"))
async def admin_toggle_series_vip_handler(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_toggle_series_vip_", ""))
    new_status = await toggle_series_vip(code)
    if new_status is None:
        await callback.answer("❌ Serial topilmadi.", show_alert=True)
        return
    
    series = await get_series_by_code(code)
    vip_status = "Ha ⭐" if series.is_vip else "Yo'q"
    info = f"📺 **Serial tafsilotlari**\n\n" \
           f"🆔 Kodi: `{series.series_code}`\n" \
           f"📌 Nomi: {series.title}\n" \
           f"👁️ Qidiruvlar soni: {series.search_count}\n" \
           f"⭐ VIP: {vip_status}\n"
    
    if series.channel_link:
        info += f"🔗 Havola: {series.channel_link}"
    else:
        info += f"📁 Qismlar soni: {series.episodes_count}"
        
    await callback.message.edit_text(info, reply_markup=get_series_detail_keyboard(code, is_vip=series.is_vip, has_link=bool(series.channel_link)))
    await callback.answer("✅ VIP holati o'zgartirildi.")

@admin_router.callback_query(F.data.startswith("admin_view_series_"))
async def admin_view_series(callback: CallbackQuery, bot: Bot):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_view_series_", ""))
    series = await get_series_by_code(code)
    if not series:
        await callback.answer("❌ Serial topilmadi.", show_alert=True)
        return
        
    if series.channel_link:
        await callback.message.answer(f"🔗 Serial havolasi: {series.channel_link}")
        await callback.answer()
    else:
        await callback.answer("Qismlar yuborilmoqda...")
        for ep in series.episodes:
            try:
                await bot.copy_message(
                    chat_id=callback.message.chat.id,
                    from_chat_id=ep.channel_id,
                    message_id=ep.message_id,
                    caption=f"📺 {series.title} | {ep.episode_number}-qism"
                )
            except Exception as e:
                logger.error(f"Error copying series episode {ep.id}: {e}")

@admin_router.callback_query(F.data.startswith("admin_rename_series_"))
async def admin_rename_series_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_rename_series_", ""))
    await state.set_state(AddSeriesState.waiting_for_rename)
    await state.update_data(edit_series_code=code)
    await callback.message.edit_text("✏️ Iltimos, serial uchun yangi nom yuboring:")
    await callback.answer()

@admin_router.message(AddSeriesState.waiting_for_rename)
async def admin_rename_series_save(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    data = await state.get_data()
    code = data.get("edit_series_code")
    new_title = message.text.strip()
    
    success = await rename_series(code, new_title)
    await state.clear()
    if success:
        await message.answer(f"✅ Serial nomi muvaffaqiyatli '{new_title}'ga o'zgartirildi!", reply_markup=get_admin_panel())
    else:
        await message.answer("❌ Serial nomini o'zgartirib bo'lmadi.", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data.startswith("admin_edit_series_link_"))
async def admin_edit_series_link_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_edit_series_link_", ""))
    await state.set_state(AddSeriesState.waiting_for_edit_link)
    await state.update_data(edit_series_code=code)
    await callback.message.edit_text("🔗 Iltimos, serial uchun yangi havolani yuboring (masalan: https://t.me/... yoki @kanal):")
    await callback.answer()

@admin_router.message(AddSeriesState.waiting_for_edit_link)
async def admin_edit_series_link_save(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    data = await state.get_data()
    code = data.get("edit_series_code")
    new_link = message.text.strip()
    
    success = await update_series_link(code, new_link)
    await state.clear()
    if success:
        await message.answer(f"✅ Serial havolasi muvaffaqiyatli yangilandi!\n\nYangi havola: {new_link}", reply_markup=get_admin_panel())
    else:
        await message.answer("❌ Serial havolasini yangilab bo'lmadi.", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data.startswith("admin_delete_series_"))
async def admin_delete_series_action(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_delete_series_", ""))
    success = await delete_series(code)
    if success:
        await callback.answer("✅ Serial o'chirildi.")
        await callback.message.edit_text("✅ Serial muvaffaqiyatli o'chirildi.", reply_markup=get_admin_panel())
    else:
        await callback.answer("❌ Serialni o'chirishda xatolik.", show_alert=True)


# --- DYNAMIC ADMINS MANAGEMENT HANDLERS ---
@admin_router.callback_query(F.data == "admin_manage_admins")
async def manage_admins(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    admins = await get_all_admins()
    await callback.message.edit_text(
        "👥 **Bot administratorlari boshqaruvi**\n\n"
        "Quyidagi dynamic adminlar ro'yxatidan o'chirishingiz mumkin yoki yangi admin qo'shing:",
        reply_markup=get_admin_manage_admins_keyboard(admins)
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_add_admin_prompt")
async def add_admin_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AddAdminState.waiting_for_admin_id)
    await callback.message.edit_text("👤 Yangi adminning Telegram **User ID** raqamini kiriting:")
    await callback.answer()

@admin_router.message(AddAdminState.waiting_for_admin_id)
async def add_admin_save(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    user_id_str = message.text.strip()
    if not user_id_str.isdigit():
        await message.answer("❌ Noto'g'ri format. Iltimos faqat raqamlardan iborat bo'lgan User ID yuboring.")
        return
    user_id = int(user_id_str)
    user = await get_user(user_id)
    
    username = user.username if user else None
    full_name = user.full_name if user else f"User ID: {user_id}"
    
    await add_admin_user(user_id, username, full_name)
    await state.clear()
    await message.answer(f"✅ Yangi admin qo'shildi: {full_name}", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data.startswith("admin_delete_admin_"))
async def delete_admin_action(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    admin_id = int(callback.data.replace("admin_delete_admin_", ""))
    success = await delete_admin_user(admin_id)
    if success:
        await callback.answer("✅ Admin o'chirildi.")
        admins = await get_all_admins()
        await callback.message.edit_text("👥 Administratorlar ro'yxati yangilandi:", reply_markup=get_admin_manage_admins_keyboard(admins))
    else:
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)


# --- CUSTOMIZABLE TEXT SETTINGS HANDLERS ---
@admin_router.callback_query(F.data == "admin_edit_texts")
async def edit_texts_menu(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    await callback.message.edit_text(
        "📝 **Bot matnlarini sozlash bo'limi**\n\n"
        "Tahrirlamoqchi bo'lgan matnni tanlang:",
        reply_markup=get_admin_edit_texts_keyboard()
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_edit_text_"))
async def edit_text_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    key = callback.data.replace("admin_edit_text_", "")
    current_text = await get_setting(key, "Mavjud emas")
    await state.update_data(editing_text_key=key)
    await state.set_state(EditTextState.waiting_for_new_text)
    await callback.message.edit_text(
        f"📝 **Hozirgi matn ({key}):**\n\n`{current_text}`\n\n"
        "Yangi matnni yuboring:"
    )
    await callback.answer()

@admin_router.message(EditTextState.waiting_for_new_text)
async def save_custom_text(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    new_text = message.text.strip()
    data = await state.get_data()
    key = data.get("editing_text_key")
    
    await set_setting(key, new_text)
    await state.clear()
    await message.answer(f"✅ Matn muvaffaqiyatli saqlandi!", reply_markup=get_admin_panel())


# --- SEASONS & EPISODES MANAGEMENT HANDLERS ---
@admin_router.callback_query(F.data.startswith("admin_series_manage_episodes_"))
async def admin_series_manage_episodes(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_series_manage_episodes_", ""))
    series = await get_series_by_code(code)
    if not series:
        await callback.answer("Serial topilmadi.", show_alert=True)
        return
    seasons = sorted(list(set([ep.season_number or 1 for ep in series.episodes])))
    if not seasons:
        seasons = [1]
    await callback.message.edit_text(
        f"📺 **{series.title}** qismlarini boshqarish.\n\n"
        "Faslni tanlang:",
        reply_markup=get_admin_seasons_keyboard(code, seasons)
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_series_season_"))
async def admin_series_season_episodes(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    parts = callback.data.replace("admin_series_season_", "").split("_")
    code = int(parts[0])
    season_num = int(parts[1])
    series = await get_series_by_code(code)
    if not series:
        await callback.answer("Serial topilmadi.", show_alert=True)
        return
    episodes = [ep for ep in series.episodes if (ep.season_number or 1) == season_num]
    episodes.sort(key=lambda x: x.episode_number)
    await callback.message.edit_text(
        f"📺 **{series.title} | {season_num}-fasl qismlari**\n\n"
        "Boshqarish uchun qismni tanlang:",
        reply_markup=get_admin_season_episodes_keyboard(code, season_num, episodes)
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_series_ep_detail_"))
async def admin_series_ep_detail(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    parts = callback.data.replace("admin_series_ep_detail_", "").split("_")
    series_code = int(parts[0])
    ep_id = int(parts[1])
    
    series = await get_series_by_code(series_code)
    episode = next((ep for ep in series.episodes if ep.id == ep_id), None)
    if not episode:
        await callback.answer("Qism topilmadi.", show_alert=True)
        return
        
    await callback.message.edit_text(
        f"📺 **{series.title} | {(episode.season_number or 1)}-fasl, {episode.episode_number}-qism**\n\n"
        "Amalni tanlang:",
        reply_markup=get_admin_episode_detail_keyboard(series_code, ep_id, (episode.season_number or 1))
    )
    await callback.answer()

@admin_router.callback_query(F.data.startswith("admin_series_ep_view_"))
async def admin_series_ep_view(callback: CallbackQuery, bot: Bot):
    if not is_admin_callback(callback):
        return
    ep_id = int(callback.data.replace("admin_series_ep_view_", ""))
    from app.database import AsyncSessionLocal
    from app.models import SeriesEpisode
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(SeriesEpisode).where(SeriesEpisode.id == ep_id))
        episode = res.scalars().first()
        
    if not episode:
        await callback.answer("Qism topilmadi.", show_alert=True)
        return
        
    try:
        await bot.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=episode.channel_id,
            message_id=episode.message_id
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Xatolik: {e}", show_alert=True)

@admin_router.callback_query(F.data.startswith("admin_series_ep_replace_"))
async def admin_series_ep_replace_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    ep_id = int(callback.data.replace("admin_series_ep_replace_", ""))
    await state.set_state(ManageSeriesEpisodesState.waiting_for_replace_file)
    await state.update_data(replace_episode_id=ep_id)
    await callback.message.edit_text("🔄 Yangi qism faylini yuboring:")
    await callback.answer()

@admin_router.message(ManageSeriesEpisodesState.waiting_for_replace_file)
async def admin_series_ep_replace_save(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
        
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.animation:
        file_id = message.animation.file_id
    else:
        await message.answer("❌ Iltimos, video, hujjat, audio yoki animatsiya fayli yuboring.")
        return
        
    data = await state.get_data()
    ep_id = data.get("replace_episode_id")
    
    try:
        forwarded = await bot.forward_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        success = await replace_series_episode_file(ep_id, STORAGE_CHANNEL_ID, forwarded.message_id, file_id)
        await state.clear()
        if success:
            await message.answer("✅ Fayl muvaffaqiyatli almashtirildi!", reply_markup=get_admin_panel())
        else:
            await message.answer("❌ Faylni almashtirib bo'lmadi.", reply_markup=get_admin_panel())
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

@admin_router.callback_query(F.data.startswith("admin_series_ep_delete_"))
async def admin_series_ep_delete(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    ep_id = int(callback.data.replace("admin_series_ep_delete_", ""))
    success = await delete_series_episode(ep_id)
    if success:
        await callback.answer("✅ Qism o'chirildi.")
        await callback.message.edit_text("✅ Qism muvaffaqiyatli o'chirildi.", reply_markup=get_admin_panel())
    else:
        await callback.answer("❌ O'chirishda xatolik yuz berdi.", show_alert=True)

@admin_router.callback_query(F.data.startswith("admin_series_add_ep_"))
async def admin_series_add_ep_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_series_add_ep_", ""))
    await state.set_state(ManageSeriesEpisodesState.waiting_for_season)
    await state.update_data(add_ep_series_code=code)
    await callback.message.edit_text("📅 Qism qaysi **fasl**ga tegishli? (Faqat raqam yozing, masalan: 1):")
    await callback.answer()

@admin_router.message(ManageSeriesEpisodesState.waiting_for_season)
async def admin_series_add_ep_season(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    val = message.text.strip()
    if not val.isdigit():
        await message.answer("❌ Iltimos faqat raqam kiriting:")
        return
    await state.update_data(add_ep_season=int(val))
    await state.set_state(ManageSeriesEpisodesState.waiting_for_episode)
    await message.answer("🔢 Bu nechanchi **qism**? (Faqat raqam yozing, masalan: 12):")

@admin_router.message(ManageSeriesEpisodesState.waiting_for_episode)
async def admin_series_add_ep_num(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    val = message.text.strip()
    if not val.isdigit():
        await message.answer("❌ Iltimos faqat raqam kiriting:")
        return
    await state.update_data(add_ep_episode=int(val))
    await state.set_state(ManageSeriesEpisodesState.waiting_for_file)
    await message.answer("📁 Endi qism faylini yuboring (video, hujjat):")

@admin_router.message(ManageSeriesEpisodesState.waiting_for_file)
async def admin_series_add_ep_file(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
        
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.animation:
        file_id = message.animation.file_id
    else:
        await message.answer("❌ Iltimos, video, hujjat, audio yoki animatsiya fayli yuboring.")
        return
        
    data = await state.get_data()
    code = data.get("add_ep_series_code")
    season = data.get("add_ep_season")
    episode = data.get("add_ep_episode")
    
    try:
        forwarded = await bot.forward_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        await add_series_episode(
            series_code=code,
            season_number=season,
            episode_number=episode,
            channel_id=STORAGE_CHANNEL_ID,
            message_id=forwarded.message_id,
            file_id=file_id
        )
        await state.clear()
        await message.answer(f"✅ {season}-fasl, {episode}-qism muvaffaqiyatli qo'shildi!", reply_markup=get_admin_panel())
    except Exception as e:
        await message.answer(f"❌ Faylni saqlashda xatolik: {e}")

# --- BULK UPLOAD EPISODES ---
@admin_router.callback_query(F.data.startswith("admin_series_add_ep_bulk_"))
async def admin_series_add_ep_bulk_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_series_add_ep_bulk_", ""))
    await state.set_state(ManageSeriesEpisodesState.waiting_for_bulk_season)
    await state.update_data(add_ep_series_code=code)
    await callback.message.edit_text("📅 Qismlar qaysi **fasl**ga tegishli? (Faqat raqam yozing, masalan: 1):")
    await callback.answer()

@admin_router.message(ManageSeriesEpisodesState.waiting_for_bulk_season)
async def admin_series_add_ep_bulk_season(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    val = message.text.strip()
    if not val.isdigit():
        await message.answer("❌ Iltimos faqat raqam kiriting:")
        return
    await state.update_data(add_ep_season=int(val), bulk_episodes_list=[])
    await state.set_state(ManageSeriesEpisodesState.waiting_for_bulk_files)
    
    from app.keyboards import get_bulk_finish_upload_keyboard
    await message.answer(
        "📁 Endi ushbu fasl uchun barcha qismlarni yuboring (fayllarni bittalab yoki guruhlab yuborishingiz mumkin).\n\n"
        "Yuklashni tugatganingizdan so'ng **💾 Yuklashni yakunlash** tugmasini bosing:",
        reply_markup=get_bulk_finish_upload_keyboard()
    )

@admin_router.message(ManageSeriesEpisodesState.waiting_for_bulk_files)
async def admin_series_add_ep_bulk_files(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
        
    file_id = None
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.audio:
        file_id = message.audio.file_id
    elif message.animation:
        file_id = message.animation.file_id
    else:
        await message.answer("❌ Iltimos, video, hujjat, audio yoki animatsiya fayli yuboring.")
        return
        
    data = await state.get_data()
    ep_list = data.get("bulk_episodes_list", [])
    
    try:
        forwarded = await bot.forward_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        ep_list.append({
            "channel_id": STORAGE_CHANNEL_ID,
            "message_id": forwarded.message_id,
            "file_id": file_id
        })
        await state.update_data(bulk_episodes_list=ep_list)
        
        from app.keyboards import get_bulk_finish_upload_keyboard
        await message.answer(
            f"✅ {len(ep_list)}-fayl qabul qilindi.\n"
            "Yana yuborishingiz yoki yakunlashingiz mumkin:",
            reply_markup=get_bulk_finish_upload_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ Faylni saqlashda xatolik: {e}")

@admin_router.callback_query(F.data == "series_bulk_finish_upload")
async def admin_series_bulk_finish_upload(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    data = await state.get_data()
    code = data.get("add_ep_series_code")
    season = data.get("add_ep_season")
    ep_list = data.get("bulk_episodes_list", [])
    
    if not ep_list:
        await callback.answer("⚠️ Iltimos, avval kamida 1 ta qism yuklang!", show_alert=True)
        return
        
    try:
        series = await get_series_by_code(code)
        # Find max episode number for this season
        existing_eps = [ep.episode_number for ep in series.episodes if (ep.season_number or 1) == season]
        next_ep_num = max(existing_eps) + 1 if existing_eps else 1
        
        for ep in ep_list:
            await add_series_episode(
                series_code=code,
                season_number=season,
                episode_number=next_ep_num,
                channel_id=ep["channel_id"],
                message_id=ep["message_id"],
                file_id=ep["file_id"]
            )
            next_ep_num += 1
            
        await state.clear()
        await callback.message.edit_text(
            f"✅ {season}-faslga {len(ep_list)} ta qism muvaffaqiyatli qo'shildi!",
            reply_markup=get_admin_panel()
        )
    except Exception as e:
        logger.error(f"Error finishing bulk upload: {e}")
        await callback.message.answer(f"❌ Qismlarni saqlashda xatolik: {e}")
    await callback.answer()
