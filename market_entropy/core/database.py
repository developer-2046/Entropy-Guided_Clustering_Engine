import asyncpg
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://entropy_user:password@localhost:5432/marketentropy")

# Replace postgresql:// with postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

class RegimeState(Base):
    __tablename__ = "regime_states"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    regime_id = Column(Integer, nullable=False)
    probability = Column(Float, nullable=False)
    entropy_score = Column(Float, nullable=False)
    stress_level = Column(String(20), nullable=False)
    eigenvalues = Column(JSON)

class MarketData(Base):
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Integer)
    returns = Column(Float)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    api_key = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    rate_limit = Column(Integer, default=1000)
    is_active = Column(Boolean, default=True)

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
