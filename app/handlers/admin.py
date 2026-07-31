import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from app.config import ADMIN_IDS, STORAGE_CHANNEL_ID
from app.states import AdminState, AddMovieState
from app.database import (
    get_statistics, get_setting, set_setting, get_required_channels,
    add_required_channel, delete_required_channel, add_movie,
    get_all_movies, get_movie_count, get_movie_by_code, rename_movie,
    replace_movie_file, delete_movie, update_vip_until
)
from app.keyboards import (
    get_admin_panel, get_admin_channels_keyboard, get_admin_movies_keyboard,
    get_movie_detail_keyboard, get_broadcast_confirm_keyboard,
    get_receipt_approval_keyboard
)

logger = logging.getLogger(__name__)
admin_router = Router()

def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS

def is_admin_callback(callback: CallbackQuery) -> bool:
    return callback.from_user.id in ADMIN_IDS

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
        f"⭐ VIP foydalanuvchilar: {stats['vip_users']}\n"
        f"🎬 Jami kinolar: {stats['movies']}\n"
        f"🔍 Jami qidiruvlar: {stats['searches']}\n"
        f"📅 Bugungi ro'yxatdan o'tganlar: {stats['today_users']}"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_panel())
    await callback.answer()

# --- BANK CARD ---
@admin_router.callback_query(F.data == "admin_bank_card")
async def view_bank_card(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    card = await get_setting("bank_card", "Sozlanmagan")
    await state.set_state(AdminState.waiting_for_card)
    await callback.message.edit_text(
        f"💳 **Hozirgi bank kartasi:** `{card}`\n\n"
        "O'zgartirish uchun yangi bank kartasi raqamini/tafsilotlarini yuboring. Bekor qilish uchun Orqaga bosing.",
        reply_markup=get_admin_panel()
    )
    await callback.answer()

@admin_router.message(AdminState.waiting_for_card)
async def update_bank_card(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    card_details = message.text.strip()
    await set_setting("bank_card", card_details)
    await state.clear()
    await message.answer(f"✅ Bank kartasi ma'lumotlari yangilandi:\n`{card_details}`", reply_markup=get_admin_panel())

# --- REQUIRED CHANNELS ---
@admin_router.callback_query(F.data == "admin_channels")
async def view_required_channels(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    channels = await get_required_channels()
    text = "📺 **Foydalanuvchilar uchun majburiy kanallar:**\n\n"
    if not channels:
        text += "Hech qanday majburiy kanal qo'shilmagan. Foydalanuvchilar to'g'ridan-to'g'ri foydalanishi mumkin."
    else:
        for idx, chan in enumerate(channels, 1):
            text += f"{idx}. {chan.name} (ID: `{chan.channel_id}`)\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_channels_keyboard(channels))
    await callback.answer()

@admin_router.callback_query(F.data == "admin_add_channel")
async def add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AdminState.waiting_for_add_channel)
    await callback.message.edit_text(
        "📺 Iltimos, kanal ma'lumotlarini quyidagi formatda yuboring:\n\n"
        "`channel_id|taklif_Linki|kanal_nomi`\n\n"
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
        
        await add_required_channel(channel_id, invite_link, name)
        await state.clear()
        await message.answer("✅ Kanal muvaffaqiyatli qo'shildi!", reply_markup=get_admin_panel())
    except ValueError:
        await message.answer("❌ Kanal ID raqam (integer) bo'lishi kerak. Qayta urinib ko'ring.")

@admin_router.callback_query(F.data.startswith("admin_delete_channel_"))
async def delete_channel_action(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    channel_id = int(callback.data.replace("admin_delete_channel_", ""))
    success = await delete_required_channel(channel_id)
    if success:
        await callback.answer("✅ Kanal o'chirildi.")
        channels = await get_required_channels()
        await callback.message.edit_text("📺 Majburiy kanallar ro'yxati yangilandi:", reply_markup=get_admin_channels_keyboard(channels))
    else:
        await callback.answer("❌ Kanal topilmadi.")

# --- BROADCAST ---
@admin_router.callback_query(F.data == "admin_broadcast")
async def broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.edit_text("📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring (matn, rasm, video va h.k.):")
    await callback.answer()

@admin_router.message(AdminState.waiting_for_broadcast)
async def broadcast_confirm(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await state.update_data(
        broadcast_msg_id=message.message_id,
        broadcast_chat_id=message.chat.id
    )
    await message.answer("❓ Haqiqatan ham ushbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?", reply_markup=get_broadcast_confirm_keyboard())

@admin_router.callback_query(F.data == "admin_confirm_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin_callback(callback):
        return
    data = await state.get_data()
    msg_id = data.get("broadcast_msg_id")
    chat_id = data.get("broadcast_chat_id")
    
    if not msg_id or not chat_id:
        await callback.answer("❌ Reklama tafsilotlari topilmadi. Qayta urinib ko'ring.", show_alert=True)
        await state.clear()
        return
        
    await callback.answer("🚀 Reklama yuborilmoqda...")
    await callback.message.edit_text("📤 Yuborish jarayoni boshlandi...")
    
    stats = await get_statistics()
    user_ids = stats.get("all_user_ids", [])
    
    success_count = 0
    fail_count = 0
    
    for uid in user_ids:
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=chat_id, message_id=msg_id)
            success_count += 1
        except Exception:
            fail_count += 1
            
    await state.clear()
    await callback.message.answer(
        f"📢 **Reklama yuborish yakunlandi**\n\n"
        f"✅ Muvaffaqiyatli: {success_count}\n"
        f"❌ Muqobil/Xato: {fail_count}",
        reply_markup=get_admin_panel()
    )

# --- ADD MOVIE ---
@admin_router.callback_query(F.data == "admin_add_movie")
async def add_movie_title(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AddMovieState.waiting_for_title)
    await callback.message.edit_text("🎬 Iltimos, kino nomini yuboring:")
    await callback.answer()

@admin_router.message(AddMovieState.waiting_for_title)
async def add_movie_file(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    title = message.text.strip()
    await state.update_data(movie_title=title)
    await state.set_state(AddMovieState.waiting_for_file)
    await message.answer("📁 Endi kino faylini yuboring (Video, Hujjat va h.k.):")

@admin_router.message(AddMovieState.waiting_for_file)
async def process_movie_file(message: Message, state: FSMContext, bot: Bot):
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
        await message.answer("❌ Iltimos, yaroqli video, hujjat, animatsiya yoki audio fayl yuboring.")
        return
        
    data = await state.get_data()
    title = data.get("movie_title")
    
    try:
        # Forward message to storage channel
        forwarded = await bot.forward_message(
            chat_id=STORAGE_CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        
        # Save to DB
        movie = await add_movie(
            title=title,
            channel_id=STORAGE_CHANNEL_ID,
            message_id=forwarded.message_id,
            file_id=file_id
        )
        
        await state.clear()
        await message.answer(
            f"✅ **Kino muvaffaqiyatli qo'shildi!**\n\n"
            f"🎬 Nomi: {movie.title}\n"
            f"🆔 Kodi: `{movie.movie_code}`",
            reply_markup=get_admin_panel()
        )
    except Exception as e:
        logger.error(f"Error adding movie: {e}")
        await message.answer(f"❌ Kino qo'shishda xatolik: {e}\nSaqlash kanali ID'si to'g'ri ekanligini va bot u yerda admin ekanligini tekshiring.")

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
        
    await callback.message.edit_text(
        f"🎬 **Kino tafsilotlari**\n\n"
        f"🆔 Kodi: `{movie.movie_code}`\n"
        f"📌 Nomi: {movie.title}\n"
        f"👁️ Qidiruvlar soni: {movie.search_count}",
        reply_markup=get_movie_detail_keyboard(code)
    )
    await callback.answer()

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
        except Exception:
            pass
        await callback.message.edit_text(f"✅ Foydalanuvchi {user_id} uchun VIP faollashtirildi ({months} oy). Muddat: {new_expiry.strftime('%Y-%m-%d')}")
    else:
        await callback.message.edit_text("❌ Foydalanuvchi topilmadi.")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("reject_vip_"))
async def reject_vip(callback: CallbackQuery, bot: Bot):
    if not is_admin_callback(callback):
        return
    user_id = int(callback.data.replace("reject_vip_", ""))
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ **VIP obuna so'rovi rad etildi**\n\nYuborgan to'lov chekingiz rad etildi. Agar xatolik deb o'ylasangiz, administrator bilan bog'laning."
        )
    except Exception:
        pass
    await callback.message.edit_text(f"❌ Foydalanuvchi {user_id} uchun VIP so'rovi rad etildi.")
    await callback.answer()

# --- MANUAL VIP MANAGEMENT (ADMIN) ---
@admin_router.callback_query(F.data == "admin_vip_plans")
async def admin_vip_menu(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    from app.keyboards import get_admin_vip_keyboard
    await callback.message.edit_text(
        "⭐ **VIP Boshqaruvi**\n\nBu bo'lim orqali foydalanuvchilarga qo'lda VIP berishingiz mumkin.",
        reply_markup=get_admin_vip_keyboard()
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
    from app.keyboards import get_admin_manual_vip_plans_keyboard
    await state.clear()
    await message.answer(
        f"👤 Tanlangan foydalanuvchi ID: `{user_id}`\n\nUshbu foydalanuvchiga qancha muddatga VIP obuna bermoqchisiz?",
        reply_markup=get_admin_manual_vip_plans_keyboard(user_id)
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
            f"Muddat: {new_expiry.strftime('%Y-%m-%d')}"
        )
    else:
        await callback.message.edit_text("❌ Foydalanuvchi topilmadi. U kamida bir marta botni start qilgan bo'lishi kerak.")
    await callback.answer()
