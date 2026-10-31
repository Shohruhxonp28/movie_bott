import logging
import re
from typing import List, Optional, Any
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from rapidfuzz import process, fuzz
from app.models import Movie, RequiredChannel, Series
from app.database import get_required_channels, get_user, has_join_request

logger = logging.getLogger(__name__)

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Checks if a user is subscribed to all required channels, bots, and instagram accounts.
    VIP users bypass this check automatically.
    """
    user = await get_user(user_id)
    if user and user.is_vip:
        return True
        
    channels = await get_required_channels()
    if not channels:
        return True

    from app.database import has_user_started_bot, has_user_subbed_instagram
        
    for channel in channels:
        sub_type = getattr(channel, "sub_type", "channel") or "channel"

        if sub_type == "bot":
            target_bot = getattr(channel, "target_username", None) or channel.name
            if not await has_user_started_bot(user_id, target_bot):
                return False
        elif sub_type == "instagram":
            insta_user = getattr(channel, "target_username", None) or channel.name
            from app.database import record_user_instagram_sub
            await record_user_instagram_sub(user_id, insta_user)
        else:
            if not channel.channel_id:
                continue
            try:
                member = await bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    # If they are not a member, check if they have a pending join request
                    if not await has_join_request(user_id, channel.channel_id):
                        return False
            except TelegramAPIError as e:
                # If the bot is not admin or some other error, check join request just in case
                if not await has_join_request(user_id, channel.channel_id):
                    logger.error(f"Error checking channel sub for channel {channel.channel_id} and user {user_id}: {e}")
                    return False
            
    return True

def search_items_fuzzy(query: str, items: List[Any], threshold: float = 60.0) -> List[Any]:
    """
    Fuzzy search items (Movies or Series) by title using RapidFuzz.
    """
    if not items:
        return []
        
    title_to_items = {}
    for item in items:
        title_lower = item.title.lower()
        if title_lower not in title_to_items:
            title_to_items[title_lower] = []
        title_to_items[title_lower].append(item)
        
    titles = list(title_to_items.keys())
    
    results = process.extract(
        query.lower(),
        titles,
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
        limit=10
    )
    
    matched_items = []
    for match in results:
        matched_title = match[0]
        matched_items.extend(title_to_items[matched_title])
        
    return matched_items[:10]

META_PREFIXES = [
    r'sifati?', r'quality', r'качество',
    r'yili?', r'year', r'год',
    r'janri?', r'genre', r'жанр',
    r'davlat', r'mamlakat', r'country', r'страна',
    r'tarjima', r'ovoz', r'dublyaj', r'translation', r'til', r'tili', r'перевод',
    r'yuklash', r'kodi?', r'code', r'download', r'код',
    r'davomiyligi', r'vaqti', r'duration', r'время',
    r'yosh\s*chegarasi', r'yosh', r'age', r'возраст',
    r'rejissyor', r'director', r'режиссер',
    r'rollarda', r'aktyorlar', r'actors', r'в\s*ролях',
    r'hajmi?', r'size', r'размер',
    r'imdb', r'kinopoisk', r'reyting', r'rating', r'рейтинг',
    r'format', r'формат',
]

PROMO_KEYWORDS = [
    r'obuna\s*bo', r'qo[\'ʼ`’]?shiling', r'kanalimiz', r'bizning\s*bot', r'botimiz',
    r'reklama', r'hamkor', r'administrator', r'aloqa', r'murojaat',
    r'ulashing', r'layk\s*bosing', r'do[\'ʼ`’]?stlarga',
]

BADGE_KEYWORDS = [
    r'premyera', r'yangi\s*kino', r'kino\s*olami', r'kino\s*vaqti', r'top\s*kino',
    r'premyera\s*kino', r'exclusive', r'eksklyuziv',
]

def clean_title_candidate(text: str) -> str:
    """
    Cleans tags, emojis, markdown, and links from candidate title text.
    """
    if not text:
        return ""
    text = re.sub(r'[\*_`~]', '', text)
    stripped = text.strip()
    if stripped.startswith('#') and '_' in stripped and ' ' not in stripped:
        text = text.replace('_', ' ')
    # Strip leading hashtags, emojis, bullets, colons, dashes
    text = re.sub(r'^[#🎥🎬🍿📽️🎞️📹📀📺🔹🔸▪️▫️•\-\s:]+', '', text)
    # Strip leading labels like Kino:, Film:, Nomi: if present
    text = re.sub(r'^(?:kino|film|nomi|kino\s*nomi|film\s*nomi|name|название)\s*[:：\-–—]\s*', '', text, flags=re.IGNORECASE)
    # Remove URLs and @mentions
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    # Strip trailing emojis, symbols, dashes
    text = re.sub(r'[🎥🎬🍿📽️🎞️📹📀📺🔹🔸▪️▫️•\-\s:]+$', '', text)
    text = text.strip(' "\'«»')
    return text.strip()

def is_meta_or_promo_line(line: str) -> bool:
    """
    Returns True if the line represents metadata (e.g. Sifati: HD, Yil: 2021) or promo/channel ads.
    """
    clean = re.sub(r'^[^\w#]+', '', line).strip()
    clean_lower = clean.lower()
    
    if not clean_lower or len(clean_lower) < 2:
        return True
        
    if re.match(r'^(?:https?://\S+|@\w+)\s*$', clean_lower):
        return True
        
    for prefix in META_PREFIXES:
        if re.match(rf'^{prefix}\s*[:：\-–—]', clean_lower):
            return True
            
    for promo in PROMO_KEYWORDS:
        if re.search(rf'\b{promo}', clean_lower):
            return True
            
    for badge in BADGE_KEYWORDS:
        if re.search(rf'^\W*{badge}\W*$', clean_lower):
            return True
            
    return False

def extract_movie_title(caption: Optional[str]) -> Optional[str]:
    """
    Telegram post matnidan (caption) kino nomini avtomatik ajratib oladi.
    Topa olsa kino nomini qaytaradi, topa olmasa None qaytaradi.
    """
    if not caption or not caption.strip():
        return None
        
    lines = [line.strip() for line in caption.strip().splitlines() if line.strip()]
    if not lines:
        return None

    # 1. 'Nomi:', 'Film:', 'Kino:' kabi aniq ko'rsatilgan qatorlarni tekshirish
    for line in lines:
        cleaned_start = re.sub(r'^[^\w#]+', '', line).strip()
        match = re.match(
            r'^(?:kino|film|nomi|kino\s*nomi|film\s*nomi|name|название)\s*[:：\-–—]\s*(.+)',
            cleaned_start,
            re.IGNORECASE
        )
        if match:
            candidate = clean_title_candidate(match.group(1))
            if candidate and len(candidate) >= 2 and not is_meta_or_promo_line(candidate):
                return candidate

    # 2. Maxsus emoji yoki heshteg bilan boshlanuvchi kino qatorlari: #🎥, #🎬, 🎥, 🎬, #
    for line in lines:
        cleaned_line = line.strip()
        if re.match(r'^(?:#\s*)?[🎥🎬🍿📽️🎞️📹📀📺]', cleaned_line):
            candidate = clean_title_candidate(cleaned_line)
            if candidate and len(candidate) >= 2 and not is_meta_or_promo_line(candidate):
                return candidate

    # 3. Birinchi meta va promo bo'lmagan matnli qator
    for line in lines:
        if not is_meta_or_promo_line(line):
            candidate = clean_title_candidate(line)
            if candidate and len(candidate) >= 2 and not is_meta_or_promo_line(candidate):
                return candidate

    return None
