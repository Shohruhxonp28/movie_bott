import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from app.database import (
    get_or_create_user, get_movie_by_code, get_all_movies, get_movie_count,
    get_setting, search_movies_db, increment_search_count
)
from app.keyboards import (
    get_main_keyboard, get_join_channels_keyboard, get_vip_plans_keyboard,
    get_share_keyboard, get_movie_list_keyboard
)
from app.utils import check_user_subscription, search_movies_fuzzy

logger = logging.getLogger(__name__)
user_router = Router()

async def send_movie_to_user(bot: Bot, chat_id: int, movie, bot_username: str):
    """Utility to send movie to user using copyMessage and increment search counter."""
    caption = (
        f"🎬 Kino: {movie.title}\n\n"
        f"🆔 Kodi: {movie.movie_code}"
    )
    # Increment search count
    await increment_search_count(movie.movie_code)
    
    # Copy message
    await bot.copy_message(
        chat_id=chat_id,
        from_chat_id=movie.channel_id,
        message_id=movie.message_id,
        caption=caption,
        reply_markup=get_share_keyboard(bot_username, movie.movie_code)
    )

async def check_and_prompt_subscription(message: Message, bot: Bot, state: FSMContext, pending_movie_code: int = None) -> bool:
    """
    Checks subscription and sends prompt if not subscribed.
    Saves pending movie code in state to send after subscription is verified.
    """
    is_subscribed = await check_user_subscription(bot, message.from_user.id)
    if is_subscribed:
        return True
        
    # Not subscribed. Save pending movie if any
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
            "Kinobotga xush kelibsiz. Kino kodini yuboring yoki nomi bo'yicha qidiring.",
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
        await message.answer("Hozircha kinolar mavjud emas.")
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
        "1. **Kod orqali**: Shunchaki kino kodini yuboring (masalan, `125`) va bot kinoni darhol yuboradi.\n"
        "2. **Nomi orqali**: Kino nomini xatolar bilan bo'lsa ham yuboring (masalan, `Avatar` yoki `Awater`). Bot eng yaqin mos keladigan kinolarni topadi.\n"
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
    
    # 1. Check if query is only digits (Movie Code Search)
    if query.isdigit():
        code = int(query)
        movie = await get_movie_by_code(code)
        if movie:
            await send_movie_to_user(bot, message.chat.id, movie, bot_username)
        else:
            await message.answer("Kino topilmadi.")
        return
        
    # 2. Movie Title Search (Fuzzy Match using RapidFuzz)
    movies = await search_movies_db()
    matches = search_movies_fuzzy(query, movies)
    
    if not matches:
        await message.answer("Kino topilmadi.")
        return
        
    # If exactly one high quality match or short list, let the user choose
    if len(matches) == 1:
        await send_movie_to_user(bot, message.chat.id, matches[0], bot_username)
    else:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for movie in matches:
            builder.row(
                InlineKeyboardButton(
                    text=f"🎬 {movie.title} [{movie.movie_code}]",
                    callback_data=f"view_movie_user_{movie.movie_code}"
                )
            )
        await message.answer("Bir nechta mos keladigan kinolar topildi. Kinoni tanlang:", reply_markup=builder.as_markup())
