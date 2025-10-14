#!/usr/bin/env python3
"""
G2B Service Connection Diagnostic Tool
Test G2B API connectivity and service availability
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

class G2BConnectionTester:
    def __init__(self):
        self.g2b_api_key = settings.G2B_API_KEY
        self.api_base_urls = [
            "https://apis.data.go.kr/1230000/ad/BidPublicInfoService02",
            "https://apis.data.go.kr/1230000/ad/BidPublicInfoService",
            "https://apis.data.go.kr/1230000/BidPublicInfoService02",
            "https://apis.data.go.kr/1230000/BidPublicInfoService",
        ]

    async def test_basic_connectivity(self):
        """Basic network connectivity test"""
        print("=" * 60)
        print("G2B Basic Connection Test")
        print("=" * 60)

        test_urls = [
            "http://apis.data.go.kr",
            "http://apis.data.go.kr/1230000",
            "https://www.g2b.go.kr",
            "https://www.data.go.kr"
        ]

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            for url in test_urls:
                try:
                    async with session.get(url) as response:
                        status = "OK Connected" if response.status < 400 else f"ERROR {response.status}"
                        print(f"{url:<40} | {status}")
                except Exception as e:
                    print(f"{url:<40} | FAILED: {str(e)[:30]}")

        print()

    async def test_api_endpoints(self):
        """G2B API endpoint test"""
        print("=" * 60)
        print("G2B API Endpoint Test")
        print("=" * 60)

        if not self.g2b_api_key:
            print("ERROR: G2B API key not configured")
            print("   Please set G2B_API_KEY in .env file")
            return False

        # API endpoints to test
        endpoints = [
            {
                "name": f"BidPublicInfoService ({base_url})",
                "url": f"{base_url}/getBidPblancListInfoServcPPSSrch",
                "params": {
                    "ServiceKey": self.g2b_api_key,
                    "pageNo": "1",
                    "numOfRows": "1",
                    "type": "json"
                }
            }
            for base_url in self.api_base_urls
        ]

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for endpoint in endpoints:
                try:
                    print(f"\n{endpoint['name']} Test")
                    print(f"   URL: {endpoint['url']}")

                    async with session.get(endpoint['url'], params=endpoint['params']) as response:
                        print(f"   Status Code: {response.status}")
                        print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")

                        if response.status == 200:
                            try:
                                data = await response.json()
                                if 'response' in data:
                                    header = data.get('response', {}).get('header', {})
                                    result_code = header.get('resultCode', 'Unknown')
                                    result_msg = header.get('resultMsg', 'Unknown')

                                    print(f"   API Response Code: {result_code}")
                                    print(f"   API Response Message: {result_msg}")

                                    if result_code == "00":
                                        print(f"   SUCCESS: {endpoint['name']} API working")

                                        # Check data count
                                        body = data.get('response', {}).get('body', {})
                                        total_count = body.get('totalCount', 0)
                                        print(f"   Total Data Count: {total_count:,}")
                                    else:
                                        print(f"   ERROR: {endpoint['name']} API error: {result_msg}")
                                else:
                                    print(f"   ERROR: Unexpected response format")

                            except json.JSONDecodeError:
                                text = await response.text()
                                print(f"   ERROR: JSON parsing failed")
                                print(f"   Response: {text[:200]}...")
                        else:
                            text = await response.text()
                            print(f"   ERROR: HTTP error: {response.status}")
                            print(f"   Response: {text[:200]}...")

                except Exception as e:
                    print(f"   ERROR: Connection failed: {str(e)}")

        return True

    async def test_search_functionality(self):
        """Test actual search functionality"""
        print("\n" + "=" * 60)
        print("G2B Search Functionality Test")
        print("=" * 60)

        if not self.g2b_api_key:
            print("ERROR: API key required")
            return

        # Search test case
        search_keywords = ['medical', 'PCR']

        # Date range (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        search_params = {
            "ServiceKey": self.g2b_api_key,
            "pageNo": "1",
            "numOfRows": "10",
            "type": "json",
            "bidNtceBgnDt": start_date.strftime("%Y%m%d"),
            "bidNtceEndDt": end_date.strftime("%Y%m%d"),
            "bidNtceNm": " OR ".join(search_keywords)
        }

        print(f"Search Keywords: {search_keywords}")
        print(f"Search Period: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for base_url in self.api_base_urls:
                url = f"{base_url}/getBidPblancListInfoServcPPSSrch"
                print(f"\nTrying endpoint: {url}")
                try:
                    async with session.get(url, params=search_params) as response:
                        print(f"Status Code: {response.status}")

                        if response.status == 200:
                            data = await response.json()

                            if 'response' in data:
                                header = data['response'].get('header', {})
                                body = data['response'].get('body', {})

                                result_code = header.get('resultCode', 'Unknown')
                                result_msg = header.get('resultMsg', 'Unknown')

                                print(f"API Result: {result_code} - {result_msg}")

                                if result_code == "00":
                                    total_count = body.get('totalCount', 0)
                                    items = body.get('items', [])

                                    print(f"SUCCESS: Search completed!")
                                    print(f"Total Search Results: {total_count:,}")
                                    print(f"Current Page Results: {len(items)}")

                                    if items:
                                        print(f"\nFirst Result Example:")
                                        first_item = items[0]
                                        print(f"   Title: {first_item.get('bidNtceNm', 'N/A')}")
                                        print(f"   Organization: {first_item.get('ntceInsttNm', 'N/A')}")
                                        print(f"   Notice Date: {first_item.get('bidNtceDt', 'N/A')}")
                                        print(f"   Deadline: {first_item.get('bidClseDt', 'N/A')}")
                                    break
                                else:
                                    print(f"ERROR: Search failed: {result_msg}")
                            else:
                                print(f"ERROR: Unexpected response format")
                        else:
                            text = await response.text()
                            print(f"ERROR: HTTP error: {response.status}")
                            print(f"Response: {text[:300]}...")

                except Exception as e:
                    print(f"ERROR: Search test failed: {str(e)}")
                    continue

    async def run_full_diagnostic(self):
        """Run full diagnostic"""
        print("Seegene G2B Connection Diagnostic Tool")
        print(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 1. Basic connectivity test
        await self.test_basic_connectivity()

        # 2. API endpoint test
        await self.test_api_endpoints()

        # 3. Search functionality test
        await self.test_search_functionality()

        print("\n" + "=" * 60)
        print("Diagnostic Completed")
        print("=" * 60)
        print("If problems persist, check:")
        print("1. G2B_API_KEY setting in .env file")
        print("2. API approval status on data.go.kr")
        print("3. Daily API call limit")
        print("4. Firewall or network restrictions")


async def main():
    """Main execution function"""
    tester = G2BConnectionTester()
    await tester.run_full_diagnostic()


if __name__ == "__main__":
    asyncio.run(main())