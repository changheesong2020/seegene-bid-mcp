"""
German Vergabestellen 크롤러
독일 공공조달 플랫폼 데이터 수집
"""

import asyncio
import ssl
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin

import aiohttp
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from ..config import settings
from ..crawler.base import BaseCrawler
from ..models.tender_notice import (
    TenderNotice, TenderStatus, TenderType, ProcurementMethod,
    TenderValue, Organization, Classification, TenderDocument,
    CurrencyCode,
)
from ..utils.cpv_filter import cpv_filter
from ..utils.logger import get_logger
from ..database.connection import DatabaseManager

logger = get_logger(__name__)


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "application/rss+xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def create_ssl_context():
    """SSL 검증 우회를 위한 컨텍스트 생성"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    custom_ca_bundle = getattr(settings, "SSL_CUSTOM_CA_BUNDLE", None)
    if custom_ca_bundle:
        ca_path = Path(custom_ca_bundle)
        if not ca_path.is_absolute():
            ca_path = Path.cwd() / ca_path

        if ca_path.exists():
            try:
                ssl_context.load_verify_locations(cafile=str(ca_path))
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                logger.info(f"커스텀 CA 번들을 로드했습니다: {ca_path}")
            except Exception as exc:
                logger.warning(f"커스텀 CA 번들 로드 실패: {exc}")
        else:
            logger.warning(f"지정된 CA 번들을 찾을 수 없습니다: {ca_path}")

    return ssl_context


class GermanyVergabestellenCrawler(BaseCrawler):
    """독일 Vergabestellen 공공조달 크롤러"""

    def __init__(self):
        super().__init__("DE_VERGABESTELLEN", "DE")

        # 독일 주요 조달 포털들
        self.portals = {
            "deutsches_vergabeportal": "https://www.deutsches-vergabeportal.de",
            "evergabe": "https://www.evergabe.de",
            "bund": "https://www.evergabe-online.de",
            "bayern": "https://www.vergabe24.bayern.de",
            "nrw": "https://www.vergabe.nrw.de"
        }

        # RSS/XML 피드 URL들
        # RSS 피드 URL들 (연결 오류 때문에 주석 처리)
        self.rss_feeds = [
            # 연결 실패로 인해 주석 처리
            # "https://www.deutsches-vergabeportal.de/rss",
            # "https://www.evergabe.de/api/rss"
        ]

        # 의료기기 관련 CPV 코드 (독일 특화)
        self.healthcare_cpv_codes = [
            "33100000",  # 의료기기
            "33140000",  # 의료용품
            "33183000",  # 진단장비
            "33184000",  # 실험실 장비
            "33600000",  # 의약품
            "33700000",  # 개인보호장비
        ]

        # 독일어 의료 키워드
        self.medical_keywords_de = [
            "medizin", "medizinisch", "krankenhaus", "klinik", "labor",
            "diagnose", "diagnostik", "medizinprodukt", "medizintechnik",
            "gesundheit", "arzt", "pflege", "therapie", "chirurgie"
        ]

    async def crawl(self, keywords: List[str] = None) -> Dict[str, Any]:
        """크롤링 실행"""
        logger.info(f"독일 Vergabestellen 크롤링 시작 - 키워드: {keywords}")

        results = []
        had_failures = False

        try:
            # RSS 피드 수집
            rss_results, rss_failed = await self._crawl_rss_feeds(keywords)
            results.extend(rss_results)
            had_failures = had_failures or rss_failed

            # 주요 포털 크롤링
            for portal_name, portal_url in self.portals.items():
                try:
                    portal_results, portal_failed = await self._crawl_portal(portal_name, portal_url, keywords)
                    results.extend(portal_results)
                    had_failures = had_failures or portal_failed
                except Exception as e:
                    logger.warning(f"{portal_name} 포털 크롤링 오류: {e}")
                    had_failures = True

            if not results and had_failures:
                logger.warning("독일 Vergabestellen 포털에서 데이터 수집에 실패했습니다")

            # 결과 중복 제거
            unique_results = self._remove_duplicates(results)

            logger.info(f"독일 Vergabestellen 크롤링 완료 - 총 {len(unique_results)}건 수집")

            # 데이터베이스에 저장
            if unique_results:
                try:
                    await DatabaseManager.save_bid_info(unique_results)
                    logger.info(f"💾 DE_VERGABESTELLEN 데이터베이스 저장 완료: {len(unique_results)}건")
                except Exception as e:
                    logger.error(f"❌ DE_VERGABESTELLEN 데이터베이스 저장 실패: {e}")
            else:
                logger.info("📝 DE_VERGABESTELLEN 저장할 데이터가 없습니다")

            return {
                "success": True,
                "total_collected": len(unique_results),
                "results": unique_results,
                "source": "DE_VERGABESTELLEN",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"독일 Vergabestellen 크롤링 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": results,
                "source": "DE_VERGABESTELLEN",
                "timestamp": datetime.now().isoformat()
            }

    async def _crawl_rss_feeds(self, keywords: List[str] = None) -> Tuple[List[Dict[str, Any]], bool]:
        """RSS 피드에서 공고 수집"""
        results = []
        had_failures = False

        if not self.rss_feeds:
            logger.info("RSS 피드 URL이 설정되지 않음 - 스킵")
            return results, False

        connector = aiohttp.TCPConnector(ssl=create_ssl_context())
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=connector,
            headers=DEFAULT_HEADERS,
        ) as session:

            for feed_url in self.rss_feeds:
                try:
                    logger.info(f"독일 RSS 피드 크롤링: {feed_url}")

                    async with session.get(feed_url, headers=DEFAULT_HEADERS) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed_results = await self._parse_rss_feed(content, keywords)
                            results.extend(feed_results)
                            logger.info(f"RSS에서 {len(feed_results)}건 수집")
                        else:
                            logger.warning(f"RSS 피드 접근 실패: {response.status}")
                            had_failures = True

                except Exception as e:
                    logger.warning(f"RSS 피드 크롤링 오류 {feed_url}: {e}")
                    had_failures = True

        return results, had_failures

    async def _crawl_portal(
        self,
        portal_name: str,
        portal_url: str,
        keywords: List[str] = None
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """개별 포털 크롤링"""
        results = []
        had_failures = False

        try:
            logger.info(f"독일 포털 크롤링: {portal_name}")

            connector = aiohttp.TCPConnector(ssl=create_ssl_context())
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=45),
                connector=connector,
                headers=DEFAULT_HEADERS,
            ) as session:

                # 메인 페이지 접근
                async with session.get(portal_url, headers=DEFAULT_HEADERS) as response:
                    if response.status == 200:
                        html_content = await response.text()

                        # 공고 목록 페이지 찾기
                        search_results = await self._parse_portal_page(html_content, portal_name, keywords)
                        results.extend(search_results)

                        logger.info(f"{portal_name}에서 {len(search_results)}건 수집")
                    else:
                        logger.warning(f"{portal_name} 접근 실패: {response.status}")
                        had_failures = True

                # 요청 간격 조절
                await asyncio.sleep(3)

        except Exception as e:
            logger.warning(f"{portal_name} 포털 크롤링 오류: {e}")
            had_failures = True

        return results, had_failures

    async def _parse_rss_feed(self, content: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """RSS 피드 파싱"""
        results = []

        try:
            # XML 파싱
            root = ET.fromstring(content)
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

                    # 키워드 필터링 (독일어 포함)
                    if keywords and not self._matches_keywords_de(title_text + " " + description_text, keywords):
                        continue

                    # 데이터베이스 스키마에 맞는 공고 정보 구성
                    tender_info = {
                        "title": title_text.strip()[:500],  # 길이 제한
                        "organization": self._extract_organization_de(description_text) or "Deutsche Behörde",
                        "bid_number": f"DE-RSS-{datetime.now().strftime('%Y%m%d')}-{len(results)+1:03d}",
                        "announcement_date": self._parse_date(pub_date_text),
                        "deadline_date": self._extract_deadline_de(description_text) or self._estimate_deadline_date_de(),
                        "estimated_price": str(self._extract_value_de(description_text)) if self._extract_value_de(description_text) else "",
                        "currency": "EUR",
                        "source_url": link_url.strip(),
                        "source_site": "DE_VERGABESTELLEN",
                        "country": "DE",
                        "keywords": keywords or [],
                        "relevance_score": self._calculate_relevance_score_de(title_text, keywords[0] if keywords else ""),
                        "urgency_level": "medium",
                        "status": "active",
                        "extra_data": {
                            "description": description_text.strip()[:1000],  # 길이 제한
                            "tender_type": self._determine_tender_type_de(title_text),
                            "cpv_codes": self._extract_cpv_codes(description_text),
                            "notice_type": "RSS",
                            "language": "de",
                            "crawled_at": datetime.now().isoformat()
                        }
                    }

                    # 의료기기 관련 필터링
                    if self._is_healthcare_related_de(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"RSS 아이템 파싱 오류: {e}")
                    continue

        except ET.ParseError as e:
            logger.warning(f"RSS XML 파싱 오류: {e}")

        return results

    async def _parse_portal_page(self, html_content: str, portal_name: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """포털 페이지 파싱"""
        results = []

        try:
            import re

            # 공고 제목 패턴 (독일어)
            title_patterns = [
                r'<h[2-4][^>]*>([^<]*(?:Ausschreibung|Vergabe|Auftrag|Beschaffung)[^<]*)</h[2-4]>',
                r'title="([^"]*(?:Ausschreibung|Vergabe|Auftrag|Beschaffung)[^"]*)"'
            ]

            # 링크 패턴
            link_patterns = [
                r'href="([^"]*(?:vergabe|ausschreibung|auftrag)[^"]*)"',
                r'href="([^"]*tender[^"]*)"'
            ]

            titles = []
            for pattern in title_patterns:
                titles.extend(re.findall(pattern, html_content, re.IGNORECASE))

            links = []
            for pattern in link_patterns:
                links.extend(re.findall(pattern, html_content))

            # 제목과 링크 매칭
            for i, title in enumerate(titles[:8]):  # 최대 8개
                try:
                    # 키워드 필터링
                    if keywords and not self._matches_keywords_de(title, keywords):
                        continue

                    link_url = ""
                    if i < len(links):
                        base_url = self.portals.get(portal_name, portal_url)
                        link_url = urljoin(base_url, links[i])

                    tender_info = {
                        "title": title.strip()[:500],
                        "organization": self._extract_organization_from_title_de(title) or "Deutsche Behörde",
                        "bid_number": f"DE-WEB-{datetime.now().strftime('%Y%m%d')}-{i+1:03d}",
                        "announcement_date": datetime.now().date().isoformat(),
                        "deadline_date": self._estimate_deadline_date_de(),
                        "estimated_price": "",
                        "currency": "EUR",
                        "source_url": link_url,
                        "source_site": "DE_VERGABESTELLEN",
                        "country": "DE",
                        "keywords": [],
                        "relevance_score": self._calculate_relevance_score_de(title, ""),
                        "urgency_level": "medium",
                        "status": "active",
                        "extra_data": {
                            "description": f"포털: {portal_name}",
                            "tender_type": self._determine_tender_type_de(title),
                            "notice_type": "WEB_CRAWL",
                            "language": "de",
                            "portal_name": portal_name,
                            "crawled_at": datetime.now().isoformat()
                        }
                    }

                    # 의료기기 관련 확인
                    if self._is_healthcare_related_de(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"포털 아이템 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"포털 페이지 파싱 오류: {e}")

        return results


    def _matches_keywords_de(self, text: str, keywords: List[str]) -> bool:
        """독일어 키워드 매칭"""
        if not keywords:
            return True

        text_lower = text.lower()

        # 영어 키워드 매칭
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True

        # 독일어 의료 키워드 매칭
        for med_keyword in self.medical_keywords_de:
            if med_keyword in text_lower:
                return True

        return False

    def _determine_tender_type_de(self, title: str) -> str:
        """독일어 공고 유형 판단"""
        title_lower = title.lower()

        if "ausschreibung" in title_lower or "öffentlich" in title_lower:
            return "OPEN"
        elif "beschränkt" in title_lower or "begrenzt" in title_lower:
            return "RESTRICTED"
        elif "auftrag" in title_lower or "vertrag" in title_lower:
            return "CONTRACT"
        elif "rahmen" in title_lower:
            return "FRAMEWORK"
        else:
            return "OTHER"

    def _extract_organization_de(self, text: str) -> str:
        """독일어 발주기관 추출"""
        import re

        org_patterns = [
            r"(Bundesministerium[^,\n]+)",
            r"(Landesregierung[^,\n]+)",
            r"(Stadt[^,\n]+)",
            r"(Gemeinde[^,\n]+)",
            r"(Klinikum[^,\n]+)",
            r"(Krankenhaus[^,\n]+)",
            r"(Universitäts[^,\n]+)",
            r"(Charité[^,\n]*)",
            r"(Universitätsklinikum[^,\n]+)"
        ]

        for pattern in org_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Deutsche Behörde"

    def _extract_organization_from_title_de(self, title: str) -> str:
        """제목에서 발주기관 추출"""
        import re

        # 제목에서 기관명 패턴 찾기
        if "klinik" in title.lower() or "krankenhaus" in title.lower():
            return "Deutsches Krankenhaus"
        elif "universität" in title.lower():
            return "Deutsche Universität"
        elif "stadt" in title.lower():
            return "Deutsche Stadtverwaltung"
        elif "bund" in title.lower():
            return "Bundesbehörde"
        else:
            return "Deutsche Behörde"

    def _extract_value_de(self, text: str) -> Optional[float]:
        """독일어 추정가격 추출"""
        import re

        # 독일 금액 패턴
        value_patterns = [
            r"(\d+(?:\.\d+)*(?:,\d+)?)\s*€",
            r"€\s*(\d+(?:\.\d+)*(?:,\d+)?)",
            r"(\d+(?:\.\d+)*(?:,\d+)?)\s*Euro",
            r"Wert:\s*(\d+(?:\.\d+)*(?:,\d+)?)"
        ]

        for pattern in value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1).replace(".", "").replace(",", ".")
                    return float(value_str)
                except ValueError:
                    continue

        return None

    def _extract_deadline_de(self, text: str) -> Optional[str]:
        """독일어 마감일 추출"""
        import re

        # 독일 날짜 패턴
        date_patterns = [
            r"(\d{1,2}\.\d{1,2}\.\d{4})",
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{4}-\d{1,2}-\d{1,2})",
            r"Frist:\s*(\d{1,2}\.\d{1,2}\.\d{4})",
            r"bis\s*(\d{1,2}\.\d{1,2}\.\d{4})"
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _parse_date(self, date_str: str) -> str:
        """독일 날짜 형식 파싱"""
        try:
            from datetime import datetime

            # 독일어 날짜 형식들
            formats = [
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S %z",
                "%d.%m.%Y %H:%M:%S",
                "%d.%m.%Y",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue

            return datetime.now().date().isoformat()

        except Exception:
            return datetime.now().date().isoformat()

    def _is_healthcare_related_de(self, tender_info: Dict[str, Any]) -> bool:
        """독일어 의료기기 관련 공고 확인"""
        # CPV 코드 확인
        cpv_codes = tender_info.get("cpv_codes", [])
        if any(cpv.startswith(hc) for cpv in cpv_codes for hc in ["331", "336", "337"]):
            return True

        # 독일어 의료 키워드 확인
        text = f"{tender_info.get('title', '')} {tender_info.get('description', '')}".lower()

        return any(keyword in text for keyword in self.medical_keywords_de)

    def _extract_cpv_codes(self, text: str) -> List[str]:
        """CPV 코드 추출"""
        import re

        cpv_pattern = r"CPV[:\s]*(\d{8})"
        matches = re.findall(cpv_pattern, text, re.IGNORECASE)

        return matches if matches else []

    def _remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 제거"""
        seen_urls = set()
        unique_results = []

        for result in results:
            url = result.get("source_url", "")
            title = result.get("title", "")

            key = url if url else title
            if key and key not in seen_urls:
                seen_urls.add(key)
                unique_results.append(result)

        return unique_results

    async def login(self) -> bool:
        """로그인 - 독일 Vergabestellen 대부분 공개 사이트이므로 로그인 불필요"""
        return True

    async def search_bids(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """입찰 정보 검색 - crawl 메서드를 호출"""
        result = await self.crawl(keywords)
        return result.get("results", [])

    def _estimate_deadline_date_de(self) -> str:
        """마감일 추정 (독일 기준 30일 후)"""
        try:
            estimated_date = datetime.now() + timedelta(days=30)
            return estimated_date.date().isoformat()
        except Exception:
            return datetime.now().date().isoformat()

    def _calculate_relevance_score_de(self, title: str, keyword: str) -> float:
        """관련성 점수 계산 (독일어)"""
        if not keyword or not title:
            return 5.0

        title_lower = title.lower()
        keyword_lower = keyword.lower()

        # 완전 일치
        if keyword_lower in title_lower:
            return 8.0

        # 독일어 의료 키워드 부분 일치
        german_medical_keywords = [
            "medizinisch", "medizinische", "krankenhaus", "klinik", "diagnostik",
            "labor", "medizingeräte", "gesundheitswesen", "gesundheit",
            "therapie", "chirurgie", "radiologie", "kardiologie", "onkologie"
        ]

        for medical_kw in german_medical_keywords:
            if medical_kw.lower() in title_lower:
                return 7.0

        return 5.0