# Changelog

All notable changes to Commute Radio are documented here.

---

## [1.1.0] - 2026-03-29

### Added
- 3PM daily auto-trigger via macOS launchd (`scheduler/com.commute-radio.plist`)
- `scheduler/setup.sh` — one-command installer for the daily trigger
- `public/index.html` — landing page at commute-radio.vercel.app
- `public/feed.xml` — RSS feed committed to repo so Vercel can serve it

### Fixed
- Vercel CLI deploy: use full binary path (`~/.npm-global/bin/vercel`)
- Vercel CLI deploy: skip feed.xml copy if source and destination are the same file
- Vercel CLI deploy: parse deployed URL from `Aliased:` line in CLI output
- Vercel build: set `framework: null` and `buildCommand: null` to prevent Python app detection
- `.gitignore`: changed `public/` to `public/audio/` so static files are tracked by git
- `.gitignore`: exclude `.vercel/` directory auto-created by `vercel link`

---

## [1.0.0] - 2026-03-28

### Added
- `scraper.py` — Playwright-based X scraper for regular tweets and subscriber-only X Articles
- `summarizer.py` — Claude claude-opus-4-6 radio script generator from scraped posts
- `audio.py` — edge-tts text-to-speech (free, Microsoft neural voices, no API key)
- `feed.py` — Podcast RSS feed generator (single daily episode, Apple Podcasts compatible)
- `deploy.py` — Vercel deployment pipeline (stages MP3 + feed.xml, runs Vercel CLI)
- `run.py` — Single entry point chaining all pipeline steps
- `vercel.json` — Vercel static hosting config with RSS and audio headers
- `.env.example` — Template for all required environment variables
- `DECISIONS.md` — 16 architectural decisions documented
- `CLAUDE.md` — Project memory for Claude Code
- `README.md` — Full setup and usage documentation

### Architecture decisions
- Cookie-based X authentication (Cookie-Editor Chrome extension) — avoids bot detection
- X Articles extracted via standalone article URL + Draft.js selectors
- edge-tts chosen over ElevenLabs for zero cost
- Vercel free tier for podcast hosting (RSS + MP3 publicly accessible)
- GitHub → Vercel auto-deploy for feed.xml; Vercel CLI for MP3 (too large for git)
- macOS launchd for scheduling (built into every Mac, no extra software)
- Single daily episode model — no archive, always today's content
- 3PM run window covering 8:30AM–3PM posts, ready for evening commute

---
