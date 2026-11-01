import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Integer, DateTime, Boolean, ForeignKey, Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram User ID
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    vip_until: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_active_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    referred_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    @property
    def is_vip(self) -> bool:
        if self.vip_until is None:
            return False
        return self.vip_until > datetime.datetime.utcnow()

class Movie(Base):
    __tablename__ = "movies"

    movie_code: Mapped[int] = mapped_column(Integer, primary_key=True)  # Custom code starting at 1
    title: Mapped[str] = mapped_column(String(500), index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[str] = mapped_column(String(500))
    search_count: Mapped[int] = mapped_column(Integer, default=0)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)

class Series(Base):
    __tablename__ = "series"

    series_code: Mapped[int] = mapped_column(Integer, primary_key=True)  # Custom code starting at 1000
    title: Mapped[str] = mapped_column(String(500), index=True)
    channel_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    episodes_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    search_count: Mapped[int] = mapped_column(Integer, default=0)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)

    episodes = relationship("SeriesEpisode", back_populates="series", cascade="all, delete-orphan", lazy="selectin")

class SeriesEpisode(Base):
    __tablename__ = "series_episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_code: Mapped[int] = mapped_column(Integer, ForeignKey("series.series_code", ondelete="CASCADE"))
    season_number: Mapped[Optional[int]] = mapped_column(Integer, default=1, nullable=True)
    episode_number: Mapped[int] = mapped_column(Integer)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[str] = mapped_column(String(500))

    series = relationship("Series", back_populates="episodes")

class RequiredChannel(Base):
    __tablename__ = "required_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    invite_link: Mapped[str] = mapped_column(String(500))
    name: Mapped[str] = mapped_column(String(255))
    sub_type: Mapped[str] = mapped_column(String(50), default="channel")  # 'channel', 'bot', 'instagram'
    target_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

class UserBotStart(Base):
    __tablename__ = "user_bot_starts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    target_bot_username: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class UserInstagramSub(Base):
    __tablename__ = "user_instagram_subs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    instagram_username: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(1000))

class VipPlan(Base):
    __tablename__ = "vip_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    months: Mapped[int] = mapped_column(Integer)
    price: Mapped[str] = mapped_column(String(100))

class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram User ID
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

class DailySearch(Base):
    __tablename__ = "daily_searches"

    date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)

class JoinRequest(Base):
    __tablename__ = "join_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, index=True)
    referred_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
