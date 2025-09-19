"""
Filtering models for bid search
입찰 검색을 위한 필터링 모델
"""

from typing import List, Optional
from pydantic import BaseModel


class BidFilter(BaseModel):
    """입찰 정보 필터"""
    
    keywords: List[str] = []
    days_range: int = 7
    countries: List[str] = ["KR", "US"]
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    urgent_only: bool = False
    source_sites: List[str] = []
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return self.dict(exclude_none=True)
