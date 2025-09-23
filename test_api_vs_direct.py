#!/usr/bin/env python3
"""API vs 직접 호출 차이점 테스트"""

import asyncio
import sys
import os
import requests
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler.manager import CrawlerManager

async def test_api_vs_direct():
    """API 호출 vs 직접 호출 비교 테스트"""
    print("="*60)
    print("API vs Direct Call Comparison Test")
    print("="*60)

    # 1. 직접 호출 테스트 (이미 성공했던 방법)
    print("\n1. Direct Call Test (Previous Success)")
    print("-" * 40)

    try:
        manager = CrawlerManager()
        direct_result = await manager.run_crawler("G2B", None)
        print(f"   Direct Result: {direct_result.get('total_found', 0)} items")
    except Exception as e:
        print(f"   Direct Error: {e}")

    # 2. HTTP API 호출 테스트 (문제가 있는 방법)
    print("\n2. HTTP API Call Test (Problem Method)")
    print("-" * 40)

    try:
        # HTTP API 호출 (로컬 서버가 실행 중이라고 가정)
        api_url = "http://localhost:8000/crawl/G2B"

        # POST 요청 - body 없이 (None 키워드)
        response = requests.post(api_url, json=None, timeout=30)
        if response.status_code == 200:
            api_result = response.json()
            print(f"   API Result: {api_result.get('result', {}).get('total_found', 0)} items")
            print(f"   API Response: {api_result}")
        else:
            print(f"   API Error: HTTP {response.status_code}")
            print(f"   Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("   API Error: Server not running on port 8000")
    except Exception as e:
        print(f"   API Error: {e}")

    # 3. 빈 키워드로 API 호출 테스트
    print("\n3. HTTP API Call with Empty Keywords")
    print("-" * 40)

    try:
        api_url = "http://localhost:8000/crawl/G2B"

        # POST 요청 - 빈 키워드 배열
        payload = {"keywords": []}
        response = requests.post(api_url, json=payload, timeout=30)
        if response.status_code == 200:
            api_result = response.json()
            print(f"   Empty Keywords Result: {api_result.get('result', {}).get('total_found', 0)} items")
        else:
            print(f"   Empty Keywords Error: HTTP {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("   API Error: Server not running on port 8000")
    except Exception as e:
        print(f"   Empty Keywords Error: {e}")

    # 4. 'string' 키워드로 API 호출 테스트 (문제의 원인일 수 있음)
    print("\n4. HTTP API Call with 'string' Keyword")
    print("-" * 40)

    try:
        api_url = "http://localhost:8000/crawl/G2B"

        # POST 요청 - 'string' 키워드 (문제의 원인)
        payload = {"keywords": ["string"]}
        response = requests.post(api_url, json=payload, timeout=30)
        if response.status_code == 200:
            api_result = response.json()
            print(f"   'string' Keyword Result: {api_result.get('result', {}).get('total_found', 0)} items")
        else:
            print(f"   'string' Keyword Error: HTTP {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("   API Error: Server not running on port 8000")
    except Exception as e:
        print(f"   'string' Keyword Error: {e}")

    # 5. Seegene 키워드로 API 호출 테스트
    print("\n5. HTTP API Call with Seegene Keywords")
    print("-" * 40)

    try:
        from src.config import crawler_config
        api_url = "http://localhost:8000/crawl/G2B"

        # POST 요청 - 실제 Seegene 키워드 일부
        seegene_keywords = ["PCR", "diagnostic"]  # 영어로만 테스트
        payload = {"keywords": seegene_keywords}
        response = requests.post(api_url, json=payload, timeout=30)
        if response.status_code == 200:
            api_result = response.json()
            print(f"   Seegene Keywords Result: {api_result.get('result', {}).get('total_found', 0)} items")
            print(f"   Used Keywords: {seegene_keywords}")
        else:
            print(f"   Seegene Keywords Error: HTTP {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("   API Error: Server not running on port 8000")
    except Exception as e:
        print(f"   Seegene Keywords Error: {e}")

    print("\n" + "="*60)
    print("Test Summary:")
    print("- Check which method works and which fails")
    print("- Compare keyword handling between direct and API calls")
    print("- Identify the root cause of 0 results in API calls")

if __name__ == "__main__":
    asyncio.run(test_api_vs_direct())