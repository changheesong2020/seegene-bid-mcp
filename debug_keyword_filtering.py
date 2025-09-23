#!/usr/bin/env python3
"""키워드 필터링 디버깅"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.g2b_crawler import G2BCrawler
from src.config import crawler_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def debug_keyword_filtering():
    """키워드 필터링 디버깅"""
    print("="*60)
    print("G2B Keyword Filtering Debug")
    print("="*60)

    crawler = G2BCrawler()

    # 로그인
    await crawler.login()

    # 단일 키워드로 테스트 - PCR
    print("\n1. Testing PCR keyword...")
    pcr_results = await crawler._search_bid_public_info(
        "getBidPblancListInfoThngPPSSrch",
        "thng",
        ["PCR"],
        display_name="물품"
    )

    print(f"PCR raw results: {len(pcr_results)}")

    # 키워드 관련성 체크 없이 모든 데이터 확인
    print("\n2. Testing with no keyword filtering...")
    no_filter_results = await crawler._search_bid_public_info_no_filter(
        "getBidPblancListInfoThngPPSSrch",
        "thng",
        ["PCR"],
        display_name="물품"
    )

    print(f"No filter results: {len(no_filter_results)}")

    # Seegene 키워드 테스트
    print(f"\n3. Seegene Keywords: {crawler_config.SEEGENE_KEYWORDS['korean']}")

    # 키워드 매칭 테스트
    test_titles = [
        "[바이오헬스] PCR 시스템 및 Electroporator 구매",
        "2025년 시험연구비 진단키트 구입요청(질병진단과)",
        "연구용 실시간 핵산 분석기(RT-PCR) 구매"
    ]

    for title in test_titles:
        is_relevant = crawler._is_keyword_relevant(title, "", ["PCR"])
        seegene_relevant = crawler._is_keyword_relevant(title, "", crawler_config.SEEGENE_KEYWORDS['korean'])
        print(f"Title: {title[:50]}...")
        print(f"  PCR relevant: {is_relevant}")
        print(f"  Seegene relevant: {seegene_relevant}")

# G2BCrawler에 임시 메서드 추가
async def _search_bid_public_info_no_filter(self, operation, category, keywords, display_name=None):
    """키워드 필터링 없이 API 검색"""
    from datetime import datetime, timedelta
    import aiohttp
    import json

    results = []

    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        base_params = {
            "ServiceKey": self.encoded_api_key,
            "type": "json",
            "numOfRows": self.api_rows_per_page,
            "inqryDiv": "1",
            "inqryBgnDt": start_date.strftime("%Y%m%d0000"),
            "inqryEndDt": end_date.strftime("%Y%m%d2359"),
        }
        search_params = self._build_search_query_params(category, keywords, start_date, end_date)

        url = f"{self.api_base_url}/{operation}"

        async with aiohttp.ClientSession(timeout=self.api_request_timeout) as session:
            request_params = {**base_params, **search_params, "pageNo": 1}

            async with session.get(url, params=request_params) as response:
                if response.status == 200:
                    data = await response.text()
                    json_data = json.loads(data)

                    if 'response' in json_data:
                        response_data = json_data['response']
                        header = response_data.get('header', {})
                        result_code = header.get('resultCode')

                        if result_code == '00':
                            body = response_data.get('body', {})
                            items = body.get('items', [])

                            # 키워드 필터링 없이 모든 아이템 반환
                            items = self._normalize_items(items)

                            for item in items:
                                title = self._get_first_non_empty(item, ['bidNtceNm', 'ntceNm', 'bidNm'])
                                organization = self._get_first_non_empty(item, ['ntceInsttNm', 'dminsttNm', 'insttNm'])

                                print(f"Raw item: {title[:50]}... | Org: {organization[:30]}...")

                                # 기본 정보만 포함한 결과 생성
                                bid_info = {
                                    "title": title,
                                    "organization": organization,
                                    "filtered": False
                                }
                                results.append(bid_info)

    except Exception as e:
        print(f"Error in no-filter search: {e}")

    return results

# 임시 메서드를 클래스에 추가
G2BCrawler._search_bid_public_info_no_filter = _search_bid_public_info_no_filter

if __name__ == "__main__":
    asyncio.run(debug_keyword_filtering())