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

# Helper filter for admins
def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS

def is_admin_callback(callback: CallbackQuery) -> bool:
    return callback.from_user.id in ADMIN_IDS

@admin_router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await state.clear()
    await message.answer("🛠️ Welcome to the Admin Panel. Choose an action:", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data == "admin_back")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text("🛠️ Welcome to the Admin Panel. Choose an action:", reply_markup=get_admin_panel())
    await callback.answer()

# --- STATISTICS ---
@admin_router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    stats = await get_statistics()
    text = (
        "📊 **Bot Statistics**\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"⭐ VIP Users: {stats['vip_users']}\n"
        f"🎬 Total Movies: {stats['movies']}\n"
        f"🔍 Total Searches: {stats['searches']}\n"
        f"📅 Today's Registrations: {stats['today_users']}"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_panel())
    await callback.answer()

# --- BANK CARD ---
@admin_router.callback_query(F.data == "admin_bank_card")
async def view_bank_card(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    card = await get_setting("bank_card", "Not configured")
    await state.set_state(AdminState.waiting_for_card)
    await callback.message.edit_text(
        f"💳 **Current Bank Card:** `{card}`\n\n"
        "Please send a new bank card number / details to update it. Or click back to cancel.",
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
    await message.answer(f"✅ Bank card details updated to:\n`{card_details}`", reply_markup=get_admin_panel())

# --- REQUIRED CHANNELS ---
@admin_router.callback_query(F.data == "admin_channels")
async def view_required_channels(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    channels = await get_required_channels()
    text = "📺 **Required Channels for Users:**\n\n"
    if not channels:
        text += "No required channels set. Users have instant access."
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
        "📺 Please send the channel details in the following format:\n\n"
        "`channel_id|invite_link|channel_name`\n\n"
        "Example:\n"
        "`-1001234567890|https://t.me/+AbCdEf|My Channel`"
    )
    await callback.answer()

@admin_router.message(AdminState.waiting_for_add_channel)
async def add_channel_save(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    parts = message.text.split("|")
    if len(parts) != 3:
        await message.answer("❌ Invalid format. Please use: `channel_id|invite_link|channel_name`")
        return
    
    try:
        channel_id = int(parts[0].strip())
        invite_link = parts[1].strip()
        name = parts[2].strip()
        
        await add_required_channel(channel_id, invite_link, name)
        await state.clear()
        await message.answer("✅ Channel added successfully!", reply_markup=get_admin_panel())
    except ValueError:
        await message.answer("❌ Channel ID must be an integer. Please try again.")

@admin_router.callback_query(F.data.startswith("admin_delete_channel_"))
async def delete_channel_action(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    channel_id = int(callback.data.replace("admin_delete_channel_", ""))
    success = await delete_required_channel(channel_id)
    if success:
        await callback.answer("✅ Channel deleted.")
        channels = await get_required_channels()
        await callback.message.edit_text("📺 Required Channels updated:", reply_markup=get_admin_channels_keyboard(channels))
    else:
        await callback.answer("❌ Channel not found.")

# --- BROADCAST ---
@admin_router.callback_query(F.data == "admin_broadcast")
async def broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.message.edit_text("📢 Send the message you want to broadcast to all users (can be text, photo, video, etc.):")
    await callback.answer()

@admin_router.message(AdminState.waiting_for_broadcast)
async def broadcast_confirm(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    # Save message details in FSM context
    await state.update_data(
        broadcast_msg_id=message.message_id,
        broadcast_chat_id=message.chat.id
    )
    await message.answer("❓ Are you sure you want to broadcast this message to all users?", reply_markup=get_broadcast_confirm_keyboard())

@admin_router.callback_query(F.data == "admin_confirm_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_admin_callback(callback):
        return
    data = await state.get_data()
    msg_id = data.get("broadcast_msg_id")
    chat_id = data.get("broadcast_chat_id")
    
    if not msg_id or not chat_id:
        await callback.answer("❌ Broadcast details not found. Please start again.", show_alert=True)
        await state.clear()
        return
        
    await callback.answer("🚀 Starting broadcast...")
    await callback.message.edit_text("📤 Broadcasting in progress...")
    
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
        f"📢 **Broadcast Finished**\n\n"
        f"✅ Sent: {success_count}\n"
        f"❌ Failed: {fail_count}",
        reply_markup=get_admin_panel()
    )

# --- ADD MOVIE ---
@admin_router.callback_query(F.data == "admin_add_movie")
async def add_movie_title(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    await state.set_state(AddMovieState.waiting_for_title)
    await callback.message.edit_text("🎬 Please send the title of the movie:")
    await callback.answer()

@admin_router.message(AddMovieState.waiting_for_title)
async def add_movie_file(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    title = message.text.strip()
    await state.update_data(movie_title=title)
    await state.set_state(AddMovieState.waiting_for_file)
    await message.answer("📁 Now send the movie file (Video, Document, etc.):")

@admin_router.message(AddMovieState.waiting_for_file)
async def process_movie_file(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message):
        return
    
    # Determine the file ID
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
        await message.answer("❌ Please upload a valid video, document, animation, or audio file.")
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
            f"✅ **Movie Added Successfully!**\n\n"
            f"🎬 Title: {movie.title}\n"
            f"🆔 Code: `{movie.movie_code}`",
            reply_markup=get_admin_panel()
        )
    except Exception as e:
        logger.error(f"Error adding movie: {e}")
        await message.answer(f"❌ Error adding movie: {e}\nEnsure storage channel ID is correct and bot is an admin there.")

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
        f"🎬 **Movies List (Admin) - Page {page}/{max(1, total_pages)}**\n"
        "Click on a movie to manage it:",
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
        await callback.answer("❌ Movie not found.", show_alert=True)
        return
        
    await callback.message.edit_text(
        f"🎬 **Movie Details**\n\n"
        f"🆔 Code: `{movie.movie_code}`\n"
        f"📌 Title: {movie.title}\n"
        f"👁️ Searches: {movie.search_count}",
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
        await callback.answer("❌ Movie not found.", show_alert=True)
        return
        
    try:
        await bot.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=movie.channel_id,
            message_id=movie.message_id
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Error copying message: {e}", show_alert=True)

@admin_router.callback_query(F.data.startswith("admin_rename_movie_"))
async def admin_rename_movie_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_rename_movie_", ""))
    await state.set_state(AdminState.waiting_for_rename_movie)
    await state.update_data(edit_movie_code=code)
    await callback.message.edit_text("✏️ Please send the new title for this movie:")
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
        await message.answer(f"✅ Movie renamed successfully to {new_title}!", reply_markup=get_admin_panel())
    else:
        await message.answer("❌ Failed to rename movie.", reply_markup=get_admin_panel())

@admin_router.callback_query(F.data.startswith("admin_replace_movie_"))
async def admin_replace_movie_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_replace_movie_", ""))
    await state.set_state(AdminState.waiting_for_replace_movie_file)
    await state.update_data(edit_movie_code=code)
    await callback.message.edit_text("🔄 Please send the new movie file:")
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
        await message.answer("❌ Please upload a valid video, document, animation, or audio file.")
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
            await message.answer("✅ Movie file replaced successfully!", reply_markup=get_admin_panel())
        else:
            await message.answer("❌ Failed to replace movie file.", reply_markup=get_admin_panel())
    except Exception as e:
        await message.answer(f"❌ Error replacing movie file: {e}")

@admin_router.callback_query(F.data.startswith("admin_delete_movie_"))
async def admin_delete_movie_action(callback: CallbackQuery):
    if not is_admin_callback(callback):
        return
    code = int(callback.data.replace("admin_delete_movie_", ""))
    success = await delete_movie(code)
    if success:
        await callback.answer("✅ Movie deleted.")
        await callback.message.edit_text("✅ Movie deleted successfully.", reply_markup=get_admin_panel())
    else:
        await callback.answer("❌ Failed to delete movie.", show_alert=True)

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
        # Notify user
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🎉 **VIP Activation Successful!**\n\nYour subscription has been activated for {months} month(s) until {new_expiry.strftime('%Y-%m-%d %H:%M:%S')} UTC."
            )
        except Exception:
            pass
        await callback.message.edit_text(f"✅ Approved VIP for user {user_id} ({months} months). Expiry: {new_expiry.strftime('%Y-%m-%d')}")
    else:
        await callback.message.edit_text("❌ User not found.")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("reject_vip_"))
async def reject_vip(callback: CallbackQuery, bot: Bot):
    if not is_admin_callback(callback):
        return
    user_id = int(callback.data.replace("reject_vip_", ""))
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ **VIP Subscription Request Rejected**\n\nYour receipt was reviewed and rejected. If you think this is a mistake, contact administration."
        )
    except Exception:
        pass
    await callback.message.edit_text(f"❌ Rejected VIP request for user {user_id}.")
    await callback.answer()
