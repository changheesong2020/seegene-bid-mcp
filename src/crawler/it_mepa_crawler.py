"""
Italian MEPA 크롤러
이탈리아 공공조달 플랫폼 (Acquisti in Rete della PA) 데이터 수집
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


class ItalyMEPACrawler(BaseCrawler):
    """이탈리아 MEPA (Acquisti in Rete della PA) 크롤러"""

    def __init__(self):
        super().__init__("IT_MEPA", "IT")

        # MEPA 플랫폼 URL들
        self.mepa_base_url = "https://www.acquistinretepa.it"
        self.gare_base_url = "https://www.gare.consip.it"

        # API 엔드포인트들 (추정)
        self.search_api_url = f"{self.mepa_base_url}/opencms/opencms/HandlersPool"
        self.rss_feeds = [
            f"{self.mepa_base_url}/rss/gare.xml",
            f"{self.gare_base_url}/rss/bandi.xml"
        ]

        # 이탈리아어 의료 키워드
        self.medical_keywords_it = [
            "medico", "medica", "sanitario", "ospedale", "clinica",
            "diagnostico", "laboratorio", "strumentazione medica",
            "dispositivi medici", "farmaceutico", "salute", "cura",
            "terapia", "chirurgia", "radiologia", "cardiologia"
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
        logger.info(f"이탈리아 MEPA 크롤링 시작 - 키워드: {keywords}")

        results = []

        try:
            # RSS 피드 수집
            rss_results = await self._crawl_rss_feeds(keywords)
            results.extend(rss_results)

            # 웹 검색 크롤링
            if keywords:
                web_results = await self._crawl_web_search(keywords)
                results.extend(web_results)

            # CONSIP 포털 크롤링
            consip_results = await self._crawl_consip_portal(keywords)
            results.extend(consip_results)

            # 결과 중복 제거
            unique_results = self._remove_duplicates(results)

            logger.info(f"이탈리아 MEPA 크롤링 완료 - 총 {len(unique_results)}건 수집")

            return {
                "success": True,
                "total_collected": len(unique_results),
                "results": unique_results,
                "source": "IT_MEPA",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"이탈리아 MEPA 크롤링 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": results,
                "source": "IT_MEPA",
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
                    logger.info(f"이탈리아 RSS 피드 크롤링: {feed_url}")

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

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45)
        ) as session:

            for keyword in keywords[:3]:  # 최대 3개 키워드
                try:
                    logger.info(f"이탈리아 웹 검색: {keyword}")

                    # MEPA 검색 페이지
                    search_url = f"{self.mepa_base_url}/opencms/opencms/gare"
                    search_params = {
                        "q": keyword,
                        "tipo": "gare",
                        "stato": "aperto"
                    }

                    async with session.get(search_url, params=search_params) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            search_results = await self._parse_search_results_it(html_content, keyword)
                            results.extend(search_results)
                            logger.info(f"웹 검색에서 {len(search_results)}건 수집")
                        else:
                            logger.warning(f"웹 검색 실패: {response.status}")

                    # 요청 간격 조절
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.warning(f"웹 검색 오류 {keyword}: {e}")

        return results

    async def _crawl_consip_portal(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """CONSIP 포털 크롤링"""
        results = []

        try:
            logger.info("CONSIP 포털 크롤링")

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=45)
            ) as session:

                # CONSIP 메인 페이지
                async with session.get(self.gare_base_url) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        consip_results = await self._parse_consip_page(html_content, keywords)
                        results.extend(consip_results)
                        logger.info(f"CONSIP에서 {len(consip_results)}건 수집")

        except Exception as e:
            logger.warning(f"CONSIP 포털 크롤링 오류: {e}")

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

                    # 키워드 필터링 (이탈리아어 포함)
                    if keywords and not self._matches_keywords_it(title_text + " " + description_text, keywords):
                        continue

                    # 공고 정보 구성
                    tender_info = {
                        "title": title_text.strip(),
                        "description": description_text.strip(),
                        "source_url": link_url.strip(),
                        "publication_date": self._parse_date_it(pub_date_text),
                        "source_site": "MEPA",
                        "country": "IT",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type_it(title_text),
                        "organization": self._extract_organization_it(description_text),
                        "cpv_codes": self._extract_cpv_codes(description_text),
                        "estimated_value": self._extract_value_it(description_text),
                        "deadline_date": self._extract_deadline_it(description_text),
                        "notice_type": "RSS",
                        "language": "it"
                    }

                    # 의료기기 관련 필터링
                    if self._is_healthcare_related_it(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"RSS 아이템 파싱 오류: {e}")
                    continue

        except ET.ParseError as e:
            logger.warning(f"RSS XML 파싱 오류: {e}")

        return results

    async def _parse_search_results_it(self, html_content: str, keyword: str) -> List[Dict[str, Any]]:
        """이탈리아어 검색 결과 파싱"""
        results = []

        try:
            import re

            # 이탈리아어 공고 제목 패턴
            title_patterns = [
                r'<h[2-4][^>]*>([^<]*(?:gara|bando|appalto|procedura)[^<]*)</h[2-4]>',
                r'title="([^"]*(?:gara|bando|appalto|procedura)[^"]*)"'
            ]

            # 링크 패턴
            link_patterns = [
                r'href="([^"]*(?:gara|bando|appalto)[^"]*)"',
                r'href="([^"]*procedure[^"]*)"'
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
                        link_url = urljoin(self.mepa_base_url, links[i])

                    tender_info = {
                        "title": title.strip(),
                        "description": f"검색 키워드: {keyword}",
                        "source_url": link_url,
                        "publication_date": datetime.now().date().isoformat(),
                        "source_site": "MEPA",
                        "country": "IT",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type_it(title),
                        "organization": self._extract_organization_from_title_it(title),
                        "keywords": [keyword],
                        "notice_type": "WEB_SEARCH",
                        "language": "it"
                    }

                    # 의료기기 관련 확인
                    if self._is_healthcare_related_it(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"검색 결과 아이템 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"HTML 파싱 오류: {e}")

        return results

    async def _parse_consip_page(self, html_content: str, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """CONSIP 페이지 파싱"""
        results = []

        try:
            import re

            # CONSIP 공고 패턴
            title_patterns = [
                r'<a[^>]*>([^<]*(?:procedura|gara|bando)[^<]*)</a>',
                r'<td[^>]*>([^<]*(?:sanitario|medico|ospedaliero)[^<]*)</td>'
            ]

            titles = []
            for pattern in title_patterns:
                titles.extend(re.findall(pattern, html_content, re.IGNORECASE))

            for title in titles[:6]:  # 최대 6개
                try:
                    # 키워드 필터링
                    if keywords and not self._matches_keywords_it(title, keywords):
                        continue

                    tender_info = {
                        "title": title.strip(),
                        "description": "CONSIP 포털",
                        "source_url": self.gare_base_url,
                        "publication_date": datetime.now().date().isoformat(),
                        "source_site": "CONSIP",
                        "country": "IT",
                        "currency": "EUR",
                        "tender_type": self._determine_tender_type_it(title),
                        "organization": "CONSIP",
                        "notice_type": "CONSIP_PORTAL",
                        "language": "it"
                    }

                    # 의료기기 관련 확인
                    if self._is_healthcare_related_it(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"CONSIP 아이템 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"CONSIP 페이지 파싱 오류: {e}")

        return results

    def _matches_keywords_it(self, text: str, keywords: List[str]) -> bool:
        """이탈리아어 키워드 매칭"""
        if not keywords:
            return True

        text_lower = text.lower()

        # 영어 키워드 매칭
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True

        # 이탈리아어 의료 키워드 매칭
        for med_keyword in self.medical_keywords_it:
            if med_keyword in text_lower:
                return True

        return False

    def _determine_tender_type_it(self, title: str) -> str:
        """이탈리아어 공고 유형 판단"""
        title_lower = title.lower()

        if "aperto" in title_lower or "pubblico" in title_lower:
            return "OPEN"
        elif "ristretto" in title_lower or "limitato" in title_lower:
            return "RESTRICTED"
        elif "negoziato" in title_lower or "trattativa" in title_lower:
            return "NEGOTIATED"
        elif "accordo quadro" in title_lower:
            return "FRAMEWORK"
        else:
            return "OTHER"

    def _extract_organization_it(self, text: str) -> str:
        """이탈리아어 발주기관 추출"""
        import re

        org_patterns = [
            r"(Ministero[^,\n]+)",
            r"(Regione[^,\n]+)",
            r"(Comune[^,\n]+)",
            r"(Provincia[^,\n]+)",
            r"(Ospedale[^,\n]+)",
            r"(ASL[^,\n]+)",
            r"(Università[^,\n]+)",
            r"(CONSIP[^,\n]*)",
            r"(Azienda[^,\n]+)"
        ]

        for pattern in org_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Ente Pubblico Italiano"

    def _extract_organization_from_title_it(self, title: str) -> str:
        """제목에서 발주기관 추출"""
        title_lower = title.lower()

        if "ospedale" in title_lower or "sanitario" in title_lower:
            return "Ospedale Italiano"
        elif "università" in title_lower:
            return "Università Italiana"
        elif "comune" in title_lower:
            return "Comune Italiano"
        elif "regione" in title_lower:
            return "Regione Italiana"
        elif "ministero" in title_lower:
            return "Ministero Italiano"
        else:
            return "Ente Pubblico Italiano"

    def _extract_value_it(self, text: str) -> Optional[float]:
        """이탈리아어 추정가격 추출"""
        import re

        # 이탈리아 금액 패턴
        value_patterns = [
            r"(\d+(?:\.\d+)*(?:,\d+)?)\s*€",
            r"€\s*(\d+(?:\.\d+)*(?:,\d+)?)",
            r"(\d+(?:\.\d+)*(?:,\d+)?)\s*euro",
            r"importo[:\s]*(\d+(?:\.\d+)*(?:,\d+)?)",
            r"valore[:\s]*(\d+(?:\.\d+)*(?:,\d+)?)"
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

    def _extract_deadline_it(self, text: str) -> Optional[str]:
        """이탈리아어 마감일 추출"""
        import re

        # 이탈리아 날짜 패턴
        date_patterns = [
            r"(\d{1,2}/\d{1,2}/\d{4})",
            r"(\d{1,2}-\d{1,2}-\d{4})",
            r"(\d{4}-\d{1,2}-\d{1,2})",
            r"scadenza[:\s]*(\d{1,2}/\d{1,2}/\d{4})",
            r"entro[:\s]*(\d{1,2}/\d{1,2}/\d{4})"
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _parse_date_it(self, date_str: str) -> str:
        """이탈리아 날짜 형식 파싱"""
        try:
            from datetime import datetime

            # 이탈리아어 날짜 형식들
            formats = [
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S %z",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y",
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

    def _is_healthcare_related_it(self, tender_info: Dict[str, Any]) -> bool:
        """이탈리아어 의료기기 관련 공고 확인"""
        # CPV 코드 확인
        cpv_codes = tender_info.get("cpv_codes", [])
        if any(cpv.startswith(hc) for cpv in cpv_codes for hc in ["331", "336", "337"]):
            return True

        # 이탈리아어 의료 키워드 확인
        text = f"{tender_info.get('title', '')} {tender_info.get('description', '')}".lower()

        return any(keyword in text for keyword in self.medical_keywords_it)

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