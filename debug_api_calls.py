#!/usr/bin/env python3
"""API 호출 0건 문제 디버깅"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.g2b_crawler import G2BCrawler
from src.config import crawler_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def debug_api_calls():
    """API 호출 문제 디버깅"""
    print("="*60)
    print("G2B API Call Debug - 0 Results Issue")
    print("="*60)

    crawler = G2BCrawler()

    # 로그인
    login_success = await crawler.login()
    print(f"Login success: {login_success}")

    if not login_success:
        print("Login failed - cannot proceed")
        return

    # 1. Seegene 키워드로 검색 (실제 사용되는 키워드)
    print("\n1. Testing with SEEGENE keywords...")
    seegene_keywords = [
        'PCR', 'COVID', 'RT-PCR'  # 영어만 사용
    ]
    print(f"Keywords: {seegene_keywords}")

    seegene_results = await crawler.search_bids(seegene_keywords)
    print(f"Seegene keywords result count: {len(seegene_results)}")

    # 2. 단일 키워드 테스트
    print("\n2. Testing individual keywords...")
    test_keywords = ['PCR', 'COVID', 'RT-PCR', 'medical', 'diagnostic']

    for keyword in test_keywords:
        try:
            results = await crawler.search_bids([keyword])
            print(f"Keyword '{keyword}': {len(results)} results")
        except Exception as e:
            print(f"Keyword '{keyword}': ERROR - {e}")

    # 3. 빈 키워드 테스트
    print("\n3. Testing with empty keywords...")
    try:
        empty_results = await crawler.search_bids([])
        print(f"Empty keywords result count: {len(empty_results)}")
    except Exception as e:
        print(f"Empty keywords: ERROR - {e}")

    # 4. None 키워드 테스트
    print("\n4. Testing with None keywords...")
    try:
        none_results = await crawler.search_bids(None)
        print(f"None keywords result count: {len(none_results)}")
    except Exception as e:
        print(f"None keywords: ERROR - {e}")

    # 5. 키워드 관련성 함수 직접 테스트
    print("\n5. Testing keyword relevance function...")
    test_titles = [
        "PCR System Purchase",
        "RT-PCR Equipment",
        "COVID-19 Test Kit",
        "Diagnostic Equipment",
        "Laboratory Supplies",
        "Office Furniture"  # 관련 없는 항목
    ]

    for title in test_titles:
        is_relevant_pcr = crawler._is_keyword_relevant(title, "", ["PCR"])
        is_relevant_covid = crawler._is_keyword_relevant(title, "", ["COVID"])
        is_relevant_seegene = crawler._is_keyword_relevant(title, "", seegene_keywords)

        print(f"Title: '{title}'")
        print(f"  PCR relevant: {is_relevant_pcr}")
        print(f"  COVID relevant: {is_relevant_covid}")
        print(f"  Seegene relevant: {is_relevant_seegene}")

if __name__ == "__main__":
    asyncio.run(debug_api_calls())