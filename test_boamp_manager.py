#!/usr/bin/env python3
import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.crawler.manager import crawler_manager

async def test_boamp_through_manager():
    """Test French BOAMP crawler through manager"""
    print("Testing French BOAMP crawler through manager...")

    # Test with medical keywords
    keywords = ["diagnostic", "medical"]

    try:
        result = await crawler_manager.run_crawler("FR_BOAMP", keywords)

        print(f"Manager result:")
        print(f"  Success: {result.get('success', False)}")
        print(f"  Site: {result.get('site', 'Unknown')}")
        print(f"  Total found: {result.get('total_found', 0)}")
        print(f"  Error: {result.get('error', 'None')}")

        return result

    except Exception as e:
        print(f"Error testing BOAMP through manager: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_boamp_through_manager())