"""The article pipeline: research -> write -> clean -> images -> WordPress draft."""
import datetime as dt
import html
import json
import mimetypes
import re
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse

from . import config, niches
from .gemini import Gemini, resolve_url
from .llm import make_writer
from .images import pexels_search, download

# ----------------------------------------------------------------------------- prompts

BANNED_PHRASES = [
    "in today's fast-paced world", "in today's digital age", "ever-evolving", "ever-changing landscape",
    "let's dive in", "dive into", "delve", "game-changer", "game changer", "revolutionize", "unlock the power",
    "harness the power", "navigate the complexities", "in conclusion", "tapestry", "testament to",
    "it's important to note", "in the realm of", "buckle up", "look no further", "seamlessly",
]

RESEARCH_SYSTEM = (
    "You are a careful research assistant for a blog about {niche}. Use Google Search. "
    "Report only facts you actually found in search results, with the name of the source for each fact. "
    "Prefer official sources (company announcements, documentation, government sites) and major publications. "
    "If something is uncertain or reports disagree, say so. Never invent numbers, quotes or dates."
)

RESEARCH_PROMPT = """Topic: {topic}
{angle_line}Today's date: {today}
Audience: {audience}
{news_line}
Research this topic and return organised notes in plain text with these sections:
1. What it is / what happened (with exact dates)
2. Key facts and numbers (each with the source name)
3. Why it matters to everyday users
4. Practical steps, tips or how-to details (if relevant)
5. What is still uncertain or disputed
6. Questions people commonly ask about it
Keep it factual and dense. No intro, no conclusion."""

WRITER_SYSTEM = """You write for {site}, a blog about {niche}, written by {author}{location}.
Readers: {audience}. Write the whole article in {language}.
Voice: {tone}. Plain words, short paragraphs (2-4 sentences), specific facts, numbers and dates.

HARD RULES
- Use ONLY facts from the research notes. If a detail is not in the notes, leave it out. Never invent statistics, studies, quotes, prices, dates, product names or features.
- Never write first-person experience or testing claims ("I tested", "I tried", "in my experience", "we reviewed", "our team", "hands-on"). The author adds his or her own experience separately.
{experience_rule}- Do not use these phrases or anything like them: {banned}.
- Open with a 2-3 sentence intro paragraph that tells the reader what happened or what they will learn. No heading called "Introduction".
- HTML only: <h2>, <h3>, <p>, <ul>, <ol>, <li>, <strong>, <em>, <a>, <table>/<tr>/<th>/<td>, <blockquote>. No <h1>, no images, no inline styles, no scripts, no markdown.
- Internal links: add up to {max_internal} links to related articles, using ONLY URLs from the INTERNAL ARTICLES list, with descriptive anchor text, placed where they genuinely help. Skip if none fit.
- External links: at most {max_external}, using ONLY URLs from the SOURCES list, to back up key facts.
- Include a practical section (for example "What this means for you" or step-by-step instructions).
{faq_rule}- Do not add a "Sources" or "References" section; the app adds it.
{ymyl_rule}- Target length about {words} words. Do not pad."""

WRITER_PROMPT = """TOPIC: {topic}
{angle_line}
RESEARCH NOTES:
{notes}

SOURCES (title | url):
{sources}

INTERNAL ARTICLES on {site} (title | url):
{internal}

CATEGORIES (choose exactly one name): {categories}

Return JSON with exactly these keys:
{{
  "title": "headline, max 65 characters, specific, no clickbait, no year unless the topic is about that year",
  "seo_title": "max 60 characters, includes the focus keyword near the start",
  "slug": "short-lowercase-hyphen-slug-max-6-words",
  "focus_keyword": "2-4 word phrase people search for",
  "meta_description": "140-155 characters, includes the focus keyword, says what the reader gets",
  "excerpt": "1-2 sentence summary",
  "category": "one name from CATEGORIES",
  "tags": ["5 to 8 short tags"],
  "body_html": "the full article HTML following all rules, including the <!--MY_EXPERIENCE--> marker",
  "featured_image": {{"prompt": "...", "alt": "...", "stock_query": "2-4 words for a stock photo search"}},
  "inline_images": [{{"after_h2": 1, "prompt": "...", "alt": "...", "stock_query": "..."}}]
}}
Image prompts: describe a clean editorial scene that illustrates the section, photorealistic or modern flat illustration,
no text or letters, no logos or brand marks, no real people's faces, 16:9. Give exactly {n_inline} inline_images with different after_h2 values
(1 = after the first <h2> section)."""

