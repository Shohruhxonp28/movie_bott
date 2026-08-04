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

class Series(Base):
    __tablename__ = "series"

    series_code: Mapped[int] = mapped_column(Integer, primary_key=True)  # Custom code starting at 1000
    title: Mapped[str] = mapped_column(String(500), index=True)
    channel_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    episodes_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    search_count: Mapped[int] = mapped_column(Integer, default=0)

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
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    invite_link: Mapped[str] = mapped_column(String(500))
    name: Mapped[str] = mapped_column(String(255))

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

