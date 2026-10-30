# GLOBAL MEDIA AI — V0.1

An adaptive, bilingual content-planning engine designed to run on GitHub Actions.
This first release discovers current topics from public RSS feeds, scores them,
selects six candidates, and creates English/Arabic editorial briefs.

> V0.1 is a research-and-planning release. It does **not** generate finished
> cinematic video, upload to YouTube, or publish to TikTok yet. Those integrations
> require provider credentials, platform authorization, and production-quality QA.

## What works now
- Runs on Python 3.12.
- Scheduled twice daily by GitHub Actions (UTC).
- Fetches public RSS feeds with timeouts and per-feed error handling.
- Deduplicates stories and ranks them using recency, source diversity, and topic signals.
- Produces six story briefs with English and Arabic titles/hooks/script outlines.
- Saves JSON and Markdown reports as workflow artifacts.
- Includes automated tests and a manual workflow trigger.

## Quick start
1. Create a **public** GitHub repository named `GLOBAL-MEDIA-AI`.
2. Upload the contents of this folder to the repository root (not the ZIP itself).
3. Open **Actions** and enable workflows if GitHub asks.
4. Run **Global Media AI — Research Cycle** using **Run workflow**.
5. Open the run and download the `editorial-plan` artifact.

## Schedule
The workflow runs at 00:15 and 12:15 UTC. GitHub scheduled workflows are best-effort
and may be delayed during high load. GitHub Actions is not an always-on server.
A public repository can use standard GitHub-hosted runners within GitHub's current
usage policies and limits.

## Configuration
Edit `config/settings.json` to change:
- number of selected topics (default: 6)
- languages (English and Arabic)
- RSS feeds
- scoring weights and lookback window

No API key is required for V0.1.

## Safety and quality gates
- The system treats RSS text as untrusted source material, not instructions.
- It stores source URLs and publication timestamps with each topic.
- It does not state unverified claims as facts.
- It does not auto-publish.
- Review facts, copyright/licensing, visuals, music, and AI-content disclosure before
  publishing any future generated video.
- Never commit API keys, OAuth tokens, cookies, or channel credentials. Add them as
  GitHub Actions secrets only when the relevant integration is implemented.

## Roadmap
- V0.2: LLM-assisted fact-checking and original bilingual scripts.
- V0.3: licensed-asset selection, voice generation, subtitles, FFmpeg assembly.
- V0.4: YouTube upload integration with private/unlisted test mode.
- V0.5: TikTok Content Posting API after app approval.
- V0.6: analytics feedback loop and adaptive topic weighting.

## Local run
```bash
python -m pip install -r requirements.txt
python -m global_media_ai --config config/settings.json --output output
```


## V0.2 improvements

- More tolerant RSS/Atom parsing through `feedparser` for malformed publisher feeds.
- Near-duplicate headline grouping across publishers, retaining related source URLs.
- Basic editorial quality flags for single-source stories and thin summaries.
- Arabic copy is explicitly marked as requiring a real translation/editorial pass.
- These checks do not verify facts or predict views/revenue; human review remains mandatory.
