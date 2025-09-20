"""
통합 입찰공고 스키마 모델
Common tender notice schema for multi-source bid collection system
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, model_validator


class TenderStatus(str, Enum):
    """입찰 상태"""
    ACTIVE = "active"           # 진행중
    CLOSED = "closed"          # 마감
    AWARDED = "awarded"        # 낙찰완료
    CANCELLED = "cancelled"    # 취소
    PLANNED = "planned"        # 계획


class TenderType(str, Enum):
    """입찰 유형"""
    GOODS = "goods"            # 물품
    SERVICES = "services"      # 용역/서비스
    WORKS = "works"           # 공사
    FOREIGN = "foreign"       # 외자
    OTHER = "other"           # 기타


class ProcurementMethod(str, Enum):
    """조달 방식"""
    OPEN = "open"                    # 공개입찰
    SELECTIVE = "selective"          # 제한입찰
    NEGOTIATED = "negotiated"        # 수의계약
    COMPETITIVE_DIALOGUE = "competitive_dialogue"  # 경쟁대화
    FRAMEWORK = "framework"          # 프레임워크
    OTHER = "other"                  # 기타


class CurrencyCode(str, Enum):
    """통화 코드"""
    KRW = "KRW"  # 한국 원
    EUR = "EUR"  # 유로
    USD = "USD"  # 미국 달러
    GBP = "GBP"  # 영국 파운드


class TenderValue(BaseModel):
    """입찰 금액 정보"""
    amount: Optional[Decimal] = Field(None, description="입찰 금액")
    currency: Optional[CurrencyCode] = Field(None, description="통화")
    vat_included: Optional[bool] = Field(None, description="VAT 포함 여부")

    class Config:
        use_enum_values = True


class Organization(BaseModel):
    """기관/업체 정보"""
    name: str = Field(..., description="기관명")
    identifier: Optional[str] = Field(None, description="기관 식별자")
    country_code: Optional[str] = Field(None, description="국가 코드")
    contact_email: Optional[str] = Field(None, description="연락처 이메일")
    contact_phone: Optional[str] = Field(None, description="연락처 전화")
    address: Optional[str] = Field(None, description="주소")


class TenderDocument(BaseModel):
    """입찰 관련 문서"""
    title: str = Field(..., description="문서명")
    url: Optional[str] = Field(None, description="문서 URL")
    document_type: Optional[str] = Field(None, description="문서 유형")
    language: Optional[str] = Field(None, description="언어")


class Classification(BaseModel):
    """분류 정보 (CPV, 업종 등)"""
    scheme: str = Field(..., description="분류 체계 (CPV, UNSPSC 등)")
    code: str = Field(..., description="분류 코드")
    description: Optional[str] = Field(None, description="분류 설명")


class TenderNotice(BaseModel):
    """통합 입찰공고 모델"""

    # 기본 식별 정보
    source_system: str = Field(..., description="출처 시스템 (G2B, TED, UK_FTS 등)")
    source_id: str = Field(..., description="출처 시스템의 고유 ID")
    source_url: Optional[str] = Field(None, description="원본 공고 URL")

    # 공고 기본 정보
    title: str = Field(..., description="입찰 제목")
    description: Optional[str] = Field(None, description="입찰 내용/설명")
    tender_type: TenderType = Field(..., description="입찰 유형")
    status: TenderStatus = Field(default=TenderStatus.ACTIVE, description="입찰 상태")
    procurement_method: Optional[ProcurementMethod] = Field(None, description="조달 방식")

    # 발주기관 정보
    buyer: Organization = Field(..., description="발주기관")

    # 일정 정보
    published_date: Optional[datetime] = Field(None, description="공고일")
    submission_deadline: Optional[datetime] = Field(None, description="제출 마감일")
    opening_date: Optional[datetime] = Field(None, description="개찰일")

    # 금액 정보
    estimated_value: Optional[TenderValue] = Field(None, description="추정 가격")
    maximum_value: Optional[TenderValue] = Field(None, description="최대 가격")

    # 지역 정보
    country_code: str = Field(..., description="국가 코드 (ISO 3166-1 alpha-2)")
    region: Optional[str] = Field(None, description="지역")

    # 분류 정보
    classifications: List[Classification] = Field(default_factory=list, description="분류 정보")

    # 문서 정보
    documents: List[TenderDocument] = Field(default_factory=list, description="관련 문서")

    # 키워드 매칭 정보
    matched_keywords: List[str] = Field(default_factory=list, description="매칭된 키워드")
    healthcare_relevant: bool = Field(default=False, description="헬스케어 관련 여부")

    # 메타데이터
    collected_at: datetime = Field(default_factory=datetime.now, description="수집 시간")
    last_updated: Optional[datetime] = Field(None, description="최종 업데이트 시간")
    language: Optional[str] = Field(None, description="공고 언어")

    # 원본 데이터 (디버깅/분석용)
    raw_data: Optional[Dict[str, Any]] = Field(None, description="원본 데이터")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v) if v else None
        }

    @validator('country_code')
    def validate_country_code(cls, v):
        """국가 코드 검증"""
        if v and len(v) != 2:
            raise ValueError('Country code must be 2 characters (ISO 3166-1 alpha-2)')
        return v.upper() if v else v

    @validator('matched_keywords')
    def lowercase_keywords(cls, v):
        """키워드를 소문자로 변환"""
        return [kw.lower() for kw in v] if v else []

    @model_validator(mode='before')
    @classmethod
    def validate_dates(cls, values):
        """날짜 검증"""
        if isinstance(values, dict):
            published = values.get('published_date')
            deadline = values.get('submission_deadline')
            opening = values.get('opening_date')

            if published and deadline and deadline < published:
                raise ValueError('Submission deadline cannot be before published date')

            if deadline and opening and opening < deadline:
                raise ValueError('Opening date cannot be before submission deadline')

        return values


class TenderSearchQuery(BaseModel):
    """입찰 검색 쿼리"""
    keywords: Optional[List[str]] = Field(None, description="검색 키워드")
    countries: Optional[List[str]] = Field(None, description="국가 코드 필터")
    tender_types: Optional[List[TenderType]] = Field(None, description="입찰 유형 필터")
    status: Optional[List[TenderStatus]] = Field(None, description="상태 필터")
    min_value: Optional[Decimal] = Field(None, description="최소 금액")
    max_value: Optional[Decimal] = Field(None, description="최대 금액")
    currency: Optional[CurrencyCode] = Field(None, description="통화 필터")
    published_from: Optional[date] = Field(None, description="공고일 시작")
    published_to: Optional[date] = Field(None, description="공고일 종료")
    deadline_from: Optional[date] = Field(None, description="마감일 시작")
    deadline_to: Optional[date] = Field(None, description="마감일 종료")
    cpv_codes: Optional[List[str]] = Field(None, description="CPV 코드 필터")
    healthcare_only: bool = Field(default=False, description="헬스케어만 검색")

    class Config:
        use_enum_values = True


class TenderSearchResult(BaseModel):
    """입찰 검색 결과"""
    query: TenderSearchQuery = Field(..., description="검색 쿼리")
    results: List[TenderNotice] = Field(..., description="검색 결과")
    total_count: int = Field(..., description="전체 결과 수")
    page: int = Field(default=1, description="페이지 번호")
    page_size: int = Field(default=50, description="페이지 크기")
    execution_time_ms: Optional[int] = Field(None, description="실행 시간 (밀리초)")

    class Config:
        use_enum_values = True