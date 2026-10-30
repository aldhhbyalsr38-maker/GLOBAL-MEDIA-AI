"""Create human-reviewable bilingual production packs from editorial plans.

This module deliberately does not claim to fact-check, translate, synthesize audio,
source licensed media, render video, or publish. It creates structured drafts only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _slug(value: str, fallback: str = "story") -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return (value[:48] or fallback)


def _duration_for(summary: str) -> int:
    # Short-form default; this is a target duration, not a runtime guarantee.
    words = len((summary or "").split())
    return 45 if words < 90 else 60


def build_production_pack(topic: dict[str, Any]) -> dict[str, Any]:
    title = str(topic.get("source_title") or topic.get("english", {}).get("working_title") or "Untitled story")
    summary = str(topic.get("english", {}).get("summary_for_writer") or "")
    sources = topic.get("corroborating_sources") or [{"source": topic.get("source"), "url": topic.get("source_url")}]
    flags = list(topic.get("quality_flags") or [])
    if len(sources) < 2 and "single_source_only" not in flags:
        flags.append("single_source_only")
    if len(summary.strip()) < 100 and "thin_source_summary" not in flags:
        flags.append("thin_source_summary")
    gate_pass = len(sources) >= 2 and len(summary.strip()) >= 100 and not flags
    duration = _duration_for(summary)

    en_script = [
        f"[HOOK — 0:00–0:05] {title}",
        "[CONTEXT — 0:05–0:18] Explain what happened, where, and when. Insert only facts confirmed by the source review.",
        f"[WHAT WE KNOW — 0:18–0:38] {summary or '[Add a concise summary after reading the source in full.]'}",
        "[WHY IT MATTERS — 0:38–0:52] Explain the practical or human significance. Support every claim with evidence.",
        "[UNCERTAINTY — 0:52–0:57] State what is not yet known; do not speculate.",
        "[CLOSE — 0:57–1:00] Ask one relevant question or invite viewers to follow for verified updates.",
    ]
    ar_script = [
        f"[الافتتاحية — 0:00–0:05] {title}",
        "[السياق — 0:05–0:18] اشرح ماذا حدث وأين ومتى، بعد التحقق من المصدر الأصلي.",
        "[ما نعرفه — 0:18–0:38] أضف هنا ملخصًا عربيًا أصيلًا بعد قراءة المصدر والتحقق من الوقائع؛ لا تستخدم ترجمة حرفية آلية.",
        "[لماذا يهم؟ — 0:38–0:52] وضّح الأثر العملي أو الإنساني مع إسناد كل ادعاء إلى دليل.",
        "[ما لا نعرفه — 0:52–0:57] اذكر المعلومات غير المؤكدة بوضوح وتجنب التخمين.",
        "[الخاتمة — 0:57–1:00] اطرح سؤالًا مرتبطًا بالموضوع أو ادعُ لمتابعة التحديثات الموثقة.",
    ]
    scenes = [
        {"time": "00:00-00:05", "purpose": "Hook", "visual": "Original motion graphic or licensed establishing visual", "on_screen_text": "The key question", "audio": "Opening line", "rights": "Use owned, generated, or licensed assets only"},
        {"time": "00:05-00:18", "purpose": "Context", "visual": "Simple location/date/context graphic; avoid implying it is real footage", "on_screen_text": "Who • What • When • Where", "audio": "Verified context", "rights": "Cite source in description"},
        {"time": "00:18-00:38", "purpose": "Evidence", "visual": "Source-led chart, timeline, or clearly labeled illustration", "on_screen_text": "What the evidence says", "audio": "Confirmed facts", "rights": "Check chart/data reuse permissions"},
        {"time": "00:38-00:52", "purpose": "Impact", "visual": "Relevant licensed b-roll or original explanatory animation", "on_screen_text": "Why it matters", "audio": "Evidence-based impact", "rights": "No unlicensed news footage"},
        {"time": "00:52-01:00", "purpose": "Caveat and close", "visual": "Clean end card with source note", "on_screen_text": "What remains unknown", "audio": "Uncertainty + close", "rights": "No third-party logos without permission"},
    ]
    return {
        "schema_version": "0.3.0",
        "topic_rank": topic.get("rank"),
        "title": title,
        "source_url": topic.get("source_url"),
        "source_name": topic.get("source"),
        "related_sources": sources,
        "quality_gate": {
            "status": "ready_for_human_review" if gate_pass else "blocked_pending_verification",
            "passed": gate_pass,
            "flags": flags,
            "requirements": [
                "Read the complete original article.",
                "Verify the key claims against at least one genuinely independent reputable source.",
                "Confirm names, dates, figures, quotations, and context.",
                "Complete Arabic localization with a fluent reviewer.",
                "Clear rights for every image, clip, sound, and music asset.",
            ],
        },
        "target_formats": [
            {"platform": "YouTube Shorts", "aspect_ratio": "9:16", "target_duration_seconds": duration},
            {"platform": "TikTok", "aspect_ratio": "9:16", "target_duration_seconds": duration},
        ],
        "scripts": {"en_draft": en_script, "ar_localization_template": ar_script},
        "storyboard": scenes,
        "production_notes": [
            "All scripts are drafts based on RSS metadata; they are not independently verified.",
            "Do not present illustrative or AI-generated visuals as authentic documentary footage.",
            "Do not use copyrighted clips, images, or music without permission or a valid license.",
            "No voice generation, video rendering, or platform publishing occurs in V0.3.",
        ],
    }


def create_production_packs(plan_path: Path, output_dir: Path) -> list[Path]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    index = []
    for i, topic in enumerate(plan.get("topics", []), start=1):
        pack = build_production_pack(topic)
        slug = _slug(pack["title"], f"topic-{i}")
        topic_dir = output_dir / f"{i:02d}-{slug}"
        topic_dir.mkdir(parents=True, exist_ok=True)
        json_file = topic_dir / "production_pack.json"
        json_file.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
        md_lines = [f"# {pack['title']}", "", f"- Status: **{pack['quality_gate']['status']}**", f"- Source: {pack['source_url']}", "", "## English draft", ""]
        md_lines.extend(f"- {line}" for line in pack["scripts"]["en_draft"])
        md_lines += ["", "## Arabic localization template", ""]
        md_lines.extend(f"- {line}" for line in pack["scripts"]["ar_localization_template"])
        md_lines += ["", "## Storyboard", ""]
        for scene in pack["storyboard"]:
            md_lines.append(f"### {scene['time']} — {scene['purpose']}")
            md_lines.append(f"- Visual: {scene['visual']}")
            md_lines.append(f"- On-screen: {scene['on_screen_text']}")
            md_lines.append(f"- Audio: {scene['audio']}")
            md_lines.append(f"- Rights: {scene['rights']}")
            md_lines.append("")
        md_lines += ["## Quality gate", "", f"**{pack['quality_gate']['status']}**", ""]
        md_lines.extend(f"- [ ] {item}" for item in pack["quality_gate"]["requirements"])
        md_file = topic_dir / "production_pack.md"
        md_file.write_text("\n".join(md_lines), encoding="utf-8")
        created.extend([json_file, md_file])
        index.append({"rank": pack["topic_rank"], "title": pack["title"], "status": pack["quality_gate"]["status"], "path": str(topic_dir)})
    index_path = output_dir / "production_index.json"
    index_path.write_text(json.dumps({"version": "0.3.0", "items": index}, ensure_ascii=False, indent=2), encoding="utf-8")
    created.append(index_path)
    return created
