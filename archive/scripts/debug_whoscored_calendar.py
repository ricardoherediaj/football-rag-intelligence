"""
Debug WhoScored calendar page to identify Cloudflare blocking point.
"""

import asyncio
from playwright.async_api import async_playwright

async def main():
    fixtures_url = "https://www.whoscored.com/Regions/155/Tournaments/13/Seasons/10752/Stages/24542/Fixtures/Netherlands-Eredivisie-2025-2026"

    print("🔍 Test 2: Can we load the WhoScored calendar page?")
    print(f"URL: {fixtures_url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print("⏳ Navigating to calendar...")
            await page.goto(fixtures_url, wait_until="domcontentloaded", timeout=60000)
            print("✅ Page loaded (domcontentloaded)\n")

            # Take a screenshot to see what rendered
            await page.screenshot(path="debug_calendar.png")
            print("📸 Screenshot saved: debug_calendar.png\n")

            # Check if Cloudflare challenge appears
            cloudflare_check = await page.locator("text=/cloudflare|challenge|just a moment/i").count()
            if cloudflare_check > 0:
                print("🛑 CLOUDFLARE CHALLENGE DETECTED")
                print("Waiting 10 seconds to see if it auto-solves...")
                await asyncio.sleep(10)

            # Try to wait for the match selector
            print("⏳ Waiting for .Match-module_match__XlKTY selector...")
            try:
                await page.wait_for_selector(".Match-module_match__XlKTY", timeout=30000)
                print("✅ Match selector found!")

                # Count matches
                match_count = await page.locator(".Match-module_match__XlKTY").count()
                print(f"📊 Found {match_count} match elements on current page")

            except Exception as e:
                print(f"❌ Selector timeout: {e}\n")

                # Debug: What selectors ARE available?
                print("🔍 Debugging available content...")
                content = await page.content()

                if "cloudflare" in content.lower() or "challenge" in content.lower():
                    print("🛑 Cloudflare content detected in HTML")
                elif "Match-module" in content:
                    print("✅ Match-module classes exist - selector might be wrong")
                else:
                    print("⚠️ No match-related content found")

                # Save HTML for inspection
                with open("debug_calendar.html", "w") as f:
                    f.write(content)
                print("💾 HTML saved: debug_calendar.html")

        finally:
            print("\n🔍 Browser will stay open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