OUTLINE_PROMPT = """TOPIC: {topic}
{angle_line}
RESEARCH NOTES:
{notes}

Plan an article for {site} (a blog about {niche}) for readers who are {audience}.
Use only what the research notes support. Return JSON:
{{"title": "working headline",
  "sections": [{{"h2": "section heading", "points": ["what this section covers, 1 short line each"]}}],
  "faq": ["up to 3 questions readers really ask"]}}
Give 4-7 sections in a logical order, including one practical "what to do" section."""

FACTCHECK_PROMPT = """RESEARCH NOTES (the only allowed facts):
{notes}

SOURCES: {sources}

ARTICLE:
{article}

List every factual claim in the ARTICLE (numbers, dates, names, prices, features, quotes, rankings) that is NOT
supported by the RESEARCH NOTES, or that contradicts them. Ignore general advice and opinions.
Return JSON: {{"issues": [{{"sentence": "the exact sentence from the article", "problem": "unsupported" or "contradicted",
"note": "short reason"}}]}}. Return {{"issues": []}} if everything is supported."""

SOCIAL_PROMPT = """Article title: {title}
Summary: {summary}
Link: {url}
Language: {language}

Write promotion texts for this blog post. Be honest and specific, no clickbait, no hashtags spam (max 3).
Return JSON: {{"facebook": "2-3 sentences + link", "x": "max 260 characters incl. link",
"pinterest": {{"title": "max 90 chars", "description": "max 300 chars"}}, "linkedin": "3-4 sentences + link",
"youtube_short": {{"title": "max 70 chars", "script": "30-45 second spoken script, short lines"}}}}"""

POLISH_SYSTEM = (
    "You turn an author's rough notes (any language, e.g. Roman Urdu, Hindi or English) into short first-person {language} for their blog. "
    "Keep ONLY what the notes say. Do not add any new facts, numbers, durations, results, opinions, products or feelings. "
    "If the notes are thin, write less, not more."
)

POLISH_PROMPT = """Article title: {title}
Author's notes:
\"\"\"{notes}\"\"\"

Return JSON: {{"heading": "short H2 heading in first person, e.g. 'How I use it myself'", "paragraphs": ["1-2 short paragraphs"]}}"""

FABRICATION_RE = re.compile(
    r"\b(I|we)\s+(have\s+)?(tested|tried|used|reviewed|spent|bought|found|noticed|ran)\b|"
    r"\bin my experience\b|\bour (team|testing|tests|experts|editors)\b|\bhands-on\b|\bwe tested\b",
    re.I)

ALLOWED_TAGS = {"h2", "h3", "h4", "p", "ul", "ol", "li", "strong", "em", "b", "i", "a", "table", "thead",
                "tbody", "tr", "th", "td", "blockquote", "br", "figure", "figcaption", "img", "hr", "code"}


# ----------------------------------------------------------------------------- data

@dataclass
class Article:
    topic: str
    angle: str = ""
    notes: str = ""
    sources: list = field(default_factory=list)          # [[title, url]]
    title: str = ""
    seo_title: str = ""
    slug: str = ""
    focus_keyword: str = ""
    meta_description: str = ""
    excerpt: str = ""
    category: str = ""
    tags: list = field(default_factory=list)
    body_html: str = ""
    featured_image: dict = field(default_factory=dict)
    inline_images: list = field(default_factory=list)
    experience_notes: str = ""
    experience_html: str = ""
    warnings: list = field(default_factory=list)
    wp_post_id: int = 0
    outline: str = ""                                     # editable plan, "## heading" + "- point" lines
    fact_issues: list = field(default_factory=list)      # [{"sentence","problem","note"}]
    seo_report: list = field(default_factory=list)       # [{"label","ok","value"}]
    similar_posts: list = field(default_factory=list)    # [{"title","url"}]
    own_images: list = field(default_factory=list)       # [{"file","alt","caption","after_h2","featured"}]
    social: dict = field(default_factory=dict)
    profile: str = ""
    file: str = ""                                        # stable file name of the local draft
    created: str = field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))

    def save(self) -> str:
        config.DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        if not self.file:
            name = re.sub(r"[^a-z0-9-]+", "-", (self.slug or self.topic).lower()).strip("-")[:50] or "draft"
            self.file = f"{self.created[:10]}-{self.created[11:19].replace(':', '')}-{name}.json"
        path = config.DRAFTS_DIR / self.file
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, path: str) -> "Article":
        data = json.loads(open(path, encoding="utf-8").read())
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ----------------------------------------------------------------------------- helpers

