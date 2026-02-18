"""Re-scrape missing FotMob matches and upload to MinIO."""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any

from playwright.async_api import async_playwright

import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from football_rag.data.fotmob_scraper import scrape_fotmob_match_details
from football_rag.storage.minio_client import MinIOClient


async def main():
    base_dir = Path(__file__).parent.parent

    # Load FotMob match IDs to scrape
    targets_file = base_dir / "data" / "fotmob_match_ids_to_scrape.json"
    with open(targets_file) as f:
        targets = json.load(f)
    print(f"📊 Loaded {len(targets)} FotMob matches to scrape")

    # Create output directory
    output_dir = base_dir / "data" / "raw" / "fotmob_rescrape"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize MinIO client
    minio_client = MinIOClient()
    minio_client.ensure_bucket("football-rag")

    # Track results
    success_count = 0
    failed_matches = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to FotMob to establish session
        print("🌐 Establishing FotMob session...")
        await page.goto("https://www.fotmob.com", wait_until="domcontentloaded")

        for idx, target in enumerate(targets, 1):
            fotmob_id = target['fotmob_match_id']
            ws_id = target['whoscored_id']
            home_team = target['home_team']
            away_team = target['away_team']

            print(f"\n[{idx}/{len(targets)}] Scraping {fotmob_id}: {home_team} vs {away_team}")

            # Scrape match details
            match_data = await scrape_fotmob_match_details(fotmob_id, page)

            if match_data:
                # Save locally
                output_file = output_dir / f"{fotmob_id}.json"
                with open(output_file, 'w') as f:
                    json.dump(match_data, f, indent=2)

                # Upload to MinIO
                try:
                    s3_key = f"fotmob/eredivisie/2025-2026/{fotmob_id}.json"
                    minio_client.upload_json(
                        bucket="football-rag",
                        key=s3_key,
                        data=match_data
                    )
                    print(f"✅ Uploaded to MinIO: {s3_key}")
                    success_count += 1
                except Exception as e:
                    print(f"⚠️  MinIO upload failed: {e}")
                    failed_matches.append({
                        'fotmob_id': fotmob_id,
                        'whoscored_id': ws_id,
                        'reason': f"MinIO upload failed: {e}"
                    })
            else:
                print(f"❌ Scraping failed for {fotmob_id}")
                failed_matches.append({
                    'fotmob_id': fotmob_id,
                    'whoscored_id': ws_id,
                    'reason': 'Scraping returned None'
                })

            # Rate limiting
            await asyncio.sleep(2)

        await browser.close()

    # Summary report
    print(f"\n{'='*60}")
    print(f"📊 Re-scraping Summary")
    print(f"{'='*60}")
    print(f"✅ Successfully scraped: {success_count}/{len(targets)} matches")
    print(f"💾 Local files: {output_dir}")

    if failed_matches:
        print(f"\n⚠️  {len(failed_matches)} matches failed:")
        for fail in failed_matches[:10]:
            print(f"   - {fail['fotmob_id']} ({fail['whoscored_id']}): {fail['reason']}")
        if len(failed_matches) > 10:
            print(f"   ... and {len(failed_matches) - 10} more")

        # Save failure report
        fail_report = base_dir / "data" / "rescrape_failures.json"
        with open(fail_report, 'w') as f:
            json.dump(failed_matches, f, indent=2)
        print(f"\n📝 Failure report: {fail_report}")

    print(f"\n✅ Re-scraping complete!")
    print(f"Next step: Reload Bronze layer with:")
    print(f"  uv run dagster asset materialize -m orchestration.defs --select raw_matches_bronze")


if __name__ == "__main__":
    asyncio.run(main())
