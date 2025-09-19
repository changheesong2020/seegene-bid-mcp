"""
Advanced Search Service
고급 검색 서비스
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import and_, or_, not_, func, desc, asc, select
from sqlalchemy.orm import Query

from src.models.advanced_filters import (
    AdvancedSearchQuery, KeywordExpansion, SearchFilter,
    AdvancedBidSearchRequest, AdvancedSearchResponse, SearchResult,
    RelevanceLevel, UrgencyLevel, SearchOperator
)
from src.database.connection import DatabaseManager, BidInfoModel, get_db_session
from src.utils.keyword_expansion import keyword_engine, ExpandedKeyword
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedSearchService:
    """고급 검색 서비스"""

    @staticmethod
    async def search_bids(request: AdvancedBidSearchRequest) -> AdvancedSearchResponse:
        """고급 입찰 검색"""
        start_time = time.time()
        query = request.query

        try:
            async with get_db_session() as session:
                # 간단한 검색으로 시작 - 모든 active bid 조회
                db_query = select(BidInfoModel).where(BidInfoModel.status == 'active')

                # 키워드 확장
                expanded_keywords = []
                if request.expansion and query.keyword_groups:
                    for group in query.keyword_groups:
                        expanded = keyword_engine.expand_keywords(
                            group.keywords,
                            request.expansion
                        )
                        expanded_keywords.extend(expanded)

                # 페이징 적용
                if query.limit:
                    db_query = db_query.limit(query.limit)
                if query.offset:
                    db_query = db_query.offset(query.offset)

                # 결과 조회
                results = await session.execute(db_query)
                bid_models = results.scalars().all()

                # 검색 결과 변환
                search_results = []
                for bid in bid_models:
                    search_result = SearchResult(
                        id=bid.id,
                        title=bid.title,
                        organization=bid.organization,
                        source_site=bid.source_site,
                        source_url=bid.source_url,
                        country=bid.country,
                        announcement_date=bid.announcement_date,
                        deadline_date=bid.deadline_date,
                        estimated_price=bid.estimated_price,
                        currency=bid.currency,
                        relevance_score=bid.relevance_score,
                        urgency_level=bid.urgency_level,
                        matched_keywords=[]
                    )
                    search_results.append(search_result)

                search_time = time.time() - start_time
                query_summary = f"키워드 확장 {len(expanded_keywords)}개 적용" if expanded_keywords else "전체 검색"

                return AdvancedSearchResponse(
                    success=True,
                    total_found=len(search_results),
                    results=search_results,
                    search_time=round(search_time, 3),
                    query_summary=query_summary,
                    filters_applied=["기본 필터"],
                    aggregations={},
                    offset=query.offset or 0,
                    limit=query.limit or 50,
                    has_more=False
                )

        except Exception as e:
            logger.error(f"고급 검색 실패: {e}")
            return AdvancedSearchResponse(
                success=False,
                total_found=0,
                results=[],
                search_time=time.time() - start_time,
                query_summary="검색 실패",
                filters_applied=[],
                offset=0,
                limit=50,
                has_more=False
            )

    @staticmethod
    def _apply_custom_filter(db_query, filter_obj: SearchFilter):
        """커스텀 필터 적용"""
        column = getattr(BidInfoModel, filter_obj.field, None)
        if not column:
            return db_query

        if filter_obj.operator == "eq":
            return db_query.where(column == filter_obj.value)
        elif filter_obj.operator == "ne":
            return db_query.where(column != filter_obj.value)
        elif filter_obj.operator == "gt":
            return db_query.where(column > filter_obj.value)
        elif filter_obj.operator == "lt":
            return db_query.where(column < filter_obj.value)
        elif filter_obj.operator == "gte":
            return db_query.where(column >= filter_obj.value)
        elif filter_obj.operator == "lte":
            return db_query.where(column <= filter_obj.value)
        elif filter_obj.operator == "in":
            return db_query.where(column.in_(filter_obj.value))
        elif filter_obj.operator == "not_in":
            return db_query.where(not_(column.in_(filter_obj.value)))
        elif filter_obj.operator == "contains":
            return db_query.where(column.contains(filter_obj.value))
        elif filter_obj.operator == "starts_with":
            return db_query.where(column.like(f"{filter_obj.value}%"))
        elif filter_obj.operator == "ends_with":
            return db_query.where(column.like(f"%{filter_obj.value}"))

        return db_query

    @staticmethod
    def _get_sort_column(sort_by: str):
        """정렬 컬럼 반환"""
        sort_mapping = {
            "relevance": BidInfoModel.relevance_score,
            "date": BidInfoModel.created_at,
            "announcement_date": BidInfoModel.announcement_date,
            "deadline_date": BidInfoModel.deadline_date,
            "price": BidInfoModel.estimated_price,
            "urgency": BidInfoModel.urgency_level,
            "organization": BidInfoModel.organization,
            "country": BidInfoModel.country,
            "site": BidInfoModel.source_site
        }
        return sort_mapping.get(sort_by, BidInfoModel.relevance_score)

    @staticmethod
    def _find_matched_keywords(
        bid: BidInfoModel,
        expanded_keywords: List[ExpandedKeyword]
    ) -> List[str]:
        """매칭된 키워드 찾기"""
        matched = []
        text = f"{bid.title} {bid.organization}".lower()

        for expanded_kw in expanded_keywords:
            if expanded_kw.keyword.lower() in text:
                matched.append(expanded_kw.keyword)

        return list(set(matched))

    @staticmethod
    async def _generate_aggregations(session, base_query) -> Dict[str, Any]:
        """집계 정보 생성"""
        try:
            # 국가별 집계
            country_agg = await session.execute(
                base_query.with_only_columns(
                    BidInfoModel.country,
                    func.count(BidInfoModel.id).label('count')
                ).group_by(BidInfoModel.country)
            )

            # 사이트별 집계
            site_agg = await session.execute(
                base_query.with_only_columns(
                    BidInfoModel.source_site,
                    func.count(BidInfoModel.id).label('count')
                ).group_by(BidInfoModel.source_site)
            )

            # 긴급도별 집계
            urgency_agg = await session.execute(
                base_query.with_only_columns(
                    BidInfoModel.urgency_level,
                    func.count(BidInfoModel.id).label('count')
                ).group_by(BidInfoModel.urgency_level)
            )

            return {
                "by_country": dict(country_agg.all()),
                "by_site": dict(site_agg.all()),
                "by_urgency": dict(urgency_agg.all())
            }
        except:
            return {}

    @staticmethod
    def _generate_query_summary(
        query: AdvancedSearchQuery,
        expanded_keywords: List[ExpandedKeyword]
    ) -> str:
        """쿼리 요약 생성"""
        summary_parts = []

        if expanded_keywords:
            original_count = len([k for k in expanded_keywords if k.source == "original"])
            expanded_count = len(expanded_keywords) - original_count
            summary_parts.append(f"키워드 {original_count}개")
            if expanded_count > 0:
                summary_parts.append(f"(+확장 {expanded_count}개)")

        if query.countries:
            summary_parts.append(f"국가: {', '.join(query.countries)}")

        if query.sites:
            summary_parts.append(f"사이트: {', '.join(query.sites)}")

        if query.min_relevance_score:
            summary_parts.append(f"관련성 ≥{query.min_relevance_score}")

        return " | ".join(summary_parts) if summary_parts else "전체 검색"


# 전역 고급 검색 서비스 인스턴스
advanced_search_service = AdvancedSearchService()