def pick_internal(posts: list, topic: str, k: int = 25) -> list:
    words = {w for w in re.findall(r"[a-z0-9]+", topic.lower()) if len(w) > 2}
    def score(p):
        text = (p["title"] + " " + p.get("excerpt", "")).lower()
        return sum(1 for w in words if w in text)
    ranked = sorted(posts, key=score, reverse=True)
    return ranked[:k]


def _words(text: str) -> set:
    stop = {"the", "and", "for", "with", "what", "how", "why", "your", "you", "are", "this", "that", "from", "into",
            "best", "guide", "2024", "2025", "2026", "2027", "new", "about", "does", "will", "can", "its"}
    return {w for w in re.findall(r"[a-z0-9]{3,}", text.lower()) if w not in stop}


def similar_posts(text: str, posts: list, threshold: float = 0.5, k: int = 3) -> list:
    """Existing posts that look like the same topic (to avoid two posts competing for one search)."""
    want = _words(text)
    out = []
    for p in posts:
        have = _words(p.get("title", ""))
        if want and have:
            score = len(want & have) / min(len(want), len(have))
            if score >= threshold and len(want & have) >= 2:
                out.append((score, {"title": p["title"], "url": p.get("url", "")}))
    return [p for _, p in sorted(out, key=lambda x: -x[0])[:k]]


def _sentences(text: str) -> list:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    n = len(groups) - (1 if word.endswith("e") and len(groups) > 1 else 0)
    return max(1, n)


def seo_report(a: "Article", language: str = "English") -> list:
    """Readability and on-page SEO checks. Each row: label, ok (True/False/None = info), value."""
    plain = html.unescape(re.sub(r"<[^>]+>", " ", a.body_html))
    words = re.findall(r"[\w'’-]+", plain)
    n = len(words)
    sents = _sentences(plain)
    paras = [html.unescape(re.sub(r"<[^>]+>", " ", p)).split() for p in re.findall(r"<p[^>]*>(.*?)</p>", a.body_html, re.S)]
    long_paras = sum(1 for p in paras if len(p) > 120)
    avg_sent = round(n / max(1, len(sents)), 1)
    kw = a.focus_keyword.lower().strip()
    kw_count = plain.lower().count(kw) if kw else 0
    density = round(kw_count * len(kw.split()) / max(1, n) * 100, 2) if kw else 0
    first_p = html.unescape(re.sub(r"<[^>]+>", " ", (re.findall(r"<p[^>]*>(.*?)</p>", a.body_html, re.S) or [""])[0])).lower()
    h2 = len(re.findall(r"<h2", a.body_html, re.I))
    links = re.findall(r'href="([^"]+)"', a.body_html)
    rows = [
        {"label": "Length", "ok": n >= 600, "value": f"{n} words"},
        {"label": "Sections (H2)", "ok": h2 >= 3, "value": str(h2)},
        {"label": "Average sentence", "ok": avg_sent <= 22, "value": f"{avg_sent} words"},
        {"label": "Long paragraphs (120+ words)", "ok": long_paras == 0, "value": str(long_paras)},
    ]
    if language.lower().startswith("english") and n:
        syl = sum(_syllables(w) for w in words)
        flesch = round(206.835 - 1.015 * (n / max(1, len(sents))) - 84.6 * (syl / n))
        rows.append({"label": "Reading ease (Flesch)", "ok": flesch >= 50,
                     "value": f"{flesch} ({'easy' if flesch >= 60 else 'fairly hard' if flesch >= 50 else 'hard'})"})
    if kw:
        rows += [
            {"label": "Keyword in SEO title", "ok": kw in a.seo_title.lower(), "value": ""},
            {"label": "Keyword in meta description", "ok": kw in a.meta_description.lower(), "value": ""},
            {"label": "Keyword in first paragraph", "ok": kw in first_p, "value": ""},
            {"label": "Keyword in slug", "ok": all(w in a.slug for w in re.findall(r"[a-z0-9]+", kw)), "value": ""},
            {"label": "Keyword uses", "ok": 0.3 <= density <= 2.5, "value": f"{kw_count}× ({density}%)"},
        ]
    else:
        rows.append({"label": "Focus keyword", "ok": False, "value": "missing"})
    rows += [
        {"label": "Meta description length", "ok": 120 <= len(a.meta_description) <= 160, "value": str(len(a.meta_description))},
        {"label": "Links", "ok": None, "value": f"{len(links)} in text"},
    ]
    return rows


def domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def clean_sources(raw: list, resolve=resolve_url, limit: int = 8) -> list:
    out, seen = [], set()
    for title, url in raw:
        real = resolve(url)
        if not real or not real.startswith("http"):
            continue
        key = real.split("#")[0].rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append([title or domain(real), real])
        if len(out) >= limit:
            break
    return out


def strip_disallowed_links(body: str, allowed_urls: set) -> tuple:
    removed = []
    def norm(u):
        return u.split("#")[0].rstrip("/")
    allowed = {norm(u) for u in allowed_urls}
    def repl(m):
        href = m.group(2)
        if norm(href) in allowed:
            return m.group(0)
        removed.append(href)
        return m.group(3)
    body = re.sub(r'<a\s[^>]*?href=(["\'])(.*?)\1[^>]*>(.*?)</a>', repl, body, flags=re.S | re.I)
    return body, removed


def sanitize_html(body: str) -> str:
    body = re.sub(r"```(?:html)?", "", body)
    body = re.sub(r"<(script|style|iframe)[^>]*>.*?</\1>", "", body, flags=re.S | re.I)
    body = re.sub(r"<h1([^>]*)>(.*?)</h1>", r"<h2>\2</h2>", body, flags=re.S | re.I)
    body = re.sub(r'\sstyle="[^"]*"', "", body)
    body = re.sub(r"<h2[^>]*>\s*Introduction\s*</h2>", "", body, flags=re.I)
    def tag_ok(m):
        name = m.group(1).lower()
        return m.group(0) if name in ALLOWED_TAGS else ""
    body = re.sub(r"</?([a-zA-Z0-9]+)(?:\s[^>]*)?>", tag_ok, body)
    return body.strip()


def find_banned(text: str) -> list:
    low = html.unescape(re.sub(r"<[^>]+>", " ", text)).lower()
    return [p for p in BANNED_PHRASES if p in low]


def find_fabrication(text: str) -> list:
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text))
    hits = []
    for sent in re.split(r"(?<=[.!?])\s+", plain):
        if FABRICATION_RE.search(sent):
            hits.append(sent.strip()[:160])
    return hits


def trim_meta(desc: str, limit: int = 155) -> str:
    desc = " ".join(desc.split())
    if len(desc) <= limit:
        return desc
    cut = desc[:limit].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut + "."


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return "-".join(s.split("-")[:8])


def figure_html(url: str, alt: str, caption: str, link: str = "") -> str:
    alt_e = html.escape(alt, quote=True)
    cap = caption
    return (f'<figure class="wp-block-image size-large"><img src="{html.escape(url, quote=True)}" alt="{alt_e}" loading="lazy" />'
            f"<figcaption>{cap}</figcaption></figure>")


def insert_after_section(body: str, n: int, snippet: str) -> str:
    """Insert snippet after the first paragraph that follows the n-th <h2>."""
    h2s = [m.end() for m in re.finditer(r"</h2>", body, flags=re.I)]
    if not h2s:
        return body + "\n" + snippet
    idx = h2s[min(max(n, 1), len(h2s)) - 1]
    p_end = body.find("</p>", idx)
    pos = p_end + 4 if p_end != -1 else idx
    return body[:pos] + "\n" + snippet + "\n" + body[pos:]


