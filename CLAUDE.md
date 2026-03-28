# Commute Radio: Project Memory

## 🎯 Project Overview
A personalized automation tool that scrapes X (Twitter) posts, analyzes them (text + images), and generates high-quality audio summaries for a 2.5-hour daily commute.

## 🛠 Tech Stack
- **Language:** Python 3.14.3
- **Environment Manager:** uv (0.11.1)
- **Framework:** FastMCP (Python)
- **Scraper:** Playwright (Headless Browser)
- **Vision:** Claude 3.5 Sonnet (Vision API)
- **Voice:** ElevenLabs (TTS API)

## 📋 High-Level Workflow
1. **Scrape:** Use Playwright to visit X profiles and capture post content + screenshots.
2. **Analyze:** Use Claude Vision to describe screenshots (charts/images).
3. **Script:** Format the data into a "Radio Script" optimized for listening.
4. **Produce:** Send the script to ElevenLabs to generate a `.mp3` file.

## ⌨️ Common Commands
- **Environment:** `uv sync` (to install dependencies)
- **Run Server:** `uv run mcp-server.py`
- **Tests:** `uv run pytest`

## ⚖️ Coding Standards
- **Architectural Style:** Modular MCP tools.
- **Documentation:** Every function must have a docstring explaining the "why," not just the "how."
- **Safety:** Never hardcode API keys. Use a `.env` file.
- **Novice Friendly:** If you (Claude) write complex logic, add a `# COMMENT` block explaining it in plain English for a developer re-entering the field after 15 years.
