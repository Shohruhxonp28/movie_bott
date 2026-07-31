import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from app.database import (
    get_or_create_user, get_movie_by_code, get_all_movies, get_movie_count,
    get_setting, search_movies_db, increment_search_count,
    get_series_by_code, search_series_db, increment_series_search_count
)
from app.keyboards import (
    get_main_keyboard, get_join_channels_keyboard, get_vip_plans_keyboard,
    get_share_keyboard, get_movie_list_keyboard, get_share_series_keyboard,
    get_series_episodes_keyboard, get_series_link_keyboard
)
from app.utils import check_user_subscription, search_items_fuzzy

logger = logging.getLogger(__name__)
user_router = Router()

async def send_movie_to_user(bot: Bot, chat_id: int, movie, bot_username: str):
    """Utility to send movie to user using copyMessage and increment search counter."""
    caption = (
        f"🎬 Kino: {movie.title}\n\n"
        f"🆔 Kodi: {movie.movie_code}"
    )
    await increment_search_count(movie.movie_code)
    
    await bot.copy_message(
        chat_id=chat_id,
        from_chat_id=movie.channel_id,
        message_id=movie.message_id,
        caption=caption,
        reply_markup=get_share_keyboard(bot_username, movie.movie_code)
    )

async def send_series_to_user(bot: Bot, chat_id: int, series, bot_username: str):
    """Utility to display series details to user."""
    await increment_series_search_count(series.series_code)
    
    text = (
        f"📺 Serial: {series.title}\n\n"
        f"🆔 Kodi: {series.series_code}\n\n"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    if series.channel_link:
        text += "🍿 Ushbu serialni ko'rish uchun quyidagi havola orqali kanalga o'ting:"
        # Add link button
        url = series.channel_link.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"https://t.me/{url.replace('@', '')}"
        builder.button(text="🍿 Serialni ko'rish (Kanal)", url=url)
    else:
        text += "🍿 Qismni tanlab tomosha qiling:"
        # Add episodes grid
        for i in range(1, series.episodes_count + 1):
            builder.button(text=f"{i}-qism", callback_data=f"view_episode_{series.series_code}_{i}")
        builder.adjust(4)
        
    # Append share button
    share_url = f"https://t.me/{bot_username}?start=movie_{series.series_code}"
    builder.row(InlineKeyboardButton(text="📤 Ulashish", url=f"https://t.me/share/url?url={share_url}"))
    
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=builder.as_markup()
    )

async def check_and_prompt_subscription(message: Message, bot: Bot, state: FSMContext, pending_movie_code: int = None) -> bool:
    """
    Checks subscription and sends prompt if not subscribed.
    Saves pending movie code in state to send after subscription is verified.
    """
    is_subscribed = await check_user_subscription(bot, message.from_user.id)
    if is_subscribed:
        return True
        
    # Not subscribed. Save pending code if any
    if pending_movie_code:
        await state.update_data(pending_movie_code=pending_movie_code)
        
    from app.database import get_required_channels
    channels = await get_required_channels()
    
    await message.answer(
        "⚠️ **Ruxsat berilmadi!**\n\n"
        "Botdan foydalanish uchun homiy kanallarimizga a'zo bo'lishingiz kerak "
        "yoki barcha cheklovlarni chetlab o'tish uchun VIP obuna sotib oling.",
        reply_markup=get_join_channels_keyboard(channels)
    )
    return False

@user_router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    # Save user to DB
    user = await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    # Check if there is a deep link start parameter (e.g., movie_125)
    args = command.args
    pending_code = None
    if args and args.startswith("movie_"):
        code_str = args.replace("movie_", "")
        if code_str.isdigit():
            pending_code = int(code_str)

    # If deep link requested, check subscription
    if pending_code:
        is_subbed = await check_and_prompt_subscription(message, bot, state, pending_code)
        if is_subbed:
            if pending_code >= 1000:
                series = await get_series_by_code(pending_code)
                if series:
                    await send_series_to_user(bot, message.chat.id, series, bot_username)
                else:
                    await message.answer("Serial topilmadi.")
            else:
                movie = await get_movie_by_code(pending_code)
                if movie:
                    await send_movie_to_user(bot, message.chat.id, movie, bot_username)
                else:
                    await message.answer("Kino topilmadi.")
        return
        
    # Normal start flow
    is_subbed = await check_user_subscription(bot, message.from_user.id)
    if is_subbed:
        await message.answer(
            f"👋 Salom {message.from_user.full_name}!\n"
            "Kinobotga xush kelibsiz. Kino yoki serial kodini yuboring yoki nomi bo'yicha qidiring.",
            reply_markup=get_main_keyboard()
        )
    else:
        await check_and_prompt_subscription(message, bot, state)

