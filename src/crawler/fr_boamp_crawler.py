"""
French BOAMP/PLACE 크롤러
프랑스 공공조달 플랫폼 데이터 수집
"""

import asyncio
import aiohttp
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote

from ..utils.logger import get_logger
from ..crawler.base import BaseCrawler
from ..models.tender_notice import (
    TenderNotice, TenderStatus, TenderType, ProcurementMethod,
    TenderValue, Organization, Classification, TenderDocument,
    CurrencyCode
)
from ..utils.cpv_filter import cpv_filter

logger = get_logger(__name__)


class FranceBOAMPCrawler(BaseCrawler):
    """프랑스 BOAMP/PLACE 공공조달 크롤러"""

    def __init__(self):
        super().__init__("FR_BOAMP", "FR")

        # BOAMP API 설정
        self.boamp_base_url = "https://www.boamp.fr"
        self.place_base_url = "https://www.marches-publics.gouv.fr"

        # RSS/XML 피드 URL들
        self.rss_feeds = [
            "https://www.boamp.fr/avis/rss",
            "https://www.boamp.fr/rss/boamp.xml"
        ]

        # 검색 API 엔드포인트 (추정)
        self.search_api_url = f"{self.boamp_base_url}/api/search"

        # CPV 코드 필터 (의료기기 관련)
        self.healthcare_cpv_codes = [
            "33100000",  # 의료기기
            "33140000",  # 의료용품
            "33183000",  # 진단기기
            "33184000",  # 실험실 기기
            "33600000",  # 의약품
            "33700000",  # 개인보호장비
        ]

    async def crawl(self, keywords: List[str] = None) -> Dict[str, Any]:
        """크롤링 실행"""
        logger.info(f"프랑스 BOAMP 크롤링 시작 - 키워드: {keywords}")

        results = []

        try:
            # RSS 피드 수집
            rss_results = await self._crawl_rss_feeds(keywords)
            results.extend(rss_results)

            # 웹 검색 (키워드가 있는 경우)
            if keywords:
                web_results = await self._crawl_web_search(keywords)
                results.extend(web_results)

            # 결과 중복 제거
            unique_results = self._remove_duplicates(results)

            logger.info(f"프랑스 BOAMP 크롤링 완료 - 총 {len(unique_results)}건 수집")

            return {
                "success": True,
                "total_collected": len(unique_results),
                "results": unique_results,
                "source": "FR_BOAMP",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"프랑스 BOAMP 크롤링 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": results,
                "source": "FR_BOAMP",
                "timestamp": datetime.now().isoformat()
            }

    async def _crawl_rss_feeds(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """RSS 피드에서 공고 수집"""
        results = []

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:

            for feed_url in self.rss_feeds:
                try:
                    logger.info(f"RSS 피드 크롤링: {feed_url}")

                    async with session.get(feed_url) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed_results = await self._parse_rss_feed(content, keywords)
                            results.extend(feed_results)
                            logger.info(f"RSS에서 {len(feed_results)}건 수집")
                        else:
                            logger.warning(f"RSS 피드 접근 실패: {response.status}")

                except Exception as e:
                    logger.warning(f"RSS 피드 크롤링 오류 {feed_url}: {e}")

        return results

    async def _parse_rss_feed(self, content: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """RSS 피드 파싱"""
        results = []

        try:
            # XML 파싱 시도
            root = ET.fromstring(content)

            # RSS 2.0 형식 처리
            items = root.findall(".//item")

            for item in items:
                try:
                    title = item.find("title")
                    title_text = title.text if title is not None else ""

                    description = item.find("description")
                    description_text = description.text if description is not None else ""

                    link = item.find("link")
                    link_url = link.text if link is not None else ""

                    pub_date = item.find("pubDate")
                    pub_date_text = pub_date.text if pub_date is not None else ""

                    # 키워드 필터링
                    if keywords and not self._matches_keywords(title_text + " " + description_text, keywords):
                        continue

                    # 공고 정보 구성
                    tender_info = {
                        "title": title_text.strip(),
                        "description": description_text.strip(),
                        "source_url": link_url.strip(),
                        "publication_date": self._parse_date(pub_date_text),
                        "source_site": "BOAMP",
                        "country": "FR",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type(title_text),
                        "organization": self._extract_organization(description_text),
                        "cpv_codes": self._extract_cpv_codes(description_text),
                        "estimated_value": self._extract_value(description_text),
                        "deadline_date": self._extract_deadline(description_text),
                        "notice_type": "RSS",
                        "language": "fr"
                    }

                    # 의료기기 관련 필터링
                    if self._is_healthcare_related(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"RSS 아이템 파싱 오류: {e}")
                    continue

        except ET.ParseError as e:
            logger.warning(f"RSS XML 파싱 오류: {e}")

        return results

    async def _crawl_web_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """웹 검색을 통한 공고 수집"""
        results = []

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45)
        ) as session:

            for keyword in keywords[:3]:  # 최대 3개 키워드
                try:
                    logger.info(f"웹 검색: {keyword}")

                    # BOAMP 검색 페이지
                    search_url = f"{self.boamp_base_url}/avis"
                    search_params = {
                        "query": keyword,
                        "type": "marches",
                        "sort": "date_desc"
                    }

                    async with session.get(search_url, params=search_params) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            search_results = await self._parse_search_results(html_content, keyword)
                            results.extend(search_results)
                            logger.info(f"웹 검색에서 {len(search_results)}건 수집")
                        else:
                            logger.warning(f"웹 검색 실패: {response.status}")

                    # 요청 간격 조절
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.warning(f"웹 검색 오류 {keyword}: {e}")

        return results

    async def _parse_search_results(self, html_content: str, keyword: str) -> List[Dict[str, Any]]:
        """검색 결과 HTML 파싱"""
        results = []

        try:
            # BeautifulSoup 사용 대신 간단한 정규표현식 패턴 매칭 시도
            # 실제 구현에서는 BeautifulSoup4를 사용하는 것이 좋음

            # 제목과 링크 패턴 추출 (예시)
            import re

            # 공고 제목 패턴
            title_pattern = r'<h[2-4][^>]*>([^<]*(?:marché|appel|consultation)[^<]*)</h[2-4]>'
            titles = re.findall(title_pattern, html_content, re.IGNORECASE)

            # 링크 패턴
            link_pattern = r'href="([^"]*avis[^"]*)"'
            links = re.findall(link_pattern, html_content)

            # 제목과 링크 매칭
            for i, title in enumerate(titles[:10]):  # 최대 10개
                try:
                    link_url = urljoin(self.boamp_base_url, links[i] if i < len(links) else "")

                    tender_info = {
                        "title": title.strip(),
                        "description": f"검색 키워드: {keyword}",
                        "source_url": link_url,
                        "publication_date": datetime.now().date().isoformat(),
                        "source_site": "BOAMP",
                        "country": "FR",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type(title),
                        "organization": "프랑스 공공기관",
                        "keywords": [keyword],
                        "notice_type": "WEB_SEARCH",
                        "language": "fr"
                    }

                    results.append(tender_info)

                except Exception as e:
                    logger.warning(f"검색 결과 아이템 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"HTML 파싱 오류: {e}")

        return results

    def _matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """키워드 매칭 확인"""
        if not keywords:
            return True

        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    def _determine_tender_type(self, title: str) -> str:
        """공고 유형 판단"""
        title_lower = title.lower()

        if "appel" in title_lower or "offres" in title_lower:
            return "OPEN"
        elif "consultation" in title_lower:
            return "RESTRICTED"
        elif "marché" in title_lower:
            return "CONTRACT"
        else:
            return "OTHER"

    def _extract_organization(self, text: str) -> str:
        """발주기관 추출"""
        # 간단한 패턴 매칭으로 기관명 추출 시도
        import re

        org_patterns = [
            r"(Ministère[^,\n]+)",
            r"(Conseil [^,\n]+)",
            r"(Mairie [^,\n]+)",
            r"(Hôpital [^,\n]+)",
            r"(CHU [^,\n]+)",
            r"(APHP[^,\n]*)",
        ]

        for pattern in org_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "프랑스 공공기관"

    def _extract_cpv_codes(self, text: str) -> List[str]:
        """CPV 코드 추출"""
        import re

        # CPV 코드 패턴 (8자리 숫자)
        cpv_pattern = r"CPV\s*:?\s*(\d{8})"
        matches = re.findall(cpv_pattern, text, re.IGNORECASE)

        return matches if matches else []

    def _extract_value(self, text: str) -> Optional[float]:
        """추정가격 추출"""
        import re

        # 금액 패턴 (유로)
        value_patterns = [
            r"(\d+(?:\s*\d+)*(?:,\d+)?)\s*€",
            r"€\s*(\d+(?:\s*\d+)*(?:,\d+)?)",
            r"(\d+(?:\s*\d+)*(?:,\d+)?)\s*euros?",
        ]

        for pattern in value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1).replace(" ", "").replace(",", ".")
                    return float(value_str)
                except ValueError:
                    continue

        return None

    def _extract_deadline(self, text: str) -> Optional[str]:
        """마감일 추출"""
        import re

        # 날짜 패턴
        date_patterns = [
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{1,2}-\d{1,2}-\d{4})",
            r"(\d{4}-\d{1,2}-\d{1,2})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _parse_date(self, date_str: str) -> str:
        """날짜 문자열 파싱"""
        try:
            # RSS pubDate 형식 파싱
            from datetime import datetime

            # 일반적인 RSS 날짜 형식들
            formats = [
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S %z",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue

            # 파싱 실패시 오늘 날짜 반환
            return datetime.now().date().isoformat()

        except Exception:
            return datetime.now().date().isoformat()

    def _is_healthcare_related(self, tender_info: Dict[str, Any]) -> bool:
        """의료기기 관련 공고인지 확인"""
        # CPV 코드 확인
        cpv_codes = tender_info.get("cpv_codes", [])
        if any(cpv.startswith(hc) for cpv in cpv_codes for hc in ["331", "336", "337"]):
            return True

        # 키워드 확인
        text = f"{tender_info.get('title', '')} {tender_info.get('description', '')}".lower()

        healthcare_keywords = [
            "médical", "médecin", "santé", "hôpital", "clinique",
            "diagnostic", "laboratoire", "équipement médical",
            "dispositif médical", "matériel médical", "chu", "aphp"
        ]

        return any(keyword in text for keyword in healthcare_keywords)

    def _remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 제거"""
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.get("source_url", "")
            title = result.get("title", "")

            # URL 또는 제목으로 중복 체크
            key = url if url else title
            if key and key not in seen_urls:
                seen_urls.add(key)
                unique_results.append(result)

        return unique_results