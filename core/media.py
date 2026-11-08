"""Image helpers: make photos light (WebP, max 1600 px wide) so pages load fast, and FAQ schema."""
import html
import io
import json
import re

try:
    from PIL import Image
except ImportError:  # Pillow is optional: images are then uploaded unchanged
    Image = None


def compress(data: bytes, mime: str, max_width: int = 1600, quality: int = 82) -> tuple:
    """Returns (bytes, mime). Falls back to the original when Pillow is missing or the image is a GIF."""
    if Image is None or mime == "image/gif":
        return data, mime
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
        if im.width > max_width:
            im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "WEBP", quality=quality, method=4)
        new = out.getvalue()
        return (new, "image/webp") if len(new) < len(data) else (data, mime)
    except Exception:  # noqa: BLE001 - never block publishing because of an image
        return data, mime


def faq_schema(body_html: str) -> str:
    """FAQPage JSON-LD from the article's "Frequently asked questions" section, or ""."""
    m = re.search(r"<h2[^>]*>\s*(Frequently asked questions|FAQ)[^<]*</h2>(.*?)(?=<h2|$)", body_html, re.S | re.I)
    if not m:
        return ""
    pairs = re.findall(r"<h3[^>]*>(.*?)</h3>\s*(.*?)(?=<h3|$)", m.group(2), re.S)
    items = []
    for q, a in pairs:
        q = html.unescape(re.sub(r"<[^>]+>", "", q)).strip()
        a = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", a)).split())
        if q and a:
            items.append({"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}})
    if not items:
        return ""
    data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": items}
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"