# --- REPLY KEYBOARD ACTIONS ---
@user_router.message(F.text == "🎬 Kinolar")
async def show_movies_menu(message: Message, bot: Bot, state: FSMContext):
    is_subbed = await check_and_prompt_subscription(message, bot, state)
    if not is_subbed:
        return
        
    limit = 10
    movies = await get_all_movies(offset=0, limit=limit)
    total_count = await get_movie_count()
    total_pages = (total_count + limit - 1) // limit
    
    if not movies:
        await message.answer("Hozircha kinolar va seriallar mavjud emas.")
        return
        
    await message.answer(
        "🎬 **Kinolar Katalogi**\n\nRo'yxatdan kinoni tanlang:",
        reply_markup=get_movie_list_keyboard(movies, 1, total_pages)
    )

@user_router.message(F.text == "⭐ VIP")
async def show_vip_menu(message: Message, bot: Bot, state: FSMContext):
    # Retrieve user information
    user = await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    if user.is_vip:
        await message.answer(
            f"⭐ **Siz VIP foydalanuvchisiz!**\n\n"
            f"VIP obuna muddati: {user.vip_until.strftime('%Y-%m-%d %H:%M:%S')} UTC gacha\n"
            "Siz homiy kanallarga a'zo bo'lmasdan botdan to'liq foydalana olasiz."
        )
        return
        
    card = await get_setting("bank_card", "Sozlanmagan")
    text = (
        "⭐ **VIP Obuna**\n\n"
        "VIP foydalanuvchilar homiy kanallarga a'zo bo'lishlari shart emas!\n\n"
        "💳 **To'lov ma'lumotlari (Bank Kartasi):**\n"
        f"`{card}`\n\n"
        "Boshlash uchun quyidagi VIP obuna rejalaridan birini tanlang:"
    )
    await message.answer(text, reply_markup=get_vip_plans_keyboard())

@user_router.message(F.text == "ℹ️ Yordam")
async def show_help_menu(message: Message):
    text = (
        "ℹ️ **Botdan foydalanish bo'yicha yo'riqnoma**\n\n"
        "1. **Kod orqali**: Shunchaki kino yoki serial kodini yuboring (masalan, `125` yoki `1000`) va bot uni darhol yuboradi.\n"
        "2. **Nomi orqali**: Nomi bo'yicha qidiring (masalan, `Avatar` yoki `Titanik`). Bot eng yaqin mos keladigan kinolar va seriallarni topadi.\n"
        "3. **VIP Kirish**: Homiy kanallarga a'zo bo'lmaslik uchun VIP obunani sotib oling.\n"
        "4. **Katalog**: Barcha kinolarni sahifalab ko'rish uchun '🎬 Kinolar' bo'limiga bosing."
    )
    await message.answer(text, reply_markup=get_main_keyboard())

# --- DYNAMIC TEXT SEARCH (CODE OR FUZZY TITLE) ---
@user_router.message(F.text)
async def process_search(message: Message, bot: Bot, state: FSMContext):
    is_subbed = await check_and_prompt_subscription(message, bot, state)
    if not is_subbed:
        return
        
    query = message.text.strip()
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    # 1. Code Search (Digits only)
    if query.isdigit():
        code = int(query)
        if code >= 1000:
            series = await get_series_by_code(code)
            if series:
                await send_series_to_user(bot, message.chat.id, series, bot_username)
            else:
                await message.answer("Serial topilmadi.")
        else:
            movie = await get_movie_by_code(code)
            if movie:
                await send_movie_to_user(bot, message.chat.id, movie, bot_username)
            else:
                await message.answer("Kino topilmadi.")
        return
        
    # 2. Title Search (Fuzzy Match Movies and Series combined)
    movies = await search_movies_db()
    series_list = await search_series_db()
    
    # Combine items
    combined_items = list(movies) + list(series_list)
    matches = search_items_fuzzy(query, combined_items)
    
    if not matches:
        await message.answer("Kino yoki serial topilmadi.")
        return
        
    if len(matches) == 1:
        match = matches[0]
        from app.models import Movie as MovieModel
        if isinstance(match, MovieModel):
            await send_movie_to_user(bot, message.chat.id, match, bot_username)
        else:
            await send_series_to_user(bot, message.chat.id, match, bot_username)
    else:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for item in matches:
            from app.models import Movie as MovieModel
            if isinstance(item, MovieModel):
                builder.row(
                    InlineKeyboardButton(
                        text=f"🎬 {item.title} [{item.movie_code}]",
                        callback_data=f"view_movie_user_{item.movie_code}"
                    )
                )
            else:
                builder.row(
                    InlineKeyboardButton(
                        text=f"📺 {item.title} [{item.series_code}]",
                        callback_data=f"view_series_user_{item.series_code}"
                    )
                )
        await message.answer("Bir nechta mos keladigan natijalar topildi. Tanlang:", reply_markup=builder.as_markup())
