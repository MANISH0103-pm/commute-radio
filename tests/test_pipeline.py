"""
test_pipeline.py — End-to-end test: scrape → summarize
Targets @Basssem666, today's posts only, text only (no images).
"""

import asyncio
from dotenv import load_dotenv

# load_dotenv() must run BEFORE importing summarizer/audio — both clients
# initialize at import time and read API keys from the environment.
load_dotenv()

from scraper import scrape_profile, XPost
from summarizer import build_radio_script
from audio import text_to_speech

async def main():
    # ── Step 1: Scrape ────────────────────────────────────────────────────────
    print("Step 1: Scraping @Basssem666...")
    all_posts = await scrape_profile(handle="Basssem666", max_posts=20)

    # Filter to today's posts only
    todays_posts = [p for p in all_posts if "2026-03-27" in p.timestamp]

    # Strip images so this test is text-only (zero vision API cost)
    for p in todays_posts:
        p.image_urls = []

    print(f"  Found {len(todays_posts)} posts from today")
    if not todays_posts:
        print("  No posts found for today. Exiting.")
        return

    for p in todays_posts:
        kind = "ARTICLE" if p.is_article else "TWEET"
        print(f"  [{kind}] {p.timestamp[:10]} — {p.text[:80]}...")

    # ── Step 2: Summarize → Radio Script ─────────────────────────────────────
    print("\nStep 2: Generating radio script via Claude...")
    script = await build_radio_script(
        posts=todays_posts,
        handle="Basssem666",
        style="calm, insightful financial podcast host",
    )

    print("\n" + "=" * 60)
    print("RADIO SCRIPT")
    print("=" * 60)
    print(script)
    print("=" * 60)

    # ── Step 3: Convert to Audio ──────────────────────────────────────────────
    print("\nStep 3: Sending to ElevenLabs for text-to-speech...")
    audio_path = await text_to_speech(script, filename="basssem666_test.mp3")
    print(f"\n✓ Audio saved to: {audio_path}")
    print("Opening in default audio player...")
    import subprocess
    subprocess.run(["open", str(audio_path)])

asyncio.run(main())
