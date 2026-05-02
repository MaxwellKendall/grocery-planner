#!/usr/bin/env python3
# /// script
# dependencies = ["playwright"]
# ///
"""Scrape source URLs from a Pinterest board using Playwright.

No Pinterest API key required. Intercepts Pinterest's internal feed API as the
board scrolls, extracting the source URL from each pin's JSON payload.

Usage:
    python scripts/scrape_board.py <board_url>
    python scripts/scrape_board.py https://www.pinterest.com/username/board-name/

Pipe into extract_recipe.py:
    python scripts/scrape_board.py https://www.pinterest.com/you/recipes/ \\
        | python scripts/extract_recipe.py --batch

First run opens a browser window — log in to Pinterest, then press Enter in the
terminal. Subsequent runs reuse the saved session and run headlessly.

Install:
    pip install playwright
    playwright install chromium
"""

import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

SESSION_FILE = Path(__file__).parent / ".pinterest_session.json"

# Pinterest internal API endpoints that carry pin feed data
FEED_PATTERNS = [
    "BoardFeedResource",
    "UserActivityPinsResource",
    "BoardResource",
]


async def get_context(playwright):
    headless = SESSION_FILE.exists()
    browser = await playwright.chromium.launch(headless=headless)
    if SESSION_FILE.exists():
        context = await browser.new_context(storage_state=str(SESSION_FILE))
    else:
        context = await browser.new_context()
    return browser, context


async def login_and_save(context):
    page = await context.new_page()
    await page.goto("https://www.pinterest.com/login/")
    print("Log in to Pinterest in the browser window, then press Enter here...", file=sys.stderr)
    input()
    await context.storage_state(path=str(SESSION_FILE))
    print(f"Session saved to {SESSION_FILE}", file=sys.stderr)
    await page.close()


async def scroll_to_end(page, max_scrolls=60):
    """Scroll until the page stops growing (all pins loaded)."""
    prev_height = 0
    stalled = 0
    for _ in range(max_scrolls):
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1200)
        height = await page.evaluate("document.body.scrollHeight")
        if height == prev_height:
            stalled += 1
            if stalled >= 3:
                break
        else:
            stalled = 0
        prev_height = height


async def scrape_board(board_url: str) -> list[str]:
    source_urls = []
    seen: set[str] = set()

    async with async_playwright() as p:
        browser, context = await get_context(p)

        if not SESSION_FILE.exists():
            await login_and_save(context)

        page = await context.new_page()

        async def handle_response(response):
            if not any(pat in response.url for pat in FEED_PATTERNS):
                return
            try:
                data = await response.json()
            except Exception:
                return

            # Pinterest wraps feed data in resource_response.data
            pins = (
                data.get("resource_response", {}).get("data")
                or data.get("data")
                or []
            )
            if not isinstance(pins, list):
                return

            for pin in pins:
                if not isinstance(pin, dict):
                    continue
                link = pin.get("link")
                if link and "pinterest.com" not in link and link not in seen:
                    seen.add(link)
                    source_urls.append(link)

        page.on("response", handle_response)

        print(f"Loading: {board_url}", file=sys.stderr)
        await page.goto(board_url, wait_until="networkidle")
        await scroll_to_end(page)
        # Give any in-flight responses time to resolve
        await page.wait_for_timeout(1500)

        await page.close()
        await browser.close()

    return source_urls


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    urls = asyncio.run(scrape_board(sys.argv[1]))

    for url in urls:
        print(url)

    print(f"\nFound {len(urls)} source URLs.", file=sys.stderr)
