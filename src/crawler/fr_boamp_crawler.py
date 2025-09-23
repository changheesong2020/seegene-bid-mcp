"""
French BOAMP/PLACE 크롤러
프랑스 공공조달 플랫폼 데이터 수집
"""

import asyncio
import ssl
from pathlib import Path
from typing import Any, Dict, List, Optional
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


class FranceBOAMPCrawler(BaseCrawler):
    """프랑스 BOAMP/PLACE 공공조달 크롤러"""

    def __init__(self):
        super().__init__("FR_BOAMP", "FR")

        # BOAMP API 설정
        self.boamp_base_url = "https://www.boamp.fr"
        self.place_base_url = "https://www.marches-publics.gouv.fr"

        # OpenDataSoft API 엔드포인트 (BOAMP는 OpenDataSoft 플랫폼 사용)
        self.api_base_url = f"{self.boamp_base_url}/api"
        self.records_api = f"{self.api_base_url}/records/1.0/search/"

        # RSS/XML 피드 URL들 (OpenDataSoft 형식)
        self.rss_feeds = [
            f"{self.api_base_url}/records/1.0/search/?format=rss",
            f"{self.api_base_url}/feeds/rss"
        ]

        # 검색 페이지 URL
        self.search_page_url = f"{self.boamp_base_url}/pages/recherche/"

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
            # OpenDataSoft API 검색 (우선순위)
            if keywords:
                api_results = await self._crawl_api_search(keywords)
                results.extend(api_results)

            # API 검색 결과가 없으면 RSS 피드 시도
            if not results:
                rss_results = await self._crawl_rss_feeds(keywords)
                results.extend(rss_results)

            # 여전히 결과가 없으면 웹 검색 시도
            if not results and keywords:
                web_results = await self._crawl_web_search(keywords)
                results.extend(web_results)

            # 결과 중복 제거
            unique_results = self._remove_duplicates(results)

            logger.info(f"프랑스 BOAMP 크롤링 완료 - 총 {len(unique_results)}건 수집")

            # 데이터베이스에 저장
            if unique_results:
                try:
                    await DatabaseManager.save_bid_info(unique_results)
                    logger.info(f"💾 FR_BOAMP 데이터베이스 저장 완료: {len(unique_results)}건")
                except Exception as e:
                    logger.error(f"❌ FR_BOAMP 데이터베이스 저장 실패: {e}")
            else:
                logger.info("📝 FR_BOAMP 저장할 데이터가 없습니다")

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
                "total_collected": 0,
                "timestamp": datetime.now().isoformat()
            }

    async def _crawl_api_search(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """OpenDataSoft API를 통한 검색"""
        results = []

        connector = aiohttp.TCPConnector(ssl=create_ssl_context())
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45),
            connector=connector,
            headers=DEFAULT_HEADERS,
        ) as session:

            for keyword in keywords[:3]:  # 최대 3개 키워드
                try:
                    logger.info(f"API 검색: {keyword}")

                    # OpenDataSoft API 파라미터
                    api_params = {
                        "dataset": "boamp",  # 추정되는 데이터셋 이름
                        "q": keyword,
                        "rows": 20,
                        "start": 0,
                        "format": "json",
                        "facet": ["type_de_marche", "procedure", "cpv"]
                    }

                    async with session.get(
                        self.records_api,
                        params=api_params,
                        headers=DEFAULT_HEADERS,
                    ) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                api_results = await self._parse_api_response(data, keyword)
                                results.extend(api_results)
                                logger.info(f"API에서 {len(api_results)}건 수집")
                            except json.JSONDecodeError as e:
                                logger.warning(f"API 응답 JSON 파싱 오류: {e}")
                        else:
                            logger.warning(f"API 검색 실패: {response.status}")

                    # 요청 간격 조절
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.warning(f"API 검색 오류 {keyword}: {e}")

        return results

    async def _parse_api_response(self, data: Dict[str, Any], keyword: str) -> List[Dict[str, Any]]:
        """API 응답 데이터 파싱"""
        results = []

        try:
            records = data.get("records", [])
            total_hits = data.get("nhits", 0)
            logger.info(f"API 응답: 총 {total_hits}건 중 {len(records)}건 처리")

            for record in records:
                try:
                    fields = record.get("fields", {})
                    record_id = record.get("recordid", "")

                    # BOAMP 데이터는 'donnees' 필드에 JSON 문자열로 저장됨
                    donnees_str = fields.get("donnees", "")
                    nature_libelle = fields.get("nature_libelle", "")

                    title = ""
                    organization = ""
                    estimated_value = None
                    cpv_codes = []
                    description = f"키워드: {keyword}"

                    # JSON 데이터 파싱
                    if donnees_str:
                        try:
                            donnees = json.loads(donnees_str)

                            # 제목 추출
                            if "OBJET" in donnees:
                                objet = donnees["OBJET"]
                                title = objet.get("TITRE_MARCHE", "")
                                if "OBJET_COMPLET" in objet:
                                    description = objet["OBJET_COMPLET"]

                                # CPV 코드
                                if "CPV" in objet and "PRINCIPAL" in objet["CPV"]:
                                    cpv_codes = [objet["CPV"]["PRINCIPAL"]]

                                # 가격 정보
                                if "CARACTERISTIQUES" in objet and "VALEUR" in objet["CARACTERISTIQUES"]:
                                    valeur = objet["CARACTERISTIQUES"]["VALEUR"]
                                    if isinstance(valeur, dict) and "#text" in valeur:
                                        estimated_value = self._parse_value(valeur["#text"])
                                    elif isinstance(valeur, str):
                                        estimated_value = self._parse_value(valeur)

                            # 기관명 추출
                            if "IDENTITE" in donnees:
                                identite = donnees["IDENTITE"]
                                organization = identite.get("DENOMINATION", "")

                        except json.JSONDecodeError as e:
                            logger.warning(f"JSON 파싱 오류: {e}")
                            # JSON 파싱 실패시 기본값 사용
                            title = f"BOAMP 공고 - {keyword}"

                    # 기본값 설정
                    if not title:
                        title = f"BOAMP 공고 - {keyword}"
                    if not organization:
                        organization = "프랑스 공공기관"

                    # URL 구성
                    source_url = f"{self.boamp_base_url}/avis/{record_id}" if record_id else ""

                    tender_info = {
                        "title": title[:200].strip(),
                        "description": description[:500] if description else f"키워드: {keyword}",
                        "organization": organization.strip(),
                        "source_url": source_url,
                        "publication_date": "",  # API 응답에서 직접 날짜 정보를 찾지 못함
                        "deadline_date": "",
                        "estimated_value": estimated_value,
                        "currency": "EUR",
                        "source_site": "BOAMP",
                        "country": "FR",
                        "cpv_codes": cpv_codes,
                        "keywords": [keyword],
                        "tender_type": self._determine_tender_type(title),
                        "notice_type": "API",
                        "language": "fr",
                        "record_id": record_id,
                        "nature": nature_libelle
                    }

                    # 의료기기 관련 필터링
                    if self._is_healthcare_related(tender_info):
                        results.append(tender_info)
                        logger.debug(f"의료기기 관련 공고 발견: {title[:100]}")

                except Exception as e:
                    logger.warning(f"API 레코드 파싱 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"API 응답 파싱 오류: {e}")

        return results

    def _parse_value(self, value_str: str) -> Optional[float]:
        """가격 문자열을 숫자로 변환"""
        if not value_str:
            return None

        try:
            # 숫자가 아닌 문자 제거
            import re
            numeric_str = re.sub(r'[^\d.,]', '', str(value_str))
            numeric_str = numeric_str.replace(',', '.')

            if numeric_str:
                return float(numeric_str)
        except (ValueError, TypeError):
            pass

        return None

    async def _crawl_rss_feeds(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """RSS 피드에서 공고 수집"""
        results = []

        connector = aiohttp.TCPConnector(ssl=create_ssl_context())
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=connector,
            headers=DEFAULT_HEADERS,
        ) as session:

            for feed_url in self.rss_feeds:
                try:
                    logger.info(f"RSS 피드 크롤링: {feed_url}")

                    async with session.get(feed_url, headers=DEFAULT_HEADERS) as response:
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

                    # 데이터베이스 모델에 맞는 공고 정보 구성
                    tender_info = {
                        "title": title_text.strip()[:500],  # 길이 제한
                        "organization": self._extract_organization(description_text),
                        "bid_number": f"FR-RSS-{datetime.now().strftime('%Y%m%d')}-{len(results)+1:03d}",
                        "announcement_date": self._parse_date(pub_date_text),
                        "deadline_date": self._extract_deadline(description_text) or self._estimate_deadline_date(),
                        "estimated_price": str(self._extract_value(description_text)) if self._extract_value(description_text) else "",
                        "currency": "EUR",
                        "source_url": link_url.strip(),
                        "source_site": "FR_BOAMP",
                        "country": "FR",
                        "keywords": keywords or [],
                        "relevance_score": self._calculate_relevance_score(title_text, keywords[0] if keywords else ""),
                        "urgency_level": "medium",
                        "status": "active",
                        "extra_data": {
                            "description": description_text.strip()[:1000],  # 길이 제한
                            "tender_type": self._determine_tender_type(title_text),
                            "cpv_codes": self._extract_cpv_codes(description_text),
                            "notice_type": "RSS",
                            "language": "fr",
                            "crawled_at": datetime.now().isoformat()
                        }
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

        connector = aiohttp.TCPConnector(ssl=create_ssl_context())
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45),
            connector=connector,
            headers=DEFAULT_HEADERS,
        ) as session:

            for keyword in keywords[:3]:  # 최대 3개 키워드
                try:
                    logger.info(f"웹 검색: {keyword}")

                    # BOAMP 검색 페이지
                    search_url = self.search_page_url
                    search_params = {
                        "q": keyword,
                        "search": keyword,
                        "type": "all"
                    }

                    async with session.get(
                        search_url,
                        params=search_params,
                        headers=DEFAULT_HEADERS,
                    ) as response:
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
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # OpenDataSoft 기반 결과 검색
            result_items = soup.find_all(['div', 'article'], class_=lambda x: x and ('record' in x.lower() or 'result' in x.lower() or 'notice' in x.lower()))

            if not result_items:
                # 일반적인 HTML 구조에서 검색 결과 찾기
                result_items = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(term in x.lower() for term in ['item', 'entry', 'card', 'box']))

            if not result_items:
                # 제목 태그로 검색 시도
                result_items = soup.find_all(['h2', 'h3', 'h4'])

            logger.info(f"HTML에서 {len(result_items)}개 요소 발견")

            for item in result_items[:10]:  # 최대 10개
                try:
                    title = ""
                    link_url = ""
                    organization = ""
                    description = ""

                    # 제목 추출
                    title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    elif item.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                        title = item.get_text(strip=True)

                    # 링크 추출
                    link_elem = item.find('a', href=True)
                    if link_elem:
                        link_url = urljoin(self.boamp_base_url, link_elem['href'])
                    elif item.name == 'a' and item.get('href'):
                        link_url = urljoin(self.boamp_base_url, item['href'])

                    # 기관명 추출
                    org_elem = item.find(string=lambda text: text and ('ministère' in text.lower() or 'mairie' in text.lower() or 'conseil' in text.lower()))
                    if org_elem:
                        organization = org_elem.strip()

                    # 설명 추출
                    desc_elem = item.find(['p', 'div'], class_=lambda x: x and 'description' in x.lower())
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)

                    # 키워드가 포함된 경우만 처리
                    full_text = f"{title} {description}".lower()
                    if keyword.lower() not in full_text:
                        continue

                    if title:  # 제목이 있는 경우만 처리
                        tender_info = {
                            "title": title[:200],  # 제목 길이 제한
                            "description": description[:500] if description else f"검색 키워드: {keyword}",
                            "organization": organization if organization else "프랑스 공공기관",
                            "source_url": link_url,
                            "publication_date": datetime.now().date().isoformat(),
                            "source_site": "BOAMP",
                            "country": "FR",
                            "currency": "EUR",
                            "tender_type": self._determine_tender_type(title),
                            "keywords": [keyword],
                            "notice_type": "WEB_SEARCH",
                            "language": "fr"
                        }

                        # 의료기기 관련 필터링
                        if self._is_healthcare_related(tender_info):
                            results.append(tender_info)

                except Exception as e:
                    logger.warning(f"검색 결과 아이템 파싱 오류: {e}")
                    continue

            # BeautifulSoup가 없는 경우 정규표현식 사용
        except ImportError:
            logger.warning("BeautifulSoup4가 없어 정규표현식 파싱 사용")
            results = await self._parse_search_results_regex(html_content, keyword)
        except Exception as e:
            logger.warning(f"HTML 파싱 오류: {e}")
            # 정규표현식 파싱으로 폴백
            results = await self._parse_search_results_regex(html_content, keyword)

        return results

    async def _parse_search_results_regex(self, html_content: str, keyword: str) -> List[Dict[str, Any]]:
        """정규표현식을 이용한 검색 결과 파싱 (폴백)"""
        results = []

        try:
            import re

            # 개선된 패턴들
            patterns = [
                # 프랑스 공공조달 관련 제목 패턴
                r'<h[2-4][^>]*>([^<]*(?:marché|appel|consultation|avis|offre)[^<]*)</h[2-4]>',
                # 일반적인 제목 패턴
                r'<h[2-4][^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h[2-4]>',
                # data-* 속성이 있는 제목
                r'data-title="([^"]*)',
                # aria-label 속성
                r'aria-label="([^"]*(?:marché|appel|consultation)[^"]*)"'
            ]

            all_titles = []
            for pattern in patterns:
                titles = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                all_titles.extend(titles)

            # 링크 패턴 (더 포괄적)
            link_patterns = [
                r'href="([^"]*(?:avis|notice|marche)[^"]*)"',
                r'href="(/[^"]*detail[^"]*)"',
                r'href="(/[^"]*record[^"]*)"'
            ]

            all_links = []
            for pattern in link_patterns:
                links = re.findall(pattern, html_content, re.IGNORECASE)
                all_links.extend(links)

            # 제목과 링크 매칭
            for i, title in enumerate(all_titles[:10]):
                try:
                    # 키워드 필터링
                    if keyword.lower() not in title.lower():
                        continue

                    link_url = ""
                    if i < len(all_links):
                        link_url = urljoin(self.boamp_base_url, all_links[i])

                    title_clean = re.sub(r'<[^>]+>', '', title).strip()

                    # 데이터베이스 모델에 맞는 구조로 수정
                    tender_info = {
                        "title": title_clean[:200],
                        "organization": self._extract_organization(title_clean),
                        "bid_number": f"FR-{datetime.now().strftime('%Y%m%d')}-{i+1:03d}",
                        "announcement_date": datetime.now().date().isoformat(),
                        "deadline_date": self._estimate_deadline_date(),
                        "estimated_price": "",  # BOAMP에서는 가격 정보 제한적
                        "currency": "EUR",
                        "source_url": link_url or f"https://www.boamp.fr/search?q={keyword}",
                        "source_site": "FR_BOAMP",
                        "country": "FR",
                        "keywords": [keyword],
                        "relevance_score": self._calculate_relevance_score(title_clean, keyword),
                        "urgency_level": "medium",
                        "status": "active",
                        "extra_data": {
                            "description": f"검색 키워드: {keyword}",
                            "tender_type": self._determine_tender_type(title_clean),
                            "notice_type": "WEB_SEARCH",
                            "language": "fr",
                            "crawled_at": datetime.now().isoformat()
                        }
                    }

                    # 의료기기 관련 필터링
                    if self._is_healthcare_related(tender_info):
                        results.append(tender_info)

                except Exception as e:
                    logger.warning(f"정규표현식 파싱 아이템 오류: {e}")
                    continue

        except Exception as e:
            logger.warning(f"정규표현식 파싱 오류: {e}")

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

    def _extract_organization(self, title: str) -> str:
        """제목에서 기관명 추출"""
        import re

        # 프랑스 기관명 패턴들
        org_patterns = [
            r"(CHU [^,\n\-]+)",
            r"(Hôpital [^,\n\-]+)",
            r"(APHP[^,\n\-]*)",
            r"(Centre [^,\n\-]+)",
            r"(Université [^,\n\-]+)",
            r"(Ministère [^,\n\-]+)",
        ]

        for pattern in org_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "프랑스 공공기관"

    def _estimate_deadline_date(self) -> str:
        """마감일 추정 (BOAMP에서 정확한 날짜를 얻기 어려우므로)"""
        from datetime import timedelta
        estimated_deadline = datetime.now() + timedelta(days=30)
        return estimated_deadline.date().isoformat()

    def _calculate_relevance_score(self, title: str, keyword: str) -> float:
        """관련성 점수 계산"""
        if not title or not keyword:
            return 5.0

        title_lower = title.lower()
        keyword_lower = keyword.lower()

        # 기본 점수
        score = 5.0

        # 키워드가 제목에 있으면 점수 증가
        if keyword_lower in title_lower:
            score += 2.0

        # 의료 관련 키워드가 있으면 점수 증가
        medical_keywords = ['medical', 'health', 'hospital', 'clinical', 'diagnostic']
        for med_keyword in medical_keywords:
            if med_keyword in title_lower:
                score += 1.0
                break

        return min(score, 10.0)  # 최대 10점

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

    async def login(self) -> bool:
        """로그인 - 프랑스 BOAMP는 공개 사이트이므로 로그인 불필요"""
        return True

    async def search_bids(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """입찰 정보 검색 - crawl 메서드를 호출"""
        result = await self.crawl(keywords)
        return result.get("results", [])