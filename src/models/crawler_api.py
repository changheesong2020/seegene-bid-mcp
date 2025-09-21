"""
Crawler API Pydantic Models
크롤러 API 요청/응답 모델
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CrawlerRequest(BaseModel):
    """크롤링 요청 모델"""
    keywords: Optional[List[str]] = Field(
        default=None,
        description="검색할 키워드 목록. 기본값은 설정된 씨젠 키워드 사용"
    )


class CrawlerResult(BaseModel):
    """크롤링 결과 모델"""
    success: bool = Field(description="크롤링 성공 여부")
    site: str = Field(description="크롤링한 사이트명")
    total_found: int = Field(description="발견된 입찰 정보 수")
    execution_time: Optional[float] = Field(default=0.0, description="실행 시간(초)")
    login_success: Optional[bool] = Field(default=False, description="로그인 성공 여부")
    error: Optional[str] = Field(default=None, description="오류 메시지")


class AllCrawlerResult(BaseModel):
    """전체 크롤링 결과 모델"""
    success: bool = Field(description="전체 크롤링 성공 여부")
    total_crawlers: int = Field(description="총 크롤러 수")
    successful_crawlers: int = Field(description="성공한 크롤러 수")
    total_found: int = Field(description="전체 발견된 입찰 정보 수")
    results: Dict[str, CrawlerResult] = Field(description="사이트별 결과")
    run_time: str = Field(description="실행 시간 ISO 포맷")


class CrawlerStatus(BaseModel):
    """크롤러 상태 모델"""
    has_credentials: bool = Field(description="인증 정보 보유 여부")
    can_make_requests: bool = Field(description="요청 가능 여부")
    status: str = Field(description="상태: configured/partial/not_configured")
    last_run: Optional[str] = Field(default=None, description="마지막 실행 시간")
    last_success: bool = Field(description="마지막 실행 성공 여부")
    last_found: int = Field(description="마지막 실행에서 발견된 항목 수")


class AllCrawlerStatus(BaseModel):
    """전체 크롤러 상태 모델"""
    scheduler_running: bool = Field(description="스케줄러 실행 여부")
    crawlers: Dict[str, CrawlerStatus] = Field(description="크롤러별 상태")


class ScheduledJob(BaseModel):
    """예약된 작업 모델"""
    id: str = Field(description="작업 ID")
    name: str = Field(description="작업 이름")
    next_run: Optional[str] = Field(default=None, description="다음 실행 시간 ISO 포맷")
    trigger: str = Field(description="트리거 설정")


class ScheduleRequest(BaseModel):
    """스케줄 추가 요청 모델"""
    site_name: str = Field(description="사이트명 (G2B 또는 SAM.gov)")
    cron_expression: str = Field(
        description="크론 표현식 (분 시 일 월 요일)",
        example="0 9 * * *"
    )
    job_id: Optional[str] = Field(
        default=None,
        description="작업 ID (미지정시 자동 생성)"
    )


class APIResponse(BaseModel):
    """기본 API 응답 모델"""
    success: bool = Field(description="요청 성공 여부")
    message: str = Field(description="응답 메시지")


class CrawlerExecutionResponse(APIResponse):
    """크롤러 실행 응답 모델"""
    result: CrawlerResult = Field(description="크롤링 결과")


class AllCrawlerExecutionResponse(APIResponse):
    """전체 크롤러 실행 응답 모델"""
    result: AllCrawlerResult = Field(description="전체 크롤링 결과")


class CrawlerResultsResponse(BaseModel):
    """크롤링 결과 조회 응답"""
    success: bool = Field(description="요청 성공 여부")
    last_run_results: Dict[str, Dict[str, Any]] = Field(description="최근 실행 결과")
    timestamp: str = Field(description="조회 시간 ISO 포맷")


class SiteCrawlerResultResponse(BaseModel):
    """사이트별 크롤링 결과 응답"""
    success: bool = Field(description="요청 성공 여부")
    site: str = Field(description="사이트명")
    result: Dict[str, Any] = Field(description="크롤링 결과")


class ScheduledJobsResponse(BaseModel):
    """예약된 작업 조회 응답"""
    success: bool = Field(description="요청 성공 여부")
    scheduled_jobs: List[ScheduledJob] = Field(description="예약된 작업 목록")
    scheduler_running: bool = Field(description="스케줄러 실행 상태")


class ScheduleResponse(APIResponse):
    """스케줄 관리 응답 모델"""
    site_name: Optional[str] = Field(default=None, description="사이트명")
    cron_expression: Optional[str] = Field(default=None, description="크론 표현식")
    job_id: Optional[str] = Field(default=None, description="작업 ID")


# Bid Data API Models
class BidItem(BaseModel):
    """입찰 정보 아이템"""
    id: int = Field(description="입찰 정보 ID")
    title: str = Field(description="입찰 제목")
    organization: str = Field(description="발주 기관")
    bid_number: Optional[str] = Field(default=None, description="입찰 번호")
    announcement_date: Optional[str] = Field(default=None, description="공고일")
    deadline_date: Optional[str] = Field(default=None, description="마감일")
    estimated_price: Optional[str] = Field(default=None, description="추정 가격")
    currency: Optional[str] = Field(default=None, description="통화")
    source_url: Optional[str] = Field(default=None, description="원본 URL")
    source_site: str = Field(description="출처 사이트")
    country: str = Field(description="국가 코드")
    relevance_score: float = Field(description="관련성 점수")
    urgency_level: str = Field(description="긴급도")
    status: str = Field(description="상태")
    keywords: Optional[List[str]] = Field(default=None, description="매칭된 키워드")
    created_at: Optional[str] = Field(default=None, description="생성일시")


class BidDetailItem(BidItem):
    """입찰 정보 상세 아이템"""
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="추가 데이터")
    updated_at: Optional[str] = Field(default=None, description="수정일시")


class PaginationInfo(BaseModel):
    """페이지네이션 정보"""
    total: int = Field(description="전체 항목 수")
    limit: int = Field(description="페이지당 항목 수")
    offset: int = Field(description="시작 오프셋")
    has_next: bool = Field(description="다음 페이지 존재 여부")


class BidListResponse(BaseModel):
    """입찰 목록 응답"""
    success: bool = Field(description="성공 여부")
    data: List[BidItem] = Field(description="입찰 정보 목록")
    pagination: PaginationInfo = Field(description="페이지네이션 정보")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="적용된 필터")


class BidDetailResponse(BaseModel):
    """입찰 상세 응답"""
    success: bool = Field(description="성공 여부")
    data: BidDetailItem = Field(description="입찰 상세 정보")


class BidSearchResponse(BaseModel):
    """입찰 검색 응답"""
    success: bool = Field(description="성공 여부")
    query: str = Field(description="검색어")
    keywords: List[str] = Field(description="파싱된 키워드")
    data: List[BidItem] = Field(description="검색 결과")
    pagination: Dict[str, Any] = Field(description="페이지네이션 정보")


class BidStatisticsResponse(BaseModel):
    """입찰 통계 응답"""
    success: bool = Field(description="성공 여부")
    statistics: Dict[str, Any] = Field(description="통계 정보")
    timestamp: str = Field(description="조회 시점")