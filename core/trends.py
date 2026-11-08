"""Topic discovery: Google Trends 'Trending now' RSS + Google search suggestions."""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

import requests

from . import niches

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BlogDraftStudio/1.0"}

TRENDS_URLS = [
    "https://trends.google.com/trending/rss?geo={geo}",
    "https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}",
]

@dataclass
class Trend:
    title: str
    traffic: str = ""
    news: list = field(default_factory=list)  # [(title, url, source)]
    ai_niches: list = None                    # set by the optional Gemini filter

    @property
    def texts(self) -> list:
        return [self.title] + [n[0] for n in self.news]

    @property
    def blocked(self) -> bool:
        """Gambling, adult, violence or tragedy: never a good topic for an AdSense site."""
        return any(niches.is_blocked(t) for t in self.texts)

    @property
    def matched_niches(self) -> list:
        if self.ai_niches is not None:
            return list(self.ai_niches)
        found = set(niches.niches_of(self.title))
        # the title alone may be just a name: then two matching headlines are needed
        counts = {}
        for head, *_ in self.news:
            for k in niches.niches_of(head):
                counts[k] = counts.get(k, 0) + 1
        found |= {k for k, c in counts.items() if c >= 2}
        return sorted(found)

    @property
    def traffic_num(self) -> int:
        digits = re.sub(r"[^0-9]", "", self.traffic or "")
        n = int(digits) if digits else 0
        return n * (1000 if "K" in (self.traffic or "").upper() else 1) * (
            1000000 if "M" in (self.traffic or "").upper() else 1)

    def fits(self, selected: list) -> bool:
        return not self.blocked and bool(set(self.matched_niches) & set(selected))

    def to_dict(self) -> dict:
        return {"title": self.title, "traffic": self.traffic,
                "news": [{"title": t, "url": u, "source": s} for t, u, s in self.news],
                "niches": self.matched_niches, "blocked": self.blocked}


def filter_trends(items: list, selected: list) -> list:
    return [t for t in items if t.fits(selected)]


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag.split(":", 1)[-1]


def parse_trends_rss(xml_text: str) -> list:
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter():
        if _local(item.tag) != "item":
            continue
        t = Trend(title="")
        for child in item:
            name = _local(child.tag)
            if name == "title":
                t.title = (child.text or "").strip()
            elif name == "approx_traffic":
                t.traffic = (child.text or "").strip()
            elif name == "news_item":
                fields = {_local(c.tag): (c.text or "").strip() for c in child}
                t.news.append((fields.get("news_item_title", ""), fields.get("news_item_url", ""),
                               fields.get("news_item_source", "")))
        if t.title:
            out.append(t)
    return out


def fetch_trending(geo: str = "US", timeout: int = 20) -> list:
    last_err = None
    for url in TRENDS_URLS:
        try:
            r = requests.get(url.format(geo=geo), headers=UA, timeout=timeout)
            if r.ok and "<rss" in r.text[:500]:
                items = parse_trends_rss(r.text)
                if items:
                    # the feed is ordered by time; Google's page shows the biggest searches first
                    items.sort(key=lambda t: t.traffic_num, reverse=True)
                    return items
            last_err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            last_err = str(e)
    raise RuntimeError(f"Google Trends feed could not be loaded ({last_err}).")


def fetch_suggestions(keyword: str, geo: str = "US", timeout: int = 15) -> list:
    """Google autocomplete: what people actually type after this keyword."""
    seeds = [keyword] + [f"{keyword} {x}" for x in ("how", "vs", "best", "why", "is")]
    seen, out = set(), []
    for q in seeds:
        try:
            r = requests.get("https://suggestqueries.google.com/complete/search",
                             params={"client": "firefox", "hl": "en", "gl": geo.lower(), "q": q},
                             headers=UA, timeout=timeout)
            data = r.json()
        except (requests.RequestException, ValueError):
            continue
        for s in data[1] if len(data) > 1 else []:
            s = s.strip()
            if s and s.lower() not in seen:
                seen.add(s.lower())
                out.append(s)
    return out
