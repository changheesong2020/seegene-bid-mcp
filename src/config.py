"""
Configuration settings for Seegene Bid MCP Server
"""

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List, Optional

# .env 파일 명시적 로딩
load_dotenv()


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 서버 설정
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    
    # 데이터베이스 설정 (SQLite)
    DATABASE_URL: str = "sqlite+aiosqlite:///./seegene_bids.db"
    
    # 로그인 자격증명
    G2B_USERNAME: Optional[str] = None
    G2B_PASSWORD: Optional[str] = None
    G2B_API_KEY: Optional[str] = None  # 조달청 공공데이터 포털 API 키
    SAMGOV_USERNAME: Optional[str] = None
    SAMGOV_PASSWORD: Optional[str] = None
    SAMGOV_API_KEY: Optional[str] = None
    
    # 이메일 설정
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    
    # 크롤링 설정
    HEADLESS_MODE: bool = True
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    # 알림 설정
    URGENT_DEADLINE_DAYS: int = 3
    HIGH_VALUE_THRESHOLD_KRW: int = 100000000
    HIGH_VALUE_THRESHOLD_USD: int = 1000000

    # SSL 설정
    SSL_ENABLED: bool = True
    SSL_CERTFILE: str = "certs/cert.pem"
    SSL_KEYFILE: str = "certs/key.pem"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class CrawlerConfig:
    """크롤러별 설정"""
    
    SEEGENE_KEYWORDS = {
        'korean': [
            '진단키트', 'PCR', '분자진단', 'RT-PCR',
            '코로나', 'COVID', '인플루엔자', '독감',
            '호흡기감염', '병원체검사', '체외진단'
        ],
        'english': [
            'diagnostic kit', 'PCR test', 'molecular diagnostic',
            'RT-PCR', 'COVID test', 'coronavirus',
            'influenza test', 'respiratory pathogen',
            'in vitro diagnostic', 'IVD', 'point of care'
        ]
    }


# 전역 설정 인스턴스
try:
    settings = Settings()
    crawler_config = CrawlerConfig()
except Exception as e:
    print(f"설정 로드 오류: {e}")
    # 기본 설정 사용
    class DefaultSettings:
        HOST = "127.0.0.1"
        PORT = 8000
        DEBUG = True
        DATABASE_URL = "sqlite+aiosqlite:///./seegene_bids.db"
        LOG_LEVEL = "INFO"
        
    settings = DefaultSettings()
    crawler_config = CrawlerConfig()
