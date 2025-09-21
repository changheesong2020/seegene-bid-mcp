#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seegene Bid MCP Server 실행 스크립트
"""

import asyncio
import os
import sys

import uvicorn

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.config import settings
    from src.database.connection import init_database
    from src.utils.logger import get_logger
except ImportError as e:
    print(f"Import 오류: {e}")
    print("필요한 의존성을 설치하세요: pip install -r requirements.txt")
    sys.exit(1)

logger = get_logger(__name__)

async def startup():
    """서버 시작 전 초기화"""
    try:
        # 데이터베이스 초기화
        await init_database()
        logger.info("데이터베이스 초기화 완료")
        
        logger.info("서버 시작 준비 완료")
        
    except Exception as e:
        logger.error(f"서버 시작 실패: {e}")
        raise

def main():
    """메인 실행 함수"""
    try:
        # 초기화 실행
        asyncio.run(startup())

        ssl_config = {}
        scheme = "http"

        if settings.SSL_ENABLED:
            cert_path = os.path.join(os.getcwd(), settings.SSL_CERTFILE)
            key_path = os.path.join(os.getcwd(), settings.SSL_KEYFILE)

            if os.path.exists(cert_path) and os.path.exists(key_path):
                ssl_config = {
                    "ssl_certfile": cert_path,
                    "ssl_keyfile": key_path
                }
                scheme = "https"
                logger.info("🔐 SSL 인증서가 감지되어 HTTPS로 실행합니다")
            else:
                logger.warning(
                    "SSL이 활성화되어 있지만 인증서를 찾을 수 없습니다. HTTP로 실행합니다"
                )

        logger.info("🚀 Seegene Bid MCP Server 시작")
        logger.info(f"서버 주소: {scheme}://{settings.HOST}:{settings.PORT}")
        logger.info(f"API 문서: {scheme}://{settings.HOST}:{settings.PORT}/docs")
        logger.info(f"MCP 엔드포인트: {scheme}://{settings.HOST}:{settings.PORT}/mcp")

        reload_mode = settings.DEBUG and not ssl_config

        # 서버 실행
        uvicorn.run(
            "src.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=reload_mode,
            log_level="info",
            **ssl_config
        )
        
    except Exception as e:
        logger.error(f"서버 실행 오류: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
