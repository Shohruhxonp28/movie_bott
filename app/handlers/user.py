import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardButton, ChatJoinRequest, ChatMemberUpdated
from aiogram.filters import Command, CommandObject, IS_MEMBER, IS_NOT_MEMBER, chat_member_updated
from aiogram.fsm.context import FSMContext
from app.config import ADMIN_IDS
from app.database import (
    get_or_create_user, get_movie_by_code, get_all_movies, get_movie_count,
    get_setting, search_movies_db, increment_search_count, get_user,
    get_series_by_code, search_series_db, increment_series_search_count, get_vip_plans,
    get_combined_catalog, increment_daily_search, get_all_series, get_series_count,
    add_join_request, set_user_inactive, add_referral, get_referral_count, add_vip_days
)
from app.keyboards import (
    get_main_keyboard, get_join_channels_keyboard,
    get_movie_list_keyboard, get_share_keyboard,
    get_user_vip_plans_keyboard, get_referral_keyboard, get_profile_keyboard, get_series_seasons_keyboard,
    get_series_season_episodes_keyboard, get_series_list_keyboard
)
from app.utils import check_user_subscription, search_items_fuzzy

logger = logging.getLogger(__name__)
user_router = Router()

@user_router.chat_join_request()
async def handle_join_request(update: ChatJoinRequest, bot: Bot):
    await add_join_request(update.from_user.id, update.chat.id)

@user_router.my_chat_member()
async def handle_my_chat_member(update: ChatMemberUpdated):
    if update.new_chat_member.status in ["kicked", "left"]:
        await set_user_inactive(update.from_user.id)

async def send_movie_to_user(bot: Bot, chat_id: int, movie, bot_username: str, user=None):
    """Utility to send movie to user using copyMessage and increment search counter."""
    if user is None:
        user = await get_user(chat_id)
        
    if movie.is_vip and (not user or not user.is_vip):
        plans = await get_vip_plans()
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ **Ushbu kino faqat VIP foydalanuvchilar uchun!**\n\nUshbu kinoni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:",
            reply_markup=get_user_vip_plans_keyboard(plans)
        )
        return

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

async def send_series_to_user(bot: Bot, chat_id: int, series, bot_username: str, user=None):
    """Utility to display series details to user."""
    if user is None:
        user = await get_user(chat_id)
        
    if series.is_vip and (not user or not user.is_vip):
        plans = await get_vip_plans()
        await bot.send_message(
            chat_id=chat_id,
            text="⚠️ **Ushbu serial faqat VIP foydalanuvchilar uchun!**\n\nUshbu serialni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:",
            reply_markup=get_user_vip_plans_keyboard(plans)
        )
        return

    await increment_series_search_count(series.series_code)
    
    text = (
        f"📺 Serial: {series.title}\n\n"
        f"🆔 Kodi: {series.series_code}\n\n"
    )
    
    if series.channel_link:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        text += "🍿 Ushbu serialni ko'rish uchun quyidagi havola orqali kanalga o'ting:"
        url = series.channel_link.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"https://t.me/{url.replace('@', '')}"
        builder.button(text="🍿 Serialni ko'rish (Kanal)", url=url)
        share_url = f"https://t.me/{bot_username}?start=movie_{series.series_code}"
        builder.row(InlineKeyboardButton(text="📤 Ulashish", url=f"https://t.me/share/url?url={share_url}"))
        reply_markup = builder.as_markup()
    else:
        # Group by season
        seasons = sorted(list(set([ep.season_number or 1 for ep in series.episodes])))
        if not seasons:
            seasons = [1]
        
        if len(seasons) > 1:
            text += "🍿 Faslni tanlab tomosha qiling:"
            reply_markup = get_series_seasons_keyboard(series.series_code, seasons)
        else:
            text += "🍿 Qismni tanlab tomosha qiling:"
            season_num = seasons[0]
            season_episodes = [ep for ep in series.episodes if (ep.season_number or 1) == season_num]
            season_episodes.sort(key=lambda x: x.episode_number)
            reply_markup = get_series_season_episodes_keyboard(series.series_code, season_num, season_episodes)
            
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup
    )

