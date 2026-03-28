"""
run.py — Mission Control
--------------------------
The single script that runs the full pipeline end to end:

  1. Scrape    — visit each X account, collect today's posts
  2. Summarise — Claude writes a radio script from the posts
  3. Audio     — edge-tts converts the script to an .mp3
  4. Feed      — generate a podcast RSS feed.xml
  5. Deploy    — push MP3 + feed.xml to Vercel

Run manually:       uv run python run.py
Run automatically:  triggered by macOS launchd at 3:00 PM daily (set up separately)

Accounts to scrape are read from the ACCOUNTS variable below or from the
X_ACCOUNTS environment variable (comma-separated handles, no @ symbol).
"""

import asyncio
import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env BEFORE importing any module that reads env vars at import time ──
load_dotenv()

from scraper import scrape_multiple_profiles, XPost
from summarizer import build_radio_script
from audio import text_to_speech
from feed import generate_feed
from deploy import push


# ── Configuration ─────────────────────────────────────────────────────────────

# Add or remove handles here (no @ symbol).
# Can also be set via X_ACCOUNTS env var: X_ACCOUNTS=market_sleuth,Basssem666
DEFAULT_ACCOUNTS = [
    "market_sleuth",
    "Basssem666",
]

# Scraping window: posts from this many hours ago up to now
# 3 PM run covering 8:30 AM–3 PM = ~6.5 hours
WINDOW_HOURS = 6.5

# Where generated files land before deploy
OUTPUT_DIR = Path("output")
FEED_DIR = Path("public")


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_accounts() -> list[str]:
    """Read account list from env var or fall back to DEFAULT_ACCOUNTS."""
    env_val = os.getenv("X_ACCOUNTS", "")
    if env_val:
        return [h.strip() for h in env_val.split(",") if h.strip()]
    return DEFAULT_ACCOUNTS


def filter_to_window(posts: list[XPost], hours: float) -> list[XPost]:
    """
    Keep only posts that fall within the scraping time window.

    We filter in Python (not in the scraper) because the scraper collects the
    most recent posts regardless of time — it's faster to filter after the fact
    than to keep scrolling looking for older posts.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = []
    for p in posts:
        try:
            # Timestamps come back as ISO 8601 strings e.g. "2026-03-27T14:26:14.000Z"
            post_time = datetime.fromisoformat(p.timestamp.replace("Z", "+00:00"))
            if post_time >= cutoff:
                result.append(p)
        except Exception:
            pass  # skip posts with unparseable timestamps
    return result


def estimate_duration(mp3_path: Path) -> int:
    """
    Estimate audio duration in seconds from file size.
    edge-tts outputs ~128kbps MP3, so: seconds = (bytes * 8) / (128 * 1024)
    """
    size = mp3_path.stat().st_size
    return int((size * 8) / (128 * 1024))


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def main():
    accounts = get_accounts()
    today = datetime.now().strftime("%B %d, %Y")
    date_slug = datetime.now().strftime("%Y%m%d")

    print(f"\n{'='*60}")
    print(f"  Commute Radio — {today}")
    print(f"  Accounts: {', '.join(f'@{a}' for a in accounts)}")
    print(f"  Window:   last {WINDOW_HOURS} hours")
    print(f"{'='*60}\n")

    # ── Step 1: Scrape ────────────────────────────────────────────────────────
    print("Step 1/5 · Scraping accounts...")
    all_posts = await scrape_multiple_profiles(
        handles=accounts,
        max_posts_per_account=50,  # no cap during trial — collect everything
    )
    posts = filter_to_window(all_posts, WINDOW_HOURS)
    print(f"  {len(all_posts)} total posts scraped → {len(posts)} within window")

    if not posts:
        print("  No posts found in window. Exiting.")
        return

    # ── Step 2: Summarise ─────────────────────────────────────────────────────
    print("\nStep 2/5 · Generating radio script...")
    script = await build_radio_script(
        posts=posts,
        handle=", ".join(f"@{a}" for a in accounts),
        style="calm, insightful financial podcast host",
    )
    word_count = len(script.split())
    print(f"  Script: {word_count} words (~{word_count // 130} min)")

    # ── Step 3: Audio ─────────────────────────────────────────────────────────
    print("\nStep 3/5 · Generating audio (edge-tts)...")
    mp3_filename = f"episode_{date_slug}.mp3"
    mp3_path = await text_to_speech(script, filename=mp3_filename)
    duration = estimate_duration(mp3_path)
    print(f"  Saved: {mp3_path} ({mp3_path.stat().st_size // 1024} KB, ~{duration//60}m {duration%60}s)")

    # ── Step 4: RSS Feed ──────────────────────────────────────────────────────
    print("\nStep 4/5 · Generating RSS feed...")
    episode_title = f"{today} · Afternoon Briefing"
    feed_path = FEED_DIR / "feed.xml"
    generate_feed(
        episode_title=episode_title,
        script=script,
        mp3_filename=mp3_filename,
        mp3_size_bytes=mp3_path.stat().st_size,
        duration_seconds=duration,
        output_path=feed_path,
    )
    print(f"  Saved: {feed_path}")

    # ── Step 5: Deploy ────────────────────────────────────────────────────────
    print("\nStep 5/5 · Deploying to Vercel...")
    try:
        url = push(mp3_path, feed_path)
        print(f"\n✓ Live at: {url}")
        print(f"  RSS feed: {url}/feed.xml")
        print(f"  Audio:    {url}/audio/{mp3_filename}")
    except RuntimeError as e:
        print(f"\n  Deploy failed: {e}")
        print(f"  Files saved locally at {OUTPUT_DIR}/ and {FEED_DIR}/")
        print("  Run 'vercel login' and 'vercel link' if this is a first-time setup.")

    print(f"\n{'='*60}")
    print("  Done.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
