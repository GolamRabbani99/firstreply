#!/usr/bin/env python3
"""Static build for firstreply.dev.

Runs on Vercel (buildCommand) and locally. Copies the static site into dist/
and renders the blog from content/posts/*.md (edited via Pages CMS):

  content/posts/<slug>.md  ->  dist/blog/<slug>.html
                               dist/blog/index.html   (live posts, newest first)
                               dist/blog/archive.html (archived posts)
                               dist/sitemap.xml       (all pages + posts)

Frontmatter fields: title (required), date (YYYY-MM-DD), description, teaser,
archived (true/false). Body may be HTML (from the rich-text editor) or simple
markdown — both are handled. Stdlib only.
"""

import datetime
import html
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
POSTS = ROOT / "content" / "posts"
SITE = "https://firstreply.dev"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

STATIC_FILES = ["index.html", "privacy.html", "robots.txt", "llms.txt"]


# ── tiny markdown → HTML (only used when the body isn't already HTML) ──────
def md_to_html(md: str) -> str:
    def inline(s: str) -> str:
        s = html.escape(s, quote=False)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
                   r'<img src="\2" alt="\1" loading="lazy">', s)
        s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
        return s

    out, para, ul, ol = [], [], False, False

    def close_lists():
        nonlocal ul, ol
        if ul: out.append("</ul>"); ul = False
        if ol: out.append("</ol>"); ol = False

    def flush_para():
        nonlocal para
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_para(); close_lists(); continue
        if line.startswith("### "):
            flush_para(); close_lists(); out.append("<h3>" + inline(line[4:]) + "</h3>")
        elif line.startswith("## "):
            flush_para(); close_lists(); out.append("<h2>" + inline(line[3:]) + "</h2>")
        elif line.startswith("# "):
            flush_para(); close_lists(); out.append("<h2>" + inline(line[2:]) + "</h2>")
        elif line.startswith("> "):
            flush_para(); close_lists(); out.append("<blockquote>" + inline(line[2:]) + "</blockquote>")
        elif re.match(r"^[-*] ", line):
            flush_para()
            if ol: out.append("</ol>"); ol = False
            if not ul: out.append("<ul>"); ul = True
            out.append("<li>" + inline(line[2:]) + "</li>")
        elif re.match(r"^\d+\. ", line):
            flush_para()
            if ul: out.append("</ul>"); ul = False
            if not ol: out.append("<ol>"); ol = True
            out.append("<li>" + inline(re.sub(r"^\d+\. ", "", line)) + "</li>")
        else:
            close_lists(); para.append(line.strip())
    flush_para(); close_lists()
    return "\n".join(out)


def parse_post(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8").lstrip("﻿")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        sys.exit(f"{path.name}: missing frontmatter")
    meta, body = {}, m.group(2).strip()
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    if "title" not in meta or not meta["title"]:
        sys.exit(f"{path.name}: missing title")
    if not body:
        sys.exit(f"{path.name}: empty body")
    if not body.lstrip().startswith("<"):
        body = md_to_html(body)
    if "<script" in body.lower():
        sys.exit(f"{path.name}: scripts are not allowed in post bodies")

    date_s = meta.get("date", "")[:10]
    try:
        d = datetime.date.fromisoformat(date_s)
    except ValueError:
        d = datetime.date.fromtimestamp(path.stat().st_mtime)
    words = len(re.sub(r"<[^>]+>", " ", body).split())
    title = meta["title"]
    image = meta.get("image", "").strip()
    if image and not image.startswith(("/", "http")):
        image = "/" + image.lstrip("./")
    return {
        "image": image,
        "slug": re.sub(r"[^a-z0-9-]", "", path.stem.lower().replace(" ", "-").replace("_", "-")),
        "title": title,
        "meta_title": (meta.get("meta_title") or f"{title} | Firstreply")[:60],
        "description": (meta.get("description") or meta.get("teaser") or title)[:155],
        "teaser": meta.get("teaser") or meta.get("description") or "",
        "archived": meta.get("archived", "false").lower() in ("true", "yes", "1"),
        "date": d,
        "iso": d.isoformat(),
        "human": f"{d.day} {MONTHS[d.month - 1]} {d.year}",
        "read": max(2, round(words / 200)),
        "body": body,
    }


def render_post(template: str, p: dict) -> str:
    def j(s):  # safe for raw embedding inside the JSON-LD string values
        return json.dumps(s)[1:-1]
    esc_title = html.escape(p["title"], quote=True)
    featured = ""
    og_image = ""
    if p["image"]:
        featured = (f'\n  <img class="feature" src="{p["image"]}" '
                    f'alt="{esc_title}" fetchpriority="high">\n')
        og_image = f'<meta property="og:image" content="{SITE}{p["image"]}">'
    out = template
    for k, v in {
        "{{FEATURED_IMAGE}}": featured,
        "{{OG_IMAGE}}": og_image,
        "{{META_TITLE}}": html.escape(p["meta_title"], quote=True),
        "{{META_DESCRIPTION}}": html.escape(p["description"], quote=True),
        "{{POST_TITLE}}": html.escape(p["title"], quote=False),
        "{{SLUG}}": p["slug"],
        "{{ISO_DATE}}": p["iso"],
        "{{HUMAN_DATE}}": p["human"],
        "{{READ_TIME}}": str(p["read"]),
        "{{POST_BODY_HTML}}": p["body"],
    }.items():
        out = out.replace(k, v)
    # JSON-LD block gets JSON-escaped values instead of HTML-escaped ones
    ld_match = re.search(r'<script type="application/ld\+json">.*?</script>', out, re.S)
    ld = ld_match.group(0)
    ld_fixed = ld.replace(html.escape(p["meta_title"], quote=True), j(p["meta_title"])) \
                 .replace(html.escape(p["description"], quote=True), j(p["description"])) \
                 .replace(html.escape(p["title"], quote=False), j(p["title"]))
    out = out.replace(ld, ld_fixed)
    json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', out, re.S).group(1))
    assert "{{" not in out, f"unreplaced placeholder in {p['slug']}"
    return out


PAGE_SHELL = """<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#0B1522">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canon}">
<link rel="icon" href="data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E%3Crect%20width='32'%20height='32'%20rx='7'%20fill='%230B1522'/%3E%3Cpath%20d='M9%2023V9h14v4h-9v3h8v4h-8v3z'%20fill='%23FFB224'/%3E%3C/svg%3E">
<link rel="stylesheet" href="/blog/blog.css">
</head>
<body>
<header class="bhead">
  <nav class="bnav" aria-label="Blog navigation">
    <a class="blogo" href="/">firstreply<span>_</span></a>
    <ul class="bnav-links">
      <li class="hide-sm"><a href="/#system">Services</a></li>
      <li><a href="/blog/">Blog</a></li>
      <li><a class="cta" href="/#book">Book a free audit</a></li>
    </ul>
  </nav>
</header>

<main class="bwide">
  <div class="bhero">
    <h1>{h1}</h1>
    <p>{intro}</p>
  </div>

  <div class="post-list">
{cards}
  </div>
{extra}
</main>

<footer class="bfoot">
  <div class="bfoot-in">
    <span>© {year} Firstreply · Based in London, working worldwide</span>
    <span><a href="/">Home</a> · <a href="/blog/">Blog</a> · <a href="/privacy">Privacy</a></span>
  </div>
</footer>
</body>
</html>
"""

CARD = """    <article class="post-card">
{thumb}      <div class="post-card-body">
      <span class="pdate">{human} · {read} min read</span>
      <h2><a href="/blog/{slug}">{title}</a></h2>
      <p>{teaser}</p>
      <span class="more"><a href="/blog/{slug}">Read the post →</a></span>
      </div>
    </article>
"""

THUMB = ('      <a class="thumb" href="/blog/{slug}" tabindex="-1" aria-hidden="true">'
         '<img src="{image}" alt="" loading="lazy"></a>\n')


def cards_html(posts):
    out = []
    for p in posts:
        thumb = THUMB.format(slug=p["slug"], image=p["image"]) if p["image"] else ""
        out.append(CARD.format(thumb=thumb, human=p["human"], read=p["read"],
                               slug=p["slug"],
                               title=html.escape(p["title"], quote=False),
                               teaser=html.escape(p["teaser"], quote=False)))
    return "".join(out) or '    <p style="color:#51606F">Nothing here yet.</p>\n'


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "blog").mkdir(parents=True)

    # static site files
    for f in STATIC_FILES:
        shutil.copy2(ROOT / f, DIST / f)
    shutil.copy2(ROOT / "blog" / "blog.css", DIST / "blog" / "blog.css")
    if (ROOT / "blog" / "images").is_dir():
        shutil.copytree(ROOT / "blog" / "images", DIST / "blog" / "images")

    # posts
    template = (ROOT / "blog" / "_TEMPLATE.html").read_text(encoding="utf-8")
    template = re.sub(r"<!-- ═+.*?═+ -->\n?", "", template, flags=re.S)
    posts = sorted((parse_post(p) for p in POSTS.glob("*.md")),
                   key=lambda p: p["date"], reverse=True)
    slugs = [p["slug"] for p in posts]
    if len(slugs) != len(set(slugs)):
        sys.exit("duplicate post slugs")
    for p in posts:
        (DIST / "blog" / f"{p['slug']}.html").write_text(
            render_post(template, p), encoding="utf-8", newline="\n")

    live = [p for p in posts if not p["archived"]]
    archived = [p for p in posts if p["archived"]]

    # blog index
    extra = ""
    if archived:
        extra = ('  <p style="margin-top:2.5rem;color:#51606F">Looking for older posts? '
                 f'<a href="/blog/archive">Browse the archive ({len(archived)})</a>.</p>\n')
    (DIST / "blog" / "index.html").write_text(PAGE_SHELL.format(
        title="Blog — Lead Generation & Marketing Automation | Firstreply",
        desc="Practical notes on Facebook lead generation, speed-to-lead and marketing automation for education, catering and events businesses. No hype, no jargon.",
        canon=f"{SITE}/blog/", h1="Lead generation, answered properly.",
        intro="Practical notes on Facebook ads, speed-to-lead and marketing automation for education, catering and events businesses — written by a marketer who builds the systems, in plain English.",
        cards=cards_html(live), extra=extra,
        year=datetime.date.today().year), encoding="utf-8", newline="\n")

    # archive page
    (DIST / "blog" / "archive.html").write_text(PAGE_SHELL.format(
        title="Blog Archive | Firstreply",
        desc="Older posts from the Firstreply blog on lead generation, tracking and marketing automation.",
        canon=f"{SITE}/blog/archive", h1="The archive.",
        intro='Older posts we\'ve retired from the front page — still here, still readable. Back to <a href="/blog/">the latest posts</a>.',
        cards=cards_html(archived), extra="",
        year=datetime.date.today().year), encoding="utf-8", newline="\n")

    # sitemap
    urls = [(f"{SITE}/", "1.0"), (f"{SITE}/privacy", "0.2"), (f"{SITE}/blog/", "0.8")]
    urls += [(f"{SITE}/blog/{p['slug']}", "0.6") for p in posts]
    if archived:
        urls.append((f"{SITE}/blog/archive", "0.3"))
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, pr in urls:
        sm.append(f"  <url>\n    <loc>{loc}</loc>\n    <priority>{pr}</priority>\n  </url>")
    sm.append("</urlset>\n")
    (DIST / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8", newline="\n")

    print(f"Built {len(posts)} post(s) ({len(live)} live, {len(archived)} archived) -> dist/")


if __name__ == "__main__":
    main()
