import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.database import (
    get_movie_by_code, get_all_movies, get_movie_count, get_setting,
    get_or_create_user
)
from app.keyboards import (
    get_movie_list_keyboard, get_receipt_approval_keyboard, get_vip_plans_keyboard,
    get_main_keyboard
)
from app.utils import check_user_subscription
from app.states import VIPState
from app.config import ADMIN_IDS

logger = logging.getLogger(__name__)
callback_router = Router()

@callback_router.callback_query(F.data == "check_subscription")
async def process_check_subscription(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(bot, user_id)
    
    if is_subscribed:
        # Check if they had a pending movie code they were trying to access
        data = await state.get_data()
        pending_code = data.get("pending_movie_code")
        
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        
        if pending_code:
            movie = await get_movie_by_code(pending_code)
            if movie:
                # Import here to avoid circular imports or reuse user's helper
                from app.handlers.user import send_movie_to_user
                await send_movie_to_user(bot, callback.message.chat.id, movie, bot_username)
                await callback.message.delete()
                await state.clear()
                return
                
        await callback.message.edit_text(
            "🎉 Thank you for subscribing! You now have full access to the bot.",
            reply_markup=None
        )
        await callback.message.answer("Choose an option from the menu:", reply_markup=get_main_keyboard())
        await state.clear()
    else:
        await callback.answer(
            "⚠️ You have not subscribed to all required channels yet. Please subscribe and try again.",
            show_alert=True
        )

@callback_router.callback_query(F.data == "buy_vip")
async def process_buy_vip(callback: CallbackQuery):
    card = await get_setting("bank_card", "Not configured")
    text = (
        "⭐ **VIP Subscription**\n\n"
        "VIP users bypass all sponsor channel subscription requirements!\n\n"
        "💳 **Payment details (Bank Card):**\n"
        f"`{card}`\n\n"
        "Select a subscription plan below to get started:"
    )
    await callback.message.edit_text(text, reply_markup=get_vip_plans_keyboard())
    await callback.answer()

@callback_router.callback_query(F.data.startswith("vip_plan_"))
async def process_vip_plan_selection(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.replace("vip_plan_", ""))
    await state.update_data(selected_vip_months=months)
    await state.set_state(VIPState.waiting_for_receipt)
    
    card = await get_setting("bank_card", "Not configured")
    text = (
        f"💳 **Plan: {months} Month(s)**\n\n"
        f"Please send the payment of the subscription to our bank card:\n"
        f"`{card}`\n\n"
        "After transferring the money, **upload the payment receipt** (as a photo or document) here. "
        "Admins will verify and approve your subscription shortly."
    )
    await callback.message.edit_text(text)
    await callback.answer()

@callback_router.callback_query(F.data == "vip_back")
async def process_vip_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Choose an option from the menu:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# Message handler for VIP State: waiting for receipt
@callback_router.message(VIPState.waiting_for_receipt, F.photo | F.document)
async def process_vip_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    months = data.get("selected_vip_months", 1)
    
    # Notify user
    await message.answer(
        "⏳ **Receipt Received!**\n\n"
        "Your payment receipt has been sent to the administrators for verification. "
        "You will be notified once it is approved."
    )
    
    # Forward receipt to admins
    for admin_id in ADMIN_IDS:
        try:
            # Send message to admin containing receipt and approval inline buttons
            caption = (
                f"💳 **New VIP Subscription Request**\n\n"
                f"👤 User: {message.from_user.full_name} (ID: `{message.from_user.id}`)\n"
                f"🏷️ Username: @{message.from_user.username or 'none'}\n"
                f"📅 Plan: {months} Month(s)"
            )
            
            if message.photo:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=message.photo[-1].file_id,
                    caption=caption,
                    reply_markup=get_receipt_approval_keyboard(message.from_user.id, months)
                )
            elif message.document:
                await bot.send_document(
                    chat_id=admin_id,
                    document=message.document.file_id,
                    caption=caption,
                    reply_markup=get_receipt_approval_keyboard(message.from_user.id, months)
                )
        except Exception as e:
            logger.error(f"Failed to forward receipt to admin {admin_id}: {e}")
            
    await state.clear()

@callback_router.callback_query(F.data.startswith("view_movie_user_"))
async def process_view_movie_user(callback: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(bot, user_id)
    
    code = int(callback.data.replace("view_movie_user_", ""))
    
    if not is_subscribed:
        # Save movie request to state, then show sub prompt
        await state.update_data(pending_movie_code=code)
        from app.database import get_required_channels
        channels = await get_required_channels()
        await callback.message.answer(
            "⚠️ **Access Denied!**\n\n"
            "To view this movie, you must subscribe to our sponsor channels first, "
            "or buy a VIP subscription to bypass all restrictions.",
            reply_markup=get_join_channels_keyboard(channels)
        )
        await callback.answer()
        return
        
    movie = await get_movie_by_code(code)
    if not movie:
        await callback.answer("❌ Movie not found.", show_alert=True)
        return
        
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    from app.handlers.user import send_movie_to_user
    try:
        await send_movie_to_user(bot, callback.message.chat.id, movie, bot_username)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Error sending movie: {e}", show_alert=True)

@callback_router.callback_query(F.data.startswith("movie_page_"))
async def process_movie_page(callback: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(bot, user_id)
    
    if not is_subscribed:
        from app.database import get_required_channels
        channels = await get_required_channels()
        await callback.message.answer(
            "⚠️ **Access Denied!**\n\n"
            "To browse movies, you must subscribe to our sponsor channels first.",
            reply_markup=get_join_channels_keyboard(channels)
        )
        await callback.answer()
        return
        
    page = int(callback.data.replace("movie_page_", ""))
    limit = 10
    offset = (page - 1) * limit
    
    movies = await get_all_movies(offset=offset, limit=limit)
    total_count = await get_movie_count()
    total_pages = (total_count + limit - 1) // limit
    
    await callback.message.edit_text(
        "🎬 **Movie Catalog**\n\nChoose a movie from the list:",
        reply_markup=get_movie_list_keyboard(movies, page, total_pages)
    )
    await callback.answer()

@callback_router.callback_query(F.data == "close_movies")
async def process_close_movies(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()
