#!/usr/bin/env python3
import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.crawler.manager import crawler_manager

async def test_g2b_crawler():
    """Test G2B crawler through manager to see enhanced logging"""
    print("Testing G2B crawler through manager...")

    # Test with single keyword
    keywords = ["PCR"]
    result = await crawler_manager.run_crawler("G2B", keywords)

    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    asyncio.run(test_g2b_crawler())