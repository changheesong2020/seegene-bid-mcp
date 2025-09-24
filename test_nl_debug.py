#!/usr/bin/env python3
"""NL 저장 로직 디버깅"""

import asyncio
import sys
import os
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.nl_tenderned_crawler import NetherlandsTenderNedCrawler
from src.database.connection import DatabaseManager, init_database

async def debug_nl_save():
    """NL 크롤러 저장 로직 디버깅"""
    print("="*60)
    print("NL Crawler Save Logic Debug")
    print("="*60)

    try:
        # 데이터베이스 초기화
        print("\n0. Database Initialization")
        await init_database()
        print("   Database initialized successfully")

        # NL 크롤러 인스턴스 생성
        crawler = NetherlandsTenderNedCrawler()

        # 작은 범위로 테스트 (단일 키워드)
        print("\n1. Testing NL Crawler with Single Keyword")
        test_keywords = ["medisch"]  # 네덜란드어 의료 키워드

        print(f"   Testing with keywords: {test_keywords}")

        # 크롤링 실행 (타임아웃 설정)
        try:
            result = await asyncio.wait_for(
                crawler.crawl(test_keywords),
                timeout=60  # 1분 타임아웃
            )

            print(f"\n2. Crawling Results Analysis")
            print(f"   Success: {result.get('success', False)}")
            print(f"   Total Collected: {result.get('total_collected', 0)}")
            print(f"   Source: {result.get('source', 'Unknown')}")

            # 실제 결과 데이터 확인
            results = result.get('results', [])
            print(f"   Results Length: {len(results)}")

            if results:
                print(f"\n3. Sample Data Analysis")
                sample = results[0]
                print(f"   Sample data keys: {list(sample.keys())}")
                print(f"   Sample title: {sample.get('title', 'No title')[:50]}...")
                print(f"   Sample organization: {sample.get('organization', 'No org')}")
                print(f"   Sample source_site: {sample.get('source_site', 'No site')}")
                print(f"   Sample country: {sample.get('country', 'No country')}")

                # 필수 필드 검증
                required_fields = ['title', 'organization', 'source_site', 'country']
                missing_fields = []
                for field in required_fields:
                    if not sample.get(field):
                        missing_fields.append(field)

                if missing_fields:
                    print(f"   WARNING: Missing required fields: {missing_fields}")
                else:
                    print(f"   SUCCESS: All required fields present")

                # 전체 데이터를 JSON으로 출력 (처음 2개만)
                print(f"\n4. Sample Data Structure")
                for i, item in enumerate(results[:2], 1):
                    print(f"   Sample {i}:")
                    print(f"   {json.dumps(item, indent=4, ensure_ascii=False)[:500]}...")
            else:
                print(f"   ERROR: No results collected")

        except asyncio.TimeoutError:
            print(f"   TIMEOUT: Crawling timeout (1 minute)")
        except Exception as e:
            print(f"   ERROR: Crawling failed: {e}")
            import traceback
            traceback.print_exc()

        # 데이터베이스 저장 테스트
        print(f"\n5. Database Save Test")
        try:
            # 간단한 테스트 데이터 생성
            test_data = [{
                "title": "Test Medische Apparatuur Procurement",
                "organization": "Test Dutch Hospital",
                "bid_number": "NL-TEST-001",
                "announcement_date": "2025-01-01",
                "deadline_date": "2025-02-01",
                "estimated_price": "60000",
                "currency": "EUR",
                "source_url": "https://test.nl/test",
                "source_site": "NL_TENDERNED",
                "country": "NL",
                "relevance_score": 8.0,
                "urgency_level": "medium",
                "status": "active",
                "keywords": ["medisch"],
                "extra_data": {"test": True}
            }]

            print(f"   Testing database save with sample data...")
            await DatabaseManager.save_bid_info(test_data)
            print(f"   SUCCESS: Database save test successful")

        except Exception as e:
            print(f"   ERROR: Database save test failed: {e}")
            import traceback
            traceback.print_exc()

        # 데이터베이스 상태 확인
        print(f"\n6. Database Status Check")
        try:
            stats = await DatabaseManager.get_database_stats()
            print(f"   Total records: {stats.get('total_bids', 'N/A')}")

            if 'site_breakdown' in stats:
                nl_count = stats['site_breakdown'].get('NL_TENDERNED', 0)
                print(f"   NL_TENDERNED records: {nl_count}")
        except Exception as e:
            print(f"   Database status check failed: {e}")

    except Exception as e:
        print(f"ERROR: Debug test failed: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n" + "="*60)
    print("NL Debug Complete")

if __name__ == "__main__":
    asyncio.run(debug_nl_save())