"""
Dutch TenderNed 크롤러
네덜란드 공공조달 플랫폼 TenderNed 데이터 수집
"""

import asyncio
import aiohttp
import json
import ssl
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, quote


def create_ssl_context():
    """SSL 검증 우회를 위한 컨텍스트 생성"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context

from ..utils.logger import get_logger
from ..crawler.base import BaseCrawler
from ..models.tender_notice import (
    TenderNotice, TenderStatus, TenderType, ProcurementMethod,
    TenderValue, Organization, Classification, TenderDocument,
    CurrencyCode
)
from ..utils.cpv_filter import cpv_filter

logger = get_logger(__name__)


class NetherlandsTenderNedCrawler(BaseCrawler):
    """네덜란드 TenderNed 공공조달 크롤러"""

    def __init__(self):
        super().__init__("NL_TENDERNED", "NL")

        # TenderNed 플랫폼 URL들
        self.tenderned_base_url = "https://www.tenderned.nl"
        self.search_url = f"{self.tenderned_base_url}/tenderned-web/search"
        self.api_url = f"{self.tenderned_base_url}/api/search"

        # RSS/XML 피드 URL들 (추정)
        self.rss_feeds = [
            f"{self.tenderned_base_url}/rss/aanbestedingen.xml",
            f"{self.tenderned_base_url}/feeds/tender.rss"
        ]

        # 네덜란드어 의료 키워드
        self.medical_keywords_nl = [
            "medisch", "medische", "ziekenhuis", "kliniek", "gezondheidszorg",
            "diagnostiek", "laboratorium", "medische apparatuur",
            "medische hulpmiddelen", "farmaceutisch", "gezondheid", "zorg",
            "therapie", "chirurgie", "radiologie", "cardiologie", "oncologie",
            "UMC", "academisch ziekenhuis", "GGD", "huisarts"
        ]

        # 의료기기 관련 CPV 코드
        self.healthcare_cpv_codes = [
            "33100000",  # 의료기기
            "33140000",  # 의료용품
            "33183000",  # 진단장비
            "33184000",  # 실험실 장비
            "33600000",  # 의약품
            "33700000",  # 개인보호장비
        ]

    async def crawl(self, keywords: List[str] = None) -> Dict[str, Any]:
        """크롤링 실행"""
        logger.info(f"네덜란드 TenderNed 크롤링 시작 - 키워드: {keywords}")

        results = []

        try:
            # RSS 피드 수집
            rss_results = await self._crawl_rss_feeds(keywords)
            results.extend(rss_results)

            # 웹 검색 크롤링
            if keywords:
                web_results = await self._crawl_web_search(keywords)
                results.extend(web_results)

            # API 검색 시도
            api_results = await self._crawl_api_search(keywords)
            results.extend(api_results)

            # 메인 포털 크롤링
            portal_results = await self._crawl_main_portal(keywords)
            results.extend(portal_results)

            # 결과 중복 제거
            unique_results = self._remove_duplicates(results)

            logger.info(f"네덜란드 TenderNed 크롤링 완료 - 총 {len(unique_results)}건 수집")

            return {
                "success": True,
                "total_collected": len(unique_results),
                "results": unique_results,
                "source": "NL_TENDERNED",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"네덜란드 TenderNed 크롤링 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": results,
                "source": "NL_TENDERNED",
                "timestamp": datetime.now().isoformat()
            }

    async def _crawl_rss_feeds(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """RSS 피드에서 공고 수집"""
        results = []

        connector = aiohttp.TCPConnector(ssl=create_ssl_context())
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=connector
        ) as session:

            for feed_url in self.rss_feeds:
                try:
                    logger.info(f"네덜란드 RSS 피드 크롤링: {feed_url}")

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

    async def _crawl_web_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """웹 검색을 통한 공고 수집"""
        results = []

        connector = aiohttp.TCPConnector(ssl=create_ssl_context())
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45),
            connector=connector
        ) as session:

            for keyword in keywords[:3]:  # 최대 3개 키워드
                try:
                    logger.info(f"네덜란드 웹 검색: {keyword}")

                    # TenderNed 검색 페이지
                    search_params = {
                        "query": keyword,
                        "type": "all",
                        "status": "open",
                        "sortBy": "publicationDate",
                        "sortOrder": "desc"
                    }

                    async with session.get(self.search_url, params=search_params) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            search_results = await self._parse_search_results_nl(html_content, keyword)
                            results.extend(search_results)
                            logger.info(f"웹 검색에서 {len(search_results)}건 수집")
                        else:
                            logger.warning(f"웹 검색 실패: {response.status}")

                    # 요청 간격 조절
                    await asyncio.sleep(3)

                except Exception as e:
                    logger.warning(f"웹 검색 오류 {keyword}: {e}")

        return results

    async def _crawl_api_search(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """API 검색을 통한 공고 수집"""
        results = []

        if not keywords:
            return results

        connector = aiohttp.TCPConnector(ssl=create_ssl_context())
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45),
            connector=connector
        ) as session:

            for keyword in keywords[:2]:  # API는 최대 2개 키워드만
                try:
                    logger.info(f"네덜란드 API 검색: {keyword}")

                    # API 검색 파라미터
                    api_params = {
                        "searchText": keyword,
                        "pageSize": 20,
                        "pageNumber": 0,
                        "sortField": "publicationDate",
                        "sortDirection": "DESC"
                    }

                    headers = {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "TenderBot/1.0"
                    }

                    async with session.get(self.api_url, params=api_params, headers=headers) as response:
                        if response.status == 200:
                            try:
                                json_data = await response.json()
                                api_results = await self._parse_api_results(json_data, keyword)
                                results.extend(api_results)
                                logger.info(f"API에서 {len(api_results)}건 수집")
                            except json.JSONDecodeError:
                                logger.warning("API 응답 JSON 파싱 실패")
                        else:
                            logger.warning(f"API 검색 실패: {response.status}")

                    await asyncio.sleep(2)

                except Exception as e:
                    logger.warning(f"API 검색 오류 {keyword}: {e}")

        return results

    async def _crawl_main_portal(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """메인 포털 크롤링"""
        results = []

        try:
            logger.info("네덜란드 TenderNed 메인 포털 크롤링")

            connector = aiohttp.TCPConnector(ssl=create_ssl_context())
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=45),
                connector=connector
            ) as session:

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }

                # 메인 페이지
                async with session.get(self.tenderned_base_url, headers=headers) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        portal_results = await self._parse_main_page(html_content, keywords)
                        results.extend(portal_results)
                        logger.info(f"메인 포털에서 {len(portal_results)}건 수집")

        except Exception as e:
            logger.warning(f"메인 포털 크롤링 오류: {e}")

        return results

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

                    # 키워드 필터링 (네덜란드어 포함)
                    if keywords and not self._matches_keywords_nl(title_text + " " + description_text, keywords):
                        continue

                    # 공고 정보 구성
                    tender_info = {
                        "title": title_text.strip(),
                        "description": description_text.strip(),
                        "source_url": link_url.strip(),
                        "publication_date": self._parse_date_nl(pub_date_text),
                        "source_site": "TenderNed",
                        "country": "NL",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type_nl(title_text),
                        "organization": self._extract_organization_nl(description_text),
                        "cpv_codes": self._extract_cpv_codes(description_text),
                        "estimated_value": self._extract_value_nl(description_text),
                        "deadline_date": self._extract_deadline_nl(description_text),
                        "notice_type": "RSS",
                        "language": "nl"
                    }

                    # 의료기기 관련 필터링
                    if self._is_healthcare_related_nl(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"RSS 아이템 파싱 오류: {e}")
                    continue

        except ET.ParseError as e:
            logger.warning(f"RSS XML 파싱 오류: {e}")

        return results

    async def _parse_search_results_nl(self, html_content: str, keyword: str) -> List[Dict[str, Any]]:
        """네덜란드어 검색 결과 파싱"""
        results = []

        try:
            import re

            # 네덜란드어 공고 제목 패턴
            title_patterns = [
                r'<h[2-4][^>]*>([^<]*(?:aanbesteding|inschrijving|tender)[^<]*)</h[2-4]>',
                r'title="([^"]*(?:aanbesteding|inschrijving|tender)[^"]*)"',
                r'<a[^>]*>([^<]*(?:medisch|ziekenhuis|gezondheidszorg)[^<]*)</a>'
            ]

            # 링크 패턴
            link_patterns = [
                r'href="([^"]*(?:tender|aanbesteding)[^"]*)"',
                r'href="([^"]*tenderned[^"]*)"'
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
                    link_url = ""
                    if i < len(links):
                        link_url = urljoin(self.tenderned_base_url, links[i])

                    tender_info = {
                        "title": title.strip(),
                        "description": f"Zoekwoord: {keyword}",
                        "source_url": link_url,
                        "publication_date": datetime.now().date().isoformat(),
                        "source_site": "TenderNed",
                        "country": "NL",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type_nl(title),
                        "organization": self._extract_organization_from_title_nl(title),
                        "keywords": [keyword],
                        "notice_type": "WEB_SEARCH",
                        "language": "nl"
                    }

                    # 의료기기 관련 확인
                    if self._is_healthcare_related_nl(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"검색 결과 아이템 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"HTML 파싱 오류: {e}")

        return results

    async def _parse_api_results(self, json_data: Dict[str, Any], keyword: str) -> List[Dict[str, Any]]:
        """API 응답 파싱"""
        results = []

        try:
            # API 응답 구조 가정
            tenders = json_data.get("results", [])
            if not tenders:
                tenders = json_data.get("data", [])
            if not tenders:
                tenders = json_data.get("content", [])

            for tender in tenders[:10]:  # 최대 10개
                try:
                    title = tender.get("title", tender.get("name", ""))
                    description = tender.get("description", tender.get("summary", ""))
                    tender_id = tender.get("id", tender.get("tenderId", ""))

                    # URL 구성
                    detail_url = ""
                    if tender_id:
                        detail_url = f"{self.tenderned_base_url}/tender/{tender_id}"

                    tender_info = {
                        "title": title.strip(),
                        "description": description.strip(),
                        "source_url": detail_url,
                        "publication_date": self._parse_date_nl(tender.get("publicationDate", "")),
                        "source_site": "TenderNed",
                        "country": "NL",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type_nl(title),
                        "organization": tender.get("organization", "Nederlandse Overheid"),
                        "estimated_value": tender.get("estimatedValue"),
                        "deadline_date": self._parse_date_nl(tender.get("deadlineDate", "")),
                        "keywords": [keyword],
                        "notice_type": "API",
                        "language": "nl"
                    }

                    # 의료기기 관련 확인
                    if self._is_healthcare_related_nl(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"API 결과 아이템 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"API JSON 파싱 오류: {e}")

        return results

    async def _parse_main_page(self, html_content: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """메인 페이지 파싱"""
        results = []

        try:
            import re

            # 메인 페이지 공고 패턴
            title_patterns = [
                r'<a[^>]*>([^<]*(?:aanbesteding|tender)[^<]*)</a>',
                r'<div[^>]*>([^<]*(?:medisch|ziekenhuis|gezondheidszorg)[^<]*)</div>',
                r'<h[2-4][^>]*>([^<]*(?:UMC|academisch ziekenhuis)[^<]*)</h[2-4]>'
            ]

            titles = []
            for pattern in title_patterns:
                titles.extend(re.findall(pattern, html_content, re.IGNORECASE))

            for title in titles[:6]:  # 최대 6개
                try:
                    # 키워드 필터링
                    if keywords and not self._matches_keywords_nl(title, keywords):
                        continue

                    tender_info = {
                        "title": title.strip(),
                        "description": "TenderNed hoofdportaal",
                        "source_url": self.tenderned_base_url,
                        "publication_date": datetime.now().date().isoformat(),
                        "source_site": "TenderNed",
                        "country": "NL",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type_nl(title),
                        "organization": "Nederlandse Overheid",
                        "notice_type": "MAIN_PORTAL",
                        "language": "nl"
                    }

                    # 의료기기 관련 확인
                    if self._is_healthcare_related_nl(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"메인 페이지 아이템 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"메인 페이지 파싱 오류: {e}")

        return results

    def _matches_keywords_nl(self, text: str, keywords: List[str]) -> bool:
        """네덜란드어 키워드 매칭"""
        if not keywords:
            return True

        text_lower = text.lower()

        # 영어 키워드 매칭
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True

        # 네덜란드어 의료 키워드 매칭
        for med_keyword in self.medical_keywords_nl:
            if med_keyword in text_lower:
                return True

        return False

    def _determine_tender_type_nl(self, title: str) -> str:
        """네덜란드어 공고 유형 판단"""
        title_lower = title.lower()

        if "openbare" in title_lower or "open" in title_lower:
            return "OPEN"
        elif "beperkte" in title_lower or "gesloten" in title_lower:
            return "RESTRICTED"
        elif "onderhandse" in title_lower:
            return "NEGOTIATED"
        elif "raamovereenkomst" in title_lower:
            return "FRAMEWORK"
        else:
            return "OTHER"

    def _extract_organization_nl(self, text: str) -> str:
        """네덜란드어 발주기관 추출"""
        import re

        org_patterns = [
            r"(Ministerie[^,\n]+)",
            r"(Gemeente[^,\n]+)",
            r"(Provincie[^,\n]+)",
            r"(Ziekenhuis[^,\n]+)",
            r"(UMC[^,\n]*)",
            r"(Academisch Ziekenhuis[^,\n]+)",
            r"(Universiteit[^,\n]+)",
            r"(GGD[^,\n]*)",
            r"(Waternet[^,\n]*)"
        ]

        for pattern in org_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Nederlandse Overheid"

    def _extract_organization_from_title_nl(self, title: str) -> str:
        """제목에서 발주기관 추출"""
        title_lower = title.lower()

        if "ziekenhuis" in title_lower or "umc" in title_lower:
            return "Nederlands Ziekenhuis"
        elif "universiteit" in title_lower:
            return "Nederlandse Universiteit"
        elif "gemeente" in title_lower:
            return "Nederlandse Gemeente"
        elif "ministerie" in title_lower:
            return "Nederlands Ministerie"
        elif "provincie" in title_lower:
            return "Nederlandse Provincie"
        elif "ggd" in title_lower:
            return "GGD Nederland"
        else:
            return "Nederlandse Overheid"

    def _extract_value_nl(self, text: str) -> Optional[float]:
        """네덜란드어 추정가격 추출"""
        import re

        # 네덜란드 금액 패턴
        value_patterns = [
            r"€\s*(\d+(?:\.\d+)*(?:,\d+)?)",
            r"(\d+(?:\.\d+)*(?:,\d+)?)\s*€",
            r"(\d+(?:\.\d+)*(?:,\d+)?)\s*euro",
            r"waarde[:\s]*€?\s*(\d+(?:\.\d+)*(?:,\d+)?)",
            r"bedrag[:\s]*€?\s*(\d+(?:\.\d+)*(?:,\d+)?)",
            r"raming[:\s]*€?\s*(\d+(?:\.\d+)*(?:,\d+)?)"
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

    def _extract_deadline_nl(self, text: str) -> Optional[str]:
        """네덜란드어 마감일 추출"""
        import re

        # 네덜란드 날짜 패턴
        date_patterns = [
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{1,2}-\d{1,2}-\d{4})",
            r"(\d{4}-\d{1,2}-\d{1,2})",
            r"inschrijftermijn[:\s]*(\d{1,2}/\d{1,2}/\d{4})",
            r"deadline[:\s]*(\d{1,2}/\d{1,2}/\d{4})",
            r"uiterlijk[:\s]*(\d{1,2}/\d{1,2}/\d{4})"
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _parse_date_nl(self, date_str: str) -> str:
        """네덜란드 날짜 형식 파싱"""
        try:
            from datetime import datetime

            if not date_str or date_str.strip() == "":
                return datetime.now().date().isoformat()

            # 네덜란드어 날짜 형식들
            formats = [
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S %z",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y",
                "%d-%m-%Y %H:%M:%S",
                "%d-%m-%Y",
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

    def _is_healthcare_related_nl(self, tender_info: Dict[str, Any]) -> bool:
        """네덜란드어 의료기기 관련 공고 확인"""
        # CPV 코드 확인
        cpv_codes = tender_info.get("cpv_codes", [])
        if any(cpv.startswith(hc) for cpv in cpv_codes for hc in ["331", "336", "337"]):
            return True

        # 네덜란드어 의료 키워드 확인
        text = f"{tender_info.get('title', '')} {tender_info.get('description', '')}".lower()

        return any(keyword in text for keyword in self.medical_keywords_nl)

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
        """로그인 - 네덜란드 TenderNed는 공개 사이트이므로 로그인 불필요"""
        return True

    async def search_bids(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """입찰 정보 검색 - crawl 메서드를 호출"""
        result = await self.crawl(keywords)
        return result.get("results", [])