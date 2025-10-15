"""
SAM.gov Crawler
미국 정부 조달 사이트 크롤러
"""

import asyncio
import requests
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.crawler.base import BaseCrawler
from src.config import settings, crawler_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SAMGovCrawler(BaseCrawler):
    """SAM.gov (미국 정부 조달) 크롤러"""

    def __init__(self):
        super().__init__("SAM.gov", "US")
        self.base_url = "https://sam.gov"
        self.login_url = "https://sam.gov/content/home"
        self.search_url = "https://sam.gov/search"
        self.api_url = "https://api.sam.gov/opportunities/v2/search"

    async def login(self) -> bool:
        """SAM.gov 로그인 (공개 모드로 진행)"""
        if not settings.SAMGOV_USERNAME or not settings.SAMGOV_PASSWORD:
            logger.info("SAM.gov 로그인 정보가 없습니다. 공개 검색을 진행합니다.")
            return False

        try:
            logger.info("SAM.gov 로그인 시도")

            # SAM.gov는 복잡한 로그인 프로세스(2FA, CAPTCHA 등)를 가지고 있어
            # 공개 모드로 진행하는 것이 더 안정적입니다
            logger.warning("SAM.gov 로그인 건너뛰고 공개 모드로 진행")
            return False

        except Exception as e:
            logger.error(f"SAM.gov 로그인 중 오류: {e}")
            return False

    async def search_bids(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """입찰 정보 검색 (API + Web 크롤링)"""
        all_results = []

        try:
            # API를 사용한 검색 시도
            if settings.SAMGOV_API_KEY:
                api_results = await self._search_via_api(keywords)
                all_results.extend(api_results)

            # 웹 크롤링을 통한 검색
            web_results = await self._search_via_web(keywords)
            all_results.extend(web_results)

            # 중복 제거
            seen_urls = set()
            unique_results = []
            for result in all_results:
                if result['source_url'] not in seen_urls:
                    seen_urls.add(result['source_url'])
                    unique_results.append(result)

            logger.info(f"SAM.gov 검색 완료: 총 {len(unique_results)}건")
            return unique_results

        except Exception as e:
            logger.error(f"SAM.gov 검색 중 오류: {e}")
            return all_results

    async def _search_via_api(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """API를 통한 검색"""
        results = []

        if not settings.SAMGOV_API_KEY:
            return results

        try:
            for keyword in keywords:
                logger.info(f"SAM.gov API에서 '{keyword}' 검색 중")

                # API 요청 헤더와 파라미터
                headers = {
                    "X-API-Key": settings.SAMGOV_API_KEY,
                    "Accept": "application/json",
                    "User-Agent": "Seegene-BidCrawler/1.0"
                }

                params = {
                    "keyword": keyword,
                    "postedFrom": (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y"),
                    "postedTo": datetime.now().strftime("%m/%d/%Y"),
                    "limit": 100,
                    "api_key": settings.SAMGOV_API_KEY,
                }

                # API 호출
                response = requests.get(self.api_url, headers=headers, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    opportunities = data.get('opportunitiesData', [])

                    for opp in opportunities:
                        try:
                            bid_info = self._parse_api_opportunity(opp)
                            if bid_info:
                                results.append(bid_info)
                        except Exception as e:
                            logger.warning(f"API 결과 파싱 중 오류: {e}")

                elif response.status_code == 401:
                    logger.warning(f"API 인증 실패 (401): API 키를 확인하세요")
                else:
                    logger.warning(f"API 호출 실패: {response.status_code} - {response.text[:200]}")

                await asyncio.sleep(1)  # API 호출 간격

        except Exception as e:
            logger.error(f"API 검색 중 오류: {e}")

        return results

    async def _search_via_web(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """웹 크롤링을 통한 검색"""
        results = []

        try:
            # 검색 페이지로 이동
            self.driver.get(self.search_url)
            await asyncio.sleep(3)

            for keyword in keywords:
                logger.info(f"SAM.gov 웹에서 '{keyword}' 검색 중")

                # 더 넓은 범위로 검색 필드 찾기
                search_field = self.safe_find_element(By.XPATH, "//input[contains(@placeholder, 'keyword') or contains(@placeholder, 'search') or @name='q' or @id='search']")

                if search_field:
                    search_field.clear()
                    search_field.send_keys(keyword)
                    logger.info(f"검색어 '{keyword}' 입력 완료")
                else:
                    logger.warning("검색 필드를 찾을 수 없습니다")
                    continue

                # Opportunities 탭/필터 클릭
                opportunities_tab = self.safe_find_element(By.XPATH, "//a[contains(text(), 'Opportunities') or contains(@href, 'opportunities')]")
                if opportunities_tab:
                    opportunities_tab.click()
                    await asyncio.sleep(2)

                # 검색 버튼 클릭
                search_btn = self.safe_find_element(By.XPATH, "//button[contains(text(), 'Search') or @type='submit']")
                if search_btn:
                    search_btn.click()
                    await asyncio.sleep(5)
                else:
                    # Enter 키로 검색 시도
                    if search_field:
                        from selenium.webdriver.common.keys import Keys
                        search_field.send_keys(Keys.RETURN)
                        await asyncio.sleep(5)

                # 결과 파싱
                keyword_results = await self._parse_web_results()
                results.extend(keyword_results)

                await asyncio.sleep(2)  # 요청 간격

        except Exception as e:
            logger.error(f"웹 검색 중 오류: {e}")

        return results

    async def _parse_web_results(self) -> List[Dict[str, Any]]:
        """웹 검색 결과 파싱"""
        results = []

        try:
            # 결과 카드들 찾기
            result_cards = self.safe_find_elements(By.XPATH, "//div[contains(@class, 'search-result')]")

            for card in result_cards[:20]:  # 최대 20개만 처리
                try:
                    # 제목
                    title_element = card.find_element(By.XPATH, ".//h3//a")
                    title = self.safe_get_text(title_element)

                    # 상세 URL
                    detail_url = self.safe_get_attribute(title_element, "href")
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = self.base_url + detail_url

                    # 기관명
                    agency_element = card.find_element(By.XPATH, ".//span[contains(@class, 'agency')]")
                    organization = self.safe_get_text(agency_element)

                    # 게시일
                    posted_element = card.find_element(By.XPATH, ".//span[contains(text(), 'Posted')]")
                    posted_date = self.safe_get_text(posted_element).replace("Posted ", "")

                    # 응답 마감일
                    response_element = card.find_element(By.XPATH, ".//span[contains(text(), 'Response Due')]")
                    deadline_date = self.safe_get_text(response_element).replace("Response Due ", "")

                    # 입찰 번호
                    notice_id_element = card.find_element(By.XPATH, ".//span[contains(text(), 'Notice ID')]")
                    bid_number = self.safe_get_text(notice_id_element).replace("Notice ID ", "")

                    # 관련성 점수 계산
                    relevance_score = self.calculate_relevance_score(title)

                    # 긴급도 레벨
                    urgency_level = self.determine_urgency_level(deadline_date)

                    bid_info = {
                        "title": title,
                        "organization": organization,
                        "bid_number": bid_number,
                        "announcement_date": posted_date,
                        "deadline_date": deadline_date,
                        "estimated_price": "",  # 웹에서는 가격 정보 제한적
                        "currency": "USD",
                        "source_url": detail_url,
                        "source_site": "SAM.gov",
                        "country": "US",
                        "keywords": self._extract_keywords(title),
                        "relevance_score": relevance_score,
                        "urgency_level": urgency_level,
                        "status": "active",
                        "extra_data": {
                            "crawled_at": datetime.now().isoformat(),
                            "search_method": "web"
                        }
                    }

                    results.append(bid_info)

                except Exception as e:
                    logger.warning(f"웹 결과 파싱 중 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"웹 결과 파싱 중 오류: {e}")

        return results

    def _parse_api_opportunity(self, opp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """API 응답 파싱"""
        try:
            title = opp.get('title', '')
            notice_id = opp.get('noticeId', '')

            # 기관 정보
            org_info = opp.get('organizationName', '')

            # 날짜 정보
            posted_date = opp.get('postedDate', '')
            response_date = opp.get('responseDeadline', '')

            # URL 구성
            detail_url = f"{self.base_url}/opportunities/{notice_id}" if notice_id else ""

            # 관련성 점수 계산
            description = opp.get('description', '')
            relevance_score = self.calculate_relevance_score(title, description)

            # 긴급도 레벨
            urgency_level = self.determine_urgency_level(response_date)

            return {
                "title": title,
                "organization": org_info,
                "bid_number": notice_id,
                "announcement_date": posted_date,
                "deadline_date": response_date,
                "estimated_price": "",
                "currency": "USD",
                "source_url": detail_url,
                "source_site": "SAM.gov",
                "country": "US",
                "keywords": self._extract_keywords(title),
                "relevance_score": relevance_score,
                "urgency_level": urgency_level,
                "status": "active",
                "extra_data": {
                    "crawled_at": datetime.now().isoformat(),
                    "search_method": "api",
                    "description": description[:500]  # 설명 일부 저장
                }
            }

        except Exception as e:
            logger.warning(f"API 응답 파싱 중 오류: {e}")
            return None

    def _extract_keywords(self, title: str) -> List[str]:
        """제목에서 키워드 추출"""
        keywords = []
        title_lower = title.lower()

        for keyword in crawler_config.SEEGENE_KEYWORDS['english']:
            if keyword.lower() in title_lower:
                keywords.append(keyword)

        for keyword in crawler_config.SEEGENE_KEYWORDS['korean']:
            if keyword.lower() in title_lower:
                keywords.append(keyword)

        return keywords

    def parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """SAM.gov 마감일 파싱"""
        try:
            if not deadline_str or deadline_str.strip() == "":
                return None

            # SAM.gov 날짜 형식들: "Dec 31, 2024", "12/31/2024", "2024-12-31"
            deadline_str = deadline_str.strip()

            # 다양한 날짜 형식 처리
            formats = [
                "%b %d, %Y",      # Dec 31, 2024
                "%B %d, %Y",      # December 31, 2024
                "%m/%d/%Y",       # 12/31/2024
                "%Y-%m-%d",       # 2024-12-31
                "%m-%d-%Y",       # 12-31-2024
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(deadline_str, fmt)
                except ValueError:
                    continue

            return None

        except Exception:
            return None

