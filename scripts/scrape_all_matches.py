"""
Simple orchestration script to run both WhoScored and Fotmob scrapers.
Logs output to text file for monitoring.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.football_rag.data.whoscored_scraper import scrape_complete_season
from src.football_rag.data.fotmob_scraper import scrape_fotmob_eredivisie, save_fotmob_matches_to_minio


def main():
    log_file = Path("data/scraping_log.txt")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Scraping started: {datetime.now().isoformat()}\n")
        f.write(f"{'='*60}\n\n")

    print("🚀 Starting complete scraping pipeline...\n")

    # Step 1: WhoScored
    print("📊 Step 1: Scraping WhoScored...")
    try:
        whoscored_data = scrape_complete_season(mode="incremental")
        if whoscored_data is not None:
            from src.football_rag.data.whoscored_scraper import save_matches_to_minio
            saved = save_matches_to_minio(whoscored_data)
            msg = f"✅ WhoScored: {saved} matches saved\n"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg)
        else:
            msg = "⚠️  WhoScored: No new matches\n"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg)
    except Exception as e:
        msg = f"❌ WhoScored failed: {e}\n"
        print(msg)
        with open(log_file, 'a') as f:
            f.write(msg)

    print()

    # Step 2: Fotmob
    print("📊 Step 2: Scraping Fotmob...")
    try:
        fotmob_data = scrape_fotmob_eredivisie(mode="incremental")
        if fotmob_data:
            saved = save_fotmob_matches_to_minio(fotmob_data)
            msg = f"✅ Fotmob: {saved} matches saved\n"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg)
        else:
            msg = "⚠️  Fotmob: No new matches\n"
            print(msg)
            with open(log_file, 'a') as f:
                f.write(msg)
    except Exception as e:
        msg = f"❌ Fotmob failed: {e}\n"
        print(msg)
        with open(log_file, 'a') as f:
            f.write(msg)

    with open(log_file, 'a') as f:
        f.write(f"\nScraping completed: {datetime.now().isoformat()}\n")

    print("\n✅ Scraping pipeline complete! Check data/scraping_log.txt for details")


if __name__ == "__main__":
    main()