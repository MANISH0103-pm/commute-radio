# Commute Radio

A personalized AI podcast that scrapes your favourite X (Twitter) accounts, summarises the posts using Claude, converts them to audio, and delivers a daily episode to Apple Podcasts on your iPhone — ready for your evening commute home.

---

## How It Works

```
Your Mac (runs at 3PM daily)
  ├── Playwright scrapes X accounts → posts (text + images)
  ├── Claude summarises posts → radio script
  ├── edge-tts converts script → .mp3
  └── Pushes MP3 + RSS feed → GitHub → Vercel (public URL)

Your iPhone
  └── Apple Podcasts subscribes to Vercel RSS URL
      └── New episode downloads automatically each day
          └── Play during evening commute via speakers or CarPlay
```

### Important: Where things run

| Component | Runs on | Why |
|---|---|---|
| Scraper (Playwright) | Your Mac | Needs your X login cookies — stays local |
| Claude summariser | Your Mac → Anthropic API | API call from your machine |
| Audio generation (edge-tts) | Your Mac | Free, local, no API key |
| MP3 + RSS feed | Vercel (cloud) | Must be publicly accessible for Apple Podcasts |

**Your Mac is the radio studio. GitHub and Vercel are the broadcast tower.** Scraping always happens locally — your credentials never leave your machine.

---

## Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| Scraping | Playwright + Chromium | Free |
| X Authentication | Browser cookies (Cookie-Editor export) | Free |
| Summarisation | Claude claude-opus-4-6 (Anthropic) | ~$5-9/month |
| Text-to-Speech | edge-tts (Microsoft neural voices) | Free |
| Podcast hosting | Vercel (static files) | Free |
| Automation | macOS launchd | Free (built into macOS) |

---

## Project Structure

```
commute-radio/
├── run.py              ← Single entry point — runs the full pipeline
├── scraper.py          ← Playwright X scraper (tweets + X Articles)
├── summarizer.py       ← Claude radio script writer
├── audio.py            ← edge-tts text-to-speech
├── feed.py             ← Podcast RSS feed generator
├── deploy.py           ← Pushes output to GitHub → Vercel
├── server.py           ← FastMCP server (exposes tools to Claude)
├── vercel.json         ← Vercel static hosting config
├── scheduler/
│   ├── com.commute-radio.plist  ← macOS 3PM daily trigger
│   └── setup.sh                 ← One-command scheduler setup
├── tests/
│   ├── test_scrape.py      ← Scraper test
│   └── test_pipeline.py    ← End-to-end pipeline test
├── .env.example        ← Template for environment variables
├── DECISIONS.md        ← Design and architecture decision log
└── CLAUDE.md           ← Project memory for Claude Code
```

---

## Setup

### 1. Prerequisites

- macOS (Apple Silicon)
- Python 3.11+ via `uv`
- Node.js (for Vercel CLI)
- A Vercel account connected to GitHub

### 2. Install dependencies

```bash
cd commute-radio
uv sync
uv run playwright install chromium
```

### 3. Configure environment variables

```bash
cp .env.example .env
open -a TextEdit .env
```

Fill in:
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `X_USERNAME` / `X_PASSWORD` — your X login
- `X_ACCOUNTS` — comma-separated handles to scrape (no @ symbol)
- `VERCEL_URL` — fill in after first deploy

### 4. Set up X authentication (cookies)

X blocks automated logins. Instead, we export your real browser session:

1. Log into x.com in Chrome
2. Install [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) (by cgagnier.ca)
3. On x.com, click the Cookie-Editor icon → Export → As JSON
4. Save to `~/commute-radio/x_cookies.json`

> **Note:** `x_cookies.json` is gitignored and never committed. If scraping stops working, your session has expired — repeat the export above (takes 2 minutes).

### 5. Run manually

```bash
uv run python run.py
```

### 6. Activate daily automation (optional)

```bash
bash scheduler/setup.sh
```

This registers a macOS launchd job that runs at 3:00 PM daily. Your Mac must be on or in sleep mode (not shut down). To stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.commute-radio.plist
```

### 7. Subscribe on iPhone

1. Open Apple Podcasts on your iPhone
2. Search → tap the search icon → paste your Vercel RSS URL:
   `https://your-project.vercel.app/feed.xml`
3. Subscribe — new episodes appear automatically each day

---

## Scraping Window

The pipeline runs at **3:00 PM** and covers posts from **8:30 AM – 3:00 PM** that day. This captures the active market/trading hours and is ready before your evening commute home.

---

## Cookie Expiry

X sessions expire periodically (typically every few weeks). If scraping stops working:

1. Log into x.com in Chrome
2. Cookie-Editor → Export → As JSON
3. Overwrite `x_cookies.json`

---

## Decisions & Design

See [DECISIONS.md](./DECISIONS.md) for the full record of architectural decisions made during the build — including what was ruled out and why.
