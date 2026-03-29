"""
deploy.py — The Transmitter
-----------------------------
Pushes the generated MP3 and RSS feed.xml to Vercel so they are publicly
accessible from your iPhone / Apple Podcasts.

How it works:
  1. Copies the MP3 and feed.xml into a `public/` folder structure.
  2. Runs `vercel --prod` via the Vercel CLI to deploy those files.
  3. The RSS feed URL becomes: https://<your-project>.vercel.app/feed.xml
  4. The MP3 URL becomes:      https://<your-project>.vercel.app/audio/<filename>.mp3

Prerequisites (one-time setup):
  - Node.js installed (already confirmed)
  - Run: npm install -g vercel
  - Run: vercel login   (opens browser, authenticate once)
  - Run: vercel link    (inside commute-radio/ — links this folder to a Vercel project)
"""

import os
import shutil
import subprocess
from pathlib import Path


# Where the files Vercel will serve live locally
PUBLIC_DIR = Path("public")
AUDIO_DIR = PUBLIC_DIR / "audio"


def stage_files(mp3_path: Path, feed_path: Path) -> None:
    """
    Copy the MP3 and feed.xml into the public/ directory so Vercel can serve them.

    Think of public/ as the shelf in a shop window — only what's on the shelf
    gets displayed. We put our files there before opening the shop (deploying).
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # Copy MP3 to public/audio/<filename>
    dest_mp3 = AUDIO_DIR / mp3_path.name
    shutil.copy2(mp3_path, dest_mp3)

    # Copy feed.xml to public/feed.xml (skip if already there)
    dest_feed = PUBLIC_DIR / "feed.xml"
    if feed_path.resolve() != dest_feed.resolve():
        shutil.copy2(feed_path, dest_feed)

    print(f"  Staged: {dest_mp3}")
    print(f"  Staged: {dest_feed}")


def deploy() -> str:
    """
    Run `vercel --prod` to push the public/ directory live.

    Returns the deployed URL (e.g. https://commute-radio.vercel.app).
    Raises RuntimeError if the deploy fails.
    """
    print("  Running: vercel --prod ...")

    vercel_bin = os.path.expanduser("~/.npm-global/bin/vercel")
    result = subprocess.run(
        [vercel_bin, "--prod", "--yes"],   # --yes skips confirmation prompts
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Vercel deploy failed:\n{result.stderr or result.stdout}"
        )

    # Extract the stable production URL from "Aliased: <url>" line
    url = "https://commute-radio.vercel.app"
    for line in result.stdout.splitlines():
        if "Aliased:" in line:
            url = line.split("Aliased:")[-1].strip().split()[0]
            break
    print(f"  Deployed to: {url}")
    return url


def push(mp3_path: Path, feed_path: Path) -> str:
    """
    Full deploy: stage files then push to Vercel.

    Args:
        mp3_path:  Path to the generated .mp3 file
        feed_path: Path to the generated feed.xml file

    Returns:
        The live Vercel URL
    """
    print("Deploying to Vercel...")
    stage_files(mp3_path, feed_path)
    return deploy()
