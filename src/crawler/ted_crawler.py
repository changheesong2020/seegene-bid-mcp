"""
TED (Tenders Electronic Daily) 크롤러
EU 공식 입찰공고 플랫폼 API 기반 데이터 수집
"""

import asyncio
import aiohttp
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

from ..crawler.base import BaseCrawler
from ..models.tender_notice import (
    TenderNotice, TenderStatus, TenderType, ProcurementMethod,
    TenderValue, Organization, Classification, TenderDocument,
    CurrencyCode
)
from ..utils.cpv_filter import cpv_filter


class TEDCrawler(BaseCrawler):
    """TED API를 이용한 EU 입찰공고 수집"""

    def __init__(self):
        super().__init__("TED", "EU")

        # TED eSenders API 설정 (실제 사이트에서 확인된 URL 구조)
        self.api_base_url = "https://ted.europa.eu"
        self.notices_endpoint = "/api/v3.0/notices/search"

        # 세션 설정
        self.session = None

        # 검색 매개변수
        self.default_params = {
            "scope": "3",  # 계약 공고
            "pageSize": "100",
            "sortField": "PD",  # 공개일순
            "sortOrder": "desc"
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션 반환"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",  # brotli 제거
                    "Connection": "keep-alive"
                }
            )
        return self.session

    async def login(self) -> bool:
        """TED API는 로그인이 필요없음"""
        return True

    async def search_bids(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """키워드로 입찰 검색 (BaseCrawler 호환)"""
        tender_notices = await self.collect_bids()
        # TenderNotice를 BaseCrawler 호환 Dict로 변환
        results = []
        for notice in tender_notices:
            # 모든 더미 데이터를 포함하되, 키워드 필터링은 선택적으로
            bid_info = {
                "title": notice.title,
                "organization": notice.buyer.name,
                "bid_number": notice.source_id,
                "announcement_date": notice.published_date.strftime("%Y-%m-%d") if notice.published_date else "",
                "deadline_date": notice.submission_deadline.strftime("%Y-%m-%d") if notice.submission_deadline else "",
                "estimated_price": f"€{notice.estimated_value.amount:,.0f}" if notice.estimated_value else "",
                "currency": "EUR",
                "source_url": notice.source_url,
                "source_site": "TED",
                "country": notice.country_code,
                "keywords": self._extract_keywords_from_notice(notice, keywords),
                "relevance_score": self.calculate_relevance_score(notice.title, notice.description or ""),
                "urgency_level": self.determine_urgency_level(notice.submission_deadline.strftime("%Y-%m-%d") if notice.submission_deadline else ""),
                "status": "active",
                "extra_data": {
                    "crawled_at": datetime.now().isoformat(),
                    "search_method": "ted_api",
                    "description": notice.description,
                    "tender_type": str(notice.tender_type) if notice.tender_type else "services",
                    "cpv_codes": [cls.code for cls in notice.classifications if cls.scheme == "CPV"]
                }
            }
            results.append(bid_info)

        logger.info(f"TED 검색 결과: {len(results)}건을 BaseCrawler 형식으로 변환")
        return results

    def _extract_keywords_from_notice(self, notice: TenderNotice, search_keywords: List[str]) -> List[str]:
        """TenderNotice에서 키워드 추출"""
        matched_keywords = []
        text = f"{notice.title} {notice.description or ''}".lower()

        for keyword in search_keywords:
            if keyword.lower() in text:
                matched_keywords.append(keyword)

        # 추가로 헬스케어 관련 키워드 확인
        healthcare_terms = ["medical", "healthcare", "diagnostic", "laboratory", "equipment"]
        for term in healthcare_terms:
            if term in text and term not in matched_keywords:
                matched_keywords.append(term)

        return matched_keywords

    async def collect_bids(self, days: int = 30) -> List[TenderNotice]:
        """TED에서 입찰 공고 수집 (현재 API 접근 불가로 더미 모드)"""
        logger.info(f"🇪🇺 TED에서 최근 {days}일간의 입찰공고 수집 시작")
        logger.warning("⚠️ TED API 접근 불가로 더미 데이터를 생성합니다")

        all_notices = []

        try:
            # 더미 데이터 생성
            dummy_notices = self._generate_dummy_notices(days)
            all_notices.extend(dummy_notices)

            # 헬스케어 관련 필터링
            healthcare_notices = []
            for notice in all_notices:
                cpv_codes = [cls.code for cls in notice.classifications if cls.scheme == "CPV"]

                if cpv_filter.is_healthcare_relevant(
                    cpv_codes=cpv_codes,
                    title=notice.title,
                    description=notice.description or "",
                    language="en",
                    threshold=0.2
                ):
                    notice.healthcare_relevant = True
                    notice.matched_keywords = cpv_filter.get_matched_keywords(
                        f"{notice.title} {notice.description or ''}", "en"
                    )
                    healthcare_notices.append(notice)

            logger.info(f"✅ TED 수집 완료: 전체 {len(all_notices)}건 중 헬스케어 관련 {len(healthcare_notices)}건")
            return healthcare_notices

        except Exception as e:
            logger.error(f"❌ TED 수집 실패: {e}")
            return []

        finally:
            if self.session and not self.session.closed:
                await self.session.close()

    async def _fetch_notices_page(self, start_date: datetime, end_date: datetime, page: int) -> Optional[Dict]:
        """TED 웹사이트에서 특정 페이지 데이터 가져오기 (웹 스크래핑)"""
        try:
            session = await self._get_session()

            # TED 검색 페이지 URL
            search_url = "https://ted.europa.eu/en/browse"

            # 검색 매개변수 설정
            params = {
                "q": "*",  # 모든 공고 검색
                "date": f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}",
                "page": page
            }

            async with session.get(search_url, params=params) as response:
                if response.status == 200:
                    html_content = await response.text()
                    # HTML 파싱 로직 추가 필요
                    return {"results": [], "total": 0}  # 임시 반환
                else:
                    logger.error(f"❌ TED 웹사이트 오류 (페이지 {page}): {response.status}")
                    return None

        except Exception as e:
            logger.error(f"❌ TED 웹사이트 요청 실패 (페이지 {page}): {e}")
            return None

    async def _parse_ted_notice(self, notice_data: Dict) -> Optional[TenderNotice]:
        """TED 공고 데이터를 TenderNotice로 변환"""
        try:
            # 기본 정보 추출
            notice_id = notice_data.get("ND", "")
            title = notice_data.get("TI", "").strip()

            if not title:
                return None

            # 공고 URL 생성
            source_url = f"https://ted.europa.eu/udl?uri=TED:NOTICE:{notice_id}:TEXT:EN:HTML"

            # 발주기관 정보
            aa_name = notice_data.get("AA", {}).get("ON", "Unknown Authority")
            country_code = notice_data.get("CY", "EU")

            buyer = Organization(
                name=aa_name,
                country_code=country_code,
                identifier=notice_data.get("AA", {}).get("OI", "")
            )

            # 날짜 정보
            published_date = self._parse_ted_date(notice_data.get("PD"))
            deadline_date = self._parse_ted_date(notice_data.get("TD"))

            # 입찰 유형 및 상태 결정
            tender_type = self._determine_tender_type(notice_data)
            status = self._determine_tender_status(notice_data, deadline_date)

            # 금액 정보
            estimated_value = self._parse_tender_value(notice_data)

            # CPV 분류 정보
            classifications = self._parse_cpv_codes(notice_data)

            # 설명 정보
            description = self._extract_description(notice_data)

            # TenderNotice 객체 생성
            tender_notice = TenderNotice(
                source_system="TED",
                source_id=notice_id,
                source_url=source_url,
                title=title,
                description=description,
                tender_type=tender_type,
                status=status,
                buyer=buyer,
                published_date=published_date,
                submission_deadline=deadline_date,
                estimated_value=estimated_value,
                country_code=country_code,
                classifications=classifications,
                language="en",
                raw_data=notice_data
            )

            return tender_notice

        except Exception as e:
            logger.error(f"❌ TED 공고 파싱 오류: {e}")
            return None

    def _parse_ted_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """TED 날짜 형식 파싱"""
        if not date_str:
            return None

        try:
            # TED 날짜 형식: YYYYMMDD
            if len(date_str) == 8 and date_str.isdigit():
                return datetime.strptime(date_str, "%Y%m%d")

            # ISO 형식도 시도
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        except Exception as e:
            logger.warning(f"⚠️ TED 날짜 파싱 실패: {date_str} - {e}")

        return None

    def _determine_tender_type(self, notice_data: Dict) -> TenderType:
        """TED 공고에서 입찰 유형 결정"""
        # TED 문서 유형 코드 확인
        doc_type = notice_data.get("TD", "")

        # CPV 코드로 유형 판단
        cpv_main = notice_data.get("CPV", {})
        if isinstance(cpv_main, dict):
            main_cpv = cpv_main.get("code", "")
        else:
            main_cpv = str(cpv_main)

        if main_cpv:
            if main_cpv.startswith("45"):  # 건설
                return TenderType.WORKS
            elif main_cpv.startswith(("03", "09", "15", "16", "18", "19", "33", "35")):  # 물품
                return TenderType.GOODS
            else:  # 서비스
                return TenderType.SERVICES

        return TenderType.SERVICES  # 기본값

    def _determine_tender_status(self, notice_data: Dict, deadline: Optional[datetime]) -> TenderStatus:
        """TED 공고 상태 결정"""
        if deadline and deadline < datetime.now():
            return TenderStatus.CLOSED

        # 계약 체결 공고인지 확인
        doc_type = notice_data.get("NC", "")
        if "award" in doc_type.lower() or "contract" in doc_type.lower():
            return TenderStatus.AWARDED

        return TenderStatus.ACTIVE

    def _parse_tender_value(self, notice_data: Dict) -> Optional[TenderValue]:
        """TED 입찰 금액 정보 파싱"""
        try:
            # 다양한 필드에서 금액 정보 찾기
            val_fields = ["VAL", "VL", "EST_VAL"]

            for field in val_fields:
                val_data = notice_data.get(field)
                if val_data:
                    if isinstance(val_data, dict):
                        amount = val_data.get("amount") or val_data.get("value")
                        currency = val_data.get("currency", "EUR")
                    elif isinstance(val_data, (int, float)):
                        amount = val_data
                        currency = "EUR"
                    else:
                        continue

                    if amount and amount > 0:
                        return TenderValue(
                            amount=float(amount),
                            currency=CurrencyCode.EUR if currency == "EUR" else currency,
                            vat_included=False
                        )

        except Exception as e:
            logger.warning(f"⚠️ TED 금액 파싱 실패: {e}")

        return None

    def _parse_cpv_codes(self, notice_data: Dict) -> List[Classification]:
        """TED CPV 코드 파싱"""
        classifications = []

        try:
            # 메인 CPV 코드
            main_cpv = notice_data.get("CPV")
            if main_cpv:
                if isinstance(main_cpv, dict):
                    code = main_cpv.get("code", "")
                    desc = main_cpv.get("text", "")
                else:
                    code = str(main_cpv)
                    desc = ""

                if code:
                    classifications.append(Classification(
                        scheme="CPV",
                        code=code,
                        description=desc
                    ))

            # 추가 CPV 코드들
            additional_cpvs = notice_data.get("ADDITIONAL_CPV", [])
            if isinstance(additional_cpvs, list):
                for cpv in additional_cpvs:
                    if isinstance(cpv, dict):
                        code = cpv.get("code", "")
                        desc = cpv.get("text", "")
                        if code:
                            classifications.append(Classification(
                                scheme="CPV",
                                code=code,
                                description=desc
                            ))

        except Exception as e:
            logger.warning(f"⚠️ TED CPV 파싱 실패: {e}")

        return classifications

    def _extract_description(self, notice_data: Dict) -> Optional[str]:
        """TED 공고에서 설명 추출"""
        description_parts = []

        # 다양한 설명 필드 확인
        desc_fields = ["DS", "SHORT_DESCR", "OBJECT_DESCR"]

        for field in desc_fields:
            desc = notice_data.get(field, "")
            if desc and isinstance(desc, str):
                desc = desc.strip()
                if desc and desc not in description_parts:
                    description_parts.append(desc)

        return " ".join(description_parts) if description_parts else None

    def _generate_dummy_notices(self, days: int) -> List[TenderNotice]:
        """더미 TED 공고 데이터 생성"""
        dummy_notices = []

        # 더미 데이터 템플릿
        dummy_templates = [
            {
                "title": "Medical Equipment Supply Contract",
                "description": "Supply of diagnostic equipment for hospitals including PCR testing machines",
                "country": "DE",
                "org": "German Health Ministry",
                "cpv": "33140000",  # Medical equipment
                "value": 500000
            },
            {
                "title": "Healthcare Digital Solutions",
                "description": "Implementation of digital health management system",
                "country": "FR",
                "org": "French Regional Health Authority",
                "cpv": "48000000",  # Software package
                "value": 750000
            },
            {
                "title": "Laboratory Testing Services",
                "description": "Outsourced laboratory testing services for molecular diagnostics",
                "country": "IT",
                "org": "Italian National Health Service",
                "cpv": "85145000",  # Laboratory services
                "value": 300000
            }
        ]

        for i, template in enumerate(dummy_templates):
            try:
                notice_id = f"TED-DUMMY-{datetime.now().strftime('%Y%m%d')}-{i+1:03d}"

                buyer = Organization(
                    name=template["org"],
                    country_code=template["country"],
                    identifier=f"ORG-{template['country']}-{i+1:03d}"
                )

                published_date = datetime.now() - timedelta(days=i+1)
                deadline_date = datetime.now() + timedelta(days=30+i*5)

                estimated_value = TenderValue(
                    amount=float(template["value"]),
                    currency=CurrencyCode.EUR,
                    vat_included=False
                )

                classifications = [Classification(
                    scheme="CPV",
                    code=template["cpv"],
                    description="Healthcare related classification"
                )]

                tender_notice = TenderNotice(
                    source_system="TED",
                    source_id=notice_id,
                    source_url=f"https://ted.europa.eu/udl?uri=TED:NOTICE:{notice_id}:TEXT:EN:HTML",
                    title=template["title"],
                    description=template["description"],
                    tender_type=TenderType.SERVICES,
                    status=TenderStatus.ACTIVE,
                    buyer=buyer,
                    published_date=published_date,
                    submission_deadline=deadline_date,
                    estimated_value=estimated_value,
                    country_code=template["country"],
                    classifications=classifications,
                    language="en",
                    raw_data={"dummy": True, "template_id": i}
                )

                dummy_notices.append(tender_notice)

            except Exception as e:
                logger.error(f"❌ 더미 데이터 생성 오류: {e}")
                continue

        logger.info(f"✅ TED 더미 데이터 {len(dummy_notices)}건 생성")
        return dummy_notices

    async def close(self):
        """리소스 정리"""
        if self.session and not self.session.closed:
            await self.session.close()