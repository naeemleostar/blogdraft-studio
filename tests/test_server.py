import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["BLOGDRAFT_HOME"] = tempfile.mkdtemp()

import server  # noqa: E402
from core import writer  # noqa: E402
from tests.test_core import FakeGemini  # noqa: E402


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.make_server(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def req(self, path, body=None, token=True, host=None):
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                   data=None if body is None else json.dumps(body).encode(),
                                   method="GET" if body is None else "POST")
        r.add_header("Content-Type", "application/json")
        if token:
            r.add_header("X-Token", server.TOKEN)
        if host:
            r.add_header("Host", host)
        try:
            with urllib.request.urlopen(r, timeout=10) as resp:
                raw = resp.read()
                return resp.status, raw
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def api(self, name, body=None):
        code, raw = self.req("/api/" + name, body or {})
        return code, json.loads(raw)

    def wait(self, jid):
        for _ in range(100):
            _, j = self.api("job", {"id": jid})
            if j["status"] != "running":
                return j
            time.sleep(0.05)
        self.fail("job did not finish")

    def test_index_and_static(self):
        code, raw = self.req("/")
        self.assertEqual(code, 200)
        self.assertIn(server.TOKEN.encode(), raw)
        self.assertNotIn(b"__TOKEN__", raw)
        for f in ("app.js", "style.css", "icons.js", "guide.js", "icon.svg"):
            self.assertEqual(self.req("/static/" + f)[0], 200, f)
        self.assertEqual(self.req("/static/../server.py")[0], 404)

    def test_security(self):
        self.assertEqual(self.req("/api/state", {}, token=False)[0], 403)
        self.assertEqual(self.req("/api/state", {}, host="evil.example.com")[0], 403)
        self.assertEqual(self.req("/", host="evil.example.com")[0], 403)

    def test_config_secrets_never_returned(self):
        code, st = self.api("config", {"gemini_api_key": "AIzaSECRETKEY1234", "niches": ["food", "bogus"],
                                       "target_words": 99999, "inline_images": 12, "wp_url": "myblog.com/"})
        self.assertEqual(code, 200)
        c = st["config"]
        self.assertEqual(c["gemini_api_key"], "")
        self.assertTrue(c["gemini_api_key_set"])
        self.assertEqual(c["gemini_api_key_hint"], "…1234")
        self.assertEqual(c["niches"], ["food"])
        self.assertEqual((c["target_words"], c["inline_images"]), (4000, 6))
        self.assertEqual(c["wp_url"], "https://myblog.com")
        # empty secret keeps the saved one
        self.api("config", {"gemini_api_key": ""})
        self.assertEqual(server.cfg()["gemini_api_key"], "AIzaSECRETKEY1234")
        self.assertNotIn(b"AIzaSECRETKEY1234", self.req("/api/state", {})[1])

    def test_topic_check(self):
        self.api("config", {"niches": ["tech"]})
        _, r = self.api("check_topic", {"topic": "Lakers vs Celtics odds tonight"})
        self.assertTrue(r["blocked"])
        _, r = self.api("check_topic", {"topic": "Best pumpkin pie recipe"})
        self.assertFalse(r["fits"])
        _, r = self.api("check_topic", {"topic": "iPhone battery drain fix"})
        self.assertTrue(r["fits"])

    def test_write_job_and_drafts(self):
        self.api("config", {"niches": ["tech"], "gemini_api_key": "k", "text_model": "m", "image_model": "im",
                            "wp_app_password": ""})
        server.STATE["cfg"]["wp_app_password"] = ""
        with mock.patch.object(writer, "Gemini", FakeGemini), mock.patch.object(writer, "resolve_url", lambda u: u), \
                mock.patch.object(FakeGemini, "generate_json", lambda self, p, s="", temperature=0.7: {
                    "title": "iOS 26.1: What Changed", "seo_title": "iOS 26.1", "slug": "ios-26-1",
                    "focus_keyword": "iOS 26.1", "meta_description": "x" * 140, "excerpt": "e", "category": "",
                    "tags": ["iOS"], "body_html": "<p>Intro</p><h2>A</h2><p>a</p>", "featured_image": {},
                    "inline_images": []}):
            _, r = self.api("write", {"topic": "iOS 26.1 update"})
            j = self.wait(r["job"])
        self.assertEqual(j["status"], "done", j)
        a = j["result"]["article"]
        self.assertEqual(a["title"], "iOS 26.1: What Changed")
        _, d = self.api("drafts")
        self.assertTrue(any(x["title"] == a["title"] for x in d["drafts"]))
        _, r = self.api("recheck", {"article": dict(a, body_html=a["body_html"] + "<p>Let's dive in, I tested it.</p>")})
        self.assertTrue(any("Generic AI" in w for w in r["article"]["warnings"]))
        self.assertTrue(any("invented first-person" in w for w in r["article"]["warnings"]))

    def test_blocked_write_refused(self):
        _, r = self.api("write", {"topic": "Powerball jackpot numbers"})
        j = self.wait(r["job"])
        self.assertEqual(j["status"], "error")
        self.assertIn("AdSense", j["error"])

    def test_missing_settings_message(self):
        server.STATE["cfg"]["wp_url"] = ""
        _, r = self.api("test_wordpress", {})
        j = self.wait(r["job"])
        self.assertIn("Please fill in Settings first", j["error"])


if __name__ == "__main__":
    unittest.main()
