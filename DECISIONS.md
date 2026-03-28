# Commute Radio — Decision Log

A running record of every design, architecture, and requirements decision made during the build.
Each entry captures **what** was decided, **why**, and **what was ruled out**.

---

## D-001 · Language & Environment Manager
**Decision:** Python 3.11 + `uv` as the package manager
**Why:** `uv` is significantly faster than `pip`/`poetry` and handles virtual environments and dependency locking in one tool. Python chosen for its mature scraping and AI SDK ecosystem.
**Ruled out:** Node.js (weaker AI/scraping libraries), Poetry (slower than uv).

---

## D-002 · Server Framework
**Decision:** FastMCP (Python)
**Why:** Allows the project to expose tools (scrape, summarize, audio) as MCP-compatible functions callable directly from Claude or any MCP client. Keeps the architecture modular — each capability is a named tool, not a monolithic script.
**Ruled out:** Flask/FastAPI (no native MCP support), raw scripts (no reusability).

---

## D-003 · X (Twitter) Scraping Method
**Decision:** Playwright headless browser — no X API key required
**Why:** X's API pricing makes it prohibitively expensive for personal use. Playwright drives a real Chromium browser, which executes JavaScript and renders posts exactly as a logged-in human would see them — including subscriber-only content.
**Ruled out:** X Developer API (too expensive), `requests`+`BeautifulSoup` (fails on JavaScript-rendered pages), third-party scraping services (cost + privacy risk).

---

## D-004 · X Authentication Method
**Decision:** Export real Chrome browser cookies via Cookie-Editor extension, load into Playwright
**Why:** X's bot detection blocks programmatic login attempts from headless browsers (confirmed in testing — received "Could not log you in now" error). Real browser cookies are indistinguishable from a live human session.
**Process:** User installs Cookie-Editor (by cgagnier.ca, ID: hlkenndednhfkekhgcdicdfddnkalmdm), exports cookies from x.com as JSON, saves to `x_cookies.json` in project root.
**Ruled out:** Programmatic login flow (blocked by X bot detection), X API OAuth (requires paid developer access).
**Security note:** `x_cookies.json` is gitignored and never committed. Cookies must be re-exported when the session expires.

---

## D-005 · Handling X Articles (Subscriber Long-Form Posts)
**Decision:** Navigate to the standalone article URL (`/handle/article/post_id`) and extract body text using Draft.js selectors
**Why:** X Articles are not regular tweets. They appear as cards in the timeline but full content lives on a separate page. The article body is rendered by Draft.js (a rich-text editor framework), so standard tweet selectors (`div[dir="auto"]`) do not capture the body.
**Key selectors discovered:**
- Article detection: empty tweet text + thumbnail image in timeline card
- Standalone URL: `https://x.com/{handle}/article/{post_id}`
- Body text: `div[class*="public-DraftEditor-content"]` → `div[data-block="true"]` → `span[data-text="true"]`
- Title: first `div[dir="auto"]` on the article page
**Ruled out:** Scraping from tweet status URL (replies contaminate the body), `/i/articles/` link detection (X does not use this URL pattern).

---

## D-006 · AI Model for Summarisation & Scripting
**Decision:** Anthropic Claude (`claude-opus-4-6`) via the Anthropic Python SDK
**Why:** Claude produces high-quality, conversational prose well-suited to radio-style delivery. Claude Vision handles image description within the same API call, avoiding a second service.
**Ruled out:** OpenAI GPT (preference for Claude quality and existing API key), local models (insufficient quality for broadcast-ready scripts).

---

## D-007 · Text-to-Speech Engine
**Decision:** `edge-tts` (Microsoft Edge neural voices — free, no API key required)
**Why:** ElevenLabs produces superior voice quality but costs money beyond the free tier. `edge-tts` uses Microsoft's neural TTS engine (the same voices used in Windows/Edge), which is free, requires no account or API key, and produces natural-sounding output acceptable for a daily commute.
**Upgrade path:** ElevenLabs can be swapped in later by replacing the `audio.py` implementation if voice quality becomes a priority.
**Ruled out:** ElevenLabs (cost), macOS `say` command (robotic quality, AIFF format), Google Cloud TTS / Amazon Polly (require cloud accounts and setup).

---