def build_final_html(a: Article, figures: list, ai_note: bool, sources: bool = True, disclaimer: str = "",
                     ai_caption: str = "AI-generated image") -> str:
    body = a.body_html
    # images first, so section numbers match what the writer model saw
    for after, snippet in sorted(figures, key=lambda x: -x[0]):
        body = insert_after_section(body, after, snippet)
    exp = a.experience_html.strip()
    if "<!--MY_EXPERIENCE-->" in body:
        body = body.replace("<!--MY_EXPERIENCE-->", exp, 1)
    elif exp:
        body = insert_after_section(body, 1, exp)
    body = body.replace("<!--MY_EXPERIENCE-->", "")
    tail = []
    if a.sources and sources:
        items = "".join(
            f'<li><a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener">{html.escape(t)}</a> ({domain(u)})</li>'
            for t, u in a.sources)
        tail.append(f"<h2>Sources</h2>\n<ul>{items}</ul>")
    if disclaimer:
        tail.append(f"<p><em>{html.escape(disclaimer)}</em></p>")
    if ai_note:
        tail.append(f"<p><em>Images marked “{html.escape(ai_caption)}” were created with AI for illustration.</em></p>")
    return body + ("\n" + "\n".join(tail) if tail else "")


# ----------------------------------------------------------------------------- pipeline

YMYL_DISCLAIMER = ("This article is for general information only and is not professional medical, "
                   "financial or legal advice. Check with a qualified professional before making decisions.")