async def check_and_prompt_subscription(message: Message, bot: Bot, state: FSMContext, pending_movie_code: int = None) -> bool:
    """
    Checks subscription and sends prompt if not subscribed.
    Saves pending movie code in state to send after subscription is verified.
    """
    user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    if user.is_vip:
        return True

    is_subscribed = await check_user_subscription(bot, message.from_user.id)
    if is_subscribed:
        return True
        
    if pending_movie_code:
        await state.update_data(pending_movie_code=pending_movie_code)
        
    from app.database import get_required_channels
    channels = await get_required_channels()
    
    await message.answer(
        "⚠️ **Ruxsat berilmadi!**\n\n"
        "Botdan foydalanish uchun homiy kanallarimizga a'zo bo'lishingiz kerak "
        "yoki barcha cheklovlarni chetlab o'tish uchun VIP obuna sotib oling.",
        reply_markup=get_join_channels_keyboard(channels, message.from_user.id)
    )
    return False

@user_router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    # Check if the user exists in DB before creating them (to notify admin of new users)
    existing_user = await get_user(message.from_user.id)
    
    user = await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    # Notify admins if new user registered
    if not existing_user:
        for admin_id in ADMIN_IDS:
            try:
                username_str = f" (@{message.from_user.username})" if message.from_user.username else ""
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"👥 **Yangi foydalanuvchi qo'shildi!**\n\n"
                         f"👤 Ismi: {message.from_user.full_name}\n"
                         f"🆔 ID: `{message.from_user.id}`{username_str}"
                )
            except Exception as e:
                logger.error(f"Failed to send registration alert to admin {admin_id}: {e}")
                
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    args = command.args
    pending_code = None
    if args:
        if args.startswith("movie_"):
            code_str = args.replace("movie_", "")
            if code_str.isdigit():
                pending_code = int(code_str)
        elif args.startswith("botstart_") or args.startswith("bot_"):
            target_bot_user = args.split("_", 1)[1]
            if target_bot_user:
                from app.database import record_user_bot_start
                await record_user_bot_start(message.from_user.id, target_bot_user)
        elif args.startswith("ref_") or (args.startswith("ref") and args[3:].isdigit()):
            ref_str = args.replace("ref_", "").replace("ref", "")
            if ref_str.isdigit():
                referrer_id = int(ref_str)
                if not existing_user and referrer_id != message.from_user.id:
                    added = await add_referral(referrer_id, message.from_user.id)
                    if added:
                        try:
                            ref_count = await get_referral_count(referrer_id)
                            target_str = await get_setting("referral_target", "5")
                            target = int(target_str) if target_str.isdigit() else 5
                            days_str = await get_setting("referral_reward_days", "3")
                            reward_days = int(days_str) if days_str.isdigit() else 3
                            
                            user_mention = message.from_user.full_name
                            notify_text = (
                                f"🎉 **Yangi do'stingiz qo'shildi!**\n\n"
                                f"👤 **{user_mention}** sizning taklif havolangiz orqali botga kirdi.\n"
                                f"👥 Jami taklif qilgan do'stlaringiz: **{ref_count} ta**"
                            )
                            
                            if target > 0 and ref_count % target == 0:
                                await add_vip_days(referrer_id, reward_days)
                                notify_text += (
                                    f"\n\n🎁 **TABRIKLAYMIZ!** Siz {ref_count} ta do'stingizni taklif qilganingiz uchun "
                                    f"**{reward_days} kunlik bepul VIP** obunaga ega bo'ldingiz! ⭐"
                                )
                                
                            await bot.send_message(chat_id=referrer_id, text=notify_text)
                        except Exception as e:
                            logger.error(f"Error notifying referrer {referrer_id}: {e}")

    if pending_code:
        is_subbed = await check_and_prompt_subscription(message, bot, state, pending_code)
        if is_subbed:
            if pending_code >= 1000:
                series = await get_series_by_code(pending_code)
                if series:
                    if series.is_vip and not user.is_vip:
                        plans = await get_vip_plans()
                        await message.answer("⚠️ **Ushbu serial faqat VIP foydalanuvchilar uchun!**\n\nUshbu serialni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:", reply_markup=get_user_vip_plans_keyboard(plans))
                        return
                    await send_series_to_user(bot, message.chat.id, series, bot_username)
                else:
                    await message.answer("Serial topilmadi.")
            else:
                movie = await get_movie_by_code(pending_code)
                if movie:
                    if movie.is_vip and not user.is_vip:
                        plans = await get_vip_plans()
                        await message.answer("⚠️ **Ushbu kino faqat VIP foydalanuvchilar uchun!**\n\nUshbu kinoni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:", reply_markup=get_user_vip_plans_keyboard(plans))
                        return
                    await send_movie_to_user(bot, message.chat.id, movie, bot_username)
                else:
                    await message.answer("Kino topilmadi.")
        return
        
    is_subbed = await check_user_subscription(bot, message.from_user.id)
    if is_subbed:
        start_tpl = await get_setting(
            "start_message",
            "Salom {full_name}!\nKinobotga xush kelibsiz. Kino yoki serial kodini yuboring yoki nomi bo'yicha qidiring."
        )
        msg_text = start_tpl.replace("{full_name}", message.from_user.full_name)
        await message.answer(msg_text, reply_markup=get_main_keyboard())
    else:
        await check_and_prompt_subscription(message, bot, state)

