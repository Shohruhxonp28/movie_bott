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
        f"🎬 Movie: {movie.title}\n\n"
        f"🆔 Code: {movie.movie_code}"
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
        "⚠️ **Access Denied!**\n\n"
        "To use this bot, you must subscribe to our sponsor channels first, "
        "or buy a VIP subscription to bypass all restrictions.",
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
                await message.answer("Movie not found.")
        return
        
    # Normal start flow
    is_subbed = await check_user_subscription(bot, message.from_user.id)
    if is_subbed:
        await message.answer(
            f"👋 Hello {message.from_user.full_name}!\n"
            "Welcome to the Movie Bot. You can send a movie code or search by title.",
            reply_markup=get_main_keyboard()
        )
    else:
        await check_and_prompt_subscription(message, bot, state)

# --- REPLY KEYBOARD ACTIONS ---
@user_router.message(F.text == "🎬 Movies")
async def show_movies_menu(message: Message, bot: Bot, state: FSMContext):
    is_subbed = await check_and_prompt_subscription(message, bot, state)
    if not is_subbed:
        return
        
    limit = 10
    movies = await get_all_movies(offset=0, limit=limit)
    total_count = await get_movie_count()
    total_pages = (total_count + limit - 1) // limit
    
    if not movies:
        await message.answer("No movies available at the moment.")
        return
        
    await message.answer(
        "🎬 **Movie Catalog**\n\nChoose a movie from the list:",
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
            f"⭐ **You are a VIP User!**\n\n"
            f"Subscription expires on: {user.vip_until.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            "You have complete access to the bot without any channel requirements."
        )
        return
        
    card = await get_setting("bank_card", "Not configured")
    text = (
        "⭐ **VIP Subscription**\n\n"
        "VIP users bypass all sponsor channel subscription requirements!\n\n"
        "💳 **Payment details (Bank Card):**\n"
        f"`{card}`\n\n"
        "Select a subscription plan below to get started:"
    )
    await message.answer(text, reply_markup=get_vip_plans_keyboard())

@user_router.message(F.text == "ℹ️ Help")
async def show_help_menu(message: Message):
    text = (
        "ℹ️ **How to Use the Movie Bot**\n\n"
        "1. **By Code**: Simply send the movie code (e.g., `125`) and the bot will send the movie file instantly.\n"
        "2. **By Title**: Send a spelling-tolerant movie name (e.g., `Avatar` or `Awater`). The bot will find the closest matches.\n"
        "3. **VIP Access**: Buy a VIP subscription to bypass all required sponsor channels.\n"
        "4. **Catalog**: Click on '🎬 Movies' to browse all movies page by page."
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
            await message.answer("Movie not found.")
        return
        
    # 2. Movie Title Search (Fuzzy Match using RapidFuzz)
    movies = await search_movies_db()
    matches = search_movies_fuzzy(query, movies)
    
    if not matches:
        await message.answer("Movie not found.")
        return
        
    # If exactly one high quality match or short list, let the user choose
    # (To be safe, we can display them as inline buttons as requested: "If multiple movies match, display them as inline buttons")
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
        await message.answer("Multiple matches found. Select a movie:", reply_markup=builder.as_markup())
