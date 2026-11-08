"""Hot stories per niche and country from Google News RSS.

Google Trends' public RSS only lists the ~10 newest trending searches of a country (often all sports), so it
rarely has anything for a given niche. Google News has a feed per topic and per search query, per country, and
each story lists how many outlets cover it — a good signal of what is hot in that niche right now.
"""
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from . import niches
from .trends import UA, Trend

BASE = "https://news.google.com/rss"

# niche -> ("section", NAME) or ("search", query)
SOURCES = {
    "tech": ("section", "TECHNOLOGY"),
    "ai": ("search", "AI OR ChatGPT OR Gemini OR OpenAI OR \"artificial intelligence\""),
    "gaming": ("search", "\"video game\" OR PlayStation OR Xbox OR Nintendo OR Steam OR gaming"),
    "sports": ("section", "SPORTS"),
    "health": ("section", "HEALTH"),
    "finance": ("search", "\"personal finance\" OR \"stock market\" OR \"interest rates\" OR inflation OR taxes OR savings"),
    "crypto": ("search", "bitcoin OR crypto OR ethereum OR blockchain"),
    "business": ("section", "BUSINESS"),
    "education": ("search", "students OR exams OR scholarship OR university OR \"online course\""),
    "travel": ("search", "travel OR flights OR visa OR tourism OR airline"),
    "food": ("search", "recipe OR food OR restaurant OR cooking"),
    "entertainment": ("section", "ENTERTAINMENT"),
    "lifestyle": ("search", "fashion OR beauty OR skincare OR style"),
    "home": ("search", "\"home improvement\" OR gardening OR DIY OR \"home decor\""),
    "auto": ("search", "car OR \"electric vehicle\" OR SUV OR automaker"),
    "parenting": ("search", "parenting OR parents OR toddlers OR \"child care\""),
    "pets": ("search", "pets OR dogs OR cats OR veterinarian"),
    "science": ("section", "SCIENCE"),
}

# Google Trends "Trending now" category ids, for the "open on Google Trends" link
TRENDS_CATEGORY = {"tech": 18, "ai": 18, "gaming": 6, "sports": 17, "health": 7, "finance": 3, "crypto": 3,
                   "business": 3, "education": 9, "travel": 19, "food": 5, "entertainment": 4, "lifestyle": 2,
                   "home": 8, "auto": 1, "pets": 13, "science": 15}


def _locale(geo: str, lang: str = "en") -> dict:
    geo = (geo or "US").upper()
    return {"hl": f"{lang}-{geo}", "gl": geo, "ceid": f"{geo}:{lang}"}


def feed_url(niche: str, geo: str, custom: str = "") -> tuple:
    if custom:
        return f"{BASE}/search", dict(_locale(geo), q=f"{custom} when:2d")
    kind, value = SOURCES.get(niche, ("search", niches.NICHES.get(niche, {}).get("label", niche)))
    if kind == "section":
        return f"{BASE}/headlines/section/topic/{value}", _locale(geo)
    return f"{BASE}/search", dict(_locale(geo), q=f"{value} when:2d")


def _clean_title(t: str) -> str:
    t = html.unescape(t or "").strip()
    return re.sub(r"\s+-\s+[^-]{2,60}$", "", t)          # drop " - Publisher"


def parse_news_rss(xml_text: str, niche: str) -> list:
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        title = _clean_title(item.findtext("title"))
        if not title:
            continue
        desc = item.findtext("description") or ""
        related = re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>(?:&nbsp;|\s)*<font[^>]*>(.*?)</font>', desc, flags=re.S)
        news = [(_clean_title(re.sub(r"<[^>]+>", "", t)), u, html.unescape(s)) for u, t, s in related]
        if not news:
            src = item.find("source")
            news = [(title, item.findtext("link") or "", src.text if src is not None else "")]
        try:
            ts = parsedate_to_datetime(item.findtext("pubDate")).timestamp()
        except (TypeError, ValueError):
            ts = 0
        t = Trend(title=title, traffic=f"{len(news)} outlet{'s' if len(news) != 1 else ''}", news=news[:5])
        t.ai_niches = [niche]
        t.score = len(news)
        t.ts = ts
        out.append(t)
    return out


def _similar(a: str, b: str) -> bool:
    wa, wb = set(re.findall(r"[a-z0-9]{4,}", a.lower())), set(re.findall(r"[a-z0-9]{4,}", b.lower()))
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.6


def fetch_hot(selected: list, geo: str = "US", custom: str = "", limit: int = 40, timeout: int = 20) -> list:
    """Hot stories for the selected niches, most-covered first."""
    targets = [(n, "") for n in selected if n in niches.NICHES]
    if custom.strip():
        targets.append(((selected or ["tech"])[0], custom.strip()))
    stories, errors = [], []
    for niche, cust in targets:
        url, params = feed_url(niche, geo, cust)
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if (not r.ok or "<item>" not in r.text) and geo.upper() != "US":
                r = requests.get(url, params={**params, **_locale("US")}, headers=UA, timeout=timeout)
            r.raise_for_status()
            stories += parse_news_rss(r.text, niche)
        except (requests.RequestException, ET.ParseError) as e:
            errors.append(f"{niche}: {e}")
    if not stories and errors:
        raise RuntimeError("Google News could not be loaded (" + "; ".join(errors[:2]) + ").")
    stories = [s for s in stories if not s.blocked]
    stories.sort(key=lambda s: (s.score, s.ts), reverse=True)
    out = []
    for s in stories:
        if not any(_similar(s.title, o.title) for o in out):
            out.append(s)
        if len(out) >= limit:
            break
    return out


def trends_page_url(geo: str, selected: list) -> str:
    cat = next((TRENDS_CATEGORY[n] for n in selected if n in TRENDS_CATEGORY), None)
    return f"https://trends.google.com/trending?geo={(geo or 'US').upper()}&hours=24" + (f"&category={cat}" if cat else "")