# --- REPLY KEYBOARD ACTIONS ---
@user_router.message(F.text == "🎬 Kinolar")
async def show_movies_menu(message: Message, bot: Bot, state: FSMContext):
    is_subbed = await check_and_prompt_subscription(message, bot, state)
    if not is_subbed:
        return
        
    limit = 10
    items, total_count = await get_combined_catalog(offset=0, limit=limit)
    total_pages = (total_count + limit - 1) // limit
    
    if not items:
        await message.answer("Hozircha kinolar va seriallar mavjud emas.")
        return
        
    await message.answer(
        f"🎬 **Kinolar Katalogi (1/{max(1, total_pages)}-sahifa)**\n\nRo'yxatdan tanlang:",
        reply_markup=get_movie_list_keyboard(items, 1, total_pages)
    )

@user_router.message(F.text == "📺 Seriallar")
async def show_series_menu(message: Message, bot: Bot, state: FSMContext):
    is_subbed = await check_and_prompt_subscription(message, bot, state)
    if not is_subbed:
        return
        
    limit = 10
    items = await get_all_series(offset=0, limit=limit)
    total_count = await get_series_count()
    total_pages = (total_count + limit - 1) // limit
    
    if not items:
        await message.answer("Hozircha seriallar mavjud emas.")
        return
        
    await message.answer(
        f"📺 **Seriallar Katalogi (1/{max(1, total_pages)}-sahifa)**\n\nRo'yxatdan tanlang:",
        reply_markup=get_series_list_keyboard(items, 1, total_pages)
    )

@user_router.message(F.text == "⭐ VIP")
async def show_vip_menu(message: Message, bot: Bot, state: FSMContext):
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
        
    plans = await get_vip_plans()
    vip_msg = await get_setting(
        "vip_message",
        "⭐ **VIP Obuna**\n\nVIP foydalanuvchilar homiy kanallarga a'zo bo'lishlari shart emas!\n\nBoshlash uchun quyidagi VIP obuna rejalaridan birini tanlang:"
    )
    await message.answer(vip_msg, reply_markup=get_user_vip_plans_keyboard(plans))

@user_router.message(F.text == "ℹ️ Yordam")
async def show_help_menu(message: Message):
    help_text = await get_setting(
        "help_message",
        "ℹ️ Botdan foydalanish bo'yicha yo'riqnoma\n\n1. Kod orqali (masalan - 7 yoki 13)\n2. Nomi orqali ( Avatar, Titanik)\n3. Vip - hech qanaqa kanallarga obuna bolmasadan film tomosha qilish va qo\n4. Katalog - Barcha kinolarni sahifalab ko'rish uchun '🎬 Kinolar' bo'limiga bosing.\n\nReklama va takliflar uchun @Kinotimeadmin"
    )
    await message.answer(help_text, reply_markup=get_main_keyboard())

