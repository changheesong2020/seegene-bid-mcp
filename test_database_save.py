#!/usr/bin/env python3
"""데이터베이스 저장 테스트"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.manager import CrawlerManager
from src.database.connection import DatabaseManager

async def test_database_save():
    """크롤링 데이터 데이터베이스 저장 테스트"""
    print("="*60)
    print("Database Save Test")
    print("="*60)

    try:
        # 데이터베이스 상태 확인
        print("\n1. Database Status Check")
        try:
            stats = await DatabaseManager.get_database_stats()
            print(f"   Database connected successfully")
            print(f"   Total records: {stats.get('total_bids', 'N/A')}")
        except Exception as e:
            print(f"   Database connection failed: {e}")
            return

        # 크롤러 매니저 인스턴스 생성
        manager = CrawlerManager()

        # G2B 크롤러 테스트 (적은 키워드로)
        print("\n2. Testing G2B Crawler with Database Save")
        g2b_result = await manager.run_crawler("G2B", ["PCR"])  # 단일 키워드로 빠르게 테스트

        print(f"   G2B Results:")
        print(f"   - Success: {g2b_result.get('success', False)}")
        print(f"   - Total Found: {g2b_result.get('total_found', 0)}")
        print(f"   - Site: {g2b_result.get('site', 'Unknown')}")

        # 데이터베이스에 저장되었는지 확인
        print("\n3. Checking Database After G2B Crawling")
        try:
            new_stats = await DatabaseManager.get_database_stats()
            print(f"   Total records after G2B: {new_stats.get('total_bids', 'N/A')}")

            # G2B 데이터 확인
            if 'site_breakdown' in new_stats:
                g2b_count = new_stats['site_breakdown'].get('G2B', 0)
                print(f"   G2B records in database: {g2b_count}")
        except Exception as e:
            print(f"   Database check failed: {e}")

        # FR 크롤러도 간단히 테스트 (시간이 오래 걸릴 수 있음)
        print("\n4. Testing FR_BOAMP Crawler with Database Save")
        print("   (This may take longer...)")

        try:
            fr_result = await asyncio.wait_for(
                manager.run_crawler("FR_BOAMP", ["medical"]),
                timeout=60  # 60초 타임아웃
            )

            print(f"   FR Results:")
            print(f"   - Success: {fr_result.get('success', False)}")
            print(f"   - Total Found: {fr_result.get('total_found', 0)}")
            print(f"   - Site: {fr_result.get('site', 'Unknown')}")

        except asyncio.TimeoutError:
            print("   FR crawler timeout (60s) - this is normal")
        except Exception as e:
            print(f"   FR crawler error: {e}")

        # 최종 데이터베이스 상태 확인
        print("\n5. Final Database Status")
        try:
            final_stats = await DatabaseManager.get_database_stats()
            print(f"   Final total records: {final_stats.get('total_bids', 'N/A')}")

            if 'site_breakdown' in final_stats:
                for site, count in final_stats['site_breakdown'].items():
                    print(f"   {site}: {count} records")

        except Exception as e:
            print(f"   Final database check failed: {e}")

    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("Database Save Test Complete")
    print("Check if crawled data is now being saved to database!")

if __name__ == "__main__":
    asyncio.run(test_database_save())