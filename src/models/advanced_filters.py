"""
Advanced Filtering Models
고급 필터링 및 검색 기능 모델
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class PriceRange(BaseModel):
    """가격 범위 모델"""
    min_price: Optional[float] = Field(default=None, description="최소 가격")
    max_price: Optional[float] = Field(default=None, description="최대 가격")
    currency: Optional[str] = Field(default=None, description="통화 (KRW, USD, EUR 등)")


class DateRange(BaseModel):
    """날짜 범위 모델"""
    start_date: Optional[date] = Field(default=None, description="시작일")
    end_date: Optional[date] = Field(default=None, description="종료일")


class UrgencyLevel(str, Enum):
    """긴급도 레벨"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RelevanceLevel(str, Enum):
    """관련성 레벨"""
    ALL = "all"
    LOW = "low"        # 1-3점
    MEDIUM = "medium"  # 4-6점
    HIGH = "high"      # 7-8점
    VERY_HIGH = "very_high"  # 9-10점


class SearchOperator(str, Enum):
    """검색 연산자"""
    AND = "and"  # 모든 키워드 포함
    OR = "or"    # 하나 이상의 키워드 포함
    NOT = "not"  # 특정 키워드 제외


class KeywordGroup(BaseModel):
    """키워드 그룹"""
    keywords: List[str] = Field(description="키워드 목록")
    operator: SearchOperator = Field(default=SearchOperator.OR, description="그룹 내 연산자")
    weight: float = Field(default=1.0, ge=0.1, le=5.0, description="가중치 (0.1-5.0)")


class AdvancedSearchQuery(BaseModel):
    """고급 검색 쿼리"""

    # 키워드 관련
    keyword_groups: List[KeywordGroup] = Field(
        default=[],
        description="키워드 그룹 목록"
    )
    exclude_keywords: Optional[List[str]] = Field(
        default=None,
        description="제외할 키워드"
    )
    exact_phrases: Optional[List[str]] = Field(
        default=None,
        description="정확한 구문 검색"
    )

    # 필터링 조건
    countries: Optional[List[str]] = Field(
        default=None,
        description="국가 필터 (KR, US, CN 등)"
    )
    sites: Optional[List[str]] = Field(
        default=None,
        description="사이트 필터 (G2B, SAM.gov 등)"
    )
    organizations: Optional[List[str]] = Field(
        default=None,
        description="발주기관 필터"
    )

    # 날짜 및 가격 범위
    announcement_date_range: Optional[DateRange] = Field(
        default=None,
        description="공고일 범위"
    )
    deadline_date_range: Optional[DateRange] = Field(
        default=None,
        description="마감일 범위"
    )
    price_range: Optional[PriceRange] = Field(
        default=None,
        description="가격 범위"
    )

    # 품질 필터
    min_relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="최소 관련성 점수 (0-10)"
    )
    relevance_level: Optional[RelevanceLevel] = Field(
        default=None,
        description="관련성 레벨"
    )
    urgency_levels: Optional[List[UrgencyLevel]] = Field(
        default=None,
        description="긴급도 레벨 필터"
    )

    # 정렬 및 제한
    sort_by: Optional[str] = Field(
        default="relevance",
        description="정렬 기준 (relevance, date, price, urgency)"
    )
    sort_order: Optional[str] = Field(
        default="desc",
        description="정렬 순서 (asc, desc)"
    )
    limit: Optional[int] = Field(
        default=50,
        ge=1,
        le=1000,
        description="결과 개수 제한"
    )
    offset: Optional[int] = Field(
        default=0,
        ge=0,
        description="결과 오프셋"
    )

    @validator('keyword_groups')
    def validate_keyword_groups(cls, v):
        if not v:
            # 기본 키워드 그룹 추가
            from src.config import crawler_config
            return [
                KeywordGroup(
                    keywords=crawler_config.SEEGENE_KEYWORDS['korean'],
                    operator=SearchOperator.OR,
                    weight=1.0
                )
            ]
        return v


