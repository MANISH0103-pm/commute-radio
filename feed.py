"""
feed.py — The Broadcast Tower
--------------------------------
Generates a valid podcast RSS feed (feed.xml) that Apple Podcasts, Overcast,
and any podcast app can subscribe to.

The feed always contains exactly ONE episode — today's briefing. There is no
archive. Each day the feed is overwritten with fresh content.

How podcast RSS works (plain English):
  A podcast RSS feed is just an XML text file hosted at a public URL.
  Podcast apps check that URL periodically. When the <guid> changes, the app
  treats it as a new episode and downloads/notifies the user.
  The <enclosure> tag points to the .mp3 file URL — that's what actually plays.
"""

from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path


# The public Vercel URL is read from .env so it works across environments.
# Set VERCEL_URL in .env once you have it after the first deploy.
import os

def _base_url() -> str:
    return os.getenv("VERCEL_URL", "https://commute-radio.vercel.app").rstrip("/")


def generate_feed(
    episode_title: str,
    script: str,
    mp3_filename: str,
    mp3_size_bytes: int,
    duration_seconds: int,
    output_path: Path,
) -> Path:
    """
    Write a podcast RSS feed XML file for today's single episode.

    Args:
        episode_title:    Human-readable episode title (e.g. "March 27 · Afternoon Briefing")
        script:           The full text of the radio script (used as episode description)
        mp3_filename:     Filename of the MP3 (e.g. "episode_20260327.mp3")
        mp3_size_bytes:   File size in bytes (required by the RSS spec for <enclosure>)
        duration_seconds: Approximate duration in seconds (for podcast apps to display)
        output_path:      Where to write the feed.xml file

    Returns:
        Path to the written feed.xml
    """
    base_url = _base_url()
    mp3_url = f"{base_url}/audio/{mp3_filename}"
    pub_date = format_datetime(datetime.now(timezone.utc))

    # Escape any characters that would break the XML
    safe_script = (
        script
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        [:2000]  # cap description length for podcast app compatibility
    )
    safe_title = episode_title.replace("&", "&amp;").replace("<", "&lt;")

    # The GUID uniquely identifies this episode. Using the date ensures the
    # podcast app recognises it as new content each day even if the title is similar.
    guid = f"commute-radio-{datetime.now().strftime('%Y%m%d')}"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:content="http://purl.org/rss/1.0/modules/content/">

  <channel>
    <title>Commute Radio</title>
    <link>{base_url}</link>
    <description>Your personalised daily market briefing from X.</description>
    <language>en-us</language>
    <lastBuildDate>{pub_date}</lastBuildDate>

    <itunes:author>Commute Radio</itunes:author>
    <itunes:summary>Daily briefing scraped from your X accounts, summarised by Claude, and read aloud for your commute.</itunes:summary>
    <itunes:category text="Business">
      <itunes:category text="Investing"/>
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>

    <item>
      <title>{safe_title}</title>
      <description>{safe_script}</description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
      <enclosure
        url="{mp3_url}"
        length="{mp3_size_bytes}"
        type="audio/mpeg"/>
      <itunes:duration>{duration_seconds}</itunes:duration>
      <itunes:summary>{safe_script}</itunes:summary>
    </item>

  </channel>
</rss>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml, encoding="utf-8")
    return output_path
