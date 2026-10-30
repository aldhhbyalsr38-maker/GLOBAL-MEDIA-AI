from __future__ import annotations

import hashlib
import html
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

USER_AGENT = "GLOBAL-MEDIA-AI/0.1 (+https://github.com/)"


def clean_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(entry: Any) -> datetime:
    # feedparser exposes parsed time tuples for common RSS/Atom date fields.
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, key, None) if not isinstance(entry, dict) else entry.get(key)
        if parsed:
            try:
                return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                pass
    raw = (entry.get("published") or entry.get("updated") or "") if isinstance(entry, dict) else ""
    if raw:
        try:
            parsed = parsedate_to_datetime(raw)
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            pass
    # Unknown dates are deliberately treated as old rather than falsely "breaking".
    return datetime.now(timezone.utc) - timedelta(days=3650)


def fetch_feed(feed: dict, timeout: int) -> list[dict]:
    req = Request(feed["url"], headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        payload = response.read(2_000_000)
    # Standard-library parser supports common RSS 2.0 and Atom feeds; no runtime
    # dependency is needed, which keeps the GitHub Actions build lightweight.
    root = ET.fromstring(payload)
    entries = []
    for item in root.findall(".//item"):
        entries.append({
            "title": item.findtext("title", ""),
            "link": item.findtext("link", ""),
            "summary": item.findtext("description", ""),
            "published": item.findtext("pubDate", "")
        })
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for item in root.findall(".//atom:entry", ns):
        link_el = item.find("atom:link", ns)
        entries.append({
            "title": item.findtext("atom:title", "", ns),
            "link": (link_el.get("href", "") if link_el is not None else ""),
            "summary": item.findtext("atom:summary", "", ns) or item.findtext("atom:content", "", ns),
            "published": item.findtext("atom:published", "", ns) or item.findtext("atom:updated", "", ns)
        })
    results = []
    for e in entries:
        get = e.get if isinstance(e, dict) else lambda k, default="": getattr(e, k, default)
        title = clean_text(get("title", ""))
        link = (get("link", "") or "").strip()
        summary = clean_text(get("summary", "") or get("description", ""))
        if not title or not link.startswith(("http://", "https://")):
            continue
        results.append({
            "title": title[:300],
            "url": link,
            "summary": summary[:1200],
            "published_at": parse_date(e).isoformat(),
            "source": feed["name"],
            "source_weight": float(feed.get("weight", 1.0))
        })
    return results


def classify_topic(text: str, signals: dict) -> list[str]:
    low = text.casefold()
    matches = []
    for category, terms in signals.items():
        if any(term.casefold() in low for term in terms):
            matches.append(category)
    return matches or ["general"]


def score_story(story: dict, now: datetime, lookback_hours: int, signals: dict) -> dict:
    published = datetime.fromisoformat(story["published_at"])
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_hours = max(0.0, (now - published).total_seconds() / 3600)
    recency = max(0.0, 1.0 - age_hours / max(lookback_hours, 1))
    text = f"{story['title']} {story['summary']}"
    categories = classify_topic(text, signals)
    # Transparent baseline score; this is a prioritization heuristic, not a virality prediction.
    score = (recency * 60.0) + (min(len(categories), 3) * 5.0) + (story["source_weight"] * 10.0)
    story.update({
        "age_hours": round(age_hours, 2),
        "categories": categories,
        "score": round(score, 2),
        "score_note": "Recency + topic-signal coverage + configured source weight; not a view forecast."
    })
    return story


def make_bilingual_brief(story: dict, rank: int) -> dict:
    title = story["title"]
    summary = story["summary"] or "No publisher summary supplied; research is required before scripting."
    return {
        "rank": rank,
        "source_title": title,
        "source": story["source"],
        "source_url": story["url"],
        "published_at": story["published_at"],
        "score": story["score"],
        "categories": story["categories"],
        "editorial_status": "research_required",
        "fact_check_checklist": [
            "Open the original source and verify the complete context.",
            "Find at least one independent, reputable corroborating source.",
            "Verify names, dates, numbers, locations, and quoted statements.",
            "Separate confirmed facts from interpretation and uncertainty.",
            "Check image/video/music rights before production."
        ],
        "english": {
            "working_title": title,
            "hook_draft": f"What happened, why does it matter, and what should viewers understand about {title.rstrip('.?')}?",
            "summary_for_writer": summary,
            "format_suggestion": "Explain the verified context first, then the human or practical impact.",
            "script_outline": [
                "0–10s: Specific hook; do not exaggerate or promise unsupported revelations.",
                "10–30s: Establish who/what/when/where using verified facts.",
                "Main section: Explain causes, evidence, context, and competing interpretations where relevant.",
                "Ending: State what remains unknown and why the story matters."
            ]
        },
        "arabic": {
            "working_title": f"مسودة عنوان عربي: {title}",
            "hook_draft": "ما الذي حدث؟ ولماذا يستحق هذا الموضوع اهتمامنا الآن؟",
            "summary_for_writer": "أعد صياغة الملخص بالعربية بعد مراجعة المصدر الأصلي؛ لا تعتمد على ترجمة آلية حرفية.",
            "format_suggestion": "سرد عربي طبيعي يشرح السياق والأثر الإنساني أو العملي.",
            "script_outline": [
                "0–10 ثوانٍ: افتتاحية محددة وجذابة بلا تهويل.",
                "10–30 ثانية: توضيح من وماذا ومتى وأين وفق معلومات موثقة.",
                "المتن: شرح الأسباب والأدلة والسياق وما لا يزال غير مؤكد.",
                "الخاتمة: تلخيص الأهمية وذكر حدود المعلومات المتاحة."
            ]
        }
    }


def build_plan(config: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    lookback = int(config.get("lookback_hours", 48))
    timeout = int(config.get("request_timeout_seconds", 15))
    all_stories, feed_errors = [], []
    for feed in config.get("feeds", []):
        try:
            all_stories.extend(fetch_feed(feed, timeout))
        except (HTTPError, URLError, TimeoutError, OSError, ET.ParseError, Exception) as exc:
            feed_errors.append({"source": feed.get("name", "unknown"), "error": str(exc)[:300]})
    seen, unique = set(), []
    for story in all_stories:
        key = hashlib.sha256(story["url"].split("?")[0].encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(story)
    cutoff = now - timedelta(hours=lookback)
    fresh = []
    for story in unique:
        published = datetime.fromisoformat(story["published_at"])
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published >= cutoff:
            fresh.append(score_story(story, now, lookback, config.get("topic_signals", {})))
    fresh.sort(key=lambda x: (x["score"], x["published_at"]), reverse=True)
    selected = fresh[:int(config.get("max_topics", 6))]
    topics = [make_bilingual_brief(item, i + 1) for i, item in enumerate(selected)]
    return {
        "project": config.get("project_name", "GLOBAL MEDIA AI"),
        "version": config.get("version", "0.1.0"),
        "generated_at": now.isoformat(),
        "lookback_hours": lookback,
        "status": "research_ready" if topics else "no_recent_topics",
        "topics_found": len(fresh),
        "topics": topics,
        "feed_errors": feed_errors,
        "limitations": [
            "RSS coverage is incomplete and varies by publisher.",
            "Ranking is a transparent heuristic, not a prediction of virality or revenue.",
            "Editorial briefs are drafts; fact-checking and rights review are mandatory.",
            "Arabic fields are editorial prompts, not a completed translation."
        ]
    }


def write_outputs(plan: dict, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "editorial_plan.json"
    md_path = output_dir / "editorial_plan.md"
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        f"# {plan['project']} — Editorial plan",
        "",
        f"- Generated: {plan['generated_at']}",
        f"- Status: {plan['status']}",
        f"- Topics found in lookback: {plan['topics_found']}",
        f"- Selected: {len(plan['topics'])}",
        "",
        "> Draft planning output only. Verify facts and rights before production or publication.",
        ""
    ]
    for item in plan["topics"]:
        lines += [
            f"## {item['rank']}. {item['source_title']}",
            f"- Source: [{item['source']}]({item['source_url']})",
            f"- Score: {item['score']} (heuristic, not a virality forecast)",
            f"- Categories: {', '.join(item['categories'])}",
            "",
            "### English",
            f"**Working title:** {item['english']['working_title']}",
            f"**Hook draft:** {item['english']['hook_draft']}",
            f"**Summary:** {item['english']['summary_for_writer']}",
            "",
            "### العربية",
            f"**عنوان عمل:** {item['arabic']['working_title']}",
            f"**افتتاحية:** {item['arabic']['hook_draft']}",
            f"**ملاحظة:** {item['arabic']['summary_for_writer']}",
            "",
            "### Fact-check before production"
        ]
        lines.extend(f"- [ ] {task}" for task in item["fact_check_checklist"])
        lines.append("")
    if plan["feed_errors"]:
        lines += ["## Feed errors", ""]
        lines.extend(f"- {e['source']}: {e['error']}" for e in plan["feed_errors"])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