class KeywordExpansion(BaseModel):
    """키워드 확장 설정"""

    enable_synonyms: bool = Field(
        default=True,
        description="동의어 확장 활성화"
    )
    enable_related_terms: bool = Field(
        default=True,
        description="관련 용어 확장 활성화"
    )
    enable_translations: bool = Field(
        default=True,
        description="다국어 번역 확장 활성화"
    )
    enable_abbreviations: bool = Field(
        default=True,
        description="약어 확장 활성화"
    )
    max_expansions_per_keyword: int = Field(
        default=5,
        ge=1,
        le=20,
        description="키워드당 최대 확장 수"
    )


class SearchFilter(BaseModel):
    """검색 필터"""
    field: str = Field(description="필터링할 필드명")
    operator: str = Field(description="연산자 (eq, ne, gt, lt, gte, lte, in, not_in, contains, starts_with, ends_with)")
    value: Union[str, int, float, bool, List[Any]] = Field(description="필터 값")


class AdvancedBidSearchRequest(BaseModel):
    """고급 입찰 검색 요청"""

    query: AdvancedSearchQuery = Field(description="검색 쿼리")
    expansion: Optional[KeywordExpansion] = Field(
        default=None,
        description="키워드 확장 설정"
    )
    custom_filters: Optional[List[SearchFilter]] = Field(
        default=None,
        description="커스텀 필터"
    )
    include_metadata: bool = Field(
        default=False,
        description="메타데이터 포함 여부"
    )
    explain_relevance: bool = Field(
        default=False,
        description="관련성 점수 설명 포함 여부"
    )


class SearchResult(BaseModel):
    """검색 결과 항목"""

    # 기본 정보
    id: int = Field(description="ID")
    title: str = Field(description="제목")
    organization: str = Field(description="발주기관")
    source_site: str = Field(description="출처 사이트")
    source_url: str = Field(description="원문 URL")
    country: str = Field(description="국가")

    # 날짜 및 가격
    announcement_date: Optional[str] = Field(default=None, description="공고일")
    deadline_date: Optional[str] = Field(default=None, description="마감일")
    estimated_price: Optional[str] = Field(default=None, description="추정 가격")
    currency: Optional[str] = Field(default=None, description="통화")

    # 품질 지표
    relevance_score: float = Field(description="관련성 점수")
    urgency_level: str = Field(description="긴급도")
    matched_keywords: List[str] = Field(default=[], description="매칭된 키워드")

    # 확장 정보 (옵션)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="메타데이터")
    relevance_explanation: Optional[str] = Field(default=None, description="관련성 점수 설명")


class AdvancedSearchResponse(BaseModel):
    """고급 검색 응답"""

    success: bool = Field(description="검색 성공 여부")
    total_found: int = Field(description="총 발견 건수")
    results: List[SearchResult] = Field(description="검색 결과")

    # 검색 통계
    search_time: float = Field(description="검색 소요 시간(초)")
    query_summary: str = Field(description="검색 쿼리 요약")
    filters_applied: List[str] = Field(description="적용된 필터 목록")

    # 집계 정보
    aggregations: Optional[Dict[str, Any]] = Field(
        default=None,
        description="집계 정보 (국가별, 사이트별, 긴급도별 등)"
    )

    # 페이징
    offset: int = Field(description="오프셋")
    limit: int = Field(description="제한")
    has_more: bool = Field(description="더 많은 결과 존재 여부")


class KeywordSuggestion(BaseModel):
    """키워드 제안"""
    keyword: str = Field(description="제안 키워드")
    frequency: int = Field(description="등장 빈도")
    relevance: float = Field(description="관련도")
    source: str = Field(description="제안 출처 (synonym, related, translation, abbreviation)")


class KeywordSuggestionsResponse(BaseModel):
    """키워드 제안 응답"""
    success: bool = Field(description="요청 성공 여부")
    original_keywords: List[str] = Field(description="원본 키워드")
    suggestions: List[KeywordSuggestion] = Field(description="제안된 키워드")
    total_suggestions: int = Field(description="총 제안 수")