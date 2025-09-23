#!/usr/bin/env python3
import asyncio
import sys
import os
import aiohttp
import ssl
import json

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def create_ssl_context():
    """SSL 검증 우회를 위한 컨텍스트 생성"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context

async def debug_boamp_api():
    """BOAMP API 응답 구조 디버깅"""
    print("Debugging BOAMP API response structure...")

    api_base_url = "https://www.boamp.fr/api"
    records_api = f"{api_base_url}/records/1.0/search/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    connector = aiohttp.TCPConnector(ssl=create_ssl_context())
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        connector=connector,
        headers=headers,
    ) as session:

        try:
            # API 파라미터
            api_params = {
                "dataset": "boamp",
                "q": "diagnostic",
                "rows": 3,  # Just get 3 for debugging
                "start": 0,
                "format": "json"
            }

            print(f"API URL: {records_api}")
            print(f"Parameters: {api_params}")

            async with session.get(
                records_api,
                params=api_params,
                headers=headers,
            ) as response:
                print(f"Response status: {response.status}")
                print(f"Response headers: {dict(response.headers)}")

                if response.status == 200:
                    try:
                        data = await response.json()
                        print(f"JSON Response structure:")
                        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])  # First 2000 chars

                        if "records" in data and data["records"]:
                            print(f"\nFirst record fields:")
                            first_record = data["records"][0]
                            print(json.dumps(first_record, indent=2, ensure_ascii=False)[:1000])

                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        text_content = await response.text()
                        print(f"Raw response (first 500 chars): {text_content[:500]}")
                else:
                    text_content = await response.text()
                    print(f"Error response: {text_content[:500]}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_boamp_api())