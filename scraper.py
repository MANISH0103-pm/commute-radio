"""
scraper.py — The Field Reporter
--------------------------------
Uses Playwright (a headless browser) to visit X profiles and extract content.

Handles two distinct post types:
  1. Regular tweets  — text + optional images, all visible in the timeline.
  2. X Articles      — long-form subscriber posts. They appear as a card in the
                       timeline but the actual content lives on a separate article
                       page that requires clicking through.

Think of Playwright as a robot that opens Chrome, navigates to a URL, reads
the page like a human would, and hands structured data back to the server.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Page


# ── Data shape for a single post ──────────────────────────────────────────────

@dataclass
class XPost:
    """One tweet or X Article scraped from X."""
    post_id: str
    author: str
    text: str
    timestamp: str
    image_urls: list[str] = field(default_factory=list)
    likes: int = 0
    retweets: int = 0
    url: str = ""
    is_article: bool = False   # True when this is a long-form X Article
    article_title: str = ""    # Title shown on the article card (e.g. "Midday Market Update!")


# ── Cookie files ──────────────────────────────────────────────────────────────

# x_cookies.json  — exported from your real Chrome browser via Cookie-Editor.
#                   This is the primary authentication method. It looks identical
#                   to a real human session so X's bot detection won't block it.
COOKIES_FILE = Path("x_cookies.json")

# .x_session.json — fallback: cookies saved after a successful programmatic login.
SESSION_FILE = Path(".x_session.json")


async def _load_cookies(context: BrowserContext) -> bool:
    """
    Load cookies into the browser context so Playwright appears as a logged-in user.

    We check for the manually exported cookie file first (most reliable),
    then fall back to the auto-saved session file.
    Returns True if cookies were loaded successfully.
    """
    source = COOKIES_FILE if COOKIES_FILE.exists() else SESSION_FILE if SESSION_FILE.exists() else None
    if not source:
        return False

    raw = json.loads(source.read_text())

    # Cookie-Editor exports cookies with a "sameSite" field that uses different
    # capitalisation than Playwright expects — normalise it here.
    # Think of this as translating between two dialects of the same language.
    for cookie in raw:
        if cookie.get("sameSite"):
            val = cookie["sameSite"].capitalize()  # "strict" → "Strict"
            cookie["sameSite"] = val if val in ("Strict", "Lax", "None") else "None"
        else:
            cookie["sameSite"] = "None"
        # Remove keys Playwright doesn't recognise
        for key in ("hostOnly", "session", "storeId", "id"):
            cookie.pop(key, None)

    await context.add_cookies(raw)
    return True


# ── Login helper (fallback if no cookie file exists) ──────────────────────────

async def _login(page: Page, username: str, password: str) -> None:
    """
    Walk through X's login flow programmatically.

    X's login has multiple possible intermediate screens — we handle each one
    explicitly. Think of it like an airport: check-in → security → boarding,
    but sometimes there's an extra ID check in between.
    """
    await page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_selector('input[autocomplete="username"]', timeout=30_000)
    await page.fill('input[autocomplete="username"]', username)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(2000)

    # X sometimes shows an extra "confirm your identity" screen
    unusual_input = page.locator('input[data-testid="ocfEnterTextTextInput"]')
    if await unusual_input.count() > 0:
        await unusual_input.fill(username)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2000)

    await page.wait_for_selector('input[name="password"]', timeout=30_000)
    await page.fill('input[name="password"]', password)
    await page.keyboard.press("Enter")
    await page.wait_for_url("**/home", timeout=30_000)


# ── Main scraping function ────────────────────────────────────────────────────

async def scrape_profile(
    handle: str,
    max_posts: int = 10,
    headless: bool = True,
) -> list[XPost]:
    """
    Scrape recent posts from an X profile — handles both regular tweets and X Articles.

    Args:
        handle:    X username without the @ symbol (e.g. "market_sleuth")
        max_posts: How many posts to collect (default 10)
        headless:  Run browser invisibly (True) or show the window for debugging (False)

    Returns:
        List of XPost objects, newest first.
    """
    username = os.getenv("X_USERNAME", "")
    password = os.getenv("X_PASSWORD", "")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )

        cookies_loaded = await _load_cookies(context)
        page = await context.new_page()

        if not cookies_loaded and username and password:
            await _login(page, username, password)

        # Navigate to the profile timeline
        await page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(3000)

        posts: list[XPost] = []
        seen_ids: set[str] = set()

        # Scroll through the timeline collecting posts until we have enough
        for _ in range(max_posts * 3):
            articles = await page.query_selector_all('article[data-testid="tweet"]')

            for article in articles:
                post = await _parse_timeline_item(article, handle)
                if not post or post.post_id in seen_ids:
                    continue

                seen_ids.add(post.post_id)

                # X Articles need a second browser visit to read the full content.
                # The timeline only shows a card with a title and thumbnail —
                # the actual body text lives on a separate article page.
                if post.is_article:
                    post = await _fetch_article_content(page, post)

                posts.append(post)

            if len(posts) >= max_posts:
                break

            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(1200)

        await browser.close()

    return posts[:max_posts]


# ── Multi-account scraper ─────────────────────────────────────────────────────

async def scrape_multiple_profiles(
    handles: list[str],
    max_posts_per_account: int = 5,
    headless: bool = True,
) -> list[XPost]:
    """
    Scrape several X accounts in a single browser session and return all posts
    combined, sorted newest first.

    We reuse one browser session across all accounts — this is faster and
    less likely to trigger bot detection than opening a new browser per account.

    Args:
        handles:               List of X usernames without @ (e.g. ["market_sleuth", "elonmusk"])
        max_posts_per_account: Posts to fetch per account (default 5)
        headless:              Show browser window? False is useful for debugging.

    Returns:
        Combined list of XPost objects sorted newest-first.
    """
    username = os.getenv("X_USERNAME", "")
    password = os.getenv("X_PASSWORD", "")
    all_posts: list[XPost] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            ignore_https_errors=True,
        )

        cookies_loaded = await _load_cookies(context)
        page = await context.new_page()

        if not cookies_loaded and username and password:
            await _login(page, username, password)

        # Visit each account one by one in the same browser session
        for handle in handles:
            print(f"  Scraping @{handle}...")
            handle_posts = await _scrape_handle(page, handle, max_posts_per_account)
            all_posts.extend(handle_posts)

        await browser.close()

    # Sort all posts newest-first across all accounts
    all_posts.sort(key=lambda p: p.timestamp, reverse=True)
    return all_posts


async def _scrape_handle(page: Page, handle: str, max_posts: int) -> list[XPost]:
    """Scrape one account using an already-open authenticated page."""
    await page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_timeout(3000)

    posts: list[XPost] = []
    seen_ids: set[str] = set()

    for _ in range(max_posts * 3):
        articles = await page.query_selector_all('article[data-testid="tweet"]')

        for article in articles:
            post = await _parse_timeline_item(article, handle)
            if not post or post.post_id in seen_ids:
                continue
            seen_ids.add(post.post_id)

            if post.is_article:
                post = await _fetch_article_content(page, post)
                # Navigate back to the profile after reading the article
                await page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=60_000)
                await page.wait_for_timeout(2000)

            posts.append(post)

        if len(posts) >= max_posts:
            break

        await page.evaluate("window.scrollBy(0, 800)")
        await page.wait_for_timeout(1200)

    return posts[:max_posts]


# ── Timeline item parser ───────────────────────────────────────────────────────

async def _parse_timeline_item(article, default_author: str) -> Optional[XPost]:
    """
    Extract structured data from a single <article> element in the timeline.

    This handles both regular tweets and X Article cards. For articles, we only
    capture the metadata visible in the card — the full body is fetched separately.
    """
    try:
        # Timestamp & permalink (present on all post types)
        time_el = await article.query_selector("time")
        timestamp = await time_el.get_attribute("datetime") if time_el else ""
        link_el = await article.query_selector("a[href*='/status/']")
        href = await link_el.get_attribute("href") if link_el else ""
        post_id = href.split("/status/")[-1].split("?")[0] if "/status/" in href else ""
        # Strip any path suffixes like /analytics, /retweets, etc.
        post_id = post_id.split("/")[0]

        if not post_id or not post_id.isdigit():
            return None

        # Author — extract the @handle from the User-Name block
        author_el = await article.query_selector('[data-testid="User-Name"]')
        author_raw = await author_el.inner_text() if author_el else ""
        author = author_raw.split("\n")[0]  # display name is first line

        # Only keep posts actually authored by the target handle.
        # X timelines include retweets and quoted posts from other accounts —
        # we filter those out by checking the @handle link in the author block.
        handle_link = await article.query_selector(f'a[href="/{default_author}"]')
        if not handle_link:
            return None

        # ── Detect X Article cards ─────────────────────────────────────────────
        # X Articles appear as a card in the timeline. Two reliable signals:
        #   1. The card contains text like "Article" or "X Article"
        #   2. There is no tweetText element but there IS a card image (thumbnail)
        # We check for signal 1 first, then fall back to signal 2.
        #
        # Why not just check for "/i/articles/" in links? X doesn't always use
        # that URL pattern — sometimes it links directly to the status URL and
        # renders the article inline when you visit it.

        # Signal 1: look for "Article" label text anywhere in the card
        full_card_text = await article.inner_text()
        has_article_label = "X Article" in full_card_text or "· Article" in full_card_text

        # Signal 2: card image present but no tweet body text
        text_el = await article.query_selector('[data-testid="tweetText"]')
        has_tweet_text = text_el is not None and bool((await text_el.inner_text()).strip())
        thumb_el = await article.query_selector('img[src*="pbs.twimg.com"]')
        has_thumbnail = thumb_el is not None

        if has_article_label or (not has_tweet_text and has_thumbnail):
            # Extract title — the largest/boldest text in the card after the username
            # X typically renders it as the first prominent text block in the card link
            title = ""
            for sel in [
                'div[data-testid="card.layoutLarge.detail"] span',
                'div[data-testid="card.layoutSmall.detail"] span',
                'a[href*="status"] div > span',
            ]:
                title_el = await article.query_selector(sel)
                if title_el:
                    title = (await title_el.inner_text()).strip()
                    if title and title not in full_card_text[:50]:  # skip author name
                        break

            thumb_url = await thumb_el.get_attribute("src") if thumb_el else ""
            image_urls = [thumb_url] if thumb_url else []

            likes = await _parse_count(article, 'like')
            retweets = await _parse_count(article, 'retweet')

            return XPost(
                post_id=post_id,
                author=author,
                text="",  # filled in later by _fetch_article_content
                timestamp=timestamp,
                image_urls=image_urls,
                likes=likes,
                retweets=retweets,
                url=f"https://x.com{href}",
                is_article=True,
                article_title=title,
            )

        # ── Regular tweet ──────────────────────────────────────────────────────
        text_el = await article.query_selector('[data-testid="tweetText"]')
        text = await text_el.inner_text() if text_el else ""

        img_els = await article.query_selector_all('img[src*="pbs.twimg.com/media"]')
        image_urls = []
        for img in img_els:
            src = await img.get_attribute("src")
            if src:
                image_urls.append(src.replace("&name=small", "&name=large"))

        likes = await _parse_count(article, 'like')
        retweets = await _parse_count(article, 'retweet')

        return XPost(
            post_id=post_id,
            author=author,
            text=text,
            timestamp=timestamp,
            image_urls=image_urls,
            likes=likes,
            retweets=retweets,
            url=f"https://x.com{href}",
            is_article=False,
        )

    except Exception:
        return None


# ── X Article full-content fetcher ────────────────────────────────────────────

async def _fetch_article_content(page: Page, post: XPost) -> XPost:
    """
    Navigate to an X Article page and scrape the title + full body text.

    X Articles are like blog posts — the timeline only shows a preview card.
    We visit the tweet URL (X redirects it to the article view), wait for it
    to render, then extract the title and all body paragraphs.
    """
    try:
        await page.goto(post.url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(3000)

        # ── Navigate to the standalone article page ───────────────────────────────
        # The tweet status URL embeds the article inline with replies below it.
        # X also has a dedicated article URL: /handle/article/post_id
        # This page shows only the article body — no replies, no clutter.
        handle = post.url.split("x.com/")[1].split("/")[0]
        article_page_url = f"https://x.com/{handle}/article/{post.post_id}"
        await page.goto(article_page_url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(2000)

        # Scroll down to lazy-load all paragraphs, then return to top to read in order
        for _ in range(8):
            await page.evaluate("window.scrollBy(0, 600)")
            await page.wait_for_timeout(400)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        # ── Extract title ──────────────────────────────────────────────────────
        # The title lives in a div[dir="auto"] at the top of the page
        title_el = await page.query_selector('div[dir="auto"]')
        if title_el:
            post.article_title = (await title_el.inner_text()).strip()

        # ── Extract body using Draft.js selectors ──────────────────────────────
        # X Articles are written in Draft.js (a rich-text editor framework).
        # The body text is stored in span[data-text="true"] elements nested inside
        # div[data-block="true"] paragraph blocks, all inside the Draft editor container.
        #
        # Think of it like a Word document's internal XML — the visible text lives
        # inside deeply nested structural tags we have to know to look for.
        editor = await page.query_selector('div[class*="public-DraftEditor-content"]')
        if editor:
            # Collect each paragraph block's text in document order
            blocks = await editor.query_selector_all('div[data-block="true"]')
            paragraphs = []
            for block in blocks:
                spans = await block.query_selector_all('span[data-text="true"]')
                block_text = "".join([(await s.inner_text()) for s in spans]).strip()
                if block_text:
                    paragraphs.append(block_text)
            body_text = "\n\n".join(paragraphs)
        else:
            body_text = ""

        # ── Grab article images ────────────────────────────────────────────────
        img_els = await page.query_selector_all('img[src*="pbs.twimg.com/media"]')
        article_images = []
        for img in img_els:
            src = await img.get_attribute("src")
            if src:
                article_images.append(src.replace("&name=small", "&name=large"))

        post.text = body_text or f"[Article: {post.article_title}]"
        if article_images:
            post.image_urls = article_images

    except Exception:
        post.text = f"[Article: {post.article_title}]"

    return post


# ── Engagement count parser ───────────────────────────────────────────────────

async def _parse_count(article, action: str) -> int:
    """Parse like/retweet counts from the action bar below a tweet."""
    el = await article.query_selector(
        f'[data-testid="{action}"] [data-testid="app-text-transition-container"]'
    )
    if not el:
        return 0
    raw = (await el.inner_text()).strip().replace(",", "")
    if raw.endswith("K"):
        return int(float(raw[:-1]) * 1000)
    if raw.endswith("M"):
        return int(float(raw[:-1]) * 1_000_000)
    try:
        return int(raw)
    except ValueError:
        return 0
