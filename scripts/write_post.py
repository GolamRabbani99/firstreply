#!/usr/bin/env python3
"""Daily blog writer for firstreply.dev.

Runs in GitHub Actions (see .github/workflows/daily-blog.yml):
takes the first unchecked topic from blog/topics.md, asks Claude to write
a humanised post following the house rules, renders blog/_TEMPLATE.html,
updates the blog index + sitemap + topic queue, and leaves the commit/push
to the workflow. Stdlib only — no pip installs.
"""

import datetime
import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
BLOG = ROOT / "blog"
MODEL = "claude-sonnet-4-6"
API_URL = "https://api.anthropic.com/v1/messages"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def call_claude(api_key: str, prompt: str, max_tokens: int = 6000) -> str:
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers={
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(b.get("text", "") for b in data.get("content", []))


def extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in model output")
    return text[start:end + 1]


def sanitize_inline(s: str) -> str:
    """Make a string safe for both HTML attributes and raw JSON-LD embedding."""
    s = s.replace('"', "’").replace("\\", "").replace("<", "").replace(">", "")
    s = s.replace("&amp;", "and").replace("&", "and")
    return s.strip()


def insert_after_marker(text: str, marker: str, block: str) -> str:
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if marker in line:
            return "".join(lines[: i + 1]) + block + "".join(lines[i + 1:])
    raise ValueError(f"Marker {marker!r} not found")


def main() -> None:
    api_key = os.environ["ANTHROPIC_API_KEY"].strip().lstrip("﻿")

    topics_path = BLOG / "topics.md"
    topics = topics_path.read_text(encoding="utf-8")
    today = datetime.date.today()
    iso = today.isoformat()
    human = f"{today.day} {MONTHS[today.month - 1]} {today.year}"

    if f"published {iso}" in topics:
        print("A post was already published today. Nothing to do.")
        return

    m = re.search(r"^- \[ \] (.+)$", topics, re.M)
    if not m:
        print("Topic queue is empty.", file=sys.stderr)
        sys.exit(1)
    topic_line = m.group(1).strip()

    existing = sorted(p.stem for p in BLOG.glob("*.html")
                      if p.stem not in ("index", "_TEMPLATE"))

    prompt = f"""You write the blog for Firstreply (https://firstreply.dev), an AI automation agency
based in London working worldwide. Services: Meta Conversions API tracking fixes,
60-second speed-to-lead systems with human approval gates, Facebook/Instagram
lead-gen campaigns. Audience: owners of education, catering and hospitality/events
businesses running paid ads. Author voice: Golam Rabbani, ex-Digital Marketing
Manager (5+ years Meta ads), MSc Computer Network & System Security — practical,
warm, direct, zero hype.

Write today's post on this topic:
{topic_line}

HARD RULES
- British English, first person singular (Golam's voice).
- 900-1,300 words. Varied sentence length. Open with a concrete scene or number,
  never a definition or "In today's world".
- Banned words/phrases: revolutionise, unleash, supercharge, game-changer, delve,
  elevate, seamless, cutting-edge, "in today's fast-paced world".
- Include at least one honest "you can do this yourself without us" moment.
- NO invented statistics, NO fake client stories or testimonials. The only real
  client you may mention is Diji Catering (London caterer; first-response time
  went from 4 hours to 60 seconds with human-approved AI replies).
- Include exactly one inline link to /#book somewhere natural in the body
  (anchor text about the free 15-minute Lead Leak Audit), plus 1-2 links to
  existing posts ONLY from this list of slugs (link as /blog/SLUG): {existing}
- Body HTML may use only: <h2>, <h3>, <p>, <ul>, <ol>, <li>, <blockquote>,
  <strong>, <em>, <a>. No <h1>, no <script>, no <img>, no inline styles.

Respond with ONLY a JSON object (no markdown fences, no commentary):
{{
  "slug": "kebab-case-from-target-keyword",
  "post_title": "the H1 / og title",
  "meta_title": "SEO title, 60 chars max, include a searchable keyword",
  "meta_description": "150 chars max, compelling, plain",
  "teaser": "one-sentence card teaser, 25 words max",
  "body_html": "the full article body HTML"
}}"""

    raw = call_claude(api_key, prompt)
    post = json.loads(extract_json(raw))

    # ── validation ─────────────────────────────────────────────────────────
    slug = post["slug"].strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        sys.exit(f"Bad slug: {slug!r}")
    if slug in existing:
        sys.exit(f"Slug already exists: {slug}")
    title = sanitize_inline(post["post_title"])
    meta_title = sanitize_inline(post["meta_title"])[:60]
    meta_desc = sanitize_inline(post["meta_description"])[:155]
    teaser = sanitize_inline(post["teaser"])
    body = post["body_html"].strip()
    if "<script" in body.lower() or "{{" in body:
        sys.exit("Body failed safety checks")
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    if not 600 <= words <= 1800:
        sys.exit(f"Body length out of range: {words} words")
    read_time = max(3, round(words / 200))

    # ── render post ────────────────────────────────────────────────────────
    template = (BLOG / "_TEMPLATE.html").read_text(encoding="utf-8")
    template = re.sub(r"<!-- ═+.*?═+ -->\n?", "", template, flags=re.S)  # drop instructions
    html = template
    for key, val in {
        "{{META_TITLE}}": meta_title,
        "{{META_DESCRIPTION}}": meta_desc,
        "{{POST_TITLE}}": title,
        "{{SLUG}}": slug,
        "{{ISO_DATE}}": iso,
        "{{HUMAN_DATE}}": human,
        "{{READ_TIME}}": str(read_time),
        "{{POST_BODY_HTML}}": body,
    }.items():
        html = html.replace(key, val)
    if "{{" in html:
        sys.exit("Unreplaced placeholder left in post")
    # JSON-LD must still parse after substitution
    ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    json.loads(ld.group(1))
    (BLOG / f"{slug}.html").write_text(html, encoding="utf-8", newline="\n")

    # ── blog index card ────────────────────────────────────────────────────
    card = f"""    <article class="post-card">
      <span class="pdate">{human} · {read_time} min read</span>
      <h2><a href="/blog/{slug}">{title}</a></h2>
      <p>{teaser}</p>
      <span class="more"><a href="/blog/{slug}">Read the post →</a></span>
    </article>
"""
    index_path = BLOG / "index.html"
    index_path.write_text(
        insert_after_marker(index_path.read_text(encoding="utf-8"),
                            "POSTS:INSERT_BELOW", card),
        encoding="utf-8", newline="\n")

    # ── sitemap ────────────────────────────────────────────────────────────
    entry = (f"  <url>\n    <loc>https://firstreply.dev/blog/{slug}</loc>\n"
             f"    <priority>0.6</priority>\n  </url>\n")
    sm_path = ROOT / "sitemap.xml"
    sm_path.write_text(
        insert_after_marker(sm_path.read_text(encoding="utf-8"),
                            "POSTS:INSERT_BELOW", entry),
        encoding="utf-8", newline="\n")

    # ── tick topic, replenish queue if low ─────────────────────────────────
    topics = topics.replace(f"- [ ] {topic_line}",
                            f"- [x] {topic_line} — published {iso}", 1)
    remaining = len(re.findall(r"^- \[ \] ", topics, re.M))
    if remaining < 5:
        more_raw = call_claude(api_key, (
            "Suggest 10 new blog topics for Firstreply, an AI automation agency "
            "(Meta ads tracking, speed-to-lead, lead nurture) writing for education, "
            "catering and events business owners. Specific, search-intent driven, "
            "not covered by these existing ones:\n" + topics +
            '\nRespond with ONLY a JSON array of strings, each formatted like: '
            '"Topic title here (keyword: target search phrase)"'), 2000)
        try:
            new_topics = json.loads(extract_json(more_raw.replace("[", "{", 1).replace("]", "}", 1)))
        except Exception:
            new_topics = None
        if new_topics is None:
            try:
                arr = re.search(r"\[.*\]", more_raw, re.S)
                new_topics = json.loads(arr.group(0)) if arr else []
            except Exception:
                new_topics = []
        additions = "".join(f"- [ ] {sanitize_inline(t)}\n" for t in new_topics if isinstance(t, str))
        if additions:
            topics = topics.rstrip("\n") + "\n" + additions
    topics_path.write_text(topics, encoding="utf-8", newline="\n")

    # commit message for the workflow step
    (ROOT / ".post_title").write_text(title, encoding="utf-8")
    print(f"Wrote blog/{slug}.html ({words} words, {read_time} min read)")


if __name__ == "__main__":
    main()