## D-008 · Output Delivery Format
**Decision:** Personal Podcast RSS Feed
**Why:** The primary use case is a 2.5-hour daily car commute. A podcast feed integrates natively with Apple Podcasts and CarPlay — episodes appear automatically, play hands-free, download overnight for offline use, and resume if interrupted. A webpage requires opening a browser and tapping play manually, adding friction in a morning commute scenario.
**Ruled out:** Webpage with Web Speech API TTS button (works but higher friction, no offline support, no CarPlay), email/iMessage delivery (no streaming playback), local MP3 files on computer (not accessible on iPhone).

---

## D-009 · Podcast Feed Hosting
**Decision:** Vercel free tier
**Why:** Vercel's free tier supports static file hosting with no monthly cost, custom domains, HTTPS by default, and fast global CDN. The podcast RSS feed and MP3 files are static assets — no server-side compute needed at runtime.
**Ruled out:** GitHub Pages (no easy programmatic deploy from Python), AWS S3 (requires AWS account setup), self-hosting (requires always-on server).

---

## D-010 · Content Scope & Retention
**Decision:** Daily content only — no archive or history
**Why:** The product is a morning commute briefing. Yesterday's market commentary has no commute value. Keeping only today's content simplifies the feed structure and avoids storage costs growing over time.
**Implementation:** The RSS feed is overwritten daily with a single episode. No episode history is retained.

---

## D-011 · Image Handling
**Decision:** Claude Vision describes images inline within the radio script (when images are present)
**Why:** Charts, screenshots, and memes are a significant part of financial X accounts. Ignoring them loses context. Claude Vision receives the image as base64 and returns a spoken description that gets woven into the radio script naturally.
**Cost control:** Capped at 2 images per post to limit Vision API token usage.
**Test mode:** Images can be stripped (`post.image_urls = []`) for zero-cost test runs.

---

## D-012 · Target Accounts & Filtering
**Decision:** User-defined list of X handles; posts filtered to the current calendar day only
**Why:** The commute radio should summarise only what was posted since the previous commute — stale posts add noise. Day-scoped filtering ensures relevance.
**Retweet handling:** Only posts authored by the target handle are included. Retweets and quoted posts from other accounts are filtered out at the scraper level.

---

## D-014 · Scraping Schedule & Content Window
**Decision:** Single daily run at 3:00 PM, covering posts from 8:30 AM → 3:00 PM
**Why:** The primary use case is an **evening commute home** — a recap of what happened during the work day. A 3 PM run captures the active trading/posting window (US market hours roughly align) and gives ~5 minutes for the pipeline to complete before a typical end-of-day departure.
**Window rationale:** 8:30 AM start skips overnight noise (accounts are mostly inactive at night). 3 PM end gives a clean cut-off before market close volatility.
**Not chosen:** Morning run (user already catches up on news at home the previous evening), real-time scraping (unnecessary cost and bot-detection risk), evening run after market close (user is already home by then).

---

## D-016 · Post Volume Cap During Trial
**Decision:** No cap on number of posts scraped per account during the trial period
**Why:** Unknown how frequently each account posts. Capping at 20 during trial risks missing important posts. After 2-3 days of observation, a cap can be introduced if the episode length becomes unwieldy.
**Expected output length:** ~10-20 minutes of audio for 5-10 active accounts (based on ~130 words/minute TTS rate). This is a highlights reel — not intended to fill the full commute.
**Script tuning deferred to:** post dry-run, once actual episode lengths are observed.

---

## D-015 · Dry Run Period Before Finalising Schedule
**Decision:** Run the pipeline manually for 2-3 days before automating, then adjust
**Why:** The schedule, content window, number of posts, and script length are all estimates. A short observation period lets us tune:
- Whether 8:30 AM–3 PM captures the richest signals
- Whether ~20 posts per run produces the right episode length for the commute
- Whether edge-tts voice quality is acceptable for extended listening
- Whether 3 PM trigger gives enough buffer before the commute
**Automation deferred until:** dry run validates the pipeline end-to-end.

---

## D-013 · Security & Secret Management
**Decision:** All API keys stored in `.env` file (gitignored). Never hardcoded.
**Files protected:**
- `.env` — API keys (Anthropic, ElevenLabs, X credentials)
- `x_cookies.json` — X session cookies
- `.x_session.json` — fallback session cache
**Why:** Accidental key exposure in version control is a common and serious security incident. Gitignoring these files prevents them from ever being committed.
