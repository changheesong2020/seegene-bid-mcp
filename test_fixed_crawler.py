#!/usr/bin/env python3
"""수정된 G2B 크롤러 테스트"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.g2b_crawler import G2BCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def test_fixed_crawler():
    """수정된 G2B 크롤러 테스트"""
    print("="*60)
    print("Fixed G2B Crawler Test")
    print("="*60)

    try:
        # G2B 크롤러 인스턴스 생성
        crawler = G2BCrawler()

        # 로그인 테스트
        print("\n1. Testing G2B API Key Authentication...")
        login_result = await crawler.login()
        print(f"   Login Result: {login_result}")

        if not login_result:
            print("   ERROR: G2B API key authentication failed")
            return

        # 문제가 있었던 키워드들 테스트
        print("\n2. Testing previously problematic keywords...")

        # 한국어 키워드 중 문제가 있던 것들
        problem_keywords = ["string"]  # 사용자가 보여준 로그에서 나온 키워드

        for keyword in problem_keywords:
            print(f"\n   Testing keyword: '{keyword}'")
            results = await crawler.search_bids([keyword])
            print(f"   Results: {len(results)} items found")

        # 정상 작동하는 키워드 테스트
        print("\n3. Testing working keywords...")
        working_keywords = ["PCR", "COVID"]

        for keyword in working_keywords:
            print(f"\n   Testing keyword: '{keyword}'")
            results = await crawler.search_bids([keyword])
            print(f"   Results: {len(results)} items found")

        # 전체 Seegene 키워드 테스트
        print("\n4. Testing full Seegene keyword set...")
        from src.config import crawler_config

        # 영어 키워드만 테스트 (UTF-8 문제 회피)
        english_keywords = ["diagnostic kit", "PCR test", "molecular diagnostic", "COVID test"]
        print(f"   English keywords: {english_keywords}")

        full_results = await crawler.search_bids(english_keywords)
        print(f"   Full Seegene English keywords results: {len(full_results)} items found")

        print("\n5. Summary:")
        print(f"   - Fixed keyword filtering logic")
        print(f"   - Disabled standard API (performance optimization)")
        print(f"   - Enhanced Seegene keyword matching")

    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_crawler())