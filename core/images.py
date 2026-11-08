"""Free stock photos from Pexels (license allows free use; we always credit the photographer)."""
import requests


def pexels_search(api_key: str, query: str, count: int = 5, orientation: str = "landscape") -> list:
    if not api_key:
        return []
    r = requests.get("https://api.pexels.com/v1/search",
                     params={"query": query, "per_page": count, "orientation": orientation},
                     headers={"Authorization": api_key.strip()}, timeout=30)
    if not r.ok:
        raise RuntimeError(f"Pexels error HTTP {r.status_code}: {r.text[:200]}")
    out = []
    for p in r.json().get("photos", []):
        out.append({
            "download_url": p["src"].get("large2x") or p["src"].get("large") or p["src"]["original"],
            "photographer": p.get("photographer", ""),
            "photographer_url": p.get("photographer_url", ""),
            "page_url": p.get("url", ""),
            "alt": p.get("alt") or query,
        })
    return out


def download(url: str) -> tuple:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "image/jpeg").split(";")[0]
