"""
Seegene Bid Information MCP Server
FastMCP를 사용한 메인 서버 애플리케이션
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

try:
    from fastmcp import FastMCP
except ImportError:
    print("FastMCP가 설치되지 않았습니다. pip install fastmcp를 실행하세요.")
    FastMCP = None

from src.config import settings
from src.database.connection import init_database, DatabaseManager
from src.models.filters import BidFilter
from src.models.bid_info import BidInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    try:
        await init_database()
        logger.info("✅ 데이터베이스 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
    
    yield
    
    # 종료 시
    logger.info("🛑 서버 종료 중...")

# FastAPI 앱 생성
app = FastAPI(
    title="Seegene Bid Information MCP Server",
    description="씨젠을 위한 글로벌 입찰 정보 수집 및 분석 시스템",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastMCP 인스턴스 생성
if FastMCP:
    mcp = FastMCP("Seegene Bid Information Server")
    
    @mcp.tool()
    async def search_bids(
        keywords: List[str],
        days_range: int = 7,
        countries: List[str] = ["KR", "US"],
        limit: int = 50
    ) -> Dict[str, Any]:
        """입찰 정보 검색"""
        try:
            logger.info(f"입찰 정보 검색: 키워드={keywords}")
            
            # 데이터베이스에서 검색
            results = await DatabaseManager.search_bids(keywords, limit)
            
            # 결과 변환
            bid_list = []
            for bid in results:
                bid_dict = {
                    "id": getattr(bid, 'id', 0),
                    "title": getattr(bid, 'title', ''),
                    "organization": getattr(bid, 'organization', ''),
                    "source_site": getattr(bid, 'source_site', ''),
                    "country": getattr(bid, 'country', ''),
                    "relevance_score": getattr(bid, 'relevance_score', 0.0),
                    "source_url": getattr(bid, 'source_url', '')
                }
                bid_list.append(bid_dict)
            
            logger.info(f"검색 완료: {len(bid_list)}건 발견")
            
            return {
                "success": True,
                "total_found": len(bid_list),
                "results": bid_list
            }
            
        except Exception as e:
            logger.error(f"입찰 검색 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    @mcp.tool()
    async def get_database_stats() -> Dict[str, Any]:
        """데이터베이스 통계 조회"""
        try:
            stats = await DatabaseManager.get_database_stats()
            
            return {
                "success": True,
                "database_statistics": stats,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"데이터베이스 통계 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # MCP 서버 마운트
    app.mount("/mcp", mcp.create_server())

# FastAPI 라우트
@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Seegene Bid Information MCP Server",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "mcp": "/mcp" if FastMCP else "Not available (install fastmcp)"
        }
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    try:
        stats = await DatabaseManager.get_database_stats()
        db_status = "ok"
    except:
        db_status = "error"
    
    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "version": "2.0.0"
    }

@app.get("/crawler-status")
async def crawler_status_endpoint():
    """크롤러 상태 확인 엔드포인트"""
    return {
        "g2b": {
            "can_make_requests": False,
            "has_credentials": False,
            "status": "not_configured"
        },
        "samgov": {
            "can_make_requests": False,
            "has_credentials": False,
            "status": "not_configured"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
