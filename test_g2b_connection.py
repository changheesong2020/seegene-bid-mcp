#!/usr/bin/env python3
"""
G2B 서비스 연결 진단 도구
G2B API 연결 상태 및 서비스 가용성 확인
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
        self.standard_api_url = (
            "https://apis.data.go.kr/1230000/ao/PubDataOpnStdService/getDataSetOpnStdBidPblancInfo"
        )

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
        endpoints = []

        for base_url in self.api_base_urls:
            endpoints.append(
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
            )

        endpoints.append(
            {
                "name": "PublicDataStandardService",
                "url": self.standard_api_url,
                "params": {
                    "ServiceKey": self.g2b_api_key,
                    "pageNo": "1",
                    "numOfRows": "1",
                    "type": "json"
                }
            }
        )

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

                                    print(f"   API 응답 코드: {result_code}")
                                    print(f"   API 응답 메시지: {result_msg}")

                                    if result_code == "00":
                                        print(f"   ✅ {endpoint['name']} API 정상 작동")

                                        # 데이터 개수 확인
                                        body = data.get('response', {}).get('body', {})
                                        total_count = body.get('totalCount', 0)
                                        print(f"   📊 전체 데이터 수: {total_count:,}건")
                                    else:
                                        print(f"   ❌ {endpoint['name']} API 오류: {result_msg}")
                                else:
                                    print(f"   ❌ 예상되지 않은 응답 형식")
                                    print(f"   응답 내용: {str(data)[:200]}...")

                            except json.JSONDecodeError:
                                text = await response.text()
                                print(f"   ❌ JSON 파싱 실패")
                                print(f"   응답 내용: {text[:200]}...")
                        else:
                            text = await response.text()
                            print(f"   ❌ HTTP 오류: {response.status}")
                            print(f"   응답 내용: {text[:200]}...")

                except Exception as e:
                    print(f"   ❌ 연결 실패: {str(e)}")

        return True

    async def test_search_functionality(self):
        """실제 검색 기능 테스트"""
        print("\n" + "=" * 60)
        print("🔍 G2B 검색 기능 테스트")
        print("=" * 60)

        if not self.g2b_api_key:
            print("❌ API 키가 필요합니다")
            return

        # 검색 테스트 케이스
        search_keywords = ['의료', 'PCR']

        # 날짜 설정 (최근 30일)
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

        print(f"검색 키워드: {search_keywords}")
        print(f"검색 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for base_url in self.api_base_urls:
                url = f"{base_url}/getBidPblancListInfoServcPPSSrch"
                print(f"\n엔드포인트 시도: {url}")
                try:
                    async with session.get(url, params=search_params) as response:
                        print(f"상태 코드: {response.status}")

                        if response.status == 200:
                            data = await response.json()

                            if 'response' in data:
                                header = data['response'].get('header', {})
                                body = data['response'].get('body', {})

                                result_code = header.get('resultCode', 'Unknown')
                                result_msg = header.get('resultMsg', 'Unknown')

                                print(f"API 결과: {result_code} - {result_msg}")

                                if result_code == "00":
                                    total_count = body.get('totalCount', 0)
                                    items = body.get('items', [])

                                    print(f"✅ 검색 성공!")
                                    print(f"📊 총 검색 결과: {total_count:,}건")
                                    print(f"📋 현재 페이지 결과: {len(items)}건")

                                    if items:
                                        print(f"\n📄 첫 번째 결과 예시:")
                                        first_item = items[0]
                                        print(f"   공고명: {first_item.get('bidNtceNm', 'N/A')}")
                                        print(f"   공고기관: {first_item.get('ntceInsttNm', 'N/A')}")
                                        print(f"   공고일자: {first_item.get('bidNtceDt', 'N/A')}")
                                        print(f"   마감일자: {first_item.get('bidClseDt', 'N/A')}")
                                    break
                                else:
                                    print(f"❌ 검색 실패: {result_msg}")
                            else:
                                print(f"❌ 예상되지 않은 응답 형식")
                        else:
                            text = await response.text()
                            print(f"❌ HTTP 오류: {response.status}")
                            print(f"응답: {text[:300]}...")

                except Exception as e:
                    print(f"❌ 검색 테스트 실패: {str(e)}")
                    continue

    async def run_full_diagnostic(self):
        """전체 진단 실행"""
        print("🏥 Seegene G2B 연결 진단 도구")
        print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 1. 기본 연결 테스트
        await self.test_basic_connectivity()

        # 2. API 엔드포인트 테스트
        await self.test_api_endpoints()

        # 3. 검색 기능 테스트
        await self.test_search_functionality()

        print("\n" + "=" * 60)
        print("🎯 진단 완료")
        print("=" * 60)
        print("문제가 지속되면 다음을 확인하세요:")
        print("1. .env 파일의 G2B_API_KEY 설정")
        print("2. 공공데이터포털(data.go.kr) API 활용신청 승인 상태")
        print("3. API 일일 호출 한도 초과 여부")
        print("4. 방화벽 또는 네트워크 제한")


async def main():
    """메인 실행 함수"""
    tester = G2BConnectionTester()
    await tester.run_full_diagnostic()


if __name__ == "__main__":
    asyncio.run(main())