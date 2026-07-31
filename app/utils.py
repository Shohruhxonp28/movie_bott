import logging
from typing import List, Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from rapidfuzz import process, fuzz
from app.models import Movie, RequiredChannel
from app.database import get_required_channels, get_user

logger = logging.getLogger(__name__)

async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Checks if a user is subscribed to all required channels.
    VIP users bypass this check automatically.
    """
    user = await get_user(user_id)
    if user and user.is_vip:
        return True
        
    channels = await get_required_channels()
    if not channels:
        return True
        
    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except TelegramAPIError as e:
            logger.error(f"Error checking channel sub for channel {channel.channel_id} and user {user_id}: {e}")
            # If the bot is not in the channel or cannot check, we might treat it as not subscribed
            return False
            
    return True

def search_movies_fuzzy(query: str, movies: List[Movie], threshold: float = 60.0) -> List[Movie]:
    """
    Fuzzy search movies by title using RapidFuzz.
    Returns list of Movie objects matching the query.
    """
    if not movies:
        return []
        
    # Create mapping of lowercase titles to movie objects
    # Note: RapidFuzz works best on strings.
    title_to_movie = {movie.title.lower(): movie for movie in movies}
    titles = list(title_to_movie.keys())
    
    # Run rapidfuzz matching
    results = process.extract(
        query.lower(),
        titles,
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
        limit=10
    )
    
    matched_movies = []
    for match in results:
        matched_title = match[0]
        matched_movies.append(title_to_movie[matched_title])
        
    return matched_movies
