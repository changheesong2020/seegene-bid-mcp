"""
Seegene Bid Information MCP Server
FastMCP를 사용한 메인 서버 애플리케이션
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
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
from src.models.crawler_api import (
    CrawlerRequest, CrawlerExecutionResponse, AllCrawlerExecutionResponse,
    CrawlerResultsResponse, SiteCrawlerResultResponse, ScheduledJobsResponse,
    ScheduleRequest, ScheduleResponse, BidListResponse, BidDetailResponse,
    BidSearchResponse, BidStatisticsResponse
)
from src.models.advanced_filters import (
    AdvancedBidSearchRequest, AdvancedSearchResponse, KeywordSuggestionsResponse,
    KeywordExpansion, AdvancedSearchQuery, KeywordGroup
)
from src.services.advanced_search import advanced_search_service
from src.services.site_compliance import list_site_compliance, get_site_compliance
from src.utils.keyword_expansion import keyword_engine
from src.utils.logger import get_logger
from src.crawler.manager import crawler_manager
from src.models.site_compliance import (
    SiteComplianceListResponse,
    SiteComplianceResponse,
)

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시
    try:
        await init_database()
        logger.info("✅ 데이터베이스 초기화 완료")

        # 크롤러 스케줄러 시작 (설정에 따라)
        if settings.ENABLE_SCHEDULER:
            await crawler_manager.start_scheduler()
            logger.info("✅ 크롤러 스케줄러 시작 완료")
        else:
            logger.info("⏸️ 크롤러 스케줄러 비활성화됨 (ENABLE_SCHEDULER=False)")
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {e}")

    yield

    # 종료 시 - 안전한 종료
    try:
        if settings.ENABLE_SCHEDULER:
            await crawler_manager.stop_scheduler()
        logger.info("🛑 서버 종료 중...")
    except Exception as e:
        logger.warning(f"종료 중 오류 (무시됨): {e}")

    # 데이터베이스 연결 정리
    try:
        from src.database.connection import async_engine
        if async_engine:
            await async_engine.dispose()
            logger.info("✅ 데이터베이스 연결 정리 완료")
    except Exception as e:
        logger.warning(f"데이터베이스 연결 정리 중 오류 (무시됨): {e}")

# FastAPI 앱 생성
app = FastAPI(
    title="Seegene Bid Information MCP Server",
    description="씨젠을 위한 글로벌 입찰 정보 수집 및 분석 시스템",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정 - MCP 및 Copilot Studio 호환
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # 개발용
        "https://copilotstudio.microsoft.com",
        "https://make.powerplatform.com",
        "https://apps.powerapps.com",
        "https://flow.microsoft.com",
        "http://localhost:*",
        "https://localhost:*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "*",
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],
    expose_headers=["*"]
)

# 추가 CORS 미들웨어 (MCP 전용)
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    """MCP 요청을 위한 추가 CORS 헤더"""
    response = await call_next(request)

    # MCP 관련 경로에 대한 특별 처리
    if request.url.path.startswith("/mcp") or request.url.path in ["/api/mcp", "/v1/mcp", "/jsonrpc"]:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With"
        response.headers["Access-Control-Expose-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"

        # OPTIONS 요청에 대한 특별 처리
        if request.method == "OPTIONS":
            response.headers["Access-Control-Max-Age"] = "86400"

    return response

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

    @mcp.tool()
    async def run_crawler(
        site_name: str,
        keywords: List[str] = None
    ) -> Dict[str, Any]:
        """특정 사이트에서 크롤링 실행"""
        try:
            logger.info(f"크롤링 실행: {site_name}")

            result = await crawler_manager.run_crawler(site_name, keywords)

            return {
                "success": True,
                "crawler_result": result
            }

        except Exception as e:
            logger.error(f"크롤링 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def run_all_crawlers(
        keywords: List[str] = None
    ) -> Dict[str, Any]:
        """모든 사이트에서 크롤링 실행"""
        try:
            logger.info("전체 크롤링 실행")

            result = await crawler_manager.run_all_crawlers(keywords)

            return {
                "success": True,
                "crawling_result": result
            }

        except Exception as e:
            logger.error(f"전체 크롤링 실행 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def get_crawler_status() -> Dict[str, Any]:
        """크롤러 상태 조회"""
        try:
            status = crawler_manager.get_crawler_status()

            return {
                "success": True,
                "crawler_status": status
            }

        except Exception as e:
            logger.error(f"크롤러 상태 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def get_scheduled_jobs() -> Dict[str, Any]:
        """예약된 크롤링 작업 조회"""
        try:
            jobs = crawler_manager.get_scheduled_jobs()

            return {
                "success": True,
                "scheduled_jobs": jobs
            }

        except Exception as e:
            logger.error(f"예약된 작업 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def add_crawler_schedule(
        site_name: str,
        cron_expression: str,
        job_id: str = None
    ) -> Dict[str, Any]:
        """크롤러 스케줄 추가"""
        try:
            success = await crawler_manager.add_custom_schedule(site_name, cron_expression, job_id)

            return {
                "success": success,
                "message": "스케줄 추가 성공" if success else "스케줄 추가 실패"
            }

        except Exception as e:
            logger.error(f"스케줄 추가 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def advanced_search_bids(
        keywords: List[str],
        countries: List[str] = None,
        enable_expansion: bool = True,
        min_relevance: float = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """고급 키워드 확장 검색"""
        try:
            logger.info(f"MCP 고급 검색: 키워드={keywords}")

            # 확장 설정
            expansion_config = None
            if enable_expansion:
                expansion_config = KeywordExpansion(
                    enable_synonyms=True,
                    enable_related_terms=True,
                    enable_translations=True,
                    enable_abbreviations=True
                )

            # 키워드 그룹 생성
            keyword_groups = [KeywordGroup(
                keywords=keywords,
                operator="or",
                weight=1.0
            )]

            # 검색 쿼리 구성
            search_query = AdvancedSearchQuery(
                keyword_groups=keyword_groups,
                countries=countries or ["KR", "US"],
                min_relevance_score=min_relevance,
                limit=limit
            )

            # 요청 생성 및 검색
            request = AdvancedBidSearchRequest(
                query=search_query,
                expansion=expansion_config,
                include_metadata=True,
                explain_relevance=True
            )

            result = await advanced_search_service.search_bids(request)

            return {
                "success": True,
                "search_result": {
                    "total_found": result.total_found,
                    "search_time": result.search_time,
                    "query_summary": result.query_summary,
                    "filters_applied": result.filters_applied,
                    "results": [
                        {
                            "title": r.title,
                            "organization": r.organization,
                            "country": r.country,
                            "relevance_score": r.relevance_score,
                            "matched_keywords": r.matched_keywords,
                            "source_url": r.source_url,
                            "urgency_level": r.urgency_level
                        } for r in result.results[:10]  # 처음 10개만
                    ]
                }
            }

        except Exception as e:
            logger.error(f"MCP 고급 검색 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def get_keyword_suggestions(
        keywords: List[str],
        max_suggestions: int = 10
    ) -> Dict[str, Any]:
        """키워드 제안 받기"""
        try:
            suggestions = keyword_engine.get_keyword_suggestions(keywords, max_suggestions)

            return {
                "success": True,
                "original_keywords": keywords,
                "suggestions": [
                    {
                        "keyword": s.keyword,
                        "relevance": s.relevance,
                        "source": s.source
                    } for s in suggestions
                ]
            }

        except Exception as e:
            logger.error(f"키워드 제안 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def reset_database() -> Dict[str, Any]:
        """데이터베이스 전체 초기화 (모든 데이터 삭제)"""
        try:
            from src.database.connection import get_db_session, BidInfoModel
            from sqlalchemy import delete

            async with get_db_session() as session:
                # 모든 입찰 정보 삭제
                result = await session.execute(delete(BidInfoModel))
                deleted_count = result.rowcount
                await session.commit()

                logger.info(f"MCP 데이터베이스 초기화 완료: {deleted_count}건 삭제")

                return {
                    "success": True,
                    "message": "데이터베이스가 성공적으로 초기화되었습니다",
                    "deleted_records": deleted_count,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"MCP 데이터베이스 초기화 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def clean_dummy_data() -> Dict[str, Any]:
        """더미 데이터만 삭제"""
        try:
            from src.database.connection import get_db_session, BidInfoModel
            from sqlalchemy import delete, select

            async with get_db_session() as session:
                # 더미 데이터 확인
                dummy_result = await session.execute(
                    select(BidInfoModel).where(
                        BidInfoModel.extra_data.contains('"dummy": true') |
                        BidInfoModel.bid_number.like('%DUMMY%') |
                        BidInfoModel.bid_number.like('%TEST%')
                    )
                )
                dummy_bids = dummy_result.scalars().all()
                dummy_count = len(dummy_bids)

                if dummy_count > 0:
                    # 더미 데이터 삭제
                    await session.execute(
                        delete(BidInfoModel).where(
                            BidInfoModel.extra_data.contains('"dummy": true') |
                            BidInfoModel.bid_number.like('%DUMMY%') |
                            BidInfoModel.bid_number.like('%TEST%')
                        )
                    )
                    await session.commit()

                logger.info(f"MCP 더미 데이터 정리 완료: {dummy_count}건 삭제")

                return {
                    "success": True,
                    "message": "더미 데이터가 성공적으로 삭제되었습니다",
                    "deleted_dummy_records": dummy_count,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"MCP 더미 데이터 정리 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def get_database_info() -> Dict[str, Any]:
        """데이터베이스 정보 및 통계 조회"""
        try:
            from src.database.connection import get_db_session, BidInfoModel
            from sqlalchemy import select, func

            async with get_db_session() as session:
                # 전체 레코드 수
                total_result = await session.execute(select(func.count(BidInfoModel.id)))
                total_count = total_result.scalar()

                # 소스별 통계
                source_result = await session.execute(
                    select(BidInfoModel.source_site, func.count(BidInfoModel.id))
                    .group_by(BidInfoModel.source_site)
                )
                source_stats = {site: count for site, count in source_result.fetchall()}

                # 더미 데이터 수
                dummy_result = await session.execute(
                    select(func.count(BidInfoModel.id)).where(
                        BidInfoModel.extra_data.contains('"dummy": true') |
                        BidInfoModel.bid_number.like('%DUMMY%') |
                        BidInfoModel.bid_number.like('%TEST%')
                    )
                )
                dummy_count = dummy_result.scalar()

                # 최근 데이터
                recent_result = await session.execute(
                    select(BidInfoModel.created_at, BidInfoModel.source_site, BidInfoModel.title)
                    .order_by(BidInfoModel.created_at.desc())
                    .limit(5)
                )
                recent_data = [
                    {
                        "created_at": row[0].isoformat() if row[0] else None,
                        "source": row[1],
                        "title": row[2][:50] + "..." if len(row[2]) > 50 else row[2]
                    }
                    for row in recent_result.fetchall()
                ]

                return {
                    "success": True,
                    "database_info": {
                        "total_records": total_count,
                        "dummy_records": dummy_count,
                        "real_records": total_count - dummy_count,
                        "source_breakdown": source_stats,
                        "recent_entries": recent_data
                    },
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"MCP 데이터베이스 정보 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # MCP 서버는 앱 설정 후 마운트됨 (아래에서)

# OPTIONS 요청 처리 (CORS preflight)
@app.options("/mcp")
@app.options("/mcp/")
@app.options("/api/mcp")
@app.options("/v1/mcp")
@app.options("/jsonrpc")
async def mcp_options():
    """CORS preflight 요청 처리"""
    return {"status": "ok"}

# 일반적인 MCP 경로들에 대한 정보 제공
@app.get("/api/mcp")
@app.get("/v1/mcp")
@app.get("/jsonrpc")
async def mcp_alternative_paths():
    """다른 MCP 경로들에 대한 안내"""
    return {
        "message": "MCP endpoint is available at /mcp",
        "correct_endpoint": "/mcp",
        "server_info": {
            "name": "Seegene Bid Information Server",
            "protocol": "MCP via FastMCP",
            "transport": "SSE"
        }
    }

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
            "mcp": "/mcp" if FastMCP else "Not available (install fastmcp)",
            "crawler_apis": {
                "run_single": "POST /crawl/{site_name}",
                "run_all": "POST /crawl-all",
                "get_results": "GET /crawl-results",
                "get_site_results": "GET /crawl-results/{site_name}",
                "scheduled_jobs": "GET /scheduled-jobs",
                "add_schedule": "POST /schedule-crawler",
                "remove_schedule": "DELETE /schedule-crawler/{job_id}"
            },
            "advanced_search_apis": {
                "advanced_search": "POST /search/advanced",
                "keyword_suggestions": "GET /search/keyword-suggestions",
                "search_with_expansion": "POST /search/expanded"
            },
            "bid_data_apis": {
                "get_all_bids": "GET /bids",
                "get_bid_by_id": "GET /bids/{bid_id}",
                "search_bids": "GET /bids/search",
                "get_statistics": "GET /bids/stats"
            }
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


@app.get("/compliance/sites", response_model=SiteComplianceListResponse)
async def get_site_compliance_catalog():
    """지원 대상 조달 사이트의 크롤링 및 법적 유의사항 목록을 반환합니다."""

    entries = list_site_compliance()
    return {
        "success": True,
        "total": len(entries),
        "data": entries,
    }


@app.get("/compliance/sites/{slug}", response_model=SiteComplianceResponse)
async def get_site_compliance_detail(slug: str):
    """특정 조달 사이트의 크롤링 가이드라인을 조회합니다."""

    entry = get_site_compliance(slug)
    if not entry:
        raise HTTPException(status_code=404, detail="Site compliance entry not found")

    return {
        "success": True,
        "data": entry,
    }

@app.get("/crawler-status")
async def crawler_status_endpoint():
    """크롤러 상태 확인 엔드포인트"""
    try:
        status = crawler_manager.get_crawler_status()
        return status
    except Exception as e:
        logger.error(f"크롤러 상태 조회 실패: {e}")
        return {
            "error": str(e),
            "scheduler_running": False,
            "crawlers": {}
        }

@app.post("/crawl/{site_name}", response_model=CrawlerExecutionResponse)
async def run_single_crawler(site_name: str, request: CrawlerRequest = None):
    """특정 사이트에서 크롤링 실행"""
    try:
        logger.info(f"수동 크롤링 실행 요청: {site_name}")
        logger.info(f"🔍 요청 객체: {request}")

        keywords = request.keywords if request else None
        logger.info(f"🔍 추출된 키워드: {keywords}")
        result = await crawler_manager.run_crawler(site_name, keywords)

        return CrawlerExecutionResponse(
            success=True,
            message=f"{site_name} 크롤링 완료",
            result=result
        )

    except Exception as e:
        logger.error(f"크롤링 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crawl-all", response_model=AllCrawlerExecutionResponse)
async def run_all_crawlers_endpoint(request: CrawlerRequest = None):
    """모든 사이트에서 크롤링 실행"""
    try:
        logger.info("전체 크롤링 실행 요청")

        keywords = request.keywords if request else None
        result = await crawler_manager.run_all_crawlers(keywords)

        return AllCrawlerExecutionResponse(
            success=True,
            message="전체 크롤링 완료",
            result=result
        )

    except Exception as e:
        logger.error(f"전체 크롤링 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crawl-results", response_model=CrawlerResultsResponse)
async def get_crawler_results():
    """최근 크롤링 결과 조회"""
    try:
        results = crawler_manager.last_run_results

        return CrawlerResultsResponse(
            success=True,
            last_run_results=results,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"크롤링 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/crawl-results/{site_name}", response_model=SiteCrawlerResultResponse)
async def get_site_crawler_results(site_name: str):
    """특정 사이트 크롤링 결과 조회"""
    try:
        if site_name not in crawler_manager.last_run_results:
            raise HTTPException(status_code=404, detail=f"{site_name}의 크롤링 결과를 찾을 수 없습니다")

        result = crawler_manager.last_run_results[site_name]

        return SiteCrawlerResultResponse(
            success=True,
            site=site_name,
            result=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사이트별 크롤링 결과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scheduled-jobs", response_model=ScheduledJobsResponse)
async def get_scheduled_jobs_endpoint():
    """예약된 크롤링 작업 목록 조회"""
    try:
        jobs = crawler_manager.get_scheduled_jobs()

        return ScheduledJobsResponse(
            success=True,
            scheduled_jobs=jobs,
            scheduler_running=crawler_manager.is_running
        )

    except Exception as e:
        logger.error(f"예약된 작업 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedule-crawler", response_model=ScheduleResponse)
async def add_crawler_schedule_endpoint(request: ScheduleRequest):
    """크롤러 스케줄 추가"""
    try:
        if request.site_name not in ["G2B", "SAM.gov"]:
            raise HTTPException(status_code=400, detail="지원하지 않는 사이트입니다. G2B 또는 SAM.gov만 가능합니다.")

        success = await crawler_manager.add_custom_schedule(
            request.site_name,
            request.cron_expression,
            request.job_id
        )

        if success:
            return ScheduleResponse(
                success=True,
                message=f"{request.site_name} 스케줄이 추가되었습니다",
                site_name=request.site_name,
                cron_expression=request.cron_expression,
                job_id=request.job_id
            )
        else:
            raise HTTPException(status_code=400, detail="스케줄 추가에 실패했습니다")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스케줄 추가 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/schedule-crawler/{job_id}", response_model=ScheduleResponse)
async def remove_crawler_schedule_endpoint(job_id: str):
    """크롤러 스케줄 제거"""
    try:
        success = crawler_manager.remove_scheduled_job(job_id)

        if success:
            return ScheduleResponse(
                success=True,
                message=f"스케줄 작업 '{job_id}'가 제거되었습니다",
                job_id=job_id
            )
        else:
            raise HTTPException(status_code=404, detail="해당 작업을 찾을 수 없습니다")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스케줄 제거 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/advanced", response_model=AdvancedSearchResponse)
async def advanced_search_endpoint(request: AdvancedBidSearchRequest):
    """고급 입찰 검색"""
    try:
        logger.info("고급 검색 요청")

        result = await advanced_search_service.search_bids(request)

        return result

    except Exception as e:
        logger.error(f"고급 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/keyword-suggestions", response_model=KeywordSuggestionsResponse)
async def get_keyword_suggestions(
    keywords: str,
    max_suggestions: int = 20
):
    """키워드 제안"""
    try:
        keyword_list = [k.strip() for k in keywords.split(",")]
        logger.info(f"키워드 제안 요청: {keyword_list}")

        suggestions = keyword_engine.get_keyword_suggestions(keyword_list, max_suggestions)

        return KeywordSuggestionsResponse(
            success=True,
            original_keywords=keyword_list,
            suggestions=suggestions,
            total_suggestions=len(suggestions)
        )

    except Exception as e:
        logger.error(f"키워드 제안 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/expanded", response_model=AdvancedSearchResponse)
async def search_with_keyword_expansion(
    keywords: List[str],
    expansion_config: KeywordExpansion = None,
    countries: List[str] = None,
    limit: int = 50
):
    """키워드 확장을 포함한 간단한 검색"""
    try:
        logger.info(f"확장 검색 요청: 키워드={keywords}")

        # 기본 확장 설정
        if not expansion_config:
            expansion_config = KeywordExpansion()

        # 키워드 그룹 생성
        keyword_groups = [KeywordGroup(
            keywords=keywords,
            operator="or",
            weight=1.0
        )]

        # 검색 쿼리 구성
        search_query = AdvancedSearchQuery(
            keyword_groups=keyword_groups,
            countries=countries,
            limit=limit
        )

        # 요청 객체 생성
        request = AdvancedBidSearchRequest(
            query=search_query,
            expansion=expansion_config,
            include_metadata=True,
            explain_relevance=True
        )

        # 검색 실행
        result = await advanced_search_service.search_bids(request)

        return result

    except Exception as e:
        logger.error(f"확장 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/filters-help")
async def get_filters_help():
    """고급 필터링 도움말"""
    return {
        "available_operators": [
            "eq (같음)", "ne (다름)", "gt (초과)", "lt (미만)",
            "gte (이상)", "lte (이하)", "in (포함)", "not_in (제외)",
            "contains (문자열 포함)", "starts_with (시작)", "ends_with (끝남)"
        ],
        "available_fields": [
            "title", "organization", "country", "source_site",
            "relevance_score", "urgency_level", "currency",
            "announcement_date", "deadline_date"
        ],
        "relevance_levels": ["low (1-3점)", "medium (4-6점)", "high (7-8점)", "very_high (9-10점)"],
        "urgency_levels": ["low", "medium", "high", "urgent"],
        "sort_options": ["relevance", "date", "announcement_date", "deadline_date", "price", "urgency"],
        "expansion_features": [
            "synonyms (동의어)", "related_terms (관련용어)",
            "translations (번역)", "abbreviations (약어)"
        ]
    }

@app.get("/bids", response_model=BidListResponse)
async def get_all_bids(
    limit: int = 50,
    offset: int = 0,
    site: str = None,
    country: str = None,
    min_relevance: float = None
):
    """저장된 입찰 정보 목록 조회"""
    try:
        from src.database.connection import get_db_session, BidInfoModel
        from sqlalchemy import select, desc

        async with get_db_session() as session:
            # 쿼리 빌드
            query = select(BidInfoModel)

            # 필터 적용
            if site:
                query = query.where(BidInfoModel.source_site == site)
            if country:
                query = query.where(BidInfoModel.country == country)
            if min_relevance:
                query = query.where(BidInfoModel.relevance_score >= min_relevance)

            # 정렬 및 페이지네이션
            query = query.order_by(desc(BidInfoModel.created_at)).offset(offset).limit(limit)

            # 실행
            result = await session.execute(query)
            bids = result.scalars().all()

            # 결과 변환
            bid_list = []
            for bid in bids:
                # 안전한 날짜 변환 함수
                def safe_date_format(date_value):
                    if date_value is None:
                        return None
                    if hasattr(date_value, 'isoformat'):
                        return date_value.isoformat()
                    elif isinstance(date_value, str):
                        return date_value
                    else:
                        return str(date_value)

                bid_dict = {
                    "id": bid.id,
                    "title": bid.title,
                    "organization": bid.organization,
                    "bid_number": bid.bid_number,
                    "announcement_date": safe_date_format(bid.announcement_date),
                    "deadline_date": safe_date_format(bid.deadline_date),
                    "estimated_price": bid.estimated_price,
                    "currency": bid.currency,
                    "source_url": bid.source_url,
                    "source_site": bid.source_site,
                    "country": bid.country,
                    "relevance_score": bid.relevance_score,
                    "urgency_level": bid.urgency_level,
                    "status": bid.status,
                    "keywords": bid.keywords,
                    "created_at": safe_date_format(bid.created_at)
                }
                bid_list.append(bid_dict)

            # 총 개수 조회
            count_query = select(BidInfoModel)
            if site:
                count_query = count_query.where(BidInfoModel.source_site == site)
            if country:
                count_query = count_query.where(BidInfoModel.country == country)
            if min_relevance:
                count_query = count_query.where(BidInfoModel.relevance_score >= min_relevance)

            from sqlalchemy import func
            count_result = await session.execute(select(func.count()).select_from(count_query.subquery()))
            total_count = count_result.scalar()

            return {
                "success": True,
                "data": bid_list,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + limit < total_count
                },
                "filters": {
                    "site": site,
                    "country": country,
                    "min_relevance": min_relevance
                }
            }

    except Exception as e:
        logger.error(f"입찰 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bids/{bid_id}", response_model=BidDetailResponse)
async def get_bid_by_id(bid_id: int):
    """특정 입찰 정보 상세 조회"""
    try:
        from src.database.connection import get_db_session, BidInfoModel
        from sqlalchemy import select

        async with get_db_session() as session:
            result = await session.execute(select(BidInfoModel).where(BidInfoModel.id == bid_id))
            bid = result.scalar_one_or_none()

            if not bid:
                raise HTTPException(status_code=404, detail="해당 입찰 정보를 찾을 수 없습니다")

            # 안전한 날짜 변환 함수
            def safe_date_format(date_value):
                if date_value is None:
                    return None
                if hasattr(date_value, 'isoformat'):
                    return date_value.isoformat()
                elif isinstance(date_value, str):
                    return date_value
                else:
                    return str(date_value)

            bid_detail = {
                "id": bid.id,
                "title": bid.title,
                "organization": bid.organization,
                "bid_number": bid.bid_number,
                "announcement_date": safe_date_format(bid.announcement_date),
                "deadline_date": safe_date_format(bid.deadline_date),
                "estimated_price": bid.estimated_price,
                "currency": bid.currency,
                "source_url": bid.source_url,
                "source_site": bid.source_site,
                "country": bid.country,
                "relevance_score": bid.relevance_score,
                "urgency_level": bid.urgency_level,
                "status": bid.status,
                "keywords": bid.keywords,
                "extra_data": bid.extra_data,
                "created_at": safe_date_format(bid.created_at),
                "updated_at": safe_date_format(bid.updated_at)
            }

            return {
                "success": True,
                "data": bid_detail
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"입찰 정보 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bids/search", response_model=BidSearchResponse)
async def search_bids_endpoint(
    q: str,
    limit: int = 50,
    offset: int = 0,
    site: str = None,
    country: str = None
):
    """입찰 정보 검색"""
    try:
        keywords = [k.strip() for k in q.split(",") if k.strip()]
        logger.info(f"입찰 검색 요청: 키워드={keywords}")

        # 데이터베이스에서 검색
        results = await DatabaseManager.search_bids(keywords, limit + offset)

        # 오프셋 적용 (간단한 구현)
        paginated_results = results[offset:offset + limit] if results else []

        # 추가 필터 적용
        if site:
            paginated_results = [r for r in paginated_results if getattr(r, 'source_site', '') == site]
        if country:
            paginated_results = [r for r in paginated_results if getattr(r, 'country', '') == country]

        # 결과 변환
        bid_list = []
        for bid in paginated_results:
            bid_dict = {
                "id": getattr(bid, 'id', 0),
                "title": getattr(bid, 'title', ''),
                "organization": getattr(bid, 'organization', ''),
                "source_site": getattr(bid, 'source_site', ''),
                "country": getattr(bid, 'country', ''),
                "relevance_score": getattr(bid, 'relevance_score', 0.0),
                "source_url": getattr(bid, 'source_url', ''),
                "estimated_price": getattr(bid, 'estimated_price', ''),
                "deadline_date": getattr(bid, 'deadline_date', None),
                "urgency_level": getattr(bid, 'urgency_level', 'low')
            }
            bid_list.append(bid_dict)

        return {
            "success": True,
            "query": q,
            "keywords": keywords,
            "data": bid_list,
            "pagination": {
                "total": len(results),
                "limit": limit,
                "offset": offset,
                "returned": len(bid_list)
            }
        }

    except Exception as e:
        logger.error(f"입찰 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bids/stats", response_model=BidStatisticsResponse)
async def get_bid_statistics():
    """입찰 정보 통계"""
    try:
        stats = await DatabaseManager.get_database_stats()

        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test/db")
async def test_database():
    """데이터베이스 연결 테스트"""
    from src.database.connection import get_db_session, BidInfoModel
    from sqlalchemy import select

    try:
        async with get_db_session() as session:
            # 간단한 select 쿼리 테스트
            result = await session.execute(select(BidInfoModel).limit(1))
            bids = result.scalars().all()
            return {
                "success": True,
                "message": "데이터베이스 연결 성공",
                "found_bids": len(bids)
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"데이터베이스 연결 실패: {e}",
            "error": str(e)
        }

@app.post("/admin/reset-database")
async def reset_database():
    """데이터베이스 초기화 (모든 데이터 삭제)"""
    try:
        from src.database.connection import get_db_session, BidInfoModel
        from sqlalchemy import delete

        async with get_db_session() as session:
            # 모든 입찰 정보 삭제
            result = await session.execute(delete(BidInfoModel))
            deleted_count = result.rowcount
            await session.commit()

            logger.info(f"데이터베이스 초기화 완료: {deleted_count}건 삭제")

            return {
                "success": True,
                "message": "데이터베이스가 성공적으로 초기화되었습니다",
                "deleted_records": deleted_count,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        return {
            "success": False,
            "message": f"데이터베이스 초기화 실패: {e}",
            "error": str(e)
        }

@app.post("/admin/clean-dummy-data")
async def clean_dummy_data():
    """더미 데이터만 삭제"""
    try:
        from src.database.connection import get_db_session, BidInfoModel
        from sqlalchemy import delete, select

        async with get_db_session() as session:
            # 더미 데이터 확인
            dummy_result = await session.execute(
                select(BidInfoModel).where(
                    BidInfoModel.extra_data.contains('"dummy": true') |
                    BidInfoModel.bid_number.like('%DUMMY%') |
                    BidInfoModel.bid_number.like('%TEST%')
                )
            )
            dummy_bids = dummy_result.scalars().all()
            dummy_count = len(dummy_bids)

            if dummy_count > 0:
                # 더미 데이터 삭제
                await session.execute(
                    delete(BidInfoModel).where(
                        BidInfoModel.extra_data.contains('"dummy": true') |
                        BidInfoModel.bid_number.like('%DUMMY%') |
                        BidInfoModel.bid_number.like('%TEST%')
                    )
                )
                await session.commit()

            logger.info(f"더미 데이터 정리 완료: {dummy_count}건 삭제")

            return {
                "success": True,
                "message": "더미 데이터가 성공적으로 삭제되었습니다",
                "deleted_dummy_records": dummy_count,
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"더미 데이터 정리 실패: {e}")
        return {
            "success": False,
            "message": f"더미 데이터 정리 실패: {e}",
            "error": str(e)
        }

@app.get("/admin/database-info")
async def get_database_info():
    """데이터베이스 정보 조회"""
    try:
        from src.database.connection import get_db_session, BidInfoModel
        from sqlalchemy import select, func

        async with get_db_session() as session:
            # 전체 레코드 수
            total_result = await session.execute(select(func.count(BidInfoModel.id)))
            total_count = total_result.scalar()

            # 소스별 통계
            source_result = await session.execute(
                select(BidInfoModel.source_site, func.count(BidInfoModel.id))
                .group_by(BidInfoModel.source_site)
            )
            source_stats = {site: count for site, count in source_result.fetchall()}

            # 더미 데이터 수
            dummy_result = await session.execute(
                select(func.count(BidInfoModel.id)).where(
                    BidInfoModel.extra_data.contains('"dummy": true') |
                    BidInfoModel.bid_number.like('%DUMMY%') |
                    BidInfoModel.bid_number.like('%TEST%')
                )
            )
            dummy_count = dummy_result.scalar()

            # 최근 데이터
            recent_result = await session.execute(
                select(BidInfoModel.created_at, BidInfoModel.source_site)
                .order_by(BidInfoModel.created_at.desc())
                .limit(5)
            )
            recent_data = [
                {"created_at": row[0].isoformat() if row[0] else None, "source": row[1]}
                for row in recent_result.fetchall()
            ]

            return {
                "success": True,
                "database_info": {
                    "total_records": total_count,
                    "dummy_records": dummy_count,
                    "real_records": total_count - dummy_count,
                    "source_breakdown": source_stats,
                    "recent_entries": recent_data
                },
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"데이터베이스 정보 조회 실패: {e}")
        return {
            "success": False,
            "message": f"데이터베이스 정보 조회 실패: {e}",
            "error": str(e)
        }

# MCP 서버 마운트 (FastAPI 설정 완료 후)
if FastMCP:
    # MCP 상태 엔드포인트를 먼저 정의
    @app.get("/mcp-status")
    async def mcp_status():
        """MCP 서버 상태 확인"""
        return {
            "status": "active",
            "protocol": "MCP (Model Context Protocol)",
            "transport": "SSE (Server-Sent Events)",
            "server_name": "Seegene Bid Information Server",
            "tools_count": len(mcp._tools) if hasattr(mcp, '_tools') else 0,
            "note": "⚠️ SSE transport deprecated after Aug 2025"
        }

    # MCP 서버 마운트 (라우트 정의 후)
    app.mount("/mcp", mcp.sse_app())

if __name__ == "__main__":
    import uvicorn
    import os

    # SSL 설정
    ssl_config = {}
    if settings.SSL_ENABLED:
        cert_path = os.path.join(os.getcwd(), settings.SSL_CERTFILE)
        key_path = os.path.join(os.getcwd(), settings.SSL_KEYFILE)

        if os.path.exists(cert_path) and os.path.exists(key_path):
            ssl_config = {
                "ssl_keyfile": key_path,
                "ssl_certfile": cert_path
            }
            print(f"[SSL] HTTPS enabled with SSL certificates")
            print(f"[INFO] Server will run on https://{settings.HOST}:{settings.PORT}")
        else:
            print(f"[WARNING] SSL certificates not found, running HTTP instead")
            print(f"[INFO] Server will run on http://{settings.HOST}:{settings.PORT}")
    else:
        print(f"[INFO] Server will run on http://{settings.HOST}:{settings.PORT}")

    # SSL과 reload는 잘 작동하지 않으므로 SSL이 활성화된 경우 reload 비활성화
    reload_mode = settings.DEBUG and not ssl_config

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=reload_mode,
        **ssl_config
    )
