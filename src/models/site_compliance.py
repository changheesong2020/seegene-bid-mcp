"""Pydantic models for site compliance metadata."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SiteComplianceDetails(BaseModel):
    """Represents compliance and crawling guidance for a procurement site."""

    slug: str = Field(description="Unique identifier for the site entry")
    country: str = Field(description="Country name or code for the site")
    site_name: str = Field(description="Official name of the procurement platform")
    base_urls: List[str] = Field(description="Relevant base URLs for the platform")
    robots_txt_url: Optional[str] = Field(
        default=None,
        description="Direct URL to the robots.txt file if known"
    )
    robots_notes: str = Field(description="Summary of the robots.txt availability or findings")
    crawling_constraints: str = Field(
        description="Practical considerations or limitations when crawling the site"
    )
    legal_notes: str = Field(
        description="Copyright or legal reuse considerations for collected materials"
    )
    last_reviewed: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the information was last reviewed"
    )


class SiteComplianceListResponse(BaseModel):
    """Response model containing a collection of site compliance entries."""

    success: bool = Field(description="Indicates whether the request succeeded")
    total: int = Field(description="Number of entries returned")
    data: List[SiteComplianceDetails] = Field(
        description="Collection of site compliance entries"
    )


class SiteComplianceResponse(BaseModel):
    """Response model returning a single site compliance entry."""

    success: bool = Field(description="Indicates whether the request succeeded")
    data: SiteComplianceDetails = Field(description="Compliance entry for the requested site")
