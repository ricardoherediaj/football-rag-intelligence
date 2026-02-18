"""
Fotmob scraper using Playwright to extract SSR'd match data.

FotMob is a Next.js app that server-side renders full match data into
__NEXT_DATA__. We navigate to each match page and extract the embedded
JSON — no API calls needed, bypassing the x-mas auth header requirement.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, async_playwright, Route


_BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}


async def _block_heavy_resources(route: Route) -> None:
    """Abort image/media/font/stylesheet requests to reduce memory usage."""
    if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.continue_()


async def scrape_fotmob_match_details(
    match_id: str, page_url: str, page: Page
) -> Optional[Dict[str, Any]]:
    """
    Navigate to the match page and extract data from __NEXT_DATA__.

    FotMob SSRs the full match payload (general, content.shotmap, etc.)
    into the HTML. The proper pageUrl (with slug) is required — the old
    /matches/match/{id} format returns empty pageProps.
    """
    url = f"https://www.fotmob.com{page_url}"
    print(f"🗺️ Navigating to: {url}")

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        page_props = await page.evaluate("""() => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;
            const data = JSON.parse(el.textContent);
            return data.props && data.props.pageProps ? data.props.pageProps : null;
        }""")

        if not page_props or "general" not in page_props:
            print(f"❌ No match data in __NEXT_DATA__ for {match_id}")
            return None

        general = page_props["general"]
        content = page_props.get("content", {})
        shotmap = content.get("shotmap", {})
        shots = shotmap.get("shots", []) if isinstance(shotmap, dict) else []

        home = general.get("homeTeam", {}).get("name")
        away = general.get("awayTeam", {}).get("name")
        print(f"✅ {home} vs {away} — {len(shots)} shots")

        return {
            "shots": shots,
            "match_info": {
                "match_id": match_id,
                "home_team": home,
                "away_team": away,
                "home_team_id": general.get("homeTeam", {}).get("id"),
                "away_team_id": general.get("awayTeam", {}).get("id"),
                "score": general.get("matchTimeUTC"),
                "utc_time": general.get("matchTimeUTCDate"),
            },
        }

    except Exception as e:
        print(f"❌ Failed for {match_id}: {e}")
        return None


async def collect_fixtures(page: Page, league_id: int = 57) -> List[Dict[str, str]]:
    """
    Fetch finished match IDs and pageUrls from the fixtures endpoint.

    Returns list of {'id': str, 'pageUrl': str} dicts.
    """
    print(f"📅 Fetching fixtures for league {league_id}...")
    try:
        data = await page.evaluate(
            """async (leagueId) => {
            const response = await fetch('/api/leagues?id=' + leagueId);
            return await response.json();
        }""",
            league_id,
        )

        matches = data.get("fixtures", {}).get("allMatches", [])
        finished = [
            {"id": str(m["id"]), "pageUrl": m.get("pageUrl", "")}
            for m in matches
            if m.get("status", {}).get("finished")
            and not m.get("status", {}).get("cancelled")
        ]

        print(f"✅ Found {len(finished)} finished matches")
        return finished

    except Exception as e:
        print(f"❌ Failed to fetch fixtures: {e}")
        return []


async def scrape_fotmob_season(
    league_id: int = 57, mode: str = "incremental", limit: int = None
) -> List[Dict]:
    """
    Main entry point for scraping a season.

    Modes:
    - 'full': Scrape everything.
    - 'incremental': Scrape only what we don't have locally.
    - 'recent': Scrape 1 most recent.
    - 'n_matches': Scrape last N.
    """
    results = []

    if mode == "recent":
        limit = 1

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.route("**/*", _block_heavy_resources)

        # 1. Go to homepage to init session
        await page.goto("https://www.fotmob.com", wait_until="domcontentloaded")

        # 2. Get fixtures (id + pageUrl)
        fixtures = await collect_fixtures(page, league_id)

        if mode == "incremental":
            output_dir = Path("data/raw/fotmob_matches/eredivisie/2025-2026")
            existing_ids = set()
            if output_dir.exists():
                for f in output_dir.glob("match_*.json"):
                    existing_ids.add(f.stem.replace("match_", ""))
            fixtures = [f for f in fixtures if f["id"] not in existing_ids]
            print(f"Incremental mode: {len(fixtures)} new matches to scrape.")

        elif mode in ["recent", "n_matches"] and limit:
            fixtures = fixtures[-limit:]
            ids = [f["id"] for f in fixtures]
            print(f"Mode '{mode}': SCRAPING LAST {limit} MATCHES: {ids}")

        print(f"🚀 Starting scrape of {len(fixtures)} matches...")

        for fix in fixtures:
            if not fix.get("pageUrl"):
                print(f"⚠️ No pageUrl for {fix['id']}, skipping")
                continue
            match_data = await scrape_fotmob_match_details(
                fix["id"], fix["pageUrl"], page
            )
            if match_data:
                results.append(match_data)
            await asyncio.sleep(1)

        await browser.close()

    return results


def save_fotmob_matches_locally(matches: List[Dict]) -> int:
    """Save scraped matches to data/raw/fotmob_matches."""
    save_dir = Path("data/raw/fotmob_matches/eredivisie/2025-2026")
    save_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for m in matches:
        mid = m["match_info"]["match_id"]
        path = save_dir / f"match_{mid}.json"
        with open(path, "w") as f:
            json.dump(m, f, indent=2)
        count += 1

    print(f"💾 Saved {count} matches locally")
    return count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["full", "incremental", "recent", "n_matches"],
        default="incremental",
    )
    parser.add_argument("--limit", type=int, help="Number of matches (for n_matches)")
    parser.add_argument("--league_id", type=int, default=57)
    args = parser.parse_args()

    matches = asyncio.run(
        scrape_fotmob_season(args.league_id, args.mode, args.limit)
    )

    if matches:
        save_fotmob_matches_locally(matches)
    else:
        print("No matches scraped.")
