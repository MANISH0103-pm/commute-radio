"""
summarizer.py — The News Editor
---------------------------------
Takes a raw list of XPost objects and uses Claude (via the Anthropic API) to:
  1. Read and understand all text posts.
  2. Look at any attached images and describe what's in them.
  3. Write a concise, conversational radio-style summary you'd enjoy during a commute.

Think of this as the editor who sits between the field reporter (scraper.py)
and the voice booth (audio.py). They turn raw notes into broadcast-ready copy.
"""

import base64
import os
from typing import Optional

import httpx
from anthropic import AsyncAnthropic

from scraper import XPost


client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# ── Image helper ──────────────────────────────────────────────────────────────

async def _fetch_image_b64(url: str) -> Optional[str]:
    """Download an image and return it as a base64 string for Claude's vision."""
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.get(url)
            r.raise_for_status()
            return base64.standard_b64encode(r.content).decode()
    except Exception:
        return None


# ── Per-post summariser ───────────────────────────────────────────────────────

async def summarize_post(post: XPost) -> str:
    """
    Produce a one-to-two sentence radio-friendly summary of a single post.
    If the post contains images, Claude will describe them too.
    """
    # Build the message content — text first, then images
    content: list = [
        {
            "type": "text",
            "text": (
                f"This is a post by @{post.author} posted at {post.timestamp}.\n\n"
                f"Post text:\n{post.text or '(no text)'}\n\n"
                f"Engagement: {post.likes:,} likes · {post.retweets:,} retweets\n\n"
                "Please summarise this post in 1–2 casual, conversational sentences "
                "suitable for a morning commute radio segment. "
                "If there are images, describe what you see in them briefly."
            ),
        }
    ]

    for img_url in post.image_urls[:2]:  # cap at 2 images per post
        b64 = await _fetch_image_b64(img_url)
        if b64:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": b64,
                    },
                }
            )

    response = await client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text.strip()


# ── Full radio script builder ─────────────────────────────────────────────────

async def build_radio_script(
    posts: list[XPost],
    handle: str,
    style: str = "upbeat morning radio host",
) -> str:
    """
    Take a list of summarised posts and stitch them into a full radio script.

    Args:
        posts:  List of XPost objects from the scraper.
        handle: The X username being summarised (for context).
        style:  Personality/tone instruction for Claude.

    Returns:
        A string of broadcast-ready text ready to be spoken by ElevenLabs.
    """
    post_summaries = []
    for i, post in enumerate(posts, 1):
        summary = await summarize_post(post)
        post_summaries.append(f"{i}. {summary}")

    joined = "\n".join(post_summaries)

    script_prompt = (
        f"You are a {style}. Below are summaries of recent posts from @{handle} on X.\n\n"
        f"{joined}\n\n"
        "Write a flowing, engaging 60–90 second radio segment that covers the highlights. "
        "Open with a catchy intro mentioning @{handle}. "
        "Transition naturally between topics. "
        "End with a brief sign-off. "
        "Write ONLY the spoken words — no stage directions, no asterisks, no markdown. "
        "Keep it warm, human, and listenable."
    )

    response = await client.messages.create(
        model="claude-opus-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": script_prompt}],
    )
    return response.content[0].text.strip()
