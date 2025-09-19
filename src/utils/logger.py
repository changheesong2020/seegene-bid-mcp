"""
Logging utilities
로깅 유틸리티
"""

import os
import logging
import sys
from pathlib import Path

# 로그 디렉토리 생성
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

def setup_logger(name: str, level: str = "INFO"):
    """로거 설정"""
    
    try:
        from loguru import logger as loguru_logger
        
        # 기존 핸들러 제거
        loguru_logger.remove()
        
        # 콘솔 출력
        loguru_logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True
        )
        
        # 파일 출력
        loguru_logger.add(
            "logs/seegene_bid_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="30 days",
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}",
            compression="zip"
        )
        
        return loguru_logger
    
    except ImportError:
        # loguru가 없는 경우 기본 logging 사용
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level))
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('[%(asctime)s] %(levelname)s - %(name)s - %(message)s')
        )
        logger.addHandler(console_handler)
        
        return logger

def get_logger(name: str):
    """로거 인스턴스 반환"""
    level = os.getenv("LOG_LEVEL", "INFO")
    return setup_logger(name, level)
