"""G2B (나라장터) API Crawler."""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import quote

from src.crawler.base import BaseCrawler
from src.config import settings
from src.database.connection import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class G2BCrawler(BaseCrawler):
    """나라장터(G2B) API 크롤러"""

    def __init__(self):
        super().__init__("G2B", "KR")
        self.api_key = settings.G2B_API_KEY
        self.encoded_api_key = self._prepare_service_key(self.api_key)

        # BidPublicInfoService 설정
        # 최근 data.go.kr API 경로가 02 버전으로 변경되면서 기존 엔드포인트에서 404가
        # 발생하는 사례가 있어 다중 엔드포인트를 준비한다.
        self.api_base_url_candidates: List[str] = [
            "https://apis.data.go.kr/1230000/ad/BidPublicInfoService02",
            "https://apis.data.go.kr/1230000/ad/BidPublicInfoService",
            "https://apis.data.go.kr/1230000/BidPublicInfoService02",
            "https://apis.data.go.kr/1230000/BidPublicInfoService",
        ]
        self.active_api_base_url: Optional[str] = None
        self.operations = {
            "cnstwk": ("getBidPblancListInfoCnstwkPPSSrch", "공사"),
            "servc": ("getBidPblancListInfoServcPPSSrch", "용역"),
            "thng": ("getBidPblancListInfoThngPPSSrch", "물품"),
            "frgcpt": ("getBidPblancListInfoFrgcptPPSSrch", "외자"),
        }
        self.api_request_timeout = aiohttp.ClientTimeout(total=20)
        self.api_rate_limit_tps = 30
        self.api_rows_per_page = 50  # 페이지 크기 줄여서 API 제한 회피

        # 공공데이터개방표준서비스 설정 (백업용)
        self.standard_api_base_url = "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService"
        self.standard_operation = "getDataSetOpnStdBidPblancInfo"

    async def login(self) -> bool:
        """API 기반이므로 로그인 불필요"""
        if not self.encoded_api_key:
            logger.warning("G2B API 키가 설정되지 않았습니다.")
            logger.warning("data.go.kr에서 '누리장터 민간입찰공고서비스' API 키를 발급받아 .env 파일의 G2B_API_KEY에 설정하세요.")
            return False

        logger.info("G2B API 키 인증 준비 완료")
        return True

    def setup_driver(self):
        """API 기반이므로 WebDriver 불필요"""
        logger.info("G2B API 크롤러 - WebDriver 설정 스킵")

    def teardown_driver(self):
        """API 기반이므로 정리 작업 불필요"""
        logger.info("G2B API 크롤러 - WebDriver 정리 스킵")

    async def search_bids(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """입찰 정보 검색 - 키워드별 개별 검색"""
        if not self.encoded_api_key:
            logger.warning("G2B API 키가 없어 검색 불가")
            return []

        all_results: List[Dict[str, Any]] = []

        try:
            # 키워드가 제공되지 않은 경우 기본 키워드 사용
            if not keywords:
                keywords = ["PCR", "진단키트", "분자진단", "체외진단", "의료기기"]

            logger.info(f"🇰🇷 G2B API 키워드별 개별 검색 시작")
            logger.info(f"🔍 검색 키워드: {keywords}")

            # API 서비스 가용성 사전 체크
            service_available = await self._check_api_service_availability()
            if not service_available:
                logger.error("🚫 G2B API 서비스가 현재 이용 불가능합니다")
                logger.error("💡 해결 방법:")
                logger.error("   1. 나중에 다시 시도하세요")
                logger.error("   2. data.go.kr 서비스 상태를 확인하세요")
                logger.error("   3. 대안: 나라장터 웹사이트 직접 크롤링 고려")
                return []

            # 각 키워드별로 개별 검색
            successful_searches = 0
            for i, keyword in enumerate(keywords, 1):
                try:
                    logger.info(f"[{i}/{len(keywords)}] 키워드 '{keyword}' 검색 중...")
                    keyword_results = []

                    # BidPublicInfoService API 검색 (카테고리별)
                    for category, (operation, label) in self.operations.items():
                        log_label = label if label == category else f"{label}({category})"
                        logger.info(f"  📡 [{keyword}] {log_label} 카테고리 검색")

                        results = await self._search_bid_public_info(
                            operation, category, [keyword], display_name=label
                        )

                        if results:
                            keyword_results.extend(results)
                            logger.info(f"  ✅ [{keyword}] {log_label}에서 {len(results)}건 수집")
                            successful_searches += 1
                        else:
                            logger.info(f"  ⚪ [{keyword}] {log_label} 검색 결과 없음")

                        await asyncio.sleep(0.5)  # 카테고리 간 짧은 대기

                    # 표준 API로도 검색 (일시적으로 비활성화 - 성능 개선)
                    # try:
                    #     standard_results = await self._search_standard_api([keyword])
                    #     if standard_results:
                    #         keyword_results.extend(standard_results)
                    #         logger.info(f"  📦 [{keyword}] 표준 API에서 {len(standard_results)}건 추가")
                    # except Exception as e:
                    #     logger.warning(f"  ⚠️ [{keyword}] 표준 API 검색 실패: {e}")
                    logger.info(f"  ⏭️ [{keyword}] 표준 API 검색 스킵 (성능 최적화)")

                    all_results.extend(keyword_results)
                    logger.info(f"✅ 키워드 '{keyword}' 총 {len(keyword_results)}건 수집")

                    # 키워드 간 대기 (API 제한 준수)
                    if i < len(keywords):
                        await asyncio.sleep(1)

                except Exception as e:
                    logger.warning(f"⚠️ 키워드 '{keyword}' 검색 실패: {e}")
                    continue

            # 검색 결과 요약
            if successful_searches == 0:
                logger.warning("🚨 모든 G2B API 검색이 실패했습니다")
                logger.warning("📋 가능한 원인:")
                logger.warning("   - API 서비스 일시적 중단")
                logger.warning("   - API 키 권한 문제")
                logger.warning("   - 네트워크 연결 문제")
                return []

            # 중복 제거
            unique_results = self._remove_duplicates(all_results)

            logger.info(f"✅ G2B 키워드별 검색 완료: 전체 {len(all_results)}건 수집 → 중복 제거 후 {len(unique_results)}건")

            # 데이터베이스에 저장
            if unique_results:
                try:
                    await DatabaseManager.save_bid_info(unique_results)
                    logger.info(f"💾 G2B 데이터베이스 저장 완료: {len(unique_results)}건")
                except Exception as e:
                    logger.error(f"❌ G2B 데이터베이스 저장 실패: {e}")
            else:
                logger.info("📝 G2B 저장할 데이터가 없습니다")

            return unique_results

        except Exception as e:
            logger.error(f"❌ G2B API 검색 중 오류: {e}")
            return all_results

    def _get_prioritized_api_base_urls(self) -> List[str]:
        """최근 성공한 엔드포인트를 우선적으로 시도"""
        if self.active_api_base_url and self.active_api_base_url in self.api_base_url_candidates:
            prioritized = [self.active_api_base_url]
            prioritized.extend(
                [url for url in self.api_base_url_candidates if url != self.active_api_base_url]
            )
            return prioritized
        return self.api_base_url_candidates

    async def _request_bid_public_info(
        self,
        session: aiohttp.ClientSession,
        operation: str,
        params: Dict[str, Any],
        category_label: str,
    ) -> Optional[str]:
        """엔드포인트 후보를 순회하며 BidPublicInfoService 응답을 가져온다."""

        last_status: Optional[int] = None
        service_unavailable_count = 0

        for base_url in self._get_prioritized_api_base_urls():
            url = f"{base_url}/{operation}"
            try:
                async with session.get(url, params=params) as response:
                    last_status = response.status

                    if response.status == 200:
                        if base_url != self.active_api_base_url:
                            logger.info(f"[{category_label}] G2B API 엔드포인트 사용: {base_url}")
                        self.active_api_base_url = base_url
                        return await response.text()

                    if response.status == 404:
                        logger.warning(
                            f"[{category_label}] 엔드포인트 {url} 에서 404 응답 - 다른 경로 시도"
                        )
                        if self.active_api_base_url == base_url:
                            self.active_api_base_url = None
                        continue

                    if response.status == 503:
                        service_unavailable_count += 1
                        logger.warning(
                            f"[{category_label}] 엔드포인트 {url} 에서 503 서비스 불가 응답 - 다른 경로 시도"
                        )
                        if self.active_api_base_url == base_url:
                            self.active_api_base_url = None
                        continue

                    error_text = await response.text()
                    logger.error(
                        f"[{category_label}] API 호출 실패: {response.status}"
                    )
                    if error_text:
                        logger.debug(f"[{category_label}] API 실패 응답: {error_text[:200]}")
                    return None

            except Exception as e:
                logger.error(f"[{category_label}] API 호출 중 예외 발생 ({url}): {e}")
                if self.active_api_base_url == base_url:
                    self.active_api_base_url = None
                continue

        # 서비스 상태에 따른 적절한 에러 메시지 출력
        if service_unavailable_count == len(self.api_base_url_candidates):
            logger.error(f"[{category_label}] G2B API 서비스가 현재 이용 불가능합니다 (503 Service Unavailable)")
            logger.error(f"[{category_label}] 해결 방법: 1) 나중에 다시 시도, 2) data.go.kr 서비스 상태 확인, 3) API 키 유효성 검증")
        elif last_status == 404:
            logger.error(f"[{category_label}] 모든 G2B 엔드포인트에서 404 응답")
            logger.error(f"[{category_label}] G2B API 구조가 변경되었을 가능성이 있습니다. 최신 API 문서를 확인하세요.")

        return None

    async def _search_bid_public_info(
        self,
        operation: str,
        category: str,
        keywords: List[str],
        display_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """BidPublicInfoService API 검색"""
        results: List[Dict[str, Any]] = []

        try:
            category_label = display_name or category
            if not self.encoded_api_key:
                logger.warning("유효한 G2B API 키가 없어 BidPublicInfoService 호출을 건너뜁니다.")
                return results

            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # 30일로 단축하여 API 제한 회피

            base_params = {
                "ServiceKey": self.encoded_api_key,
                "type": "json",
                "numOfRows": self.api_rows_per_page,
                "inqryDiv": "1",  # 등록일시 기준
                "inqryBgnDt": start_date.strftime("%Y%m%d0000"),  # 시간을 0000으로 고정
                "inqryEndDt": end_date.strftime("%Y%m%d2359"),    # 시간을 2359로 고정
            }
            search_params = self._build_search_query_params(category, keywords, start_date, end_date)

            timeout = self.api_request_timeout

            async with aiohttp.ClientSession(timeout=timeout) as session:
                page_no = 1
                total_count: Optional[int] = None

                while True:
                    request_params = {**base_params, **search_params, "pageNo": page_no}
                    json_data: Optional[Dict[str, Any]] = None
                    should_break = False

                    data = await self._request_bid_public_info(
                        session, operation, request_params, category_label
                    )

                    if data is None:
                        should_break = True
                    else:
                        if not data.strip():
                            logger.warning(
                                f"[{category_label}] API에서 빈 응답 수신 (page {page_no})"
                            )
                            should_break = True
                        else:
                            try:
                                json_data = json.loads(data)
                            except json.JSONDecodeError:
                                logger.error(
                                    f"[{category_label}] API 응답을 JSON으로 파싱하지 못했습니다. 응답 내용: {data[:200]}"
                                )
                                should_break = True

                    if should_break:
                        break

                    if json_data is None:
                        break

                    page_results = await self._parse_api_response(
                        json_data, category, keywords, display_name=display_name
                    )
                    if page_results:
                        results.extend(page_results)

                    if total_count is None:
                        total_count = self._extract_total_count(json_data)

                    if not page_results:
                        logger.info(f"[{category_label}] 더 이상 결과가 없어 페이지 순회를 종료합니다.")
                        break

                    if total_count is not None and page_no * self.api_rows_per_page >= total_count:
                        break

                    page_no += 1
                    await asyncio.sleep(1 / self.api_rate_limit_tps)

        except Exception as e:
            logger.error(f"카테고리 '{category}' API 검색 중 오류: {e}")

        return results

    def _build_search_query_params(
        self,
        category: str,
        keywords: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """나라장터 검색조건을 PPS 전용 검색 파라미터로 매핑 (키워드 검색 강화)"""

        params: Dict[str, Any] = {
            "searchDtType": "1",  # 1: 등록일시 기준 검색
            "searchBgnDt": start_date.strftime("%Y%m%d"),
            "searchEndDt": end_date.strftime("%Y%m%d"),
        }

        # 키워드 정리 및 검증
        sanitized_keywords: List[str] = []
        seen = set()
        for keyword in keywords:
            if not keyword:
                continue
            cleaned = keyword.strip()
            if not cleaned or cleaned in seen:
                continue
            sanitized_keywords.append(cleaned)
            seen.add(cleaned)

        if sanitized_keywords:
            # G2B API는 OR 문법을 지원하지 않으므로 첫 번째 키워드만 대표 검색어로 사용
            main_keyword = sanitized_keywords[0]

            params.update({
                "searchType": "1",  # 1: 공고명 검색
                "searchWrd": main_keyword,
                "bidNtceNm": main_keyword,
                # 추가 검색 옵션
                "searchCndtnType": "1",  # 검색 조건 타입
                "kwdSearch": "Y",  # 키워드 검색 활성화
            })

            # 개별 키워드로도 검색 (더 넓은 범위)
            for i, keyword in enumerate(sanitized_keywords[:3]):  # 최대 3개 키워드
                if i == 0:
                    params[f"bidNtceNm01"] = keyword
                elif i == 1:
                    params[f"bidNtceNm02"] = keyword
                elif i == 2:
                    params[f"bidNtceNm03"] = keyword

            logger.info(f"🔍 G2B 대표 검색어: {main_keyword}")
            if len(sanitized_keywords) > 1:
                logger.info(f"📋 추가 키워드는 개별 파라미터로 전달: {sanitized_keywords[1:]}")
            logger.info(f"📋 전체 검색 키워드: {sanitized_keywords}")
        else:
            # 키워드가 없으면 전체 검색
            params.update({
                "searchType": "0",  # 0: 전체 검색
                "kwdSearch": "N"
            })
            logger.info("📥 G2B 전체 검색 (키워드 미지정)")

        return params

    async def _search_standard_api(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """공공데이터개방표준서비스 API 검색 (키워드 기반)"""
        results: List[Dict[str, Any]] = []

        try:
            if not self.encoded_api_key:
                logger.warning("유효한 G2B API 키가 없어 표준 API 호출을 건너뜁니다.")
                return results

            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # 30일로 단축하여 API 제한 회피

            # 기본 매개변수
            base_params = {
                "ServiceKey": self.encoded_api_key,
                "type": "json",
                "numOfRows": self.api_rows_per_page,
                "pageNo": 1,
                "bidNtceBgnDt": start_date.strftime("%Y%m%d0000"),
                "bidNtceEndDt": end_date.strftime("%Y%m%d2359"),
            }

            # 키워드 검색 매개변수 추가
            if keywords:
                # 키워드 정리
                sanitized_keywords = [kw.strip() for kw in keywords if kw.strip()]

                if sanitized_keywords:
                    # 첫 번째 키워드를 메인 검색어로 사용
                    main_keyword = sanitized_keywords[0]
                    base_params.update({
                        "bidNtceNm": main_keyword,  # 공고명 검색
                        "searchWrd": main_keyword,   # 검색어
                    })
                    logger.info(f"🔍 표준 API 키워드 검색: {main_keyword}")
                else:
                    logger.info("📋 표준 API 전체 검색 (유효한 키워드 없음)")
            else:
                logger.info("📋 표준 API 전체 검색 (키워드 미제공)")

            params = base_params

            logger.info(f"🔍 표준 API 검색 - 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

            async with aiohttp.ClientSession(timeout=self.api_request_timeout) as session:
                url = f"{self.standard_api_base_url}/{self.standard_operation}"

                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"표준 API 호출 실패: {response.status}")
                        return results

                    data = await response.text()
                    logger.info(f"표준 API 응답 내용 (처음 300자): {data[:300]}")

                    if not data.strip():
                        logger.warning("표준 API에서 빈 응답 수신")
                        return results

                    if data.strip().startswith('<OpenAPI_ServiceResponse>'):
                        logger.error("G2B 표준 API 인증 오류 - XML 오류 응답 수신")
                        if 'SERVICE_ACCESS_DENIED_ERROR' in data and self.api_key:
                            masked_key = self._mask_api_key(self.api_key)
                            logger.error("🚫 G2B API 키 인증 실패 (오류코드: 20)")
                            logger.error("📋 해결 방법:")
                            logger.error("   1. data.go.kr 공공데이터포털 접속")
                            logger.error("   2. '나라장터 공공데이터개방표준서비스' 검색 및 활용신청")
                            logger.error("   3. 승인된 API 키를 .env 파일의 G2B_API_KEY에 설정")
                            logger.error(f"   4. 현재 설정된 키: {masked_key}")
                        logger.error(f"📄 전체 오류 응답: {data}")
                        return results

                    try:
                        json_data = json.loads(data)
                        logger.info(
                            "표준 API JSON 파싱 성공. 응답 구조: "
                            f"{list(json_data.keys()) if isinstance(json_data, dict) else type(json_data)}"
                        )
                    except json.JSONDecodeError as e:
                        logger.error(f"표준 API JSON 파싱 오류: {e}")
                        logger.error(f"응답 내용: {data}")
                        return results

                    results = await self._parse_standard_api_response(json_data, keywords)

        except Exception as e:
            logger.error(f"표준 API 검색 중 오류: {e}")

        return results

    async def _parse_api_response(
        self,
        json_data: Dict[str, Any],
        category: str,
        keywords: List[str],
        display_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """BidPublicInfoService API 응답 데이터 파싱"""
        results: List[Dict[str, Any]] = []
        category_label = display_name or category

        try:
            if 'response' not in json_data:
                logger.warning("API 응답에 'response' 키가 없습니다")
                # ResponseError 키가 있는지 확인
                if 'nkoneps.com.response.ResponseError' in json_data:
                    error_info = json_data['nkoneps.com.response.ResponseError']
                    error_header = error_info.get('header', {})
                    error_code = error_header.get('resultCode', '')
                    error_msg = error_header.get('resultMsg', '')
                    logger.error(f"G2B API 오류 발생 - 코드: {error_code}, 메시지: {error_msg}")

                    if error_code == '07':
                        logger.error("입력범위값 초과 에러 - API 요청 파라미터를 확인하세요")
                        logger.error("해결 방법: 1) 검색 기간 단축, 2) 페이지 크기 감소, 3) 파라미터 값 검증")
                return results

            response = json_data['response']
            header = response.get('header', {})
            result_code = header.get('resultCode') or header.get('resultcode')
            if result_code != '00':
                logger.warning(f"API 오류: {header.get('resultMsg', 'Unknown error')} (코드: {result_code})")
                return results

            body = response.get('body', {})
            items = body.get('items', [])

            if not items:
                logger.info(f"카테고리 '{category_label}'에서 검색 결과 없음")
                return results

            # 실제 반환된 데이터 확인을 위한 로그
            logger.info(f"📋 {category_label} - API에서 {len(items)}건의 입찰 데이터 반환")
            if len(items) > 0:
                first_item = items[0]
                logger.info(f"📄 첫 번째 아이템 샘플: {first_item.get('bidNtceNm', first_item.get('ntceNm', '제목없음'))}")

            items = self._normalize_items(items)

            for item in items:
                try:
                    title = self._get_first_non_empty(item, ['bidNtceNm', 'ntceNm', 'bidNm'])
                    organization = self._get_first_non_empty(item, ['ntceInsttNm', 'dminsttNm', 'insttNm'])

                    # 키워드 관련성 확인
                    if not self._is_keyword_relevant(title, organization, keywords):
                        continue

                    deadline_date = self._get_first_non_empty(item, ['bidClseDt', 'bidClseDt1', 'bidClseDt2'])
                    estimated_price_raw = self._get_first_non_empty(
                        item, ['presmptPrce', 'asignBdgtAmt', 'bdgtAmt', 'refAmt']
                    )

                    logger.info(f"📝 [{category_label}] {title[:80]}")
                    logger.info(f"    🏢 발주기관: {organization}")
                    logger.info(f"    💰 추정가격: {self._format_price(estimated_price_raw)}")
                    logger.info(f"    📅 마감일: {deadline_date}")

                    relevance_score = self.calculate_relevance_score(title, organization)
                    urgency_level = self.determine_urgency_level(deadline_date)

                    bid_number = item.get('bidNtceNo', '')
                    bid_notice_order = item.get('bidNtceOrd', '')
                    announcement_date_raw = self._get_first_non_empty(
                        item, ['bidNtceDt', 'rgstDt', 'ntceDt']
                    )
                    estimated_price_raw = self._get_first_non_empty(
                        item, ['presmptPrce', 'asignBdgtAmt', 'bdgtAmt', 'refAmt']
                    )
                    budget_amount_raw = self._get_first_non_empty(
                        item, ['asignBdgtAmt', 'bdgtAmt', 'presmptPrce']
                    )

                    detail_url = self._get_first_non_empty(item, ['bidNtceDtlUrl', 'bidNtceUrl']) or self._generate_detail_url(
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
                        "source_site": "G2B",
                        "country": "KR",
                        "keywords": self._extract_keywords(title, organization),
                        "relevance_score": relevance_score,
                        "urgency_level": urgency_level,
                        "status": "active",
                        "extra_data": {
                            "crawled_at": datetime.now().isoformat(),
                            "category": category,
                            "category_label": category_label,
                            "bid_method": item.get('bidMethdNm', ''),
                            "contract_method": self._get_first_non_empty(
                                item, ['cntrctCnclsMthdNm', 'cntrctMthdNm']
                            ),
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
                        }
                    }

                    results.append(bid_info)

                except Exception as e:
                    logger.warning(f"[{category_label}] 개별 아이템 파싱 중 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"[{category_label}] API 응답 파싱 중 오류: {e}")

        if results:
            logger.info(f"✅ [{category_label}] 수집 완료: {len(results)}건")
        else:
            logger.info(f"❌ [{category_label}] 수집 결과 없음")

        return results

    async def _parse_standard_api_response(self, json_data: Dict[str, Any], keywords: List[str]) -> List[Dict[str, Any]]:
        """공공데이터개방표준서비스 API 응답 데이터 파싱"""
        results: List[Dict[str, Any]] = []

        try:
            if 'response' not in json_data:
                logger.warning("표준 API 응답에 'response' 키가 없습니다")
                # ResponseError 키가 있는지 확인
                if 'nkoneps.com.response.ResponseError' in json_data:
                    error_info = json_data['nkoneps.com.response.ResponseError']
                    error_header = error_info.get('header', {})
                    error_code = error_header.get('resultCode', '')
                    error_msg = error_header.get('resultMsg', '')
                    logger.error(f"표준 API 오류 발생 - 코드: {error_code}, 메시지: {error_msg}")

                    if error_code == '07':
                        logger.error("입력범위값 초과 에러 - API 요청 파라미터를 확인하세요")
                        logger.error("해결 방법: 1) 검색 기간 단축, 2) 페이지 크기 감소, 3) 파라미터 값 검증")
                return results

            response = json_data['response']
            header = response.get('header', {})
            result_code = header.get('resultCode') or header.get('resultcode')
            if result_code != '00':
                logger.warning(f"표준 API 오류: {header.get('resultMsg', 'Unknown error')} (코드: {result_code})")
                return results

            body = response.get('body', {})
            items = body.get('items', [])
            total_count = body.get('totalCount', 0)

            logger.info(f"📊 표준 API 전체 결과 수: {total_count}건")
            logger.info(f"🔍 items 타입: {type(items)}, 길이: {len(items) if isinstance(items, list) else 'N/A'}")

            # 응답 구조 디버깅
            if items and isinstance(items, list) and len(items) > 0:
                logger.info(f"📄 첫 번째 아이템 샘플 키들: {list(items[0].keys())}")
                logger.info(f"📄 첫 번째 아이템 전체: {items[0]}")

            if not items:
                logger.info("표준 API 검색 결과 없음")
                return results

            items = self._normalize_items(items)

            for idx, item in enumerate(items):
                try:
                    title = item.get('ntceNm', '')
                    organization = item.get('ntceInsttNm', '')

                    # logger.info(f"📋 표준 API 입찰제목: {title}")  # 중복 로그 제거

                    # 키워드 관련성 확인
                    if not self._is_keyword_relevant(title, organization, keywords):
                        continue

                    deadline_date = item.get('bidClseDate', '')
                    estimated_price = item.get('presmptPrce', '')

                    logger.info(f"📝 [{idx+1}] {title[:80]}")
                    logger.info(f"    🏢 발주기관: {organization}")
                    logger.info(f"    💰 추정가격: {self._format_price(estimated_price)}")
                    logger.info(f"    📅 마감일: {deadline_date}")

                    relevance_score = self.calculate_relevance_score(title, organization)
                    urgency_level = self.determine_urgency_level(deadline_date)

                    bid_number = item.get('bidNtceNo', '')
                    bid_notice_order = item.get('bidNtceOrd', '')

                    bid_info = {
                        "title": title,
                        "organization": organization,
                        "bid_number": bid_number,
                        "announcement_date": self._format_date(item.get('nticeDt', '')),
                        "deadline_date": self._format_date(deadline_date),
                        "estimated_price": self._format_price(item.get('presmptPrce', '')),
                        "currency": "KRW",
                        "source_url": item.get('bidNtceUrl', ''),
                        "source_site": "G2B",
                        "country": "KR",
                        "keywords": self._extract_keywords(title, organization),
                        "relevance_score": relevance_score,
                        "urgency_level": urgency_level,
                        "status": "active",
                        "extra_data": {
                            "crawled_at": datetime.now().isoformat(),
                            "bid_notice_order": bid_notice_order,
                            "business_division": item.get('bsnsDivNm', ''),
                            "contract_method": item.get('cntrctCnclsMthdNm', ''),
                            "contract_type": item.get('cntrctCnclsSttusNm', ''),
                            "decision_method": item.get('bidwinrDcsnMthdNm', ''),
                            "opening_date": self._format_date(item.get('opengDate', '')),
                            "opening_time": item.get('opengTm', ''),
                            "opening_place": item.get('opengPlce', ''),
                            "budget_amount": self._format_price(item.get('asignBdgtAmt', '')),
                            "international_bid": item.get('intrntnlBidYn', ''),
                            "electronic_bid": item.get('elctrnBidYn', ''),
                            "demand_institution": item.get('dmndInsttNm', ''),
                            "notice_status": item.get('bidNtceSttusNm', ''),
                            "region_limit": item.get('rgnLmtYn', ''),
                            "industry_limit": item.get('indstrytyLmtYn', ''),
                            "api_data": True,
                            "api_service": "OpenDataStandard"
                        }
                    }

                    results.append(bid_info)

                except Exception as e:
                    logger.warning(f"표준 API 개별 아이템 파싱 중 오류: {e}")
                    continue

        except Exception as e:
            logger.error(f"표준 API 응답 파싱 중 오류: {e}")

        if results:
            logger.info(f"✅ [표준 API] 수집 완료: {len(results)}건")
        else:
            logger.info(f"❌ [표준 API] 수집 결과 없음")

        return results

    def _extract_total_count(self, json_data: Dict[str, Any]) -> Optional[int]:
        """응답에서 totalCount 값을 안전하게 추출"""
        try:
            body = json_data.get("response", {}).get("body", {})
            total = body.get("totalCount")
            if total is None or total == "":
                return None
            return int(total)
        except (ValueError, TypeError, AttributeError):
            return None

    def _matches_keywords(self, title: str, organization: str, keywords: List[str]) -> bool:
        """키워드 매칭 확인"""
        from src.config import crawler_config

        text = f"{title} {organization}".lower()

        all_keywords: List[str] = []
        all_keywords.extend(crawler_config.SEEGENE_KEYWORDS['korean'])
        all_keywords.extend(crawler_config.SEEGENE_KEYWORDS['english'])

        for keyword in all_keywords:
            if keyword.lower() in text:
                return True

        for keyword in keywords:
            if keyword.lower() in text:
                return True

        return False

    async def _check_api_service_availability(self) -> bool:
        """G2B API 서비스 가용성 체크"""
        try:
            import aiohttp

            # 기본 API 서비스 상태 확인
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                for base_url in self.api_base_url_candidates[:2]:  # 처음 2개만 체크
                    try:
                        # 간단한 헬스체크를 위해 기본 URL만 요청
                        async with session.get(base_url) as response:
                            if response.status in [200, 404]:  # 404도 서비스가 살아있다는 의미
                                logger.info(f"G2B API 서비스 가용성 확인: {base_url} (상태: {response.status})")
                                return True
                            elif response.status == 503:
                                logger.warning(f"G2B API 서비스 불가: {base_url} (503 Service Unavailable)")
                                continue
                    except Exception as e:
                        logger.debug(f"G2B API 가용성 체크 실패: {base_url} - {e}")
                        continue

            logger.warning("모든 G2B API 엔드포인트가 응답하지 않습니다")
            return False

        except Exception as e:
            logger.error(f"G2B API 서비스 가용성 체크 중 오류: {e}")
            return False

    def _extract_keywords(self, title: str, organization: str = "") -> List[str]:
        """제목과 기관명에서 키워드 추출"""
        keywords: List[str] = []
        text_lower = f"{title} {organization}".lower()

        from src.config import crawler_config
        for keyword in crawler_config.SEEGENE_KEYWORDS['korean']:
            if keyword.lower() in text_lower:
                keywords.append(keyword)
        for keyword in crawler_config.SEEGENE_KEYWORDS['english']:
            if keyword.lower() in text_lower:
                keywords.append(keyword)

        return list(set(keywords))

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
        unique_results: List[Dict[str, Any]] = []

        for result in results:
            bid_number = result.get('bid_number', '')
            bid_notice_order = ''
            extra_data = result.get('extra_data')
            if isinstance(extra_data, dict):
                bid_notice_order = extra_data.get('bid_notice_order', '')
            bid_key = (bid_number, bid_notice_order)

            if bid_number and bid_key not in seen_bid_keys:
                seen_bid_keys.add(bid_key)
                unique_results.append(result)
            elif not bid_number:
                source_url = result.get('source_url', '')
                if source_url not in [r.get('source_url', '') for r in unique_results]:
                    unique_results.append(result)

        return unique_results

    def parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """G2B API 마감일 파싱"""
        try:
            if not deadline_str or deadline_str.strip() == "":
                return None

            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
                try:
                    return datetime.strptime(deadline_str.strip(), fmt)
                except ValueError:
                    continue

            return None

        except Exception:
            return None


    def _prepare_service_key(self, api_key: Optional[str]) -> Optional[str]:
        """요청에 사용할 서비스 키를 전처리"""
        if not api_key:
            return None

        key = api_key.strip()
        if not key:
            return None

        # 이미 인코딩된 경우(%)는 그대로 사용
        if "%" in key:
            return key

        try:
            return quote(key, safe="")
        except Exception:
            return key

    def _mask_api_key(self, api_key: str) -> str:
        """API 키 마스킹"""
        if len(api_key) <= 8:
            return api_key
        return f"{api_key[:4]}...{api_key[-4:]}"

    def _is_keyword_relevant(self, title: str, organization: str, keywords: List[str]) -> bool:
        """키워드와 관련성이 있는지 확인"""
        if not keywords:
            return True  # 키워드가 없으면 모든 결과 포함

        text = f"{title} {organization}".lower()

        # 제공된 키워드 중 하나라도 포함되어 있으면 관련성 있음
        for keyword in keywords:
            if keyword.lower() in text:
                return True

        # Seegene 관련 키워드도 추가로 확인 (더 넓은 범위)
        from src.config import crawler_config
        all_seegene_keywords = []
        all_seegene_keywords.extend(crawler_config.SEEGENE_KEYWORDS['korean'])
        all_seegene_keywords.extend(crawler_config.SEEGENE_KEYWORDS['english'])

        for seegene_keyword in all_seegene_keywords:
            if seegene_keyword.lower() in text:
                return True

        return False
