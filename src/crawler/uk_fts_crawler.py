"""
UK Find a Tender Service (FTS) 크롤러
영국 정부 조달 플랫폼 OCDS API 기반 데이터 수집
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

from ..crawler.base_crawler import BaseCrawler
from ..models.tender_notice import (
    TenderNotice, TenderStatus, TenderType, ProcurementMethod,
    TenderValue, Organization, Classification, TenderDocument,
    CurrencyCode
)
from ..utils.cpv_filter import cpv_filter


class UKFTSCrawler(BaseCrawler):
    """UK FTS OCDS API를 이용한 영국 입찰공고 수집"""

    def __init__(self):
        super().__init__("UK_FTS", "GB")

        # UK FTS OCDS API 설정
        self.api_base_url = "https://www.contractsfinder.service.gov.uk/api/rest/2"
        self.notices_endpoint = "/live.json"

        # 세션 설정
        self.session = None

        # 검색 매개변수
        self.default_params = {
            "limit": "100",
            "offset": "0",
            "orderBy": "publishedDate",
            "order": "desc"
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션 반환"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": "Seegene-BidCrawler/1.0",
                    "Accept": "application/json"
                }
            )
        return self.session

    async def collect_bids(self, days: int = 30) -> List[TenderNotice]:
        """UK FTS에서 입찰 공고 수집"""
        logger.info(f"🇬🇧 UK FTS에서 최근 {days}일간의 입찰공고 수집 시작")

        all_notices = []

        try:
            # 날짜 범위 설정
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 페이지별로 데이터 수집
            offset = 0
            limit = int(self.default_params["limit"])
            has_more = True

            while has_more and offset < 1000:  # 최대 1000건
                logger.info(f"📄 UK FTS 오프셋 {offset} 수집 중...")

                notices_data = await self._fetch_notices_page(
                    start_date, end_date, offset, limit
                )

                if not notices_data or len(notices_data) == 0:
                    break

                # 공고 처리
                for notice_data in notices_data:
                    try:
                        tender_notice = await self._parse_uk_fts_notice(notice_data)
                        if tender_notice:
                            # 날짜 필터링
                            if (tender_notice.published_date and
                                tender_notice.published_date >= start_date):
                                all_notices.append(tender_notice)
                    except Exception as e:
                        logger.error(f"❌ UK FTS 공고 파싱 오류: {e}")
                        continue

                # 다음 페이지
                offset += limit
                has_more = len(notices_data) == limit

                # API 요청 제한 준수
                await asyncio.sleep(0.5)

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

            logger.info(f"✅ UK FTS 수집 완료: 전체 {len(all_notices)}건 중 헬스케어 관련 {len(healthcare_notices)}건")
            return healthcare_notices

        except Exception as e:
            logger.error(f"❌ UK FTS 수집 실패: {e}")
            return []

        finally:
            if self.session and not self.session.closed:
                await self.session.close()

    async def _fetch_notices_page(self, start_date: datetime, end_date: datetime,
                                offset: int, limit: int) -> Optional[List[Dict]]:
        """UK FTS API에서 특정 페이지 데이터 가져오기"""
        try:
            session = await self._get_session()

            # 검색 매개변수 설정
            params = {
                "limit": str(limit),
                "offset": str(offset),
                "orderBy": "publishedDate",
                "order": "desc",
                "publishedFrom": start_date.strftime("%Y-%m-%d"),
                "publishedTo": end_date.strftime("%Y-%m-%d")
            }

            url = f"{self.api_base_url}{self.notices_endpoint}"

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # UK FTS는 다양한 응답 형식을 가질 수 있음
                    if isinstance(data, dict):
                        if "notices" in data:
                            return data["notices"]
                        elif "releases" in data:
                            return data["releases"]
                        else:
                            return [data]  # 단일 객체
                    elif isinstance(data, list):
                        return data
                    else:
                        logger.warning(f"⚠️ UK FTS 예상치 못한 응답 형식: {type(data)}")
                        return []
                else:
                    error_text = await response.text()
                    logger.error(f"❌ UK FTS API 오류 (오프셋 {offset}): {response.status} - {error_text}")
                    return None

        except Exception as e:
            logger.error(f"❌ UK FTS API 요청 실패 (오프셋 {offset}): {e}")
            return None

    async def _parse_uk_fts_notice(self, notice_data: Dict) -> Optional[TenderNotice]:
        """UK FTS 공고 데이터를 TenderNotice로 변환"""
        try:
            # 기본 정보 추출
            notice_id = str(notice_data.get("id", ""))

            # 제목 추출 (다양한 필드에서)
            title = (notice_data.get("title") or
                    notice_data.get("tender", {}).get("title") or
                    notice_data.get("planning", {}).get("project", "") or
                    "").strip()

            if not title:
                return None

            # 공고 URL 생성
            source_url = f"https://www.contractsfinder.service.gov.uk/notice/{notice_id}"

            # 발주기관 정보
            buyer_info = self._extract_buyer_info(notice_data)
            if not buyer_info:
                return None

            # 날짜 정보
            published_date = self._parse_uk_date(
                notice_data.get("publishedDate") or
                notice_data.get("date")
            )

            deadline_date = self._parse_uk_date(
                notice_data.get("tender", {}).get("tenderPeriod", {}).get("endDate") or
                notice_data.get("closingDate")
            )

            # 입찰 유형 및 상태 결정
            tender_type = self._determine_tender_type(notice_data)
            status = self._determine_tender_status(notice_data, deadline_date)

            # 금액 정보
            estimated_value = self._parse_tender_value(notice_data)

            # 분류 정보
            classifications = self._parse_classifications(notice_data)

            # 설명 정보
            description = self._extract_description(notice_data)

            # 문서 정보
            documents = self._extract_documents(notice_data)

            # TenderNotice 객체 생성
            tender_notice = TenderNotice(
                source_system="UK_FTS",
                source_id=notice_id,
                source_url=source_url,
                title=title,
                description=description,
                tender_type=tender_type,
                status=status,
                buyer=buyer_info,
                published_date=published_date,
                submission_deadline=deadline_date,
                estimated_value=estimated_value,
                country_code="GB",
                classifications=classifications,
                documents=documents,
                language="en",
                raw_data=notice_data
            )

            return tender_notice

        except Exception as e:
            logger.error(f"❌ UK FTS 공고 파싱 오류: {e}")
            return None

    def _extract_buyer_info(self, notice_data: Dict) -> Optional[Organization]:
        """발주기관 정보 추출"""
        try:
            # OCDS 표준 구조에서 buyer 정보 추출
            buyer_data = notice_data.get("buyer", {})

            if not buyer_data:
                # parties에서 buyer 역할을 가진 조직 찾기
                parties = notice_data.get("parties", [])
                for party in parties:
                    if "buyer" in party.get("roles", []):
                        buyer_data = party
                        break

            if not buyer_data:
                return None

            name = buyer_data.get("name", "").strip()
            if not name:
                return None

            # 연락처 정보
            contact_info = buyer_data.get("contactPoint", {})

            return Organization(
                name=name,
                identifier=buyer_data.get("id", ""),
                country_code="GB",
                contact_email=contact_info.get("email"),
                contact_phone=contact_info.get("telephone"),
                address=self._format_address(buyer_data.get("address", {}))
            )

        except Exception as e:
            logger.warning(f"⚠️ UK FTS buyer 정보 추출 실패: {e}")
            return None

    def _format_address(self, address_data: Dict) -> Optional[str]:
        """주소 정보 포맷팅"""
        if not address_data:
            return None

        address_parts = []

        for field in ["streetAddress", "locality", "region", "postalCode", "countryName"]:
            value = address_data.get(field, "").strip()
            if value:
                address_parts.append(value)

        return ", ".join(address_parts) if address_parts else None

    def _parse_uk_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """UK FTS 날짜 형식 파싱"""
        if not date_str:
            return None

        try:
            # ISO 8601 형식
            if "T" in date_str:
                # Z나 타임존 정보 처리
                date_str = date_str.replace("Z", "+00:00")
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

            # 간단한 날짜 형식들
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

        except Exception as e:
            logger.warning(f"⚠️ UK FTS 날짜 파싱 실패: {date_str} - {e}")

        return None

    def _determine_tender_type(self, notice_data: Dict) -> TenderType:
        """UK FTS 공고에서 입찰 유형 결정"""
        # OCDS mainProcurementCategory 확인
        main_category = notice_data.get("tender", {}).get("mainProcurementCategory", "")

        if main_category:
            if main_category.lower() == "works":
                return TenderType.WORKS
            elif main_category.lower() == "goods":
                return TenderType.GOODS
            elif main_category.lower() == "services":
                return TenderType.SERVICES

        # CPV 코드로 판단
        items = notice_data.get("tender", {}).get("items", [])
        for item in items:
            classification = item.get("classification", {})
            cpv_code = classification.get("id", "")

            if cpv_code:
                if cpv_code.startswith("45"):  # 건설
                    return TenderType.WORKS
                elif cpv_code.startswith(("03", "09", "15", "16", "18", "19", "33", "35")):  # 물품
                    return TenderType.GOODS

        return TenderType.SERVICES  # 기본값

    def _determine_tender_status(self, notice_data: Dict, deadline: Optional[datetime]) -> TenderStatus:
        """UK FTS 공고 상태 결정"""
        # OCDS tender status 확인
        tender_status = notice_data.get("tender", {}).get("status", "")

        if tender_status:
            if tender_status.lower() in ["active", "planning"]:
                return TenderStatus.ACTIVE
            elif tender_status.lower() in ["complete", "unsuccessful"]:
                return TenderStatus.CLOSED
            elif tender_status.lower() == "cancelled":
                return TenderStatus.CANCELLED

        # 마감일로 판단
        if deadline and deadline < datetime.now():
            return TenderStatus.CLOSED

        # awards 정보 확인
        awards = notice_data.get("awards", [])
        if awards:
            return TenderStatus.AWARDED

        return TenderStatus.ACTIVE

    def _parse_tender_value(self, notice_data: Dict) -> Optional[TenderValue]:
        """UK FTS 입찰 금액 정보 파싱"""
        try:
            # OCDS tender value 확인
            tender_data = notice_data.get("tender", {})
            value_data = tender_data.get("value", {})

            if value_data:
                amount = value_data.get("amount")
                currency = value_data.get("currency", "GBP")

                if amount and amount > 0:
                    return TenderValue(
                        amount=float(amount),
                        currency=CurrencyCode.GBP if currency == "GBP" else currency,
                        vat_included=False
                    )

            # planning budget 확인
            planning_data = notice_data.get("planning", {})
            budget_data = planning_data.get("budget", {})

            if budget_data:
                amount = budget_data.get("amount", {}).get("amount")
                currency = budget_data.get("amount", {}).get("currency", "GBP")

                if amount and amount > 0:
                    return TenderValue(
                        amount=float(amount),
                        currency=CurrencyCode.GBP if currency == "GBP" else currency,
                        vat_included=False
                    )

        except Exception as e:
            logger.warning(f"⚠️ UK FTS 금액 파싱 실패: {e}")

        return None

    def _parse_classifications(self, notice_data: Dict) -> List[Classification]:
        """UK FTS 분류 정보 파싱"""
        classifications = []

        try:
            # tender items의 classification 정보
            items = notice_data.get("tender", {}).get("items", [])

            for item in items:
                classification = item.get("classification", {})

                if classification:
                    scheme = classification.get("scheme", "CPV")
                    code = classification.get("id", "")
                    description = classification.get("description", "")

                    if code:
                        classifications.append(Classification(
                            scheme=scheme,
                            code=code,
                            description=description
                        ))

                # 추가 분류들
                additional_classifications = item.get("additionalClassifications", [])
                for add_class in additional_classifications:
                    scheme = add_class.get("scheme", "")
                    code = add_class.get("id", "")
                    description = add_class.get("description", "")

                    if code:
                        classifications.append(Classification(
                            scheme=scheme,
                            code=code,
                            description=description
                        ))

        except Exception as e:
            logger.warning(f"⚠️ UK FTS 분류 파싱 실패: {e}")

        return classifications

    def _extract_description(self, notice_data: Dict) -> Optional[str]:
        """UK FTS 공고에서 설명 추출"""
        description_parts = []

        try:
            # 다양한 설명 필드 확인
            desc_fields = [
                ("tender", "description"),
                ("planning", "rationale"),
                ("description", None)
            ]

            for field_path in desc_fields:
                if len(field_path) == 2 and field_path[1]:
                    desc = notice_data.get(field_path[0], {}).get(field_path[1], "")
                else:
                    desc = notice_data.get(field_path[0], "")

                if desc and isinstance(desc, str):
                    desc = desc.strip()
                    if desc and desc not in description_parts:
                        description_parts.append(desc)

        except Exception as e:
            logger.warning(f"⚠️ UK FTS 설명 추출 실패: {e}")

        return " ".join(description_parts) if description_parts else None

    def _extract_documents(self, notice_data: Dict) -> List[TenderDocument]:
        """UK FTS 관련 문서 추출"""
        documents = []

        try:
            # OCDS documents 확인
            doc_list = notice_data.get("tender", {}).get("documents", [])

            for doc in doc_list:
                title = doc.get("title", "")
                url = doc.get("url", "")
                doc_type = doc.get("documentType", "")
                language = doc.get("language", "en")

                if title and url:
                    documents.append(TenderDocument(
                        title=title,
                        url=url,
                        document_type=doc_type,
                        language=language
                    ))

        except Exception as e:
            logger.warning(f"⚠️ UK FTS 문서 추출 실패: {e}")

        return documents

    async def close(self):
        """리소스 정리"""
        if self.session and not self.session.closed:
            await self.session.close()