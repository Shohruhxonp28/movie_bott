import logging
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
            if not await has_user_subbed_instagram(user_id, insta_user):
                return False
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
