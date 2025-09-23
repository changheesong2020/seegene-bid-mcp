#!/usr/bin/env python3
"""최종 G2B 크롤러 테스트"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.manager import CrawlerManager

async def test_final_g2b():
    """최종 G2B 크롤러 테스트"""
    print("="*60)
    print("Final G2B Crawler Test")
    print("="*60)

    try:
        # 크롤러 매니저 인스턴스 생성
        manager = CrawlerManager()

        # G2B 크롤러 실행 (키워드 None으로 전달하여 기본 키워드 사용)
        print("\n1. Testing G2B with default keywords (None passed)...")
        result = await manager.run_crawler("G2B", None)

        print(f"\n2. Final Results:")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Total Found: {result.get('total_found', 0)}")
        print(f"   Site: {result.get('site', 'Unknown')}")

        if result.get('error'):
            print(f"   Error: {result['error']}")

        if result.get('total_found', 0) > 0:
            print(f"\n   ✅ SUCCESS: {result['total_found']} items collected!")
        else:
            print(f"\n   ❌ FAILED: 0 items collected")

    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_final_g2b())