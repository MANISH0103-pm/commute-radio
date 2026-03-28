"""
server.py — The Control Room (Main MCP Server)
------------------------------------------------
This is the heart of the project. It creates an MCP (Model Context Protocol)
server using FastMCP — think of MCP as a universal plug adapter that lets AI
assistants like Claude call your custom tools.

When you connect this server to Claude Desktop or any MCP-compatible app,
Claude gains three new "superpowers" (tools):

  1. scrape_x_profile  — fetches recent posts from any public X account
  2. generate_radio_script — turns those posts into a broadcast-ready script
  3. create_audio_segment  — converts the script to an .mp3 you can play

The flow for your commute:
  Claude → scrape_x_profile("ycombinator")
        → generate_radio_script(posts)
        → create_audio_segment(script)
        → 🎧 Play MP3 on your phone
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP

# Load .env file so our API keys are available as environment variables
load_dotenv()

# ── Lazy imports (loaded only when first tool is called) ──────────────────────
# We import here rather than at top-level so the server starts instantly even
# before all dependencies are confirmed working.
from scraper import scrape_profile, XPost
from summarizer import build_radio_script
from audio import text_to_speech


# ── Create the MCP server ─────────────────────────────────────────────────────
# "commute-radio" is the name Claude will see when you connect this server.
mcp = FastMCP("commute-radio")


# ── Tool 1: Scrape X Profile ──────────────────────────────────────────────────

@mcp.tool()
async def scrape_x_profile(
    handle: str,
    max_posts: int = 10,
) -> list[dict]:
    """
    Scrape recent posts from a public X (Twitter) profile.

    Args:
        handle:    The X username WITHOUT the @ symbol. Example: "ycombinator"
        max_posts: Number of recent posts to fetch (1–20, default 10).

    Returns:
        A list of posts, each containing: post_id, author, text, timestamp,
        image_urls, likes, retweets, and a direct url to the post.
    """
    max_posts = max(1, min(max_posts, 20))  # clamp to sensible range
    posts = await scrape_profile(handle=handle, max_posts=max_posts)
    return [
        {
            "post_id": p.post_id,
            "author": p.author,
            "text": p.text,
            "timestamp": p.timestamp,
            "image_urls": p.image_urls,
            "likes": p.likes,
            "retweets": p.retweets,
            "url": p.url,
        }
        for p in posts
    ]


# ── Tool 2: Generate Radio Script ─────────────────────────────────────────────

@mcp.tool()
async def generate_radio_script(
    posts: list[dict],
    handle: str,
    style: str = "upbeat morning radio host",
) -> str:
    """
    Transform a list of scraped X posts into a spoken radio script.

    Args:
        posts:  The list returned by scrape_x_profile.
        handle: The X username (used for context in the script).
        style:  Personality tone — e.g. "calm podcast narrator", "energetic DJ",
                "dry British newsreader". Default: "upbeat morning radio host".

    Returns:
        A string of broadcast-ready text, 60–90 seconds when read aloud.
    """
    xposts = [
        XPost(
            post_id=p["post_id"],
            author=p["author"],
            text=p["text"],
            timestamp=p["timestamp"],
            image_urls=p.get("image_urls", []),
            likes=p.get("likes", 0),
            retweets=p.get("retweets", 0),
            url=p.get("url", ""),
        )
        for p in posts
    ]
    return await build_radio_script(posts=xposts, handle=handle, style=style)


# ── Tool 3: Create Audio Segment ──────────────────────────────────────────────

@mcp.tool()
async def create_audio_segment(
    script: str,
    filename: str = "",
) -> str:
    """
    Convert a radio script to an .mp3 file using ElevenLabs text-to-speech.

    Args:
        script:   The text to speak — typically the output of generate_radio_script.
        filename: Optional custom filename (e.g. "ycombinator_march25.mp3").
                  If omitted, a timestamped name is auto-generated.

    Returns:
        The absolute file path of the saved .mp3 file.
    """
    output_path = await text_to_speech(
        script=script,
        filename=filename or None,
    )
    return str(output_path.resolve())


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run in stdio mode — this is how Claude Desktop communicates with MCP servers.
    # Think of stdio as a direct phone line between Claude and this script.
    mcp.run(transport="stdio")