class Pipeline:
    def __init__(self, cfg: dict, log=print, gemini=None):
        self.cfg = cfg
        self.log = log
        self.g = gemini or Gemini(cfg["gemini_api_key"], cfg.get("text_model", ""), cfg.get("image_model", ""))
        self.w = self.g if gemini else make_writer(cfg, self.g)   # who writes (Gemini, OpenAI or Claude)
        sel = cfg.get("niches") or []
        self.niche = niches.niche_text(sel, cfg.get("niche_custom", ""))
        self.ymyl = niches.is_ymyl(sel)

    def research(self, a: Article, trend_news: list = None) -> None:
        self.log("Researching on Google Search…")
        news_line = ""
        if trend_news:
            heads = "; ".join(f"{t} ({s})" for t, _, s in trend_news[:3] if t)
            news_line = f"Recent headlines about it: {heads}\n"
        prompt = RESEARCH_PROMPT.format(topic=a.topic, angle_line=f"Angle: {a.angle}\n" if a.angle else "",
                                        today=dt.date.today().isoformat(), audience=self.cfg["audience"],
                                        news_line=news_line)
        notes, raw_sources = self.g.research(prompt, RESEARCH_SYSTEM.format(niche=self.niche))
        a.notes = notes.strip()
        self.log(f"Found {len(raw_sources)} search sources, resolving links…")
        a.sources = clean_sources(raw_sources)
        self.log(f"Research done: {len(a.notes.split())} words of notes, {len(a.sources)} sources.")

    def outline(self, a: Article) -> None:
        """Plan the article first so the author can change it before the full text is written."""
        c = self.cfg
        self.log("Planning the outline…")
        data = self.w.generate_json(OUTLINE_PROMPT.format(
            topic=a.topic, angle_line=f"ANGLE: {a.angle}" if a.angle else "", notes=a.notes[:15000],
            site=c.get("site_name") or "this blog", niche=self.niche, audience=c.get("audience") or "general readers"),
            temperature=0.4)
        lines = []
        for sec in data.get("sections", []) if isinstance(data, dict) else []:
            if sec.get("h2"):
                lines.append("## " + sec["h2"].strip())
                lines += ["- " + str(pt).strip() for pt in sec.get("points", []) if str(pt).strip()]
        faq = [q for q in (data.get("faq") or []) if str(q).strip()] if isinstance(data, dict) else []
        if faq and c.get("faq", True):
            lines.append("## Frequently asked questions")
            lines += ["- " + str(q).strip() for q in faq[:3]]
        a.outline = "\n".join(lines)
        self.log(f"Outline ready: {sum(1 for x in lines if x.startswith('## '))} sections. Edit it, then write.")

    def fact_check(self, a: Article) -> None:
        if not a.notes.strip():
            a.fact_issues = []
            return
        self.log("Fact-checking the article against the research…")
        plain = html.unescape(re.sub(r"<[^>]+>", " ", a.body_html.replace("<!--MY_EXPERIENCE-->", "")))
        data = self.g.generate_json(FACTCHECK_PROMPT.format(notes=a.notes[:20000], article=plain[:30000],
                                                            sources=", ".join(domain(u) for _, u in a.sources)),
                                    temperature=0.1)
        issues = []
        for it in (data.get("issues") or []) if isinstance(data, dict) else []:
            sent = str(it.get("sentence", "")).strip()
            if sent:
                issues.append({"sentence": sent[:400], "problem": str(it.get("problem", "unsupported")),
                               "note": str(it.get("note", ""))[:300]})
        a.fact_issues = issues[:20]
        self.log(f"Fact-check: {len(issues)} claim(s) to look at." if issues else "Fact-check: every claim is in the research.")

    def social(self, a: Article, url: str = "") -> None:
        self.log("Writing social media posts…")
        data = self.w.generate_json(SOCIAL_PROMPT.format(title=a.title, summary=a.meta_description or a.excerpt,
                                                         url=url or "(link)", language=self.cfg.get("language") or "English"),
                                    temperature=0.7)
        a.social = data if isinstance(data, dict) else {}

    def write(self, a: Article, internal_posts: list, categories: list) -> None:
        self.log("Writing the article…")
        cats = [html.unescape(c["name"]) for c in categories if c.get("name") and c["name"] != "Uncategorized"]
        internal = pick_internal(internal_posts, a.topic + " " + a.angle)
        c = self.cfg
        n_inline = max(0, min(6, int(c.get("inline_images", 2) or 0)))
        if c.get("image_source") == "none":
            n_inline = 0
        loc = (c.get("author_location") or "").strip()
        system = WRITER_SYSTEM.format(
            site=c.get("site_name") or "this blog", author=c.get("author_name") or "its author",
            location=f" from {loc}" if loc else "", audience=c.get("audience") or "general readers",
            niche=self.niche, language=c.get("language") or "English",
            tone=config.TONES.get(c.get("tone"), config.TONES["friendly"]),
            banned=", ".join(f'"{b}"' for b in BANNED_PHRASES),
            words=int(c.get("target_words", 1400) or 1400),
            max_internal=int(c.get("max_internal_links", 4)), max_external=int(c.get("max_external_links", 4)),
            experience_rule=("- Put this exact marker on its own line where a short personal section from the author "
                             "fits best (after the first or second section): <!--MY_EXPERIENCE-->\n"
                             if c.get("experience_section", True) else ""),
            faq_rule=("- FAQ only if genuinely useful: at most 3 questions, as <h2>Frequently asked questions</h2> "
                      "with each question as <h3> and a 1-3 sentence answer.\n" if c.get("faq", True)
                      else "- Do not add an FAQ section.\n"),
            ymyl_rule=("- This niche affects readers' health or money. Be careful and balanced, give no personal "
                       "advice beyond what the sources say, and suggest checking with a qualified professional "
                       "where decisions are involved.\n" if self.ymyl else ""))
        prompt = WRITER_PROMPT.format(
            topic=a.topic, angle_line=f"ANGLE: {a.angle}" if a.angle else "", notes=a.notes[:20000],
            sources="\n".join(f"{t} | {u}" for t, u in a.sources) or "(none)",
            internal="\n".join(f"{p['title']} | {p['url']}" for p in internal) or "(none)",
            categories=", ".join(cats) or "General", site=c.get("site_name") or "this blog", n_inline=n_inline)
        if a.outline.strip():
            prompt += ("\n\nOUTLINE APPROVED BY THE AUTHOR (follow its sections and order; use only facts from the notes):\n"
                       + a.outline.strip()[:6000])
        data = self.w.generate_json(prompt, system, temperature=0.6)

        a.title = (data.get("title") or a.topic).strip()
        a.seo_title = (data.get("seo_title") or a.title)[:60].strip()
        a.slug = slugify(data.get("slug") or a.title)
        a.focus_keyword = (data.get("focus_keyword") or "").strip()
        a.meta_description = trim_meta(data.get("meta_description") or data.get("excerpt") or "")
        a.excerpt = (data.get("excerpt") or "").strip()
        a.category = data.get("category") or (cats[0] if cats else "")
        a.tags = [t.strip() for t in (data.get("tags") or []) if t.strip()][:8]
        a.featured_image = data.get("featured_image") or {}
        a.inline_images = (data.get("inline_images") or [])[:n_inline]

        body = sanitize_html(data.get("body_html") or "")
        allowed = {p["url"] for p in internal} | {u for _, u in a.sources}
        body, removed = strip_disallowed_links(body, allowed)
        a.body_html = body
        a.similar_posts = [p for p in similar_posts(a.title + " " + a.topic, internal_posts)
                           if p["url"].rstrip("/") not in a.body_html]
        self._check(a, removed, internal)
        self.log(f"Draft written: “{a.title}” (~{len(re.sub('<[^>]+>', ' ', body).split())} words).")

    def _check(self, a: Article, removed: list, internal: list) -> None:
        w = []
        if removed:
            w.append(f"Removed {len(removed)} link(s) that were not in the verified source/internal lists.")
        n_int = sum(1 for p in internal if p["url"].rstrip("/") in a.body_html)
        if internal and n_int < 2:
            w.append(f"Only {n_int} internal link(s). Consider adding more before publishing.")
        bad = find_banned(a.body_html)
        if bad:
            w.append("Generic AI phrases found: " + ", ".join(bad))
        fab = find_fabrication(a.body_html)
        if fab:
            w.append("Possible invented first-person claims (remove or replace with your real experience): " + " | ".join(fab))
        if not a.sources:
            w.append("No verified sources found. Check facts carefully before publishing.")
        if self.cfg.get("experience_section", True) and "<!--MY_EXPERIENCE-->" not in a.body_html:
            w.append("No experience marker; your experience section will be placed after the first section.")
        if a.similar_posts:
            w.append("Your site already has a similar post: " + " | ".join(p["title"] for p in a.similar_posts)
                     + ". Two posts on one topic compete in Google; consider updating the old one instead.")
        a.warnings = w
        a.seo_report = seo_report(a, self.cfg.get("language") or "English")

    def polish_experience(self, a: Article) -> None:
        if not a.experience_notes.strip():
            a.experience_html = ""
            return
        self.log("Turning your notes into English (no new facts added)…")
        data = self.w.generate_json(POLISH_PROMPT.format(title=a.title or a.topic, notes=a.experience_notes.strip()),
                                    POLISH_SYSTEM.format(language=self.cfg.get("language") or "English"),
                                    temperature=0.2)
        head = html.escape((data.get("heading") or "My take").strip())
        paras = "".join(f"<p>{html.escape(p.strip())}</p>" for p in data.get("paragraphs", []) if p.strip())
        a.experience_html = f"<h2>{head}</h2>\n{paras}" if paras else ""

    # ---------- images + WordPress ----------
    def _get_image(self, spec: dict, source: str) -> tuple:
        """Returns (bytes, mime, caption_html) or None."""
        if source in ("pexels", "pexels_then_gemini") and self.cfg.get("pexels_api_key"):
            q = spec.get("stock_query") or spec.get("alt") or ""
            try:
                hits = pexels_search(self.cfg["pexels_api_key"], q, count=3)
            except Exception as e:  # noqa: BLE001
                self.log(f"Pexels search failed: {e}")
                hits = []
            if hits:
                h = hits[0]
                data, mime = download(h["download_url"])
                cap = (f'Photo by <a href="{html.escape(h["photographer_url"], quote=True)}" target="_blank" rel="noopener">'
                       f'{html.escape(h["photographer"])}</a> on <a href="{html.escape(h["page_url"], quote=True)}" '
                       f'target="_blank" rel="noopener">Pexels</a>')
                return data, mime, cap, False
            if source == "pexels":
                return None
        if source == "openai":
            from .llm import OpenAIWriter
            prompt = (spec.get("prompt") or spec.get("alt") or "") + \
                     " No text, no letters, no logos, no watermarks, no real people's faces."
            w = OpenAIWriter(self.cfg.get("openai_api_key", ""), self.cfg.get("openai_model") or "image-only",
                             self.cfg.get("openai_image_model"))
            data, mime = w.generate_image(prompt, "16:9")
            return data, mime, html.escape(self.cfg.get("ai_caption", "AI-generated image")), True
        if source in ("gemini", "pexels_then_gemini") and self.cfg.get("image_model") and not getattr(self, "_no_ai_img", False):
            prompt = (spec.get("prompt") or spec.get("alt") or "") + \
                     " No text, no letters, no logos, no watermarks, no real people's faces."
            try:
                data, mime = self.g.generate_image(prompt, "16:9")
                return data, mime, html.escape(self.cfg.get("ai_caption", "AI-generated image")), True
            except Exception as e:  # noqa: BLE001
                if "QUOTA" in str(e):
                    self._no_ai_img = True  # don't keep hitting a key with no image quota
                self.log(f"Gemini image failed: {e}")
                if source == "gemini" and self.cfg.get("pexels_api_key"):
                    self.log("Falling back to a free Pexels photo.")
                    return self._get_image(spec, "pexels")
                raise
        if source == "gemini" and getattr(self, "_no_ai_img", False) and self.cfg.get("pexels_api_key"):
            return self._get_image(spec, "pexels")
        return None

    def final_html(self, a: Article, figures: list, used_ai: bool) -> str:
        return build_final_html(a, figures, used_ai, sources=self.cfg.get("sources_section", True),
                                disclaimer=YMYL_DISCLAIMER if self.ymyl else "",
                                ai_caption=self.cfg.get("ai_caption") or "AI-generated image")

    def publish_draft(self, a: Article, wp) -> dict:
        source = self.cfg.get("image_source", "gemini")
        used_ai = False
        featured_id = 0
        figures = []
        # 1) the author's own photos and screenshots first
        own_inline = 0
        for i, img in enumerate(a.own_images, 1):
            path = config.MEDIA_DIR / str(img.get("file", ""))
            if not path.is_file():
                self.log(f"Your image {img.get('file')} was not found, skipped.")
                continue
            mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
            alt = img.get("alt") or a.title
            cap = html.escape(img.get("caption") or "")
            m = wp.upload_image(path.read_bytes(), mime, f"{a.slug}-own-{i}", alt, cap, a.title)
            if img.get("featured") and not featured_id:
                featured_id = m["id"]
            else:
                own_inline += 1
                figures.append((int(img.get("after_h2") or 1), figure_html(m["url"], alt, cap)))
        if own_inline:
            a.inline_images = a.inline_images[:max(0, len(a.inline_images) - own_inline)]
        if source == "none":
            a.inline_images = []
        if (not featured_id and a.featured_image and source != "none"
                and self.cfg.get("featured_image", True)):
            self.log("Creating featured image…")
            try:
                got = self._get_image(a.featured_image, source)
                if got:
                    data, mime, cap, is_ai = got
                    used_ai |= is_ai
                    m = wp.upload_image(data, mime, a.slug + "-featured", a.featured_image.get("alt") or a.title,
                                        cap, a.title)
                    featured_id = m["id"]
            except Exception as e:  # noqa: BLE001
                self.log(f"Featured image skipped: {e}")
        for i, spec in enumerate(a.inline_images, 1):
            self.log(f"Creating image {i}/{len(a.inline_images)}…")
            try:
                got = self._get_image(spec, source)
                if not got:
                    continue
                data, mime, cap, is_ai = got
                used_ai |= is_ai
                m = wp.upload_image(data, mime, f"{a.slug}-{i}", spec.get("alt") or a.title, cap, a.title)
                figures.append((int(spec.get("after_h2") or i), figure_html(m["url"], spec.get("alt") or a.title, cap)))
            except Exception as e:  # noqa: BLE001
                self.log(f"Image {i} skipped: {e}")

        content = self.final_html(a, figures, used_ai)
        cat_ids = [c["id"] for c in wp.categories() if html.unescape(c["name"]).lower() == (a.category or "").lower()]
        self.log("Creating tags…")
        tag_ids = wp.tag_ids(a.tags)
        post = {"status": "draft", "title": a.title, "content": content,
                "excerpt": a.excerpt or a.meta_description, "slug": a.slug,
                "categories": cat_ids, "tags": tag_ids, "featured_media": featured_id or None}
        if wp.bridge_installed():
            post["meta"] = {"_yoast_wpseo_title": a.seo_title + " %%sep%% %%sitename%%",
                            "_yoast_wpseo_metadesc": a.meta_description,
                            "_yoast_wpseo_focuskw": a.focus_keyword,
                            "rank_math_title": a.seo_title + " %sep% %sitename%",
                            "rank_math_description": a.meta_description,
                            "rank_math_focus_keyword": a.focus_keyword}
        else:
            # Without the bridge plugin Yoast fields can't be written over REST.
            # Use the meta description as the excerpt so search engines still get a good summary.
            post["excerpt"] = a.meta_description or post["excerpt"]
            self.log("Bridge plugin not installed: meta description saved as the post excerpt. "
                     "Optionally paste the SEO title/focus keyword into your SEO plugin box before publishing.")
        self.log("Saving as Draft in WordPress…")
        res = wp.create_draft(post)
        a.wp_post_id = res["id"]
        a.save()
        return res
