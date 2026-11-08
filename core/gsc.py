"""Google Search Console: read the CSV export (Performance → Export → Download CSV) and turn it into actions.

No Google login is needed: the user downloads the export zip from Search Console and opens it in the app.
"""
import csv
import io
import json
import re
import zipfile

from . import config


def _num(v: str) -> float:
    v = (v or "").strip().replace(",", "").replace("%", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def _rows(text: str) -> list:
    """Parse one Search Console CSV (Queries or Pages). Returns dicts: key, clicks, impressions, ctr, position."""
    rdr = csv.reader(io.StringIO(text.lstrip("﻿")))
    head = next(rdr, None)
    if not head:
        return []
    low = [h.strip().lower() for h in head]

    def col(*names):
        for i, h in enumerate(low):
            if any(n in h for n in names):
                return i
        return None
    ci, ii, ti, pi = col("click"), col("impression"), col("ctr"), col("position")
    if ci is None or ii is None:
        return []
    out = []
    for r in rdr:
        if not r or not r[0].strip():
            continue
        ctr = _num(r[ti]) if ti is not None and ti < len(r) else 0
        out.append({"key": r[0].strip(), "clicks": _num(r[ci]), "impressions": _num(r[ii]),
                    "ctr": ctr, "position": _num(r[pi]) if pi is not None and pi < len(r) else 0})
    return out


def parse_export(data: bytes, name: str = "") -> dict:
    """Accepts the Search Console zip, or a single Queries.csv / Pages.csv."""
    files = {}
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for n in z.namelist():
                if n.lower().endswith(".csv"):
                    files[n.split("/")[-1].lower()] = z.read(n).decode("utf-8", errors="replace")
    else:
        files[(name or "upload.csv").lower()] = data.decode("utf-8", errors="replace")
    queries, pages = [], []
    for n, text in files.items():
        rows = _rows(text)
        if not rows:
            continue
        head = text.lstrip("﻿").split("\n", 1)[0].lower()
        if "page" in n or "page" in head or rows[0]["key"].startswith("http"):
            pages = rows
        elif "quer" in n or "quer" in head:
            queries = rows
    if not queries and not pages:
        raise ValueError("No Search Console data found. In Search Console open Performance → Export → "
                         "Download CSV, then open that zip here.")
    return {"queries": queries, "pages": pages}


def _words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]{3,}", s.lower())}


def recommend(data: dict) -> dict:
    pages, queries = data.get("pages", []), data.get("queries", [])
    imp_sorted = sorted(p["impressions"] for p in pages)
    imp_cut = imp_sorted[len(imp_sorted) // 2] if imp_sorted else 0          # median

    almost = [p for p in pages if 8 <= p["position"] <= 20 and p["impressions"] >= 50]
    almost.sort(key=lambda p: -p["impressions"])

    low_ctr = [p for p in pages if p["position"] and p["position"] <= 10 and p["impressions"] >= max(100, imp_cut)
               and p["ctr"] < 2.0]
    low_ctr.sort(key=lambda p: -p["impressions"])

    page_words = [_words(re.sub(r"https?://[^/]+", "", p["key"]).replace("-", " ")) for p in pages]

    def covered(q):
        w = _words(q)
        return any(len(w & pw) >= max(2, len(w) // 2 + 1) for pw in page_words) if w else True
    gaps = [q for q in queries if q["impressions"] >= 20 and q["position"] > 10 and not covered(q["key"])]
    gaps.sort(key=lambda q: -q["impressions"])

    top = sorted(pages, key=lambda p: -p["clicks"])[:10]
    totals = {"clicks": int(sum(p["clicks"] for p in pages) or sum(q["clicks"] for q in queries)),
              "impressions": int(sum(p["impressions"] for p in pages) or sum(q["impressions"] for q in queries)),
              "pages": len(pages), "queries": len(queries)}
    return {"totals": totals, "almost_page1": almost[:15], "low_ctr": low_ctr[:15], "new_topics": gaps[:20],
            "top_pages": top}


def _file(profile: str):
    return config.CONFIG_DIR / ("gsc-" + re.sub(r"[^a-zA-Z0-9_-]+", "_", profile)[:60] + ".json")


def save(profile: str, result: dict) -> None:
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _file(profile).write_text(json.dumps(result), encoding="utf-8")


def load(profile: str) -> dict:
    try:
        return json.loads(_file(profile).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
