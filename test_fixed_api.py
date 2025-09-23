#!/usr/bin/env python3
"""수정된 API 테스트"""

import requests
import json

def test_fixed_api():
    """수정된 G2B API 테스트"""
    print("="*60)
    print("Testing Fixed G2B API")
    print("="*60)

    api_url = "http://localhost:8000/crawl/G2B"

    # 1. 빈 요청 테스트 (기본 키워드 사용해야 함)
    print("\n1. Testing with empty request (should use default keywords)")
    try:
        response = requests.post(api_url, json={}, timeout=60)
        if response.status_code == 200:
            result = response.json()
            total_found = result.get('result', {}).get('total_found', 0)
            print(f"   ✅ Empty Request Result: {total_found} items")
            if total_found > 0:
                print(f"   SUCCESS: API now uses default keywords correctly!")
            else:
                print(f"   ISSUE: Still getting 0 results")
        else:
            print(f"   ❌ Error: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Server not running on port 8000")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 2. None 요청 테스트
    print("\n2. Testing with None request")
    try:
        response = requests.post(api_url, json=None, timeout=60)
        if response.status_code == 200:
            result = response.json()
            total_found = result.get('result', {}).get('total_found', 0)
            print(f"   ✅ None Request Result: {total_found} items")
        else:
            print(f"   ❌ Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 3. 'string' 키워드 테스트 (이제 필터링되어야 함)
    print("\n3. Testing with 'string' keyword (should be filtered out)")
    try:
        payload = {"keywords": ["string"]}
        response = requests.post(api_url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            total_found = result.get('result', {}).get('total_found', 0)
            print(f"   ✅ 'string' Keyword Result: {total_found} items")
            if total_found > 0:
                print(f"   SUCCESS: 'string' keyword filtered out, default keywords used!")
            else:
                print(f"   ISSUE: Still getting 0 results even after filtering")
        else:
            print(f"   ❌ Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # 4. 유효한 키워드 테스트
    print("\n4. Testing with valid keywords")
    try:
        payload = {"keywords": ["PCR"]}
        response = requests.post(api_url, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            total_found = result.get('result', {}).get('total_found', 0)
            print(f"   ✅ Valid Keyword Result: {total_found} items")
        else:
            print(f"   ❌ Error: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n" + "="*60)
    print("Fix Summary:")
    print("1. Added 'string' keyword filtering in CrawlerRequest model")
    print("2. Added safe keyword extraction in API endpoint")
    print("3. Added detailed logging for debugging")
    print("4. Now API should use default Seegene keywords when invalid keywords are detected")

if __name__ == "__main__":
    test_fixed_api()