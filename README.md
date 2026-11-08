# BlogDraft Studio

A free desktop app for WordPress bloggers. It finds topics for **your niche**, researches them on Google,
writes an SEO-ready article, adds images and saves it in WordPress as a **Draft**. You read it, add your own
experience and click **Publish** yourself.

It runs on your own computer and opens in your browser as a dashboard. Your keys stay on your computer.

## Download (Windows, no Python needed)

1. Get **BlogDraft-Studio-Windows.zip** from the [latest release](https://github.com/naeemleostar/blogdraft-studio/releases/latest).
2. Right-click the zip → **Extract All**. Open the folder and double-click **BlogDraft Studio.exe**.
3. If Windows shows **"Windows protected your PC"**: click **More info** → **Run anyway**
   (the app is open source but not code-signed yet).

Problems? Click **Report a problem** in the app, or [open a bug report](https://github.com/naeemleostar/blogdraft-studio/issues/new?template=bug_report.yml).

## Start from the source code

**Windows:** double-click **`Start BlogDraft Studio (Windows).bat`**.
The first start takes a minute (it sets things up). If Python is missing, the file opens the download page:
install Python and tick **"Add python.exe to PATH"**, then double-click the file again.

**Mac / Linux:** run `./start_mac_linux.sh`.

The dashboard opens at `http://127.0.0.1:8765`. To stop the app, click **Quit app** in the sidebar.

## First-time setup (about 10 minutes)

Open **Setup Guide** in the app (English and Roman Urdu). In short:

1. **WordPress Application Password**: WordPress → Users → Profile → Application Passwords → Add New → copy.
2. **Gemini API key**: [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create API key → copy.
   Writing works on the free tier. AI images usually need billing turned on in Google AI Studio.
3. **Pexels API key** (optional, free photos): [pexels.com/api](https://www.pexels.com/api/).
4. In **Settings**: tick your niche → **Apply recommended settings** → paste the keys →
   **Save & test WordPress**, **Save & detect models**, **Test AI image** / **Save & test Pexels**.
5. Optional: install `wp-plugin/blogdraft-studio-bridge.zip` in WordPress (Plugins → Add New → Upload) so the app
   can also fill the Yoast SEO / Rank Math title, description and focus keyword.

## Features

- **Find Topics**: Google "Trending now" for 23 countries, filtered to your niche (18 niches), plus AI and Google
  keyword ideas. Gambling, adult, violence and tragedy topics are always hidden.
- **Write Post**: Google-grounded research, the article with SEO title, slug, meta description, tags, category,
  internal links to your own posts and source links. Live preview, Google result preview and SEO score.
- **Checks**: invented "I tested…" claims, generic AI phrases, missing internal links and meta length.
- **Images**: free Pexels photos (credited) or Gemini AI images (captioned "AI-generated image").
- **Settings per niche**: article length, number of images, tone, language, FAQ, sources list, and stricter
  rules plus a disclaimer for health and money niches.

## More tools (v3)

- **Outline first**, then write from your edited outline.
- **Your own photos & screenshots** go into the post before stock or AI images.
- **Fact-check**: lists claims that are not in the research. **Readability & SEO** report.
- **Duplicate check**: warns when your site already has a post on the same topic.
- **Content calendar** with a weekly post limit, and **Plan** buttons on Find Topics.
- **Update Old Posts**: finds what changed since a post was written and suggests edits (applied only when you click Apply; WordPress keeps revisions).
- **Links from older posts**: after publishing, suggests older posts where a link to the new one fits.
- **Social posts**: Facebook, X, LinkedIn, Pinterest text and a YouTube Short script.
- **Several sites**, each with its own niche and settings (Site menu, top left).
- **OpenAI or Claude** can write the article (research stays on Gemini + Google Search). OpenAI images optional.
- **AI usage / cost estimate** on the Dashboard, **update check**, and **Report a problem** (keys removed).

## Make the .exe (so your viewers don't need Python)

- **On a Windows PC:** double-click `build_exe.bat`. It creates `release\BlogDraft-Studio-Windows.zip`
  (the `.exe` + the WordPress plugin + this README). Share that zip.
- **Or on GitHub (free):** every push to `main` runs `.github/workflows/build-windows.yml`, which builds the zip
  and puts it in a GitHub Release named after `APP_VERSION` in `core/config.py` (e.g. `v3.0`). For a new release,
  raise `APP_VERSION` and push.
- **Update check:** upload `latest.json` (edit the version and link) somewhere public, for example in your GitHub
  repository, and put its raw link in `core/config.py` → `UPDATE_URL` before building. When you release a new
  version, raise the version in `latest.json`; users then see a "new version" banner.

## Use it responsibly

The app saves **drafts only**. Read every draft and check the facts against the Sources list before you publish.
Add your own photos, screenshots and experience. Publish 2–3 good posts a week, not dozens: mass-publishing
unedited AI content breaks Google's spam policies and AdSense rules.

## Files

- Settings: `%USERPROFILE%\.blogdraft_studio\config.json` (Windows) or `~/.blogdraft_studio/config.json`
- Drafts: the `drafts` folder next to it
- Tests: `python -m unittest discover tests`

## License

MIT — free to use, share and change. See [LICENSE](LICENSE).
