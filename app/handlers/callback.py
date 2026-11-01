import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.database import (
    get_movie_by_code, get_all_movies, get_movie_count, get_setting,
    get_or_create_user, get_series_by_code, increment_series_search_count, get_vip_plans,
    get_combined_catalog, get_all_series, get_series_count, get_top_referrers, get_referral_count
)
from app.keyboards import (
    get_movie_list_keyboard, get_receipt_approval_keyboard,
    get_main_keyboard, get_join_channels_keyboard, get_user_vip_plans_keyboard,
    get_series_list_keyboard
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
        data = await state.get_data()
        pending_code = data.get("pending_movie_code")
        
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        
        if pending_code:
            user = await get_or_create_user(user_id, callback.from_user.username, callback.from_user.full_name)
            if pending_code >= 1000:
                series = await get_series_by_code(pending_code)
                if series:
                    if series.is_vip and not user.is_vip:
                        plans = await get_vip_plans()
                        await callback.message.answer(
                            "⚠️ **Ushbu serial faqat VIP foydalanuvchilar uchun!**\n\n"
                            "Ushbu serialni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:",
                            reply_markup=get_user_vip_plans_keyboard(plans)
                        )
                        await callback.message.delete()
                        await state.clear()
                        return
                    from app.handlers.user import send_series_to_user
                    await send_series_to_user(bot, callback.message.chat.id, series, bot_username, user=user)
                    await callback.message.delete()
                    await state.clear()
                    return
            else:
                movie = await get_movie_by_code(pending_code)
                if movie:
                    if movie.is_vip and not user.is_vip:
                        plans = await get_vip_plans()
                        await callback.message.answer(
                            "⚠️ **Ushbu kino faqat VIP foydalanuvchilar uchun!**\n\n"
                            "Ushbu kinoni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:",
                            reply_markup=get_user_vip_plans_keyboard(plans)
                        )
                        await callback.message.delete()
                        await state.clear()
                        return
                    from app.handlers.user import send_movie_to_user
                    await send_movie_to_user(bot, callback.message.chat.id, movie, bot_username, user=user)
                    await callback.message.delete()
                    await state.clear()
                    return
                
        await callback.message.edit_text(
            "🎉 A'zoligingiz tasdiqlandi! Botdan to'liq foydalanishingiz mumkin.",
            reply_markup=None
        )
        await callback.message.answer("Menyudan bo'limni tanlang:", reply_markup=get_main_keyboard())
        await state.clear()
    else:
        await callback.answer(
            "⚠️ Siz hali barcha majburiy kanallarga a'zo bo'lmadingiz. Iltimos, a'zo bo'ling va qayta urinib ko'ring.",
            show_alert=True
        )

@callback_router.callback_query(F.data.startswith("click_insta_"))
async def process_click_insta(callback: CallbackQuery):
    try:
        chan_id = int(callback.data.replace("click_insta_", ""))
        from app.database import get_required_channels, record_user_instagram_sub
        channels = await get_required_channels()
        target_chan = next((c for c in channels if c.id == chan_id), None)
        
        if target_chan:
            insta_user = getattr(target_chan, "target_username", None) or target_chan.name
            await record_user_instagram_sub(callback.from_user.id, insta_user)
            url = target_chan.invite_link.strip() if target_chan.invite_link else f"https://instagram.com/{insta_user.replace('@', '')}"
            if not (url.startswith("http://") or url.startswith("https://")):
                url = f"https://{url}"
                
            await callback.answer(url=url)
        else:
            await callback.answer("Kanal topilmadi.", show_alert=True)
    except Exception as e:
        logger.error(f"Error handling click_insta: {e}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)

@callback_router.callback_query(F.data.startswith("confirm_bot_"))
async def process_confirm_bot(callback: CallbackQuery):
    try:
        chan_id = int(callback.data.replace("confirm_bot_", ""))
        from app.database import get_required_channels, record_user_bot_start
        channels = await get_required_channels()
        target_chan = next((c for c in channels if c.id == chan_id), None)
        
        if target_chan:
            bot_user = getattr(target_chan, "target_username", None) or target_chan.name
            await record_user_bot_start(callback.from_user.id, bot_user)
            await callback.answer("✅ Botga kirganingiz tasdiqlandi! Endi '🔄 A'zolikni tekshirish' tugmasini bosing.", show_alert=True)
        else:
            await callback.answer("Bot topilmadi.", show_alert=True)
    except Exception as e:
        logger.error(f"Error handling confirm_bot: {e}")
        await callback.answer("Xatolik yuz berdi.", show_alert=True)

@callback_router.callback_query(F.data == "buy_vip")
async def process_buy_vip(callback: CallbackQuery):
    plans = await get_vip_plans()
    text = (
        "⭐ **VIP Obuna**\n\n"
        "VIP foydalanuvchilar homiy kanallarga a'zo bo'lishlari shart emas!\n\n"
        "Boshlash uchun quyidagi VIP obuna rejalaridan birini tanlang:"
    )
    await callback.message.edit_text(text, reply_markup=get_user_vip_plans_keyboard(plans))
    await callback.answer()

@callback_router.callback_query(F.data.startswith("vip_plan_"))
async def process_vip_plan_selection(callback: CallbackQuery, state: FSMContext):
    months = int(callback.data.replace("vip_plan_", ""))
    await state.update_data(selected_vip_months=months)
    await state.set_state(VIPState.waiting_for_receipt)
    
    text = (
        f"💳 **Reja: {months} Oylik**\n\n"
        f"💳 **Karta raqami:** `9860350142379998`\n"
        f"👤 **Karta egasi:** Shohruhxon\n\n"
        "To'lovni amalga oshirgach, **to'lov chekini** (rasm yoki hujjat shaklida) shu yerga yuboring.\n"
        "Administratorlar to'lovni tekshirib, VIP obunangizni faollashtirib berishadi."
    )
    await callback.message.edit_text(text)
    await callback.answer()

@callback_router.callback_query(F.data == "vip_back")
async def process_vip_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Menyudan bo'limni tanlang:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

# Message handler for VIP State: waiting for receipt
@callback_router.message(VIPState.waiting_for_receipt, F.photo | F.document)
async def process_vip_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    months = data.get("selected_vip_months", 1)
    
    await message.answer(
        "⏳ **To'lov cheki qabul qilindi!**\n\n"
        "To'lov chekingiz tekshirish uchun administratorlarga yuborildi. "
        "Obunangiz faollashtirilishi bilanoq sizga xabar yuboriladi."
    )
    
    for admin_id in ADMIN_IDS:
        try:
            caption = (
                f"💳 **Yangi VIP Obuna So'rovi**\n\n"
                f"👤 Foydalanuvchi: {message.from_user.full_name} (ID: `{message.from_user.id}`)\n"
                f"🏷️ Username: @{message.from_user.username or 'yoq'}\n"
                f"📅 Reja: {months} Oylik"
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
    
    code = int(callback.data.replace("view_movie_user_", ""))
    movie = await get_movie_by_code(code)
    if not movie:
        await callback.answer("❌ Kino topilmadi.", show_alert=True)
        return
        
    user = await get_or_create_user(user_id, callback.from_user.username, callback.from_user.full_name)
    if movie.is_vip and not user.is_vip:
        plans = await get_vip_plans()
        await callback.message.answer(
            "⚠️ **Ushbu kino faqat VIP foydalanuvchilar uchun!**\n\n"
            "Ushbu kinoni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:",
            reply_markup=get_user_vip_plans_keyboard(plans)
        )
        await callback.answer()
        return

    is_subscribed = await check_user_subscription(bot, user_id)
    if not user.is_vip and not is_subscribed:
        await state.update_data(pending_movie_code=code)
        from app.database import get_required_channels
        channels = await get_required_channels()
        await callback.message.answer(
            "⚠️ **Ruxsat berilmadi!**\n\n"
            "Ushbu kinoni ko'rish uchun avval homiy kanallarimizga a'zo bo'lishingiz kerak "
            "yoki barcha cheklovlarni chetlab o'tish uchun VIP obuna sotib oling.",
            reply_markup=get_join_channels_keyboard(channels)
        )
        await callback.answer()
        return
        
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    from app.handlers.user import send_movie_to_user
    try:
        await send_movie_to_user(bot, callback.message.chat.id, movie, bot_username)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Kinoni yuborishda xatolik: {e}", show_alert=True)

# --- USER SERIES CALLBACKS ---
@callback_router.callback_query(F.data.startswith("view_series_user_"))
async def process_view_series_user(callback: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = callback.from_user.id
    
    code = int(callback.data.replace("view_series_user_", ""))
    series = await get_series_by_code(code)
    if not series:
        await callback.answer("❌ Serial topilmadi.", show_alert=True)
        return
        
    user = await get_or_create_user(user_id, callback.from_user.username, callback.from_user.full_name)
    if series.is_vip and not user.is_vip:
        plans = await get_vip_plans()
        await callback.message.answer(
            "⚠️ **Ushbu serial faqat VIP foydalanuvchilar uchun!**\n\n"
            "Ushbu serialni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:",
            reply_markup=get_user_vip_plans_keyboard(plans)
        )
        await callback.answer()
        return

    is_subscribed = await check_user_subscription(bot, user_id)
    if not user.is_vip and not is_subscribed:
        await state.update_data(pending_movie_code=code)
        from app.database import get_required_channels
        channels = await get_required_channels()
        await callback.message.answer(
            "⚠️ **Ruxsat berilmadi!**\n\n"
            "Ushbu serialni ko'rish uchun avval homiy kanallarimizga a'zo bo'lishingiz kerak "
            "yoki barcha cheklovlarni chetlab o'tish uchun VIP obuna sotib oling.",
            reply_markup=get_join_channels_keyboard(channels)
        )
        await callback.answer()
        return
        
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    from app.handlers.user import send_series_to_user
    try:
        await send_series_to_user(bot, callback.message.chat.id, series, bot_username)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Serialni yuklashda xatolik: {e}", show_alert=True)

@callback_router.callback_query(F.data.startswith("view_episode_"))
async def process_view_episode(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    parts = callback.data.replace("view_episode_", "").split("_")
    series_code = int(parts[0])
    episode_number = int(parts[1])
    season_number = int(parts[2]) if len(parts) > 2 else 1
    
    series = await get_series_by_code(series_code)
    if not series:
        await callback.answer("❌ Serial topilmadi.", show_alert=True)
        return
        
    user = await get_or_create_user(user_id, callback.from_user.username, callback.from_user.full_name)
    if series.is_vip and not user.is_vip:
        plans = await get_vip_plans()
        await callback.message.answer("⚠️ **Ushbu serial faqat VIP foydalanuvchilar uchun!**", reply_markup=get_user_vip_plans_keyboard(plans))
        await callback.answer()
        return

    is_subscribed = await check_user_subscription(bot, user_id)
    if not user.is_vip and not is_subscribed:
        await callback.answer("⚠️ Avval homiy kanallarga a'zo bo'ling!", show_alert=True)
        return
        
    episode = None
    for ep in series.episodes:
        if ep.episode_number == episode_number and (ep.season_number or 1) == season_number:
            episode = ep
            break
            
    if not episode:
        await callback.answer("❌ Ushbu qism topilmadi.", show_alert=True)
        return
        
    await callback.answer(f"{episode_number}-qism yuborilmoqda...")
    
    try:
        await increment_series_search_count(series_code)
        caption = f"📺 {series.title} | {season_number}-fasl, {episode_number}-qism" if len(parts) > 2 else f"📺 {series.title} | {episode_number}-qism"
        await bot.copy_message(
            chat_id=callback.message.chat.id,
            from_chat_id=episode.channel_id,
            message_id=episode.message_id,
            caption=caption
        )
    except Exception as e:
        logger.error(f"Error copying episode: {e}")
        await callback.message.answer(f"❌ Qismni yuborishda xatolik yuz berdi: {e}")

@callback_router.callback_query(F.data.startswith("view_season_"))
async def process_view_season(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    parts = callback.data.replace("view_season_", "").split("_")
    series_code = int(parts[0])
    season_number = int(parts[1])
    
    series = await get_series_by_code(series_code)
    if not series:
        await callback.answer("❌ Serial topilmadi.", show_alert=True)
        return
        
    user = await get_or_create_user(user_id, callback.from_user.username, callback.from_user.full_name)
    if series.is_vip and not user.is_vip:
        plans = await get_vip_plans()
        await callback.message.answer("⚠️ **Ushbu serial faqat VIP foydalanuvchilar uchun!**", reply_markup=get_user_vip_plans_keyboard(plans))
        await callback.answer()
        return

    is_subscribed = await check_user_subscription(bot, user_id)
    if not user.is_vip and not is_subscribed:
        await callback.answer("⚠️ Avval homiy kanallarga a'zo bo'ling!", show_alert=True)
        return
        
    season_episodes = [ep for ep in series.episodes if (ep.season_number or 1) == season_number]
    season_episodes.sort(key=lambda x: x.episode_number)
    
    from app.keyboards import get_series_season_episodes_keyboard
    await callback.message.edit_text(
        f"📺 **{series.title} | {season_number}-fasl qismlari**\n\nQismni tanlang:",
        reply_markup=get_series_season_episodes_keyboard(series_code, season_number, season_episodes)
    )
    await callback.answer()

@callback_router.callback_query(F.data == "noop")
async def process_noop(callback: CallbackQuery):
    await callback.answer()

@callback_router.callback_query(F.data.startswith("movie_page_"))
async def process_movie_page(callback: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(bot, user_id)
    
    if not is_subscribed:
        from app.database import get_required_channels
        channels = await get_required_channels()
        await callback.message.answer(
            "⚠️ **Ruxsat berilmadi!**\n\n"
            "Kinolar ro'yxatini ko'rish uchun avval homiy kanallarimizga a'zo bo'lishingiz kerak.",
            reply_markup=get_join_channels_keyboard(channels)
        )
        await callback.answer()
        return
        
    page = int(callback.data.replace("movie_page_", ""))
    limit = 10
    offset = (page - 1) * limit
    
    items, total_count = await get_combined_catalog(offset=offset, limit=limit)
    total_pages = (total_count + limit - 1) // limit
    
    await callback.message.edit_text(
        f"🎬 **Kinolar Katalogi ({page}/{max(1, total_pages)}-sahifa)**\n\nRo'yxatdan tanlang:",
        reply_markup=get_movie_list_keyboard(items, page, total_pages)
    )
    await callback.answer()

@callback_router.callback_query(F.data.startswith("series_page_"))
async def process_series_page(callback: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(bot, user_id)
    
    if not is_subscribed:
        from app.database import get_required_channels
        channels = await get_required_channels()
        await callback.message.answer(
            "⚠️ **Ruxsat berilmadi!**\n\n"
            "Seriallar ro'yxatini ko'rish uchun avval homiy kanallarimizga a'zo bo'lishingiz kerak.",
            reply_markup=get_join_channels_keyboard(channels)
        )
        await callback.answer()
        return
        
    page = int(callback.data.replace("series_page_", ""))
    limit = 10
    offset = (page - 1) * limit
    
    items = await get_all_series(offset=offset, limit=limit)
    total_count = await get_series_count()
    total_pages = (total_count + limit - 1) // limit
    
    await callback.message.edit_text(
        f"📺 **Seriallar Katalogi ({page}/{max(1, total_pages)}-sahifa)**\n\nRo'yxatdan tanlang:",
        reply_markup=get_series_list_keyboard(items, page, total_pages)
    )
    await callback.answer()

@callback_router.callback_query(F.data == "close_movies")
async def process_close_movies(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()
