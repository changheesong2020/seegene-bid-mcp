#!/usr/bin/env python3
import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.crawler.fr_boamp_crawler import FranceBOAMPCrawler

async def test_boamp_crawler():
    """Test French BOAMP crawler"""
    print("Testing French BOAMP crawler...")

    crawler = FranceBOAMPCrawler()

    # Test with medical keywords
    keywords = ["diagnostic", "medical", "PCR"]

    try:
        result = await crawler.crawl(keywords)

        print(f"Crawling result:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Total found: {result.get('total_collected', 0)}")
        print(f"  Source: {result.get('source', 'Unknown')}")

        if result.get('results'):
            print(f"\nSample results:")
            for i, item in enumerate(result['results'][:3]):  # Show first 3
                print(f"  {i+1}. {item.get('title', 'No title')}")
                print(f"     Organization: {item.get('organization', 'Unknown')}")
                print(f"     URL: {item.get('source_url', 'No URL')}")
                print(f"     Keywords: {item.get('keywords', [])}")
                print()

        return result

    except Exception as e:
        print(f"Error testing BOAMP crawler: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_boamp_crawler())