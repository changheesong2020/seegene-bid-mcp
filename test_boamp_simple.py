#!/usr/bin/env python3
import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.crawler.manager import crawler_manager

async def test_boamp_simple():
    """Test FR_BOAMP crawler with minimal setup"""
    print("Testing FR_BOAMP crawler...")

    try:
        # Test with one keyword
        result = await crawler_manager.run_crawler("FR_BOAMP", ["diagnostic"])

        print("Result fields:")
        for key, value in result.items():
            if key != 'results':  # Skip detailed results
                print(f"  {key}: {value}")

        print(f"Results count: {len(result.get('results', []))}")

        # Check if result has all required fields
        required_fields = ['success', 'site', 'total_found']
        missing_fields = [field for field in required_fields if field not in result]

        if missing_fields:
            print(f"Missing required fields: {missing_fields}")
        else:
            print("All required fields present!")

        return result

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_boamp_simple())