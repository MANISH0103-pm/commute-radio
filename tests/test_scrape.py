"""
test_scrape.py — Test: scrape @market_sleuth including X Articles
"""

import asyncio
from dotenv import load_dotenv
from scraper import scrape_profile

load_dotenv()

async def main():
    print("Scraping @market_sleuth (including X Articles)...")

    posts = await scrape_profile(handle="market_sleuth", max_posts=20)

    print(f"\nTotal posts fetched: {len(posts)}")
    print("=" * 60)

    for p in posts:
        kind = "X ARTICLE" if p.is_article else "TWEET"
        print(f"\n[{kind}] {p.timestamp}")
        if p.article_title:
            print(f"Title: {p.article_title}")
        print(f"URL: {p.url}")
        print(f"Text:\n{p.text[:500]}")
        if p.image_urls:
            print(f"Images: {len(p.image_urls)}")
        print(f"Likes: {p.likes} | Retweets: {p.retweets}")
        print("-" * 60)

asyncio.run(main())
