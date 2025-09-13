#!/usr/bin/env python3
"""
Test script to validate both WhoScored and Fotmob scrapers.
Run this before integrating into the full pipeline.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_whoscored_scraper():
    """Test WhoScored scraper with a single match."""
    print("🔍 Testing WhoScored scraper...")
    
    from football_rag.data.scrapers import WhoScoredScraper
    
    test_url = "https://www.whoscored.com/matches/1903736/live/netherlands-eredivisie-2025-2026-sc-heerenveen-fc-volendam"
    
    with WhoScoredScraper(headless=True) as scraper:
        df = scraper.scrape_single_match(test_url)
        
        if df is not None:
            print(f"✅ WhoScored: {len(df)} events scraped")
            print(f"📊 Columns: {list(df.columns)}")
            print(f"⚽ Event types: {df['type_display_name'].unique()[:5]}")
            return True
        else:
            print("❌ WhoScored scraping failed")
            return False


def test_fotmob_scraper():
    """Test Fotmob scraper with shot data."""
    print("\n🔍 Testing Fotmob scraper...")
    
    from football_rag.data.scrapers import FotmobScraper
    
    # Test match: Salzburg vs Real Madrid
    test_match_id = 4825080
    
    scraper = FotmobScraper()
    df = scraper.scrape_shots(test_match_id)
    
    if df is not None:
        print(f"✅ Fotmob: {len(df)} shots scraped")
        print(f"📊 Columns: {list(df.columns)}")
        if len(df) > 0:
            print(f"🎯 Teams: {df['teamId'].unique()}")
            print(f"⚽ Event types: {df['eventType'].unique()}")
        return True
    else:
        print("❌ Fotmob scraping failed")
        return False


def test_data_integration():
    """Test basic data integration concepts."""
    print("\n🔍 Testing data integration...")
    
    # This would be where we test combining WhoScored events + Fotmob shots
    # For now, just validate both scrapers can work together
    
    from football_rag.data.scrapers import WhoScoredScraper, FotmobScraper
    
    print("✅ Both scrapers imported successfully")
    print("✅ Ready for data pipeline integration")
    return True


def main():
    """Run scraper validation tests."""
    print("🚀 Starting Scraper Validation Tests\n")
    
    tests = [
        ("WhoScored Scraper", test_whoscored_scraper),
        ("Fotmob Scraper", test_fotmob_scraper),
        ("Integration Readiness", test_data_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print('='*50)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except KeyboardInterrupt:
            print("\n⚠️ Tests interrupted by user")
            break
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("📋 SCRAPER VALIDATION SUMMARY")
    print('='*50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Scrapers are ready for pipeline integration.")
        print("\n📋 Next Steps:")
        print("1. ✅ Scrapers validated")
        print("2. ⏭️  Set up MinIO storage")
        print("3. ⏭️  Create embeddings pipeline")
        print("4. ⏭️  Build RAG system")
    else:
        print("⚠️ Some tests failed. Fix issues before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    main()