#!/usr/bin/env python3
"""G2B 크롤러 직접 테스트"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.g2b_crawler import G2BCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def test_g2b_crawler():
    """G2B 크롤러 직접 테스트"""
    print("="*60)
    print("G2B Crawler Direct Test")
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

        # 키워드 검색 테스트
        print("\n2. Testing Keyword Search...")
        test_keywords = ["PCR", "medical"]
        print(f"   Search Keywords: {test_keywords}")

        results = await crawler.search_bids(test_keywords)

        print(f"\n3. Search Results:")
        print(f"   Total Results: {len(results)}")

        if results:
            print(f"\n   First 3 Results:")
            for i, result in enumerate(results[:3], 1):
                print(f"   [{i}] {result.get('title', 'No Title')[:80]}")
                print(f"       Organization: {result.get('organization', 'No Org')}")
                print(f"       Price: {result.get('estimated_price', 'No Price')}")
                print(f"       Deadline: {result.get('deadline_date', 'No Deadline')}")
                print()
        else:
            print("   No results found!")
            print("\n   Possible reasons:")
            print("   - API key not properly configured")
            print("   - No matching data in the search period")
            print("   - API service temporary issues")
            print("   - Incorrect API endpoint or parameters")

    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_g2b_crawler())