# --- DYNAMIC TEXT SEARCH (CODE OR FUZZY TITLE) ---
@user_router.message(F.text)
async def process_search(message: Message, bot: Bot, state: FSMContext):
    is_subbed = await check_and_prompt_subscription(message, bot, state)
    if not is_subbed:
        return
        
    await increment_daily_search()
        
    query = message.text.strip()
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    if query.isdigit():
        code = int(query)
        user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
        if code >= 1000:
            series = await get_series_by_code(code)
            if series:
                if series.is_vip and not user.is_vip:
                    plans = await get_vip_plans()
                    await message.answer("⚠️ **Ushbu serial faqat VIP foydalanuvchilar uchun!**\n\nUshbu serialni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:", reply_markup=get_user_vip_plans_keyboard(plans))
                    return
                await send_series_to_user(bot, message.chat.id, series, bot_username)
            else:
                await message.answer("Serial topilmadi.")
        else:
            movie = await get_movie_by_code(code)
            if movie:
                if movie.is_vip and not user.is_vip:
                    plans = await get_vip_plans()
                    await message.answer("⚠️ **Ushbu kino faqat VIP foydalanuvchilar uchun!**\n\nUshbu kinoni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:", reply_markup=get_user_vip_plans_keyboard(plans))
                    return
                await send_movie_to_user(bot, message.chat.id, movie, bot_username)
            else:
                await message.answer("Kino topilmadi.")
        return
        
    movies = await search_movies_db()
    series_list = await search_series_db()
    
    combined_items = list(movies) + list(series_list)
    matches = search_items_fuzzy(query, combined_items)
    
    if not matches:
        await message.answer("Kino yoki serial topilmadi.")
        return
        
    user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    if len(matches) == 1:
        match = matches[0]
        from app.models import Movie as MovieModel
        if isinstance(match, MovieModel):
            if match.is_vip and not user.is_vip:
                plans = await get_vip_plans()
                await message.answer("⚠️ **Ushbu kino faqat VIP foydalanuvchilar uchun!**\n\nUshbu kinoni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:", reply_markup=get_user_vip_plans_keyboard(plans))
                return
            await send_movie_to_user(bot, message.chat.id, match, bot_username)
        else:
            if match.is_vip and not user.is_vip:
                plans = await get_vip_plans()
                await message.answer("⚠️ **Ushbu serial faqat VIP foydalanuvchilar uchun!**\n\nUshbu serialni ko'rish uchun VIP obuna bo'lishingiz zarur. Rejalardan birini tanlang:", reply_markup=get_user_vip_plans_keyboard(plans))
                return
            await send_series_to_user(bot, message.chat.id, match, bot_username)
    else:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        for item in matches:
            from app.models import Movie as MovieModel
            is_vip_badge = " ⭐" if item.is_vip else ""
            if isinstance(item, MovieModel):
                builder.row(
                    InlineKeyboardButton(
                        text=f"🎬 {item.title}{is_vip_badge} [{item.movie_code}]",
                        callback_data=f"view_movie_user_{item.movie_code}"
                    )
                )
            else:
                builder.row(
                    InlineKeyboardButton(
                        text=f"📺 {item.title}{is_vip_badge} [{item.series_code}]",
                        callback_data=f"view_series_user_{item.series_code}"
                    )
                )
        await message.answer("Bir nechta mos keladigan natijalar topildi. Tanlang:", reply_markup=builder.as_markup())

@user_router.message(F.text == "👥 Referal")
async def show_referral_menu(message: Message, bot: Bot, state: FSMContext):
    is_subbed = await check_and_prompt_subscription(message, bot, state)
    if not is_subbed:
        return
        
    user_id = message.from_user.id
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    count = await get_referral_count(user_id)
    target_str = await get_setting("referral_target", "5")
    target = int(target_str) if target_str.isdigit() else 5
    days_str = await get_setting("referral_reward_days", "3")
    days = int(days_str) if days_str.isdigit() else 3
    
    text = (
        "🎁 **Do'stlarni taklif qiling va bepul VIP oling!**\n\n"
        f"🔗 **Sizning referal havolangiz:**\n`{ref_link}`\n\n"
        f"👥 Taklif qilgan do'stlaringiz soni: **{count} ta**\n"
        f"⭐ Har **{target} ta** yangi do'stingiz uchun **{days} kunlik bepul VIP** obunaga ega bo'lasiz!\n\n"
        "Havolangizni do'stlaringizga yoki kanallarga ulashing 👇"
    )
    
    await message.answer(
        text,
        reply_markup=get_referral_keyboard(bot_username, user_id)
    )

@user_router.message(F.text == "👤 Profil")
async def show_profile_menu(message: Message, bot: Bot, state: FSMContext):
    is_subbed = await check_and_prompt_subscription(message, bot, state)
    if not is_subbed:
        return
        
    user = await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    ref_count = await get_referral_count(user.id)
    
    username_str = f"@{user.username}" if user.username else "Mavjud emas"
    join_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Noma'lum"
    
    if user.is_vip and user.vip_until:
        vip_status = f"Faol ⭐ ({user.vip_until.strftime('%d.%m.%Y %H:%M')} gacha)"
    else:
        vip_status = "Faol emas ❌"
        
    text = (
        "👤 **Foydalanuvchi Profili**\n\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"👤 **Ism:** {user.full_name}\n"
        f"🔹 **Username:** {username_str}\n"
        f"⭐ **VIP holati:** {vip_status}\n"
        f"👥 **Taklif qilgan do'stlar:** {ref_count} ta\n"
        f"📅 **A'zo bo'lgan sana:** {join_date}"
    )
    
    await message.answer(
        text,
        reply_markup=get_profile_keyboard(is_vip=user.is_vip)
    )
