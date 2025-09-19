"""
G2B (나라장터) API Crawler
조달청 공공데이터 포털 Open API - 입찰공고정보서비스 기반 크롤러
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from src.crawler.base import BaseCrawler
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class G2BCrawler(BaseCrawler):
    """나라장터(G2B) API 크롤러"""

    def __init__(self):
        super().__init__("G2B", "KR")
<<<<<<< HEAD
        self.api_base_url = "http://apis.data.go.kr/1230000/ao/PubDataOpnStdService"
        self.api_key = settings.G2B_API_KEY

        # 공공데이터개방표준서비스 오퍼레이션
        self.operation = "getDataSetOpnStdBidPblancInfo"  # 입찰공고정보
=======
        self.api_base_url = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
        self.api_key = settings.G2B_API_KEY

        # API 오퍼레이션 엔드포인트
        self.operations = {
            "service": "getBidPblancListInfoServc",      # 용역
            "goods": "getBidPblancListInfoThng",         # 물품
            "construction": "getBidPblancListInfoCnstwk", # 공사
            "etc": "getBidPblancListInfoEtc"             # 기타
        }
>>>>>>> 4c7bf815c6480e85632e520778aff85a1437ef68

    async def login(self) -> bool:
        """API 기반이므로 로그인 불필요"""
        if not self.api_key:
            logger.warning("G2B API 키가 설정되지 않았습니다.")
            logger.warning("data.go.kr에서 '누리장터 민간입찰공고서비스' API 키를 발급받아 .env 파일의 G2B_API_KEY에 설정하세요.")
            logger.warning("더미 모드로 전환됩니다.")
            self.dummy_mode = True
            return False

        logger.info("G2B API 키 인증 준비 완료")
        return True

    def setup_driver(self):
        """API 기반이므로 WebDriver 불필요"""
        logger.info("G2B API 크롤러 - WebDriver 설정 스킵")
        self.dummy_mode = not bool(self.api_key)

    def teardown_driver(self):
        """API 기반이므로 정리 작업 불필요"""
        logger.info("G2B API 크롤러 - WebDriver 정리 스킵")

    async def search_bids(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """입찰 정보 검색"""
        if self.dummy_mode:
            logger.info("G2B API 키가 없어 더미 모드로 실행")
            dummy_data = self.generate_dummy_data(keywords)
            # 더미 데이터도 결과에 포함시켜 테스트 가능하도록
            await self._save_dummy_results(dummy_data)
            return dummy_data

        all_results = []

        try:
            # Seegene 키워드 추가
            from src.config import crawler_config
            seegene_keywords = []
            seegene_keywords.extend(crawler_config.SEEGENE_KEYWORDS['korean'][:3])  # 상위 3개 한국어 키워드
            seegene_keywords.extend(crawler_config.SEEGENE_KEYWORDS['english'][:3])  # 상위 3개 영어 키워드

            # 사용자 키워드와 Seegene 키워드 결합
            search_keywords = keywords + seegene_keywords
            logger.info(f"🔍 검색 키워드: {search_keywords}")

            # 공공데이터개방표준서비스 API 검색
            results = await self._search_standard_api(search_keywords)
            all_results.extend(results)

            # 중복 제거
            unique_results = self._remove_duplicates(all_results)

            logger.info(f"G2B API 검색 완료: 총 {len(unique_results)}건")
            return unique_results

        except Exception as e:
            logger.error(f"G2B API 검색 중 오류: {e}")
            return all_results

    async def _search_standard_api(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """공공데이터개방표준서비스 API 검색"""
        results = []

        try:
            # 검색 기간 설정 (최근 30일, API 제한: 1개월)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            # 표준 API 파라미터 구성
            params = {
                'ServiceKey': self.api_key,  # 대문자 S 주의
                'type': 'json',
                'numOfRows': 100,
                'pageNo': 1,
                'bidNtceBgnDt': start_date.strftime('%Y%m%d%H%M'),  # 입찰공고시작일시
                'bidNtceEndDt': end_date.strftime('%Y%m%d%H%M')     # 입찰공고종료일시
            }

            logger.info(f"🔍 표준 API 검색 - 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

            # API 호출
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base_url}/{self.operation}"

                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"API 호출 실패: {response.status}")
                        return results

                    data = await response.text()
<<<<<<< HEAD
                    logger.info(f"API 응답 내용 (처음 500자): {data[:500]}")

                    if not data.strip():
                        logger.warning("API에서 빈 응답 수신")
                        return results

                    # XML 오류 응답 확인
                    if data.strip().startswith('<OpenAPI_ServiceResponse>'):
                        logger.error("G2B API 인증 오류 - XML 오류 응답 수신")
                        if 'SERVICE_ACCESS_DENIED_ERROR' in data:
                            logger.error("🚫 G2B API 키 인증 실패 (오류코드: 20)")
                            logger.error("📋 해결 방법:")
                            logger.error("   1. data.go.kr 공공데이터포털 접속")
                            logger.error("   2. '나라장터 공공데이터개방표준서비스' 검색 및 활용신청")
                            logger.error("   3. 승인된 API 키를 .env 파일의 G2B_API_KEY에 설정")
                            logger.error(f"   4. 현재 설정된 키: {self.api_key[:10]}...{self.api_key[-10:]}")
                        logger.error(f"📄 전체 오류 응답: {data}")
                        return results

                    try:
                        json_data = json.loads(data)
                        logger.info(f"JSON 파싱 성공. 응답 구조: {list(json_data.keys()) if isinstance(json_data, dict) else type(json_data)}")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON 파싱 오류: {e}")
                        logger.error(f"응답 내용: {data}")
=======
                    try:
                        json_data = json.loads(data)
                    except json.JSONDecodeError:
                        logger.error("API 응답을 JSON으로 파싱하지 못했습니다. XML 응답일 수 있습니다.")
>>>>>>> 4c7bf815c6480e85632e520778aff85a1437ef68
                        return results

                    # 응답 데이터 파싱
                    results = await self._parse_standard_api_response(json_data, keywords)

        except Exception as e:
            logger.error(f"표준 API 검색 중 오류: {e}")

        return results

    async def _parse_standard_api_response(self, json_data: Dict, keywords: List[str]) -> List[Dict[str, Any]]:
        """API 응답 데이터 파싱"""
        results = []

        try:
            # 표준 API 응답 구조 확인
            if 'response' not in json_data:
                logger.warning("API 응답에 'response' 키가 없습니다")
                return results

            response = json_data['response']

            # 결과 코드 확인
            header = response.get('header', {})
            result_code = header.get('resultCode') or header.get('resultcode')
            if result_code != '00':
                logger.warning(f"API 오류: {header.get('resultMsg', 'Unknown error')}")
                return results

            # 데이터 추출
            body = response.get('body', {})
            items = body.get('items', [])
            total_count = body.get('totalCount', 0)

            logger.info(f"📊 전체 결과 수: {total_count}건")
            logger.info(f"🔍 items 타입: {type(items)}, 길이: {len(items) if isinstance(items, list) else 'N/A'}")

            if not items:
                logger.info("검색 결과 없음")
                return results

            # 리스트 처리 (단일 아이템인 경우 리스트로 변환)
            items = self._normalize_items(items)

            for item in items:
                try:
<<<<<<< HEAD
                    # 키워드 필터링 (표준 API 필드 사용)
                    title = item.get('ntceNm', '')  # 입찰공고명
                    organization = item.get('ntceInsttNm', '')  # 공고기관명

                    # 디버깅: 입찰 제목 로그
                    logger.info(f"📋 입찰제목: {title}")
=======
                    # 키워드 필터링
                    title = self._get_first_non_empty(item, ['bidNtceNm', 'ntceNm', 'bidNm'])
                    organization = self._get_first_non_empty(item, ['ntceInsttNm', 'dminsttNm', 'insttNm'])
>>>>>>> 4c7bf815c6480e85632e520778aff85a1437ef68

                    if not self._matches_keywords(title, organization, keywords):
                        logger.info(f"❌ 키워드 매칭 실패: {title[:50]}...")
                        continue

                    logger.info(f"✅ 키워드 매칭 성공: {title[:50]}...")

                    # 관련성 점수 계산
                    relevance_score = self.calculate_relevance_score(title, organization)

                    # 긴급도 레벨 계산
<<<<<<< HEAD
                    deadline_date = item.get('bidClseDate', '')  # 입찰마감일자
                    urgency_level = self.determine_urgency_level(deadline_date)

                    # 입찰정보 구성 (표준 API 필드 매핑)
                    bid_info = {
                        "title": title,
                        "organization": organization,
                        "bid_number": item.get('bidNtceNo', ''),  # 입찰공고번호
                        "announcement_date": item.get('nticeDt', ''),  # 입찰공고일자
                        "deadline_date": deadline_date,
                        "estimated_price": self._format_price(item.get('presmptPrce', '')),  # 추정가격
                        "currency": "KRW",
                        "source_url": item.get('bidNtceUrl', ''),  # 입찰공고URL
=======
                    deadline_date = self._get_first_non_empty(item, ['bidClseDt', 'bidClseDt1', 'bidClseDt2'])
                    urgency_level = self.determine_urgency_level(deadline_date)

                    # 입찰정보 구성
                    bid_number = item.get('bidNtceNo', '')
                    bid_notice_order = item.get('bidNtceOrd', '')
                    announcement_date_raw = self._get_first_non_empty(item, ['bidNtceDt', 'nticeDt', 'ntceDt'])
                    estimated_price_raw = self._get_first_non_empty(item, ['presmptPrce', 'refAmt', 'asignBdgtAmt'])
                    budget_amount_raw = self._get_first_non_empty(item, ['asignBdgtAmt', 'bdgtAmt'])

                    detail_url = self._get_first_non_empty(item, ['bidNtceDtlUrl']) or self._generate_detail_url(
                        bid_number,
                        bid_notice_order
                    )

                    bid_info = {
                        "title": title,
                        "organization": organization,
                        "bid_number": bid_number,
                        "announcement_date": self._format_date(announcement_date_raw),
                        "deadline_date": self._format_date(deadline_date),
                        "estimated_price": self._format_price(estimated_price_raw),
                        "currency": "KRW",
                        "source_url": detail_url,
>>>>>>> 4c7bf815c6480e85632e520778aff85a1437ef68
                        "source_site": "G2B",
                        "country": "KR",
                        "keywords": self._extract_keywords(title, organization),
                        "relevance_score": relevance_score,
                        "urgency_level": urgency_level,
                        "status": "active",
                        "extra_data": {
                            "crawled_at": datetime.now().isoformat(),
<<<<<<< HEAD
                            "bid_order": item.get('bidNtceOrd', ''),  # 입찰공고차수
                            "business_division": item.get('bsnsDivNm', ''),  # 업무구분명
                            "contract_method": item.get('cntrctCnclsMthdNm', ''),  # 계약체결방법명
                            "contract_type": item.get('cntrctCnclsSttusNm', ''),  # 계약체결형태명
                            "decision_method": item.get('bidwinrDcsnMthdNm', ''),  # 낙찰자결정방법명
                            "opening_date": item.get('opengDate', ''),  # 개찰일자
                            "opening_time": item.get('opengTm', ''),  # 개찰시각
                            "opening_place": item.get('opengPlce', ''),  # 개찰장소
                            "budget_amount": self._format_price(item.get('asignBdgtAmt', '')),  # 배정예산금액
                            "international_bid": item.get('intrntnlBidYn', ''),  # 국제입찰여부
                            "electronic_bid": item.get('elctrnBidYn', ''),  # 전자입찰여부
                            "demand_institution": item.get('dmndInsttNm', ''),  # 수요기관명
                            "notice_status": item.get('bidNtceSttusNm', ''),  # 입찰공고상태명
                            "region_limit": item.get('rgnLmtYn', ''),  # 지역제한여부
                            "industry_limit": item.get('indstrytyLmtYn', ''),  # 업종제한여부
                            "api_data": True,
                            "api_version": "standard"
=======
                            "category": category,
                            "bid_method": item.get('bidMethdNm', ''),
                            "contract_method": item.get('cntrctMthdNm', ''),
                            "bid_qualification": self._get_first_non_empty(item, ['bidQlfctNm', 'bidPrtcptQlfctNm']),
                            "opening_date": self._format_date(self._get_first_non_empty(item, ['opengDt', 'bidOpenDt'])),
                            "opening_place": self._get_first_non_empty(item, ['opengPlce', 'bidOpenPlce']),
                            "contact_name": self._get_first_non_empty(item, ['ofclNm', 'chrgePerNm']),
                            "contact_phone": self._get_first_non_empty(item, ['ofclTelNo', 'chrgePerTel']),
                            "contact_email": self._get_first_non_empty(item, ['ofclEmail', 'chrgePerEmail']),
                            "reference_number": self._get_first_non_empty(item, ['refNo', 'bidNtceRefNo']),
                            "notice_division": self._get_first_non_empty(item, ['ntceDivNm', 'ntceKindNm']),
                            "vat_included": self._get_first_non_empty(item, ['vatInclsnYnNm', 'vatYnNm']),
                            "budget_amount": self._format_price(budget_amount_raw),
                            "region_limit": self._get_first_non_empty(item, ['rgnLmtDivNm', 'bidAreaLmtYnNm']),
                            "bid_notice_order": bid_notice_order,
                            "api_data": True,
                            "api_service": "BidPublicInfoService"
>>>>>>> 4c7bf815c6480e85632e520778aff85a1437ef68
                        }
                    }

                    results.append(bid_info)

                except Exception as e:
                    logger.warning(f"개별 아이템 파싱 중 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"API 응답 파싱 중 오류: {e}")

        return results

    def _matches_keywords(self, title: str, organization: str, keywords: List[str]) -> bool:
        """키워드 매칭 확인"""
        from src.config import crawler_config

        text = f"{title} {organization}".lower()

        # Seegene 키워드 확인
        all_keywords = []
        all_keywords.extend(crawler_config.SEEGENE_KEYWORDS['korean'])
        all_keywords.extend(crawler_config.SEEGENE_KEYWORDS['english'])

        for keyword in all_keywords:
            if keyword.lower() in text:
                return True

        # 검색 키워드 확인
        for keyword in keywords:
            if keyword.lower() in text:
                return True

        return False

    def _extract_keywords(self, title: str, organization: str = "") -> List[str]:
        """제목과 기관명에서 키워드 추출"""
        keywords = []
        text_lower = f"{title} {organization}".lower()

        from src.config import crawler_config
        for keyword in crawler_config.SEEGENE_KEYWORDS['korean']:
            if keyword.lower() in text_lower:
                keywords.append(keyword)
        for keyword in crawler_config.SEEGENE_KEYWORDS['english']:
            if keyword.lower() in text_lower:
                keywords.append(keyword)

        return list(set(keywords))  # 중복 제거

    def _normalize_items(self, items: Any) -> List[Dict[str, Any]]:
        """API 응답 items 구조를 리스트로 정규화"""
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]

        if isinstance(items, dict):
            if 'item' in items:
                nested = items['item']
                if isinstance(nested, list):
                    return [item for item in nested if isinstance(item, dict)]
                if isinstance(nested, dict):
                    return [nested]
            return [items]

        return []

    def _get_first_non_empty(self, item: Dict[str, Any], keys: List[str]) -> str:
        """주어진 키 목록에서 가장 먼저 등장하는 유효한 값을 반환"""
        for key in keys:
            value = item.get(key)
            if value is not None and str(value).strip() != "":
                return value
        return ""

    def _format_date(self, date_str: str) -> str:
        """날짜 형식 변환"""
        if not date_str:
            return ""

        value = str(date_str).strip()
        if not value:
            return ""

        date_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y%m%d%H%M%S",
            "%Y%m%d%H%M",
            "%Y%m%d",
            "%Y/%m/%d",
            "%Y.%m.%d"
        ]

        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(value, fmt)
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                continue

        if len(value) >= 10:
            return value[:10]
        return value

    def _format_price(self, price_str: str) -> str:
        """가격 형식 변환"""
        if price_str is None:
            return ""

        value = str(price_str).strip()
        if not value:
            return ""

        normalized = value.replace(",", "")

        try:
            price_num = float(normalized)
        except ValueError:
            filtered = "".join(ch for ch in normalized if ch.isdigit() or ch == '.')
            if not filtered:
                return value
            try:
                price_num = float(filtered)
            except ValueError:
                return value

        return f"{int(price_num):,}원"

    def _generate_detail_url(self, bid_number: str, bid_notice_order: str = "") -> str:
        """상세 페이지 URL 생성"""
        if not bid_number:
            return ""
        base_url = "https://www.g2b.go.kr/ep/invitation/publish/bidInfoDtl/bidInfoDtl.do"
        if bid_notice_order:
            return f"{base_url}?bidNo={bid_number}&bidRound={bid_notice_order}"
        return f"{base_url}?bidNo={bid_number}"

    def _remove_duplicates(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 제거"""
        seen_bid_keys = set()
        unique_results = []

        for result in results:
            bid_number = result.get('bid_number', '')
            bid_notice_order = result.get('extra_data', {}).get('bid_notice_order', '') if isinstance(result.get('extra_data'), dict) else ''
            bid_key = (bid_number, bid_notice_order)

            if bid_number and bid_key not in seen_bid_keys:
                seen_bid_keys.add(bid_key)
                unique_results.append(result)
            elif not bid_number:  # bid_number가 없는 경우 URL로 중복 체크
                source_url = result.get('source_url', '')
                if source_url not in [r.get('source_url', '') for r in unique_results]:
                    unique_results.append(result)

        return unique_results

    def parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """G2B API 마감일 파싱"""
        try:
            if not deadline_str or deadline_str.strip() == "":
                return None

            # API 응답 형식: "2025-01-15 14:30:00"
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
                try:
                    return datetime.strptime(deadline_str.strip(), fmt)
                except ValueError:
                    continue

            return None

        except Exception:
            return None

    def generate_dummy_data(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """더미 데이터 생성 (API 키가 없을 때)"""
        dummy_bids = []

        categories = ["용역", "물품", "공사", "기타"]

        for i, keyword in enumerate(keywords[:2]):  # 최대 2개 키워드
            for j, category in enumerate(categories):
                dummy_bid = {
                    "title": f"[API 테스트] {keyword} 관련 {category} 입찰공고 {i+1}-{j+1}",
                    "organization": f"테스트기관{i+1}-{j+1}",
                    "bid_number": f"API-TEST-{datetime.now().strftime('%Y%m%d')}-{i+1:02d}{j+1:02d}",
                    "announcement_date": datetime.now().strftime("%Y-%m-%d"),
                    "deadline_date": (datetime.now() + timedelta(days=7+i+j)).strftime("%Y-%m-%d"),
                    "estimated_price": f"{(i+j+1)*15000000:,}원",
                    "currency": "KRW",
                    "source_url": f"https://test.g2b.go.kr/bid/{i+1}{j+1}",
                    "source_site": "G2B",
                    "country": "KR",
                    "keywords": [keyword],
                    "relevance_score": 8.5 - (i+j)*0.5,
                    "urgency_level": "medium",
                    "status": "active",
                    "extra_data": {
                        "crawled_at": datetime.now().isoformat(),
                        "category": category,
                        "bid_notice_order": f"{j+1}",
                        "api_data": False,
                        "api_service": "BidPublicInfoService",
                        "dummy_data": True,
                        "note": "G2B API 키 없음으로 인한 테스트 데이터"
                    }
                }
                dummy_bids.append(dummy_bid)

        logger.info(f"G2B API 더미 데이터 {len(dummy_bids)}건 생성")
        return dummy_bids
