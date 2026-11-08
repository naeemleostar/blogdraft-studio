import base64
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("BLOGDRAFT_HOME", tempfile.mkdtemp())

from core import gsc, media  # noqa: E402

PAGES = "﻿Top pages,Clicks,Impressions,CTR,Position\n" \
        "https://b.com/iphone-battery-fix/,40,4000,1%,6.2\n" \
        "https://b.com/best-budget-phones/,5,900,0.6%,12.4\n" \
        "https://b.com/old/,300,5000,6%,2.1\n"
QUERIES = "Top queries,Clicks,Impressions,CTR,Position\n" \
          "iphone battery fix,30,2000,1.5%,5\n" \
          "how to clean airpods,0,300,0%,24\n" \
          "budget phones,3,500,0.6%,13\n"


class GscTests(unittest.TestCase):
    def test_zip_and_recommendations(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Pages.csv", PAGES)
            z.writestr("Queries.csv", QUERIES)
            z.writestr("Dates.csv", "Date,Clicks,Impressions,CTR,Position\n2026-11-01,1,2,50%,3\n")
        data = gsc.parse_export(buf.getvalue())
        self.assertEqual(len(data["pages"]), 3)
        self.assertEqual(len(data["queries"]), 3)
        r = gsc.recommend(data)
        self.assertEqual([p["key"] for p in r["almost_page1"]], ["https://b.com/best-budget-phones/"])
        self.assertEqual([p["key"] for p in r["low_ctr"]], ["https://b.com/iphone-battery-fix/"])
        self.assertEqual([q["key"] for q in r["new_topics"]], ["how to clean airpods"])
        self.assertEqual(r["top_pages"][0]["key"], "https://b.com/old/")
        self.assertEqual(r["totals"]["clicks"], 345)

    def test_bad_file(self):
        with self.assertRaises(ValueError):
            gsc.parse_export(b"hello,world\n1,2\n", "x.csv")


class MediaTests(unittest.TestCase):
    def test_compress_png_to_webp(self):
        if media.Image is None:
            self.skipTest("Pillow not installed")
        im = media.Image.frombytes("RGB", (2400, 1200), os.urandom(2400 * 1200 * 3))  # photo-like: hard to compress
        b = io.BytesIO()
        im.save(b, "PNG")
        out, mime = media.compress(b.getvalue(), "image/png")
        self.assertEqual(mime, "image/webp")
        self.assertLess(len(out), len(b.getvalue()))
        self.assertEqual(media.Image.open(io.BytesIO(out)).width, 1600)
        self.assertEqual(media.compress(b"GIF89a", "image/gif"), (b"GIF89a", "image/gif"))
        self.assertEqual(media.compress(b"not an image", "image/png"), (b"not an image", "image/png"))

    def test_faq_schema(self):
        body = ("<p>x</p><h2>Frequently asked questions</h2><h3>Is it free?</h3><p>Yes, <b>free</b>.</p>"
                "<h3>Does it work offline?</h3><p>No.</p><h2>Sources</h2>")
        s = media.faq_schema(body)
        data = json.loads(s.split(">", 1)[1].rsplit("<", 1)[0])
        self.assertEqual(data["@type"], "FAQPage")
        self.assertEqual([q["name"] for q in data["mainEntity"]], ["Is it free?", "Does it work offline?"])
        self.assertEqual(data["mainEntity"][0]["acceptedAnswer"]["text"], "Yes, free .")
        self.assertEqual(media.faq_schema("<p>no faq</p>"), "")


class BackupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import threading
        import server
        cls.server = server
        cls.srv = server.make_server(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def api(self, name, body=None):
        import urllib.request
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/{name}", data=json.dumps(body or {}).encode(),
                                   method="POST", headers={"Content-Type": "application/json", "X-Token": self.server.TOKEN})
        try:
            with urllib.request.urlopen(r, timeout=15) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_export_import_roundtrip_and_gsc(self):
        self.api("config", {"gemini_api_key": "AIzaBACKUPKEY77", "site_name": "Roundtrip"})
        _, ex = self.api("export", {"include_keys": False})
        raw = base64.b64decode(ex["data"])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            cfgtext = z.read("config.json").decode()
        self.assertNotIn("AIzaBACKUPKEY77", cfgtext)
        self.assertIn("Roundtrip", cfgtext)
        # change something, then restore: setting comes back, key is kept
        self.api("config", {"site_name": "Changed"})
        code, st = self.api("import", {"data": ex["data"]})
        self.assertEqual(code, 200)
        self.assertEqual(st["config"]["site_name"], "Roundtrip")
        self.assertTrue(st["config"]["gemini_api_key_set"])
        code, _ = self.api("import", {"data": base64.b64encode(b"not a zip").decode()})
        self.assertEqual(code, 400)
        # search console import
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Pages.csv", PAGES)
            z.writestr("Queries.csv", QUERIES)
        code, r = self.api("gsc", {"data": "data:application/zip;base64," + base64.b64encode(buf.getvalue()).decode(),
                                   "name": "export.zip"})
        self.assertEqual(code, 200)
        self.assertEqual(r["totals"]["pages"], 3)
        _, again = self.api("gsc", {})
        self.assertEqual(again["totals"]["pages"], 3)


if __name__ == "__main__":
    unittest.main()
