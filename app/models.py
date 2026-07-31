import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Integer, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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

    movie_code: Mapped[int] = mapped_column(Integer, primary_key=True)  # Custom code
    title: Mapped[str] = mapped_column(String(500), index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[str] = mapped_column(String(500))
    search_count: Mapped[int] = mapped_column(Integer, default=0)

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
