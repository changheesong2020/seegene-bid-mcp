"""
Base Crawler Class
크롤러 기본 클래스
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from src.config import settings, crawler_config
from src.utils.logger import get_logger
from src.database.connection import DatabaseManager

logger = get_logger(__name__)


class BaseCrawler(ABC):
    """크롤러 기본 클래스"""

    def __init__(self, site_name: str, country: str = "KR"):
        self.site_name = site_name
        self.country = country
        self.driver = None
        self.wait = None
        self.results = []
        self.session_active = False
        self.dummy_mode = False

    def setup_driver(self):
        """WebDriver 설정 (API 기반 크롤러는 스킵)"""
        # API 기반 크롤러는 WebDriver 불필요
        if self.site_name in ["G2B", "UK_FTS", "TED"]:
            logger.info(f"{self.site_name} API 크롤러 - WebDriver 설정 스킵")
            return

        try:
            chrome_options = Options()

            if settings.HEADLESS_MODE:
                chrome_options.add_argument("--headless")

            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument("--ignore-ssl-errors")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            try:
                # Chrome 드라이버 설치 시도
                logger.info("Chrome 드라이버 설치 중...")

                # webdriver-manager 설정
                import os
                os.environ['WDM_LOG_LEVEL'] = '0'  # 로그 레벨 낮춤

                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome 드라이버 초기화 성공")

            except Exception as chrome_error:
                logger.warning(f"Chrome 드라이버 실패: {chrome_error}")

                # Edge 드라이버로 대체 시도 (Windows에서만)
                try:
                    import platform
                    if platform.system() == "Windows":
                        from selenium.webdriver.edge.options import Options as EdgeOptions
                        from selenium.webdriver.edge.service import Service as EdgeService

                        logger.info("Edge 드라이버로 대체 시도")
                        edge_options = EdgeOptions()
                        if settings.HEADLESS_MODE:
                            edge_options.add_argument("--headless")
                        edge_options.add_argument("--no-sandbox")
                        edge_options.add_argument("--disable-dev-shm-usage")
                        edge_options.add_argument("--disable-gpu")

                        # 시스템에 설치된 Edge 사용
                        self.driver = webdriver.Edge(options=edge_options)
                        logger.info("Edge 드라이버 초기화 성공")
                    else:
                        raise Exception("Linux/Mac에서 Edge 지원 안함")

                except Exception as edge_error:
                    logger.warning(f"Edge 드라이버도 실패: {edge_error}")
                    logger.warning("WebDriver 초기화 실패 - API 전용 모드")
                    self.driver = None

            if self.driver:
                self.wait = WebDriverWait(self.driver, 10)
                logger.info(f"{self.site_name} 크롤러 WebDriver 초기화 완료")
            else:
                logger.info(f"{self.site_name} 크롤러 API 전용 모드로 초기화")

        except Exception as e:
            logger.error(f"WebDriver 설정 실패: {e}")
            logger.info("API 전용 모드로 계속 진행")
            self.driver = None

    def teardown_driver(self):
        """WebDriver 정리"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info(f"{self.site_name} 크롤러 WebDriver 종료")
            except:
                pass
            finally:
                self.driver = None
                self.wait = None
                self.session_active = False

    @abstractmethod
    async def login(self) -> bool:
        """로그인 수행"""
        pass

    @abstractmethod
    async def search_bids(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """입찰 정보 검색"""
        pass

    def calculate_relevance_score(self, title: str, description: str = "") -> float:
        """향상된 관련성 점수 계산"""
        from src.utils.keyword_expansion import keyword_engine
        from src.models.advanced_filters import KeywordExpansion

        # 기본 키워드로 확장된 키워드 생성
        all_keywords = []
        all_keywords.extend(crawler_config.SEEGENE_KEYWORDS['korean'])
        all_keywords.extend(crawler_config.SEEGENE_KEYWORDS['english'])

        # 키워드 확장
        expansion_config = KeywordExpansion(
            enable_synonyms=True,
            enable_related_terms=True,
            enable_translations=True,
            enable_abbreviations=True,
            max_expansions_per_keyword=3
        )

        expanded_keywords = keyword_engine.expand_keywords(all_keywords, expansion_config)

        # 향상된 관련성 점수 계산
        text = f"{title} {description}"
        score = keyword_engine.calculate_enhanced_relevance(text, expanded_keywords)

        # 추가 점수 요소
        text_lower = text.lower()
        high_value_terms = ['대량', 'bulk', '긴급', 'urgent', '우선', 'priority', '특급', 'express']
        for term in high_value_terms:
            if term.lower() in text_lower:
                score += 0.3

        # 제목에서의 매칭에 추가 가중치
        title_lower = title.lower()
        for expanded_kw in expanded_keywords:
            if expanded_kw.keyword.lower() in title_lower:
                score += 0.2 * expanded_kw.weight

        return min(score, 10.0)  # 최대 10점

    def determine_urgency_level(self, deadline_str: str) -> str:
        """긴급도 레벨 결정"""
        try:
            # 마감일 파싱 (각 사이트별로 오버라이드 가능)
            deadline = self.parse_deadline(deadline_str)
            if not deadline:
                return 'low'

            days_left = (deadline - datetime.now()).days

            if days_left <= settings.URGENT_DEADLINE_DAYS:
                return 'high'
            elif days_left <= 7:
                return 'medium'
            else:
                return 'low'

        except Exception:
            return 'low'

    def parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """마감일 문자열 파싱 (각 크롤러에서 오버라이드)"""
        return None

    def generate_dummy_data(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """더미 데이터 생성 비활성화"""
        logger.warning(f"{self.site_name}: 더미 데이터 생성이 비활성화되었습니다")
        return []

    def safe_find_element(self, by, value, timeout=5):
        """안전한 요소 찾기"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None

    def safe_find_elements(self, by, value, timeout=5):
        """안전한 요소들 찾기"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            return []

    def safe_get_text(self, element) -> str:
        """안전한 텍스트 추출"""
        try:
            return element.text.strip() if element else ""
        except:
            return ""

    def safe_get_attribute(self, element, attribute: str) -> str:
        """안전한 속성 추출"""
        try:
            return element.get_attribute(attribute) if element else ""
        except:
            return ""

    async def save_results(self):
        """크롤링 결과 저장"""
        if not self.results:
            logger.info(f"{self.site_name}: 저장할 결과가 없습니다")
            return

        try:
            await DatabaseManager.save_bid_info(self.results)
            logger.info(f"{self.site_name}: {len(self.results)}건의 입찰 정보 저장 완료")
            self.results.clear()

        except Exception as e:
            logger.error(f"{self.site_name}: 결과 저장 실패 - {e}")

    async def run_crawler(self, keywords: List[str] = None) -> Dict[str, Any]:
        """크롤러 실행"""
        if not keywords:
            keywords = crawler_config.SEEGENE_KEYWORDS['korean']

        start_time = time.time()
        logger.info(f"{self.site_name} 크롤링 시작")

        try:
            # WebDriver 설정
            self.setup_driver()

            # 더미 모드 비활성화 - API 전용 모드로 진행

            # 로그인
            login_success = await self.login()
            if not login_success:
                logger.warning(f"{self.site_name}: 로그인 실패, 공개 검색으로 진행")

            # 입찰 정보 검색
            results = await self.search_bids(keywords)
            self.results = results

            # 결과 개수 저장 (save_results에서 clear되기 전에)
            total_found = len(results)

            # 결과 저장
            await self.save_results()

            execution_time = time.time() - start_time

            return {
                "success": True,
                "site": self.site_name,
                "total_found": total_found,
                "execution_time": round(execution_time, 2),
                "login_success": login_success
            }

        except Exception as e:
            logger.error(f"{self.site_name} 크롤링 실패: {e}")
            execution_time = time.time() - start_time
            return {
                "success": False,
                "site": self.site_name,
                "error": str(e),
                "total_found": 0,
                "execution_time": round(execution_time, 2),
                "login_success": False
            }

        finally:
            self.teardown_driver()