import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from app.config import DATABASE_URL
from app.models import Base, User, Movie, RequiredChannel, Setting, Series, SeriesEpisode

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

async def get_or_create_user(user_id: int, username: Optional[str], full_name: str) -> User:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.id == user_id))
            db_user = result.scalars().first()
            if not db_user:
                db_user = User(
                    id=user_id,
                    username=username,
                    full_name=full_name
                )
                session.add(db_user)
            else:
                # Update username or full name if changed
                db_user.username = username
                db_user.full_name = full_name
            await session.commit()
            return db_user

async def get_user(user_id: int) -> Optional[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

async def update_vip_until(user_id: int, months: int) -> Optional[datetime.datetime]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.id == user_id))
            db_user = result.scalars().first()
            if not db_user:
                return None
            
            now = datetime.datetime.utcnow()
            # If user is already VIP, extend. Otherwise start from now.
            start_date = db_user.vip_until if (db_user.vip_until and db_user.vip_until > now) else now
            
            # Simple approximation for months (30 days per month)
            days_to_add = months * 30
            db_user.vip_until = start_date + datetime.timedelta(days=days_to_add)
            
            new_vip_until = db_user.vip_until
            await session.commit()
            return new_vip_until

# --- MOVIE FUNCTIONS ---
async def add_movie(title: str, channel_id: int, message_id: int, file_id: str) -> Movie:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Generate next movie_code: max(movie_code) + 1, or 1 if empty
            result = await session.execute(select(func.max(Movie.movie_code)))
            max_code = result.scalar()
            next_code = (max_code or 0) + 1
            
            movie = Movie(
                movie_code=next_code,
                title=title,
                channel_id=channel_id,
                message_id=message_id,
                file_id=file_id
            )
            session.add(movie)
            await session.commit()
            return movie

async def get_movie_by_code(code: int) -> Optional[Movie]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie).where(Movie.movie_code == code))
        return result.scalars().first()

async def get_all_movies(offset: int = 0, limit: int = 10) -> List[Movie]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Movie).order_by(Movie.movie_code.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

async def get_movie_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Movie.movie_code)))
        return result.scalar() or 0

async def increment_search_count(code: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(Movie).where(Movie.movie_code == code).values(search_count=Movie.search_count + 1)
            )
            await session.commit()

async def rename_movie(code: int, new_title: str) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                update(Movie).where(Movie.movie_code == code).values(title=new_title)
            )
            await session.commit()
            return (result.rowcount or 0) > 0

async def replace_movie_file(code: int, channel_id: int, message_id: int, file_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                update(Movie).where(Movie.movie_code == code).values(
                    channel_id=channel_id,
                    message_id=message_id,
                    file_id=file_id
                )
            )
            await session.commit()
            return (result.rowcount or 0) > 0

async def delete_movie(code: int) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(delete(Movie).where(Movie.movie_code == code))
            await session.commit()
            return (result.rowcount or 0) > 0

async def search_movies_db() -> List[Movie]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie))
        return list(result.scalars().all())


# --- SERIES FUNCTIONS ---
async def add_series(title: str, channel_link: Optional[str] = None, episodes_count: Optional[int] = None) -> Series:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Series code starts from 1000 to avoid overlapping with movies
            result = await session.execute(select(func.max(Series.series_code)))
            max_code = result.scalar()
            next_code = (max_code or 999) + 1
            
            series = Series(
                series_code=next_code,
                title=title,
                channel_link=channel_link,
                episodes_count=episodes_count
            )
            session.add(series)
            await session.commit()
            return series

async def add_series_episode(series_code: int, episode_number: int, channel_id: int, message_id: int, file_id: str) -> SeriesEpisode:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            ep = SeriesEpisode(
                series_code=series_code,
                episode_number=episode_number,
                channel_id=channel_id,
                message_id=message_id,
                file_id=file_id
            )
            session.add(ep)
            await session.commit()
            return ep

async def get_series_by_code(code: int) -> Optional[Series]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Series)
            .where(Series.series_code == code)
            .options(selectinload(Series.episodes))
        )
        return result.scalars().first()

async def get_all_series(offset: int = 0, limit: int = 10) -> List[Series]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Series).order_by(Series.series_code.asc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

async def get_series_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Series.series_code)))
        return result.scalar() or 0

async def increment_series_search_count(code: int):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                update(Series).where(Series.series_code == code).values(search_count=Series.search_count + 1)
            )
            await session.commit()

async def rename_series(code: int, new_title: str) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                update(Series).where(Series.series_code == code).values(title=new_title)
            )
            await session.commit()
            return (result.rowcount or 0) > 0

async def delete_series(code: int) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(delete(Series).where(Series.series_code == code))
            await session.commit()
            return (result.rowcount or 0) > 0

async def search_series_db() -> List[Series]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Series))
        return list(result.scalars().all())


# --- REQUIRED CHANNELS ---
async def add_required_channel(channel_id: int, invite_link: str, name: str) -> RequiredChannel:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(RequiredChannel).where(RequiredChannel.channel_id == channel_id))
            chan = result.scalars().first()
            if chan:
                chan.invite_link = invite_link
                chan.name = name
            else:
                chan = RequiredChannel(channel_id=channel_id, invite_link=invite_link, name=name)
                session.add(chan)
            await session.commit()
            return chan

async def delete_required_channel(channel_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(delete(RequiredChannel).where(RequiredChannel.channel_id == channel_id))
            await session.commit()
            return (result.rowcount or 0) > 0

async def get_required_channels() -> List[RequiredChannel]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(RequiredChannel))
        return list(result.scalars().all())

# --- SETTINGS ---
async def get_setting(key: str, default: str = "") -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalars().first()
        return setting.value if setting else default

async def set_setting(key: str, value: str):
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(Setting).where(Setting.key == key))
            setting = result.scalars().first()
            if setting:
                setting.value = value
            else:
                setting = Setting(key=key, value=value)
                session.add(setting)
            await session.commit()

# --- STATISTICS ---
async def get_statistics() -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        total_users = await session.execute(select(func.count(User.id)))
        
        now = datetime.datetime.utcnow()
        vip_users = await session.execute(select(func.count(User.id)).where(User.vip_until > now))
        
        movies = await session.execute(select(func.count(Movie.movie_code)))
        series = await session.execute(select(func.count(Series.series_code)))
        
        movie_searches = await session.execute(select(func.sum(Movie.search_count)))
        series_searches = await session.execute(select(func.sum(Series.search_count)))
        
        total_searches = (movie_searches.scalar() or 0) + (series_searches.scalar() or 0)
        
        today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_users = await session.execute(select(func.count(User.id)).where(User.created_at >= today))
        
        all_users_res = await session.execute(select(User.id))
        all_user_ids = list(all_users_res.scalars().all())

        return {
            "total_users": total_users.scalar() or 0,
            "vip_users": vip_users.scalar() or 0,
            "movies": movies.scalar() or 0,
            "series": series.scalar() or 0,
            "searches": total_searches,
            "today_users": today_users.scalar() or 0,
            "all_user_ids": all_user_ids
        }
