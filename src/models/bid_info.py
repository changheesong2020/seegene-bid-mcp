"""
Bid information data models
입찰 정보 데이터 모델
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator


class BidInfo(BaseModel):
    """입찰 정보 모델"""
    
    title: str
    organization: Optional[str] = None
    bid_number: Optional[str] = None
    announcement_date: Optional[str] = None
    deadline_date: Optional[str] = None
    estimated_price: Optional[str] = None
    currency: str = 'KRW'
    source_url: str
    source_site: str
    country: str = 'KR'
    keywords: List[str] = []
    relevance_score: float = 0.0
    urgency_level: str = 'low'
    status: str = 'active'
    metadata: Dict[str, Any] = {}
    
    @validator('relevance_score')
    def validate_relevance_score(cls, v):
        """관련성 점수 검증 (0.0 ~ 1.0)"""
        return max(0.0, min(1.0, v))
    
    @validator('urgency_level')
    def validate_urgency_level(cls, v):
        """긴급도 레벨 검증"""
        allowed = ['low', 'medium', 'high', 'critical']
        return v if v in allowed else 'low'


class CrawlingResult(BaseModel):
    """크롤링 결과 모델"""
    
    site_name: str
    total_found: int
    items_processed: int
    success_count: int
    error_count: int
    errors: List[str] = []
    execution_time: float
    results: List[BidInfo] = []
