"""
SQLite Database Connection and Models
SQLite 데이터베이스 연결 및 모델
"""

import os
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

try:
    from src.config import settings
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
except:
    import logging
    logger = logging.getLogger(__name__)

# Base 모델
Base = declarative_base()

# 비동기 엔진 생성
try:
    async_engine = create_async_engine(
        "sqlite+aiosqlite:///./seegene_bids.db",
        echo=False,
        future=True
    )
except:
    async_engine = None

# 세션 팩토리
if async_engine:
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
else:
    async_session_maker = None


class BidInfoModel(Base):
    """입찰 정보 데이터베이스 모델"""
    
    __tablename__ = "bid_information"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    organization = Column(String(200), index=True)
    bid_number = Column(String(100))
    announcement_date = Column(String(50))
    deadline_date = Column(String(50))
    estimated_price = Column(String(100))
    currency = Column(String(10), default='KRW')
    source_url = Column(Text, nullable=False)
    source_site = Column(String(100), nullable=False, index=True)
    country = Column(String(10), default='KR', index=True)
    keywords = Column(JSON)
    relevance_score = Column(Float, default=0.0, index=True)
    urgency_level = Column(String(20), default='low')
    status = Column(String(50), default='active', index=True)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


@asynccontextmanager
async def get_db_session():
    """데이터베이스 세션 컨텍스트 매니저"""
    if not async_session_maker:
        raise Exception("Database not initialized")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"데이터베이스 세션 오류: {e}")
            raise
        finally:
            await session.close()


async def init_database():
    """데이터베이스 초기화"""
    try:
        if not async_engine:
            raise Exception("Database engine not available")
            
        # 모든 테이블 생성
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("데이터베이스 초기화 완료")
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


class DatabaseManager:
    """데이터베이스 관리 클래스"""
    
    @staticmethod
    async def save_bid_info(bid_info_list: List[Dict[str, Any]]):
        """입찰 정보 저장"""
        try:
            async with get_db_session() as session:
                for bid_data in bid_info_list:
                    bid_model = BidInfoModel(**bid_data)
                    session.add(bid_model)
                
                await session.commit()
                logger.info(f"{len(bid_info_list)}건의 입찰 정보 저장 완료")
                
        except Exception as e:
            logger.error(f"입찰 정보 저장 실패: {e}")
            raise
    
    @staticmethod
    async def search_bids(keywords: List[str], limit: int = 50) -> List[BidInfoModel]:
        """키워드로 입찰 정보 검색"""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, desc, or_
                
                # 키워드 검색 조건 생성
                conditions = []
                for keyword in keywords:
                    conditions.append(BidInfoModel.title.contains(keyword))
                
                if conditions:
                    result = await session.execute(
                        select(BidInfoModel)
                        .where(or_(*conditions))
                        .where(BidInfoModel.status == 'active')
                        .order_by(desc(BidInfoModel.relevance_score))
                        .limit(limit)
                    )
                else:
                    result = await session.execute(
                        select(BidInfoModel)
                        .where(BidInfoModel.status == 'active')
                        .order_by(desc(BidInfoModel.created_at))
                        .limit(limit)
                    )
                
                return result.scalars().all()
                
        except Exception as e:
            logger.error(f"키워드 검색 실패: {e}")
            return []
    
    @staticmethod
    async def get_database_stats():
        """데이터베이스 통계 조회"""
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, func
                
                # 총 입찰 수
                total_result = await session.execute(
                    select(func.count(BidInfoModel.id))
                )
                total_bids = total_result.scalar()
                
                return {
                    'total_bids': total_bids or 0,
                    'site_breakdown': {},
                    'country_breakdown': {},
                    'avg_relevance_score': 0.0
                }
                
        except Exception as e:
            logger.error(f"데이터베이스 통계 조회 실패: {e}")
            return {
                'total_bids': 0,
                'site_breakdown': {},
                'country_breakdown': {},
                'avg_relevance_score': 0.0
            }
