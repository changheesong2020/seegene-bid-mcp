#!/usr/bin/env python3
"""크롤러 매니저 직접 테스트"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.manager import CrawlerManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

async def test_crawler_manager():
    """크롤러 매니저 테스트"""
    print("="*60)
    print("Crawler Manager Test")
    print("="*60)

    try:
        # 크롤러 매니저 인스턴스 생성
        manager = CrawlerManager()

        # G2B 크롤러 직접 실행
        print("\n1. Testing G2B Crawler via Manager...")
        result = await manager.run_crawler("G2B")

        print(f"\n2. G2B Crawler Results:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Total Found: {result.get('total_found', 0)}")
        print(f"   Site: {result.get('site', 'Unknown')}")

        if result.get('error'):
            print(f"   Error: {result['error']}")

        if result.get('results'):
            print(f"\n   First 3 Results:")
            for i, bid in enumerate(result['results'][:3], 1):
                # Only show basic info without Korean characters
                title = bid.get('title', 'No Title')[:50] + '...' if len(bid.get('title', '')) > 50 else bid.get('title', 'No Title')
                org = bid.get('organization', 'No Org')[:30] + '...' if len(bid.get('organization', '')) > 30 else bid.get('organization', 'No Org')
                price = bid.get('estimated_price', 'No Price')

                print(f"   [{i}] Title: {repr(title)}")
                print(f"       Organization: {repr(org)}")
                print(f"       Price: {price}")
                print()

        # 마지막 실행 결과 확인
        if "G2B" in manager.last_run_results:
            last_result = manager.last_run_results["G2B"]
            print(f"\n3. Last Run Results for G2B:")
            print(f"   Run Time: {last_result.get('run_time', 'Unknown')}")
            print(f"   Manual Run: {last_result.get('manual_run', False)}")
            print(f"   Total Found: {last_result.get('total_found', 0)}")

    except Exception as e:
        print(f"ERROR: Manager test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_crawler_manager())