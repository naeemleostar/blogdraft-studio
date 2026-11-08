"""Work on posts that are already on the site: refresh an old post, and add links from old posts to a new one."""
import datetime as dt
import html
import re

from .writer import RESEARCH_SYSTEM, sanitize_html, similar_posts, trim_meta

UPDATE_RESEARCH = """An article titled "{title}" was published on {date}. Today is {today}.
Its main points: {summary}

Use Google Search to find what has CHANGED or is NEW about this topic since {date}: new versions, prices, dates,
rules, features, numbers that are now different, and anything in the article that is now outdated.
Report only facts you found, each with its source name. If nothing important changed, say so clearly."""

UPDATE_PROMPT = """ARTICLE (HTML):
{content}

WHAT CHANGED (research notes):
{notes}

Suggest an update to this article using ONLY the research notes. Keep the author's text and voice; change only what
is outdated and add what is new. Return JSON:
{{"summary": ["what changes, one short line each"],
  "edits": [{{"find": "an exact sentence copied from the ARTICLE that is now wrong or outdated",
             "replace": "the corrected sentence"}}],
  "new_sections": [{{"after_heading": "exact text of an existing <h2> heading in the ARTICLE, or empty for the end",
                    "html": "<h2>…</h2><p>…</p> using only <h2>,<h3>,<p>,<ul>,<ol>,<li>,<strong>,<em>"}}],
  "meta_description": "updated meta description, 140-155 characters, or empty"}}
Return empty lists if nothing needs to change."""

LINK_PROMPT = """NEW ARTICLE: "{title}" — {summary}

Below are numbered paragraphs from an older article on the same blog. Pick the ONE paragraph where a link to the
new article would genuinely help a reader, and the exact words in it (2-6 words, copied exactly) to use as the link
text. If no paragraph fits naturally, return {{"p": -1}}.

{paras}

Return JSON: {{"p": paragraph number, "anchor": "exact words from that paragraph"}}"""


def plain(html_text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", html_text or "")).split())


# ----------------------------------------------------------------------------- refresh an old post

def research_changes(gemini, post: dict) -> tuple:
    date = (post.get("date") or "")[:10] or "an earlier date"
    prompt = UPDATE_RESEARCH.format(title=post["title"], date=date, today=dt.date.today().isoformat(),
                                    summary=plain(post.get("content", ""))[:1500])
    return gemini.research(prompt, RESEARCH_SYSTEM.format(niche="this topic"))


def suggest_update(writer, post: dict, notes: str) -> dict:
    content = re.sub(r"<!--.*?-->", "", post.get("content", ""), flags=re.S)       # block comments add bulk only
    data = writer.generate_json(UPDATE_PROMPT.format(content=content[:30000], notes=notes[:12000]), temperature=0.3)
    return data if isinstance(data, dict) else {}


def apply_update(content: str, plan: dict, note_date: str = "") -> tuple:
    """Apply suggested edits safely: an edit is used only if its sentence is found exactly. Returns (html, log)."""
    out, done = content, []
    for e in plan.get("edits") or []:
        find, repl = str(e.get("find", "")).strip(), str(e.get("replace", "")).strip()
        if find and repl and find in out:
            out = out.replace(find, html.escape(repl, quote=False) if "<" not in repl else repl, 1)
            done.append(f"Edited: {find[:80]}")
        elif find:
            done.append(f"Skipped (text not found exactly): {find[:80]}")
    for sec in plan.get("new_sections") or []:
        block = sanitize_html(str(sec.get("html", "")))
        if not block:
            continue
        head = str(sec.get("after_heading", "")).strip()
        pos = -1
        if head:
            m = re.search(r"<h2[^>]*>\s*" + re.escape(html.escape(head, quote=False)) + r"\s*</h2>", out) or \
                re.search(r"<h2[^>]*>\s*" + re.escape(head) + r"\s*</h2>", out)
            if m:
                nxt = re.search(r"<h2", out[m.end():])
                pos = m.end() + nxt.start() if nxt else len(out)
        if pos < 0:
            faq = re.search(r"<h2[^>]*>\s*(Frequently asked|FAQ|Sources)", out, re.I)
            pos = faq.start() if faq else len(out)
        out = out[:pos] + "\n" + block + "\n" + out[pos:]
        done.append(f"Added section after: {head or 'the main text'}")
    if note_date and done:
        out = f"<p><em>Updated on {html.escape(note_date)}.</em></p>\n" + out
    return out, done


# ----------------------------------------------------------------------------- links from old posts

def paragraphs(content: str) -> list:
    """Plain paragraphs (no links or other tags inside) that can safely receive a link."""
    out = []
    for m in re.finditer(r"<p>([^<]{80,})</p>", content):
        out.append((m.start(1), m.end(1), m.group(1)))
    return out


def suggest_link(writer, old_post: dict, new_title: str, new_summary: str) -> dict:
    paras = paragraphs(old_post.get("content", ""))[:40]
    if not paras:
        return {}
    listing = "\n".join(f"[{i}] {html.unescape(p[2])[:600]}" for i, p in enumerate(paras))
    data = writer.generate_json(LINK_PROMPT.format(title=new_title, summary=new_summary, paras=listing), temperature=0.2)
    try:
        i = int(data.get("p", -1))
    except (TypeError, ValueError, AttributeError):
        return {}
    anchor = str(data.get("anchor", "")).strip()
    if i < 0 or i >= len(paras) or not anchor:
        return {}
    text = paras[i][2]
    if anchor not in text and html.escape(anchor, quote=False) not in text:
        return {}
    return {"post_id": old_post["id"], "title": old_post["title"], "url": old_post.get("url", ""),
            "paragraph": html.unescape(text), "anchor": anchor, "index": i}


def insert_link(content: str, index: int, anchor: str, url: str) -> str:
    paras = paragraphs(content)
    if index >= len(paras):
        raise ValueError("The old post changed; get suggestions again.")
    start, end, text = paras[index]
    a = anchor if anchor in text else html.escape(anchor, quote=False)
    if a not in text:
        raise ValueError("The old post changed; get suggestions again.")
    linked = text.replace(a, f'<a href="{html.escape(url, quote=True)}">{a}</a>', 1)
    return content[:start] + linked + content[end:]


def candidates_for_links(new_title: str, posts: list, k: int = 5) -> list:
    near = similar_posts(new_title, posts, threshold=0.25, k=k)
    urls = {p["url"] for p in near}
    return [p for p in posts if p.get("url") in urls]


__all__ = ["research_changes", "suggest_update", "apply_update", "suggest_link", "insert_link",
           "candidates_for_links", "trim_meta", "plain"]
