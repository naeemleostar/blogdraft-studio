/* BlogDraft Studio — dashboard front-end (vanilla JS, talks only to the local app server). */
'use strict';

const TOKEN = document.querySelector('meta[name="app-token"]').content;
const $ = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const store = {
  get(k, d) { try { const v = localStorage.getItem('bds_' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('bds_' + k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } },
};

const COUNTRIES = [['US', 'United States'], ['GB', 'United Kingdom'], ['CA', 'Canada'], ['AU', 'Australia'], ['IN', 'India'],
  ['PK', 'Pakistan'], ['AE', 'UAE'], ['SA', 'Saudi Arabia'], ['NG', 'Nigeria'], ['ZA', 'South Africa'], ['PH', 'Philippines'],
  ['MY', 'Malaysia'], ['ID', 'Indonesia'], ['DE', 'Germany'], ['FR', 'France'], ['ES', 'Spain'], ['IT', 'Italy'],
  ['BR', 'Brazil'], ['MX', 'Mexico'], ['JP', 'Japan'], ['KR', 'South Korea'], ['TR', 'Turkey'], ['BD', 'Bangladesh']];
const IMAGE_SOURCES = { pexels_then_gemini: 'free photo first, then AI', pexels: 'free photos', gemini: 'AI images', openai: 'OpenAI images', none: 'no images' };

const UI_VERSION = '3.1';
const S = { cfg: {}, niches: [], article: store.get('article', null), trends: [], news: [], newsTopic: '', wpOk: null, planId: '', usage: null, updChecked: false };

/* ------------------------------------------------------------------ API */
async function api(name, body) {
  const r = await fetch('/api/' + name, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Token': TOKEN }, body: JSON.stringify(body || {}),
  });
  let data = {};
  try { data = await r.json(); } catch (e) { /* not json */ }
  if (!r.ok) throw new Error(data.error || ('Error ' + r.status));
  return data;
}

async function runJob(name, body, opts) {
  opts = opts || {};
  const { job } = await api(name, body);
  let seen = 0;
  for (;;) {
    await new Promise((res) => setTimeout(res, 700));
    const j = await api('job', { id: job });
    if (!opts.quiet) j.logs.slice(seen).forEach((l) => log(l));
    if (opts.onLog) j.logs.slice(seen).forEach((l) => opts.onLog(l));
    seen = j.logs.length;
    if (j.status === 'done') return j.result;
    if (j.status === 'error') throw new Error(j.error);
  }
}

async function busy(btn, fn) {
  if (btn.disabled) return;
  const html = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span>' + btn.textContent.trim();
  try { return await fn(); } catch (e) { toast(e.message, 'err'); log(e.message, 'err'); } finally {
    btn.disabled = false; btn.innerHTML = html; paintIcons(btn);
  }
}

/* ------------------------------------------------------------------ UI helpers */
function toast(msg, kind) {
  const el = document.createElement('div');
  el.className = 'toast ' + (kind || 'ok');
  el.innerHTML = `<i data-icon="${kind === 'err' ? 'alert' : 'check'}"></i><div>${esc(msg)}</div>`;
  $('#toasts').appendChild(el);
  paintIcons(el);
  setTimeout(() => el.remove(), kind === 'err' ? 8000 : 4000);
}

function log(msg, cls) {
  const box = $('#log');
  if (box.querySelector('.muted')) box.innerHTML = '';
  const line = document.createElement('div');
  if (cls) line.className = cls;
  line.textContent = msg;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

function nicheLabel(id) { const n = S.niches.find((x) => x.id === id); return n ? n.label : id; }

function renderChips(container, onChange) {
  container.innerHTML = S.niches.map((n) => `
    <button type="button" class="chip ${S.cfg.niches.includes(n.id) ? 'on' : ''}" data-id="${n.id}" title="${esc(n.hint)}">
      <span class="ck">${S.cfg.niches.includes(n.id) ? iconSvg('check') : ''}</span>
      <i data-icon="${n.icon}"></i>${esc(n.label)}${n.ymyl ? '<span class="ymyl">YMYL</span>' : ''}</button>`).join('');
  paintIcons(container);
  $$('.chip', container).forEach((c) => c.addEventListener('click', () => {
    const id = c.dataset.id;
    const set = new Set(S.cfg.niches);
    set.has(id) ? set.delete(id) : set.add(id);
    S.cfg.niches = S.niches.map((n) => n.id).filter((x) => set.has(x));
    onChange();
  }));
}

function geoOptions(sel, value) {
  sel.innerHTML = COUNTRIES.map(([c, n]) => `<option value="${c}">${n}</option>`).join('');
  sel.value = value || 'US';
}

/* ------------------------------------------------------------------ router */
function route() {
  const hash = (location.hash || '#dashboard').slice(1);
  let page = hash.startsWith('guide') ? 'guide' : hash;
  if (!$('#page-' + page)) page = 'dashboard';
  $$('.page').forEach((p) => p.classList.toggle('active', p.id === 'page-' + page));
  $$('nav a').forEach((a) => a.classList.toggle('active', a.dataset.page === page));
  if (page === 'dashboard') loadDashboard();
  if (page === 'drafts') loadDrafts();
  if (page === 'topics') renderChips($('#topicNiches'), saveNichesQuick);
  if (page === 'settings') fillSettings();
  if (page === 'calendar') loadPlan();
  if (page === 'update' && !$('#postList').children.length) searchPosts();
  if (page === 'guide') { renderGuide(); if (hash !== 'guide') setTimeout(() => { const el = document.getElementById(hash); if (el) el.scrollIntoView({ behavior: 'smooth' }); }, 50); }
  window.scrollTo(0, 0);
}

/* ------------------------------------------------------------------ state */
async function loadState() {
  const st = await api('state');
  S.cfg = st.config;
  S.niches = st.niches;
  S.draftsDir = st.drafts_dir;
  S.usage = st.usage;
  $('#verText').textContent = `${st.app} v${st.version}`;
  const sel = $('#siteSel');
  sel.innerHTML = (S.cfg.profiles || []).map((n) => `<option>${esc(n)}</option>`).join('');
  sel.value = S.cfg.profile;
  if (S.cfg.check_updates && !S.updChecked) {
    S.updChecked = true;
    runJob('check_update', {}, { quiet: true }).then(showUpdate).catch(() => {});
  }
  if (st.version !== UI_VERSION) {
    const el = document.createElement('div');
    el.className = 'old-server';
    el.innerHTML = '<b>An older copy of the app is still running.</b> Click <b>Quit app</b> (bottom left), or end <code>pythonw.exe</code> in Task Manager, then start the app again with the start file.';
    document.body.prepend(el);
  }
  updatePill();
}

function showUpdate(u) {
  if (!u || !u.available) return;
  const b = $('#updateBanner');
  b.classList.remove('hidden');
  b.innerHTML = `<span><b>New version ${esc(u.latest)} is available</b> (you have ${esc(u.current)}). ${esc(u.notes || '')}</span>
    ${u.url ? `<a class="btn small primary" href="${esc(u.url)}" target="_blank" rel="noopener">Download</a>` : ''}`;
}

function updatePill() {
  const pill = $('#sitePill');
  const host = (S.cfg.wp_url || '').replace(/^https?:\/\/(www\.)?/, '');
  pill.classList.toggle('ok', !!S.wpOk);
  $('#sitePillText').textContent = host ? (S.wpOk ? host : host + (S.wpOk === false ? ' (check settings)' : '')) : 'No site connected';
}

async function saveNichesQuick() {
  renderChips($('#topicNiches'), saveNichesQuick);
  try { const st = await api('config', { niches: S.cfg.niches }); S.cfg = st.config; } catch (e) { toast(e.message, 'err'); }
  if (S.trends.length) toast('Niche changed: load the list again to update it.');
  if ($('#trendsLink')) $('#geoSel').dispatchEvent(new Event('change'));
}

/* ------------------------------------------------------------------ dashboard */
async function loadDashboard() {
  const c = S.cfg;
  $('#statNiche').textContent = (c.niches || []).map(nicheLabel).join(', ') || 'Not set';
  const u = S.usage;
  if (u) {
    $('#statCost').textContent = u.priced ? '$' + u.cost.toFixed(2) : String(u.requests);
    $('#statCostLabel').textContent = u.priced ? `Estimated AI cost in ${u.month} (${u.images} images)` : `AI requests in ${u.month} · ${u.images} images`;
  }
  loadWeekPlan();
  const items = [
    [c.niches && c.niches.length, 'Choose your niche', 'Settings → Your blog & niche', '#settings'],
    [c.wp_url && c.wp_user && c.wp_app_password_set, 'Connect WordPress', 'Site address, username, Application Password', '#guide-wp'],
    [c.gemini_api_key_set, 'Add your Gemini API key', 'Needed for research and writing', '#guide-gemini'],
    [c.text_model, 'Detect Gemini models', 'Settings → Save & detect models', '#settings'],
    [c.pexels_api_key_set || c.image_source === 'gemini' || c.image_source === 'none', 'Free photos (Pexels key)', 'Optional, for free stock photos', '#guide-pexels'],
  ];
  $('#checklist').innerHTML = items.map(([ok, t, s, href]) => `
    <li class="${ok ? 'done' : 'todo'}"><span class="ic">${iconSvg(ok ? 'check' : 'arrow')}</span>
      <div class="grow"><b>${esc(t)}</b><span>${esc(s)}</span></div>${ok ? '<span class="badge green">Done</span>' : `<a class="btn small" href="${href}">Set up</a>`}</li>`).join('');

  try {
    const d = await api('drafts');
    $('#statLocal').textContent = d.drafts.length;
    $('#recentDrafts').innerHTML = draftRows(d.drafts.slice(0, 5)) || '<div class="empty"><i data-icon="file"></i><p>No drafts yet. Write your first post!</p></div>';
    bindDraftRows($('#recentDrafts'));
    paintIcons($('#recentDrafts'));
  } catch (e) { /* ignore */ }

  if (c.wp_url && c.wp_user && c.wp_app_password_set) {
    try {
      const s = await runJob('site_stats', {}, { quiet: true });
      S.wpOk = true;
      $('#statWeek').textContent = s.published_7d;
      $('#statWpDrafts').textContent = s.drafts;
      pace(s.published_7d);
    } catch (e) { S.wpOk = false; $('#paceBox').innerHTML = `<span>Couldn't reach WordPress: ${esc(e.message)}</span>`; }
    updatePill();
  } else {
    $('#paceBox').innerHTML = '<span>Connect WordPress to see your posting pace.</span>';
  }
}

function pace(n) {
  const box = $('#paceBox');
  const lim = +S.cfg.posts_per_week || 3;
  box.className = 'pace ' + (n > lim ? 'warn' : 'good');
  box.innerHTML = `<span class="big">${n}</span><span>${n > lim
    ? `posts this week, above your limit of ${lim}. Slow down to a few carefully edited posts a week.`
    : n === 0 ? 'posts this week. Aim for 2–3 good posts a week.' : 'posts this week. A healthy pace — keep quality high.'}</span>`;
}

/* ------------------------------------------------------------------ topics */
function renderTrends() {
  const only = $('#onlyNiche').checked;
  const list = S.trends.filter((t) => !t.blocked && (!only || t.fits));
  const box = $('#trendList');
  if (!S.trends.length) return;
  const hidden = S.trends.length - list.length;
  $('#trendSummary').textContent = S.source === 'news' ? `${list.length} stories, most covered first`
    : `${list.length} shown · ${hidden} hidden (other niches or not AdSense-safe)`;
  if (!list.length) {
    box.innerHTML = S.source === 'news'
      ? '<div class="empty"><i data-icon="search"></i><p>No stories found for this niche and country. Try another country or add an "Extra niche detail" in Settings.</p></div>'
      : `<div class="empty"><i data-icon="search"></i><p>None of today's top searches in this country is about your niche.
      Click <b>Hot in my niche</b>, or try <b>Evergreen ideas</b> / <b>Keyword ideas</b> on the right.</p></div>`;
    paintIcons(box);
    return;
  }
  box.innerHTML = list.map((t) => {
    const i = S.trends.indexOf(t);
    const badges = (t.niches || []).map((n) => `<span class="badge ${S.cfg.niches.includes(n) ? 'brand' : ''}">${esc(nicheLabel(n))}</span>`).join('');
    const news = (t.news || []).slice(0, 3).map((n) => `<li><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title)}</a> <span class="src">— ${esc(n.source)}</span></li>`).join('');
    return `<div class="trend ${t.fits ? '' : 'off'}">
      <div class="trend-top"><div class="trend-title">${esc(t.title)}</div><span class="traffic">${esc(t.traffic)}${S.source === 'news' ? '' : ' searches'}</span>
        <button class="btn small" data-copy="${i}" title="Copy details"><i data-icon="copy"></i></button>
        <button class="btn small" data-plan="${esc(t.title)}" title="Add to calendar"><i data-icon="calendar"></i></button>
        <button class="btn small primary" data-use="${i}">Write this</button></div>
      ${badges ? `<div class="trend-badges">${badges}</div>` : ''}
      ${news ? `<ul class="trend-news">${news}</ul>` : ''}</div>`;
  }).join('');
  paintIcons(box);
  $$('[data-use]', box).forEach((b) => b.addEventListener('click', () => {
    const t = S.trends[+b.dataset.use];
    useTopic(t.title, '', t.news || []);
  }));
  bindPlanButtons(box);
  $$('[data-copy]', box).forEach((b) => b.addEventListener('click', async () => {
    const t = S.trends[+b.dataset.copy];
    const text = [t.title, ...(t.news || []).map((n) => `• ${n.title} — ${n.source}\n  ${n.url}`)].join('\n');
    try { await navigator.clipboard.writeText(text); toast('Copied'); } catch (e) { toast('Copy not allowed here — select the text instead.', 'err'); }
  }));
}

function bindPlanButtons(box) {
  $$('[data-plan]', box).forEach((b) => b.addEventListener('click', async () => {
    try {
      const cur = await api('plan', {});
      const used = new Set(cur.items.map((x) => x.date));
      const date = cur.suggested_dates.find((d) => !used.has(d)) || cur.suggested_dates[cur.suggested_dates.length - 1];
      await api('plan', { action: 'add', date, topic: b.dataset.plan, angle: b.dataset.angle || '' });
      b.outerHTML = `<span class="badge green">Planned ${esc(date)}</span>`;
    } catch (e) { toast(e.message, 'err'); }
  }));
}

function renderIdeas(items, kind) {
  const box = $('#ideaList');
  if (!items.length) { box.innerHTML = '<div class="empty"><p>No ideas found. Try another option.</p></div>'; return; }
  box.innerHTML = items.map((it, i) => `<div class="idea"><div class="grow"><b>${esc(it.topic)}</b>
    ${it.angle ? `<span>${esc(it.angle)}</span>` : ''}${it.trend ? `<span> · from trend “${esc(it.trend)}”</span>` : ''}</div>
    <button class="btn small" data-plan="${esc(it.topic)}" data-angle="${esc(it.angle || '')}" title="Add to calendar"><i data-icon="calendar"></i></button>
    <button class="btn small primary" data-i="${i}">Write this</button></div>`).join('');
  paintIcons(box);
  bindPlanButtons(box);
  $$('[data-i]', box).forEach((b) => b.addEventListener('click', () => {
    const it = items[+b.dataset.i];
    const t = it.trend ? S.trends.find((x) => x.title === it.trend) : null;
    useTopic(it.topic, it.angle || '', t ? t.news : []);
  }));
  void kind;
}

function useTopic(topic, angle, news, planId) {
  S.planId = planId || '';
  S.news = news || [];
  S.newsTopic = topic;
  $('#topicInput').value = topic;
  $('#angleInput').value = angle || '';
  location.hash = '#write';
  checkTopic();
  renderNews();
  setStep(1);
}

/* ------------------------------------------------------------------ write */
function setStep(n) {
  $$('#writeSteps .step').forEach((s) => {
    const k = +s.dataset.step;
    s.classList.toggle('done', k < n);
    s.classList.toggle('active', k === n);
  });
}

function renderNews() {
  const box = $('#newsBox');
  const show = S.news.length && $('#topicInput').value.trim() === S.newsTopic;
  box.classList.toggle('hidden', !show);
  if (show) box.innerHTML = '<b>Headlines used as research hints:</b><br>' + S.news.slice(0, 3).map((n) => '• ' + esc(n.title) + ' — ' + esc(n.source)).join('<br>');
}

let topicTimer;
function checkTopic() {
  clearTimeout(topicTimer);
  topicTimer = setTimeout(async () => {
    const topic = $('#topicInput').value.trim();
    const warn = $('#topicWarn');
    if (!topic) { warn.classList.add('hidden'); return; }
    try {
      const r = await api('check_topic', { topic, angle: $('#angleInput').value });
      if (r.blocked) {
        warn.className = 'inline-warn red';
        warn.textContent = 'Gambling, adult, violence or tragedy topic: this breaks AdSense rules, so the app won\'t write it.';
      } else if (!r.fits) {
        warn.className = 'inline-warn';
        warn.textContent = 'This topic doesn\'t look like your niche (' + S.cfg.niches.map(nicheLabel).join(', ') + '). Off-niche posts can hurt AdSense approval.';
      } else warn.className = 'inline-warn hidden';
    } catch (e) { /* ignore */ }
    renderNews();
  }, 350);
}

const FIELDS = ['title', 'seo_title', 'slug', 'focus_keyword', 'meta_description', 'category'];

function showArticle() {
  const a = S.article;
  const has = !!(a && a.body_html);
  ['#seoCard', '#checksCard', '#bodyCard', '#linksCard'].forEach((id) => $(id).classList.toggle('hidden', !has));
  const hasOutline = !!(a && a.outline);
  $('#outlineCard').classList.toggle('hidden', !hasOutline);
  if (hasOutline) $('#outlineInput').value = a.outline;
  renderOwnImages();
  if (a && !has) {
    $('#topicInput').value = a.topic || '';
    $('#angleInput').value = a.angle || '';
    $('#expInput').value = a.experience_notes || '';
    setStep(hasOutline ? 2 : 1);
  }
  if (!has) return;
  FIELDS.forEach((f) => { $('#f_' + f).value = a[f] || ''; });
  $('#f_tags').value = (a.tags || []).join(', ');
  $('#f_body_html').value = a.body_html;
  $('#topicInput').value = a.topic || '';
  $('#angleInput').value = a.angle || '';
  $('#expInput').value = a.experience_notes || '';
  $('#sourceList').innerHTML = (a.sources || []).map(([t, u]) => `<li>${esc(t)}<br><a href="${esc(u)}" target="_blank" rel="noopener">${esc(u)}</a></li>`).join('') || '<li class="muted">No sources were found. Check facts carefully.</li>';
  const open = $('#openWpBtn');
  open.classList.toggle('hidden', !a.wp_post_id);
  if (a.wp_post_id && S.cfg.wp_url) open.href = `${S.cfg.wp_url}/wp-admin/post.php?post=${a.wp_post_id}&action=edit`;
  renderChecks();
  renderSocial();
  refreshSeo();
  refreshPreview();
  setStep(a.wp_post_id ? 6 : 4);
}

function readArticle() {
  const a = S.article;
  if (!a) return null;
  FIELDS.forEach((f) => { a[f] = $('#f_' + f).value.trim(); });
  a.tags = $('#f_tags').value.split(',').map((s) => s.trim()).filter(Boolean);
  a.body_html = $('#f_body_html').value;
  a.experience_notes = $('#expInput').value;
  if (!$('#outlineCard').classList.contains('hidden')) a.outline = $('#outlineInput').value;
  store.set('article', a);
  return a;
}

function refreshSeo() {
  const a = readArticle();
  if (!a) return;
  const seo = a.seo_title.length, meta = a.meta_description.length;
  const cs = $('#c_seo'), cm = $('#c_meta');
  cs.textContent = seo + ' / 60'; cs.className = 'count ' + (seo > 0 && seo <= 60 ? 'ok' : 'bad');
  cm.textContent = meta + ' / 160'; cm.className = 'count ' + (meta >= 120 && meta <= 160 ? 'ok' : 'bad');
  const host = (S.cfg.wp_url || 'https://your-blog.com').replace(/^https?:\/\//, '').replace(/\/$/, '');
  $('#serp').innerHTML = `<div class="u">${esc(host)} › ${esc(a.slug)}</div><div class="t">${esc(a.seo_title || a.title)}</div><div class="d">${esc(a.meta_description)}</div>`;
  const kw = a.focus_keyword.toLowerCase();
  let score = 0;
  if (seo > 0 && seo <= 60) score++;
  if (meta >= 120 && meta <= 160) score++;
  if (kw && a.seo_title.toLowerCase().includes(kw)) score++;
  if (kw && a.meta_description.toLowerCase().includes(kw)) score++;
  if (kw && a.body_html.toLowerCase().includes(kw)) score++;
  const b = $('#seoScore');
  b.textContent = `SEO ${score}/5`;
  b.className = 'badge ' + (score >= 4 ? 'green' : score >= 3 ? 'amber' : 'red');
}

let pvTimer;
function refreshPreview() {
  clearTimeout(pvTimer);
  pvTimer = setTimeout(() => {
    const a = readArticle();
    if (!a) return;
    const words = a.body_html.replace(/<[^>]+>/g, ' ').split(/\s+/).filter(Boolean).length;
    $('#wordCount').textContent = `~${words} words`;
    const marker = a.experience_notes.trim()
      ? '<div class="exp"><b>Your experience</b> will be written here (in first person) when you save the draft.</div>'
      : '<div class="exp warn">Your experience section goes here — add a few lines in the "Your own experience" box.</div>';
    const body = a.body_html.replace('<!--MY_EXPERIENCE-->', marker);
    const sources = (a.sources || []).length && S.cfg.sources_section !== false
      ? '<h2>Sources</h2><ul>' + a.sources.map(([t, u]) => `<li><a href="${esc(u)}">${esc(t)}</a></li>`).join('') + '</ul>' : '';
    $('#previewFrame').srcdoc = `<!doctype html><html><head><meta charset="utf-8"><style>
      body{font-family:Georgia,serif;max-width:720px;margin:20px auto;padding:0 18px;line-height:1.75;color:#1f2937;font-size:16.5px}
      h1,h2,h3{font-family:'Segoe UI',system-ui,Arial;line-height:1.3;color:#0f172a} h1{font-size:28px} h2{font-size:21px;margin-top:28px}
      a{color:#4f46e5} table{border-collapse:collapse;width:100%} td,th{border:1px solid #e5e7eb;padding:6px 10px}
      .exp{font-family:'Segoe UI',Arial;background:#eef2ff;color:#3730a3;padding:12px 14px;border-radius:10px;font-size:14px}
      .exp.warn{background:#fef3c7;color:#92400e} .img{font-family:'Segoe UI',Arial;font-size:13px;color:#64748b}</style></head>
      <body><h1>${esc(a.title)}</h1><p class="img">Featured image and ${S.cfg.image_source === 'none' ? 'no' : S.cfg.inline_images} inline image(s) are added when you save the draft.</p>${body}${sources}</body></html>`;
  }, 250);
}

function renderChecks() {
  const a = S.article;
  const w = (a && a.warnings) || [];
  $('#checkList').innerHTML = w.length
    ? w.map((x) => `<li class="warn"><i data-icon="alert"></i><span>${esc(x)}</span></li>`).join('')
    : '<li class="ok"><i data-icon="check"></i><span>No problems found. Still read it once and check the facts.</span></li>';
  paintIcons($('#checkList'));
  const fi = (a && a.fact_issues) || [];
  $('#factBox').classList.toggle('hidden', !(a && a._factChecked) && !fi.length);
  $('#factList').innerHTML = fi.length
    ? fi.map((x) => `<li class="warn"><i data-icon="alert"></i><span><b>${esc(x.problem)}:</b> “${esc(x.sentence)}” <span class="muted">${esc(x.note)}</span></span></li>`).join('')
    : '<li class="ok"><i data-icon="check"></i><span>Every claim was found in the research.</span></li>';
  paintIcons($('#factList'));
  const rows = (a && a.seo_report) || [];
  $('#seoReport').innerHTML = rows.map((r) => `<tr><td><span class="dot ${r.ok === true ? 'ok' : r.ok === false ? 'bad' : ''}"></span>${esc(r.label)}</td><td>${esc(r.value)}</td></tr>`).join('')
    || '<tr><td class="muted">Click Re-check to see readability and SEO.</td></tr>';
}

/* ------------------------------------------------------------------ own images */
function renderOwnImages() {
  const box = $('#ownImages');
  const imgs = (S.article && S.article.own_images) || S.pendingImages || [];
  if (!imgs.length) { box.innerHTML = '<p class="muted small">No images yet.</p>'; return; }
  const secs = ((S.article && S.article.body_html) || (S.article && S.article.outline) || '').match(/<h2[^>]*>(.*?)<\/h2>|^## (.*)$/gm) || [];
  const opts = secs.map((h, i) => `<option value="${i + 1}">after: ${esc(h.replace(/<[^>]+>|^## /g, '').slice(0, 40))}</option>`).join('')
    || [1, 2, 3, 4, 5].map((i) => `<option value="${i}">after section ${i}</option>`).join('');
  box.innerHTML = imgs.map((im, i) => `<div class="own-img" data-i="${i}">
    <img src="/media/${esc(im.file)}" alt="">
    <input data-f="alt" placeholder="Describe the image (alt text)" value="${esc(im.alt || '')}">
    <input data-f="caption" placeholder="Caption (optional)" value="${esc(im.caption || '')}">
    <div class="row"><select data-f="after_h2">${opts}</select></div>
    <div class="row between"><label class="switch"><input type="checkbox" data-f="featured" ${im.featured ? 'checked' : ''}><span></span>Featured</label>
      <button class="btn small ghost" data-rm="${i}" title="Remove"><i data-icon="trash"></i></button></div></div>`).join('');
  $$('.own-img', box).forEach((el) => {
    const im = imgs[+el.dataset.i];
    $('[data-f="after_h2"]', el).value = String(im.after_h2 || 1);
    $$('[data-f]', el).forEach((inp) => inp.addEventListener('change', () => {
      const f = inp.dataset.f;
      im[f] = inp.type === 'checkbox' ? inp.checked : (f === 'after_h2' ? +inp.value : inp.value);
      if (f === 'featured' && inp.checked) imgs.forEach((o) => { if (o !== im) o.featured = false; });
      if (S.article) store.set('article', S.article);
      if (f === 'featured') renderOwnImages();
    }));
  });
  $$('[data-rm]', box).forEach((b) => b.addEventListener('click', () => { imgs.splice(+b.dataset.rm, 1); if (S.article) store.set('article', S.article); renderOwnImages(); }));
  paintIcons(box);
}

function ownImageList() {
  if (S.article) { S.article.own_images = S.article.own_images || []; return S.article.own_images; }
  S.pendingImages = S.pendingImages || [];
  return S.pendingImages;
}

/* ------------------------------------------------------------------ social */
function renderSocial() {
  const so = (S.article && S.article.social) || {};
  const items = [];
  if (so.facebook) items.push(['Facebook', so.facebook]);
  if (so.x) items.push(['X (Twitter)', so.x]);
  if (so.linkedin) items.push(['LinkedIn', so.linkedin]);
  if (so.pinterest) items.push(['Pinterest', `${so.pinterest.title || ''}\n\n${so.pinterest.description || ''}`]);
  if (so.youtube_short) items.push(['YouTube Short', `${so.youtube_short.title || ''}\n\n${so.youtube_short.script || ''}`]);
  $('#socialBox').innerHTML = items.map(([k, v], i) => `<div class="social-item"><div class="head">${k}<button class="btn small" data-sc="${i}"><i data-icon="copy"></i>Copy</button></div><pre>${esc(v)}</pre></div>`).join('');
  paintIcons($('#socialBox'));
  $$('[data-sc]', $('#socialBox')).forEach((b) => b.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(items[+b.dataset.sc][1]); toast('Copied'); } catch (e) { toast('Select the text and copy it.', 'err'); }
  }));
}

/* ------------------------------------------------------------------ calendar */
async function loadPlan(r) {
  r = r || await api('plan', {});
  S.plan = r;
  $('#paceBadge').textContent = `Limit: ${r.posts_per_week} posts / week`;
  if (!$('#planDate').value) $('#planDate').value = r.suggested_dates[0];
  $('#planHint').textContent = `Suggested days this week: ${r.suggested_dates.join(', ')}`;
  const box = $('#planList');
  if (!r.items.length) { box.innerHTML = '<div class="empty"><i data-icon="calendar"></i><p>Nothing planned yet. Add topics above, or use "Plan" on Find Topics.</p></div>'; paintIcons(box); return; }
  let last = '';
  box.innerHTML = r.items.map((it) => {
    const day = it.date !== last ? `<div class="plan-day">${esc(new Date(it.date + 'T00:00').toDateString())}</div>` : '';
    last = it.date;
    return `${day}<div class="plan-item"><div class="grow"><b>${esc(it.topic)}</b>${it.angle ? `<span>${esc(it.angle)}</span>` : ''}</div>
      <select data-st="${it.id}">${['planned', 'written', 'draft', 'published'].map((x) => `<option ${x === it.status ? 'selected' : ''}>${x}</option>`).join('')}</select>
      <button class="btn small primary" data-wr="${it.id}">Write</button>
      <button class="btn small ghost" data-pd="${it.id}" title="Remove"><i data-icon="trash"></i></button></div>`;
  }).join('');
  paintIcons(box);
  $$('[data-st]', box).forEach((el) => el.addEventListener('change', async () => loadPlan(await api('plan', { action: 'update', id: el.dataset.st, fields: { status: el.value } }))));
  $$('[data-pd]', box).forEach((el) => el.addEventListener('click', async () => loadPlan(await api('plan', { action: 'delete', id: el.dataset.pd }))));
  $$('[data-wr]', box).forEach((el) => el.addEventListener('click', () => {
    const it = r.items.find((x) => x.id === el.dataset.wr);
    S.article = null; store.set('article', null); showArticle();
    useTopic(it.topic, it.angle, [], it.id);
  }));
}

async function loadWeekPlan() {
  try {
    const r = await api('plan', {});
    const today = new Date().toISOString().slice(0, 10);
    const end = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);
    const items = r.items.filter((x) => x.date >= today && x.date <= end);
    $('#weekPlan').innerHTML = items.map((x) => `<div class="list-row"><i data-icon="calendar"></i><div class="grow"><div class="t">${esc(x.topic)}</div>
      <div class="meta">${esc(x.date)} · ${esc(x.status)}</div></div></div>`).join('')
      || '<div class="empty"><i data-icon="calendar"></i><p>Nothing planned for the next 7 days. <a class="link" href="#calendar">Plan your week</a></p></div>';
    paintIcons($('#weekPlan'));
  } catch (e) { /* ignore */ }
}

/* ------------------------------------------------------------------ update old posts */
async function searchPosts() {
  const box = $('#postList');
  if (!(S.cfg.wp_url && S.cfg.wp_app_password_set)) { box.innerHTML = '<p class="muted small">Connect WordPress in Settings first.</p>'; return; }
  box.innerHTML = '<p class="muted small">Loading…</p>';
  try {
    const r = await runJob('posts', { q: $('#postSearch').value }, { quiet: true });
    box.innerHTML = r.posts.map((p) => `<div class="post-row" data-pid="${p.id}"><div class="t">${esc(p.title)}</div>
      <div class="meta small muted">Published ${esc((p.date || '').slice(0, 10))}${p.modified && p.modified.slice(0, 10) !== (p.date || '').slice(0, 10) ? ' · updated ' + esc(p.modified.slice(0, 10)) : ''}</div></div>`).join('')
      || '<p class="muted small">No posts found.</p>';
    $$('[data-pid]', box).forEach((el) => el.addEventListener('click', () => suggestUpdate(el)));
  } catch (e) { box.innerHTML = `<p class="muted small">${esc(e.message)}</p>`; }
}

async function suggestUpdate(row) {
  $$('.post-row').forEach((x) => x.classList.toggle('active', x === row));
  const box = $('#updateEmpty');
  box.innerHTML = `<div class="upd-wait"><span class="spin big-spin"></span><b>Working on “${esc(row.querySelector('.t').textContent)}”</b>
    <span class="muted small">Usually 1–3 minutes. Elapsed: <span id="updElapsed">0s</span></span><div class="log upd-log" id="updLog"></div></div>`;
  box.classList.remove('hidden');
  $('#updateBody').classList.add('hidden');
  const t0 = Date.now();
  const timer = setInterval(() => { const el = $('#updElapsed'); if (el) el.textContent = Math.round((Date.now() - t0) / 1000) + 's'; }, 1000);
  const addLog = (l) => { const lg = $('#updLog'); if (!lg) return; const d = document.createElement('div'); d.textContent = l; lg.appendChild(d); lg.scrollTop = lg.scrollHeight; };
  $$('.post-row').forEach((x) => x.style.pointerEvents = 'none');
  try {
    const r = await runJob('update_suggest', { post_id: +row.dataset.pid }, { quiet: true, onLog: addLog });
    S.upd = r;
    $('#updTitle').textContent = r.post.title;
    $('#updLink').href = r.post.url;
    $('#updSummary').innerHTML = (r.summary || []).map((x) => `<li>${esc(x)}</li>`).join('') || '<li>Nothing important seems to have changed.</li>';
    $('#updChanges').innerHTML = (r.changes || []).map((x) => `<li class="${x.startsWith('Skipped') ? 'warn' : 'ok'}"><span>${esc(x)}</span></li>`).join('')
      || '<li class="ok"><span>No changes suggested.</span></li>';
    $('#updMeta').value = r.meta_description || '';
    $('#updHtml').value = r.new_html;
    $('#updFrame').srcdoc = `<!doctype html><meta charset="utf-8"><style>body{font-family:Georgia,serif;max-width:720px;margin:20px auto;padding:0 18px;line-height:1.7}h2,h3{font-family:system-ui}</style><h1 style="font-family:system-ui">${esc(r.post.title)}</h1>${r.new_html}`;
    $('#updateEmpty').classList.add('hidden');
    $('#updateBody').classList.remove('hidden');
  } catch (e) {
    box.innerHTML = `<div class="inline-warn red">${esc(e.message)}</div><p class="muted small">If this keeps happening, click <b>Report a problem</b> (bottom left) and send the report.</p>`;
  } finally {
    clearInterval(timer);
    $$('.post-row').forEach((x) => x.style.pointerEvents = '');
  }
}

/* ------------------------------------------------------------------ drafts */
function draftRows(list) {
  return list.map((d) => `<div class="list-row"><i data-icon="file"></i><div class="grow"><div class="t">${esc(d.title)}</div>
    <div class="meta">${esc((d.created || '').replace('T', ' '))} · ${d.words} words${d.wp_post_id ? ' · <span class="badge green">In WordPress</span>' : ''}</div></div>
    <button class="btn small" data-open="${esc(d.name)}">Open</button>
    <button class="btn small ghost" data-del="${esc(d.name)}" title="Delete from this computer"><i data-icon="trash"></i></button></div>`).join('');
}

function bindDraftRows(root) {
  $$('[data-open]', root).forEach((b) => b.addEventListener('click', async () => {
    try {
      const r = await api('draft', { name: b.dataset.open });
      S.article = r.article; S.news = [];
      store.set('article', S.article);
      location.hash = '#write';
      showArticle();
    } catch (e) { toast(e.message, 'err'); }
  }));
  $$('[data-del]', root).forEach((b) => b.addEventListener('click', async () => {
    if (!confirm('Delete this draft from your computer? (Drafts already in WordPress stay there.)')) return;
    await api('delete_draft', { name: b.dataset.del });
    loadDrafts();
  }));
}

async function loadDrafts() {
  const d = await api('drafts');
  const box = $('#draftList');
  box.innerHTML = draftRows(d.drafts) || '<div class="empty"><i data-icon="folder"></i><p>No drafts yet.</p></div>';
  box.insertAdjacentHTML('beforeend', `<p class="muted small">Folder: ${esc(S.draftsDir)}</p>`);
  bindDraftRows(box);
  paintIcons(box);
}

/* ------------------------------------------------------------------ settings */
function fillSettings() {
  const c = S.cfg;
  geoOptions($('#geoSettings'), c.trends_geo);
  $$('[data-k]').forEach((el) => {
    const k = el.dataset.k;
    if (el.type === 'checkbox') el.checked = !!c[k];
    else if (el.type === 'password') {
      el.value = '';
      el.placeholder = c[k + '_set'] ? `Saved ${(c[k + '_hint'] || '').replace('…', '••••')} (type to replace)` : 'Paste here';
    } else el.value = c[k] == null ? '' : c[k];
  });
  $('#wordsVal').textContent = c.target_words;
  settingsNichesChanged();
  const st = (id, ok, txt) => { const el = $(id); el.className = 'status ' + (ok ? 'ok' : 'no'); el.textContent = ok ? '● ' + txt : '○ Not set'; };
  st('#st_wp', c.wp_url && c.wp_user && c.wp_app_password_set, S.wpOk ? 'Connected' : 'Saved');
  st('#st_gem', c.gemini_api_key_set, c.text_model ? 'Key saved · ' + c.text_model : 'Key saved');
  st('#st_px', c.pexels_api_key_set, 'Key saved');
  $('#curSite').textContent = c.profile;
}

function settingsNichesChanged() { renderChips($('#settingsNiches'), settingsNichesChanged); renderPreset(); }

function renderPreset() {
  const box = $('#presetBox');
  const first = S.niches.find((n) => S.cfg.niches.includes(n.id));
  if (!first || !first.preset) { box.classList.add('hidden'); return; }
  const p = first.preset;
  box.classList.remove('hidden');
  box.innerHTML = `<span><b>Recommended for ${esc(first.label)}:</b> ${p.target_words} words · ${p.inline_images} image(s) · ${p.tone} tone ·
    FAQ ${p.faq ? 'on' : 'off'} · ${IMAGE_SOURCES[p.image_source]}${first.ymyl ? ' · careful YMYL rules + disclaimer' : ''}</span>
    <button class="btn small primary" id="applyPreset">Apply recommended settings</button>`;
  $('#applyPreset').addEventListener('click', () => {
    Object.entries(p).forEach(([k, v]) => {
      const el = $(`[data-k="${k}"]`);
      if (!el) return;
      if (el.type === 'checkbox') el.checked = !!v; else el.value = v;
    });
    $('#wordsVal').textContent = $('#wordsRange').value;
    toast('Recommended settings applied. Click Save settings to keep them.');
  });
}

function collectSettings() {
  const out = { niches: S.cfg.niches };
  $$('[data-k]').forEach((el) => {
    const k = el.dataset.k;
    if (el.type === 'checkbox') out[k] = el.checked;
    else if (el.type === 'password') { if (el.value.trim()) out[k] = el.value.trim(); }
    else out[k] = el.value;
  });
  return out;
}

async function saveSettings(quiet) {
  const st = await api('config', collectSettings());
  S.cfg = st.config;
  fillSettings();
  updatePill();
  if (!quiet) toast('Settings saved');
}

/* ------------------------------------------------------------------ guide */
function renderGuide() {
  const lang = store.get('lang', 'en');
  $$('#langSeg button').forEach((b) => b.classList.toggle('active', b.dataset.lang === lang));
  $('#guideBody').innerHTML = GUIDE[lang].map((s, i) => `<div class="card" id="${s.id}"><div class="guide-step">
    <div class="guide-num">${i + 1}</div><div><h3>${s.title}</h3>${s.html}</div></div></div>`).join('');
}

/* ------------------------------------------------------------------ wiring */
function wire() {
  window.addEventListener('hashchange', route);
  geoOptions($('#geoSel'), S.cfg.trends_geo);

  const loadTopics = (btn, kind) => busy(btn, async () => {
    const r = await runJob(kind, { geo: $('#geoSel').value }, { quiet: true });
    S.trends = r.trends;
    S.source = r.source;
    setTrendsLink();
    $('#onlyNicheWrap').classList.toggle('hidden', r.source === 'news');
    renderTrends();
    toast(r.source === 'news' ? `${r.trends.length} hot stories in your niche`
      : `${r.fit_count} of ${r.trends.length} trending searches fit your niche`);
  });
  $('#hotBtn').addEventListener('click', (e) => loadTopics(e.currentTarget, 'hot'));
  $('#trendsBtn').addEventListener('click', (e) => loadTopics(e.currentTarget, 'trends'));
  function setTrendsLink() {
    const cats = { tech: 18, ai: 18, gaming: 6, sports: 17, health: 7, finance: 3, crypto: 3, business: 3, education: 9, travel: 19,
      food: 5, entertainment: 4, lifestyle: 2, home: 8, auto: 1, pets: 13, science: 15 };
    const cat = (S.cfg.niches || []).map((n) => cats[n]).find(Boolean);
    $('#trendsLink').href = `https://trends.google.com/trending?geo=${$('#geoSel').value || 'US'}&hours=24${cat ? '&category=' + cat : ''}`;
  }
  $('#geoSel').addEventListener('change', setTrendsLink);
  setTrendsLink();
  $('#onlyNiche').addEventListener('change', renderTrends);
  $$('#ideaTabs .tab').forEach((t) => t.addEventListener('click', () => {
    $$('#ideaTabs .tab').forEach((x) => x.classList.toggle('active', x === t));
    $$('[data-pane]', t.closest('.card')).forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== t.dataset.tab));
    $('#ideaList').innerHTML = '';
  }));
  $('#ideasTrendsBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const r = await runJob('ideas', { source: 'trends' }, { quiet: true });
    renderIdeas(r.ideas, 'trends');
  }));
  $('#ideasEverBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const r = await runJob('ideas', { source: 'evergreen', keyword: $('#everKw').value }, { quiet: true });
    renderIdeas(r.ideas, 'evergreen');
  }));
  const kwSearch = (btn) => busy(btn, async () => {
    const r = await runJob('suggest', { keyword: $('#kwInput').value }, { quiet: true });
    renderIdeas(r.suggestions.map((s) => ({ topic: s })), 'kw');
  });
  $('#kwBtn').addEventListener('click', (e) => kwSearch(e.currentTarget));
  $('#kwInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') kwSearch($('#kwBtn')); });

  // write
  $('#topicInput').addEventListener('input', checkTopic);
  $('#angleInput').addEventListener('input', checkTopic);
  const startWrite = (btn, mode) => busy(btn, async () => {
    const topic = $('#topicInput').value.trim();
    if (!topic) { toast('Enter a topic first', 'err'); return; }
    const chk = await api('check_topic', { topic, angle: $('#angleInput').value });
    if (chk.blocked) { toast('This topic breaks AdSense rules, so the app won\'t write it.', 'err'); return; }
    if (!chk.fits && !confirm('This topic doesn\'t look like your niche. Off-niche posts can hurt AdSense approval.\n\nWrite it anyway?')) return;
    setStep(mode === 'outline' ? 2 : 3);
    log(`— ${mode === 'outline' ? 'Research & outline' : 'Research & write'}: ${topic}`);
    const news = topic === S.newsTopic ? S.news : [];
    const r = await runJob('write', { mode, topic, angle: $('#angleInput').value, news, experience_notes: $('#expInput').value,
      own_images: ownImageList(), plan_id: S.planId });
    S.pendingImages = [];
    S.article = r.article;
    store.set('article', S.article);
    showArticle();
    if (mode === 'outline') { log('Outline ready. Change it if you like, then click "Write from this outline".', 'ok'); toast('Outline ready'); }
    else { log('Draft ready. Review it, then save it to WordPress.', 'ok'); toast('Draft ready — review it'); }
  });
  $('#outlineBtn').addEventListener('click', (e) => startWrite(e.currentTarget, 'outline'));
  $('#writeBtn').addEventListener('click', (e) => startWrite(e.currentTarget, 'full'));
  $('#fromOutlineBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const a = S.article;
    if (!a) return;
    a.outline = $('#outlineInput').value;
    a.experience_notes = $('#expInput').value;
    setStep(3);
    log('— Writing from your outline');
    const r = await runJob('write', { mode: 'from_outline', article: a, experience_notes: a.experience_notes, plan_id: S.planId });
    S.article = r.article; store.set('article', S.article);
    showArticle();
    log('Draft ready. Review it, then save it to WordPress.', 'ok');
    toast('Draft ready — review it');
  }));
  $('#imgFiles').addEventListener('change', async (e) => {
    const files = Array.from(e.target.files || []);
    for (const f of files) {
      if (f.size > 15 * 1024 * 1024) { toast(`${f.name} is larger than 15 MB`, 'err'); continue; }
      const data = await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = rej; fr.readAsDataURL(f); });
      try {
        const r = await api('upload_image', { data });
        ownImageList().push({ file: r.file, alt: f.name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' '), caption: '', after_h2: 1, featured: false });
      } catch (err) { toast(err.message, 'err'); }
    }
    e.target.value = '';
    if (S.article) store.set('article', S.article);
    renderOwnImages();
  });
  $('#factBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const r = await runJob('factcheck', { article: readArticle() });
    S.article = r.article; S.article._factChecked = true; store.set('article', S.article);
    renderChecks();
    toast(r.article.fact_issues.length ? `${r.article.fact_issues.length} claim(s) to check` : 'All claims found in the research');
  }));
  $('#socialBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const r = await runJob('social', { article: readArticle(), url: $('#socialUrl').value.trim() }, { quiet: true });
    S.article = r.article; store.set('article', S.article);
    renderSocial();
  }));
  $('#linkBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const url = $('#linkUrl').value.trim();
    const r = await runJob('link_suggest', { article: readArticle(), url });
    const box = $('#linkList');
    box.innerHTML = r.suggestions.map((sg, i) => `<div class="list-row"><div class="grow"><div class="t">${esc(sg.title)}</div>
      <div class="meta">…${esc(sg.paragraph.slice(0, 220)).replace(esc(sg.anchor), '<b>' + esc(sg.anchor) + '</b>')}…</div></div>
      <button class="btn small primary" data-ln="${i}">Add link</button></div>`).join('') || '<p class="muted small">No good places found in older posts.</p>';
    $$('[data-ln]', box).forEach((b) => b.addEventListener('click', () => busy(b, async () => {
      const sg = r.suggestions[+b.dataset.ln];
      if (!confirm(`Add a link in "${sg.title}" on the words "${sg.anchor}"? This changes that live post.`)) return;
      await runJob('link_apply', { post_id: sg.post_id, index: sg.index, anchor: sg.anchor, url: r.url });
      b.outerHTML = '<span class="badge green">Linked</span>';
    })));
  }));
  ['#f_title', '#f_seo_title', '#f_slug', '#f_focus_keyword', '#f_meta_description', '#f_category', '#f_tags'].forEach((id) =>
    $(id).addEventListener('input', () => { refreshSeo(); if (id === '#f_title') refreshPreview(); }));
  $('#f_body_html').addEventListener('input', () => { refreshPreview(); refreshSeo(); });
  $('#expInput').addEventListener('input', () => { if (S.article) { readArticle(); refreshPreview(); } });
  $$('#bodyTabs .tab').forEach((t) => t.addEventListener('click', () => {
    $$('#bodyTabs .tab').forEach((x) => x.classList.toggle('active', x === t));
    $$('[data-pane]', $('#bodyCard')).forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== t.dataset.tab));
  }));
  $('#recheckBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const r = await api('recheck', { article: readArticle() });
    S.article = r.article; store.set('article', S.article);
    $('#f_body_html').value = S.article.body_html;
    renderChecks(); refreshPreview();
    toast('Checked');
  }));
  $('#saveLocalBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const r = await api('save_local', { article: readArticle() });
    S.article = r.article; renderChecks();
    toast('Saved on this computer');
  }));
  $('#publishBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const a = readArticle();
    if (a.wp_post_id && !confirm('This article was already saved to WordPress. Create another draft?')) return;
    if (S.cfg.experience_section && !a.experience_notes.trim() &&
        !confirm('Your experience box is empty.\n\nPosts with your own experience do much better. Save the draft anyway?')) return;
    log('— Saving draft to WordPress');
    let r;
    try {
      r = await runJob('publish', { article: a, plan_id: S.planId });
    } catch (err) {
      if (!String(err.message).startsWith('WEEKLY_LIMIT')) throw err;
      if (!confirm(err.message.replace('WEEKLY_LIMIT: ', '') + '\n\nSave this draft anyway?')) return;
      r = await runJob('publish', { article: a, plan_id: S.planId, force: true });
    }
    S.article = r.article; store.set('article', S.article);
    showArticle();
    const open = $('#openWpBtn');
    open.href = r.edit_link; open.classList.remove('hidden');
    setStep(6);
    log('Draft saved in WordPress. Open it, read it once and click Publish yourself.', 'ok');
    toast('Draft saved in WordPress');
  }));
  $('#newArticleBtn').addEventListener('click', () => {
    if (S.article && !confirm('Start a new article? The current one is saved in My Drafts.')) return;
    S.article = null; S.news = []; S.planId = ''; S.pendingImages = []; store.set('article', null);
    $('#outlineInput').value = ''; $('#socialBox').innerHTML = ''; $('#linkList').innerHTML = '';
    ['#topicInput', '#angleInput', '#expInput'].forEach((id) => { $(id).value = ''; });
    showArticle(); setStep(1); checkTopic();
  });
  $('#clearLogBtn').addEventListener('click', () => { $('#log').innerHTML = '<div class="muted small">Progress shows here.</div>'; });

  // settings
  $('#wordsRange').addEventListener('input', (e) => { $('#wordsVal').textContent = e.target.value; });
  $$('.stepper [data-step]').forEach((b) => b.addEventListener('click', () => {
    const inp = $('#imgCount');
    inp.value = Math.max(0, Math.min(6, (+inp.value || 0) + (+b.dataset.step)));
  }));
  ['#saveSettingsBtn', '#saveSettingsBtn2'].forEach((id) => $(id).addEventListener('click', (e) => busy(e.currentTarget, () => saveSettings())));
  $('#testWpBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    await saveSettings(true);
    $('#wpResult').textContent = 'Testing…';
    try {
      const r = await runJob('test_wordpress', {}, { quiet: true });
      S.wpOk = true;
      $('#wpResult').innerHTML = `<span class="status ok">✓ Logged in as ${esc(r.user)}</span> · ${r.posts} published posts · SEO plugin bridge: ${r.bridge ? 'installed' : 'not installed (optional)'}`;
    } catch (err) { S.wpOk = false; $('#wpResult').textContent = ''; throw err; } finally { updatePill(); fillSettings(); }
  }));
  $('#detectBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    await saveSettings(true);
    const r = await runJob('detect_models', {}, { quiet: true });
    $('#textModels').innerHTML = r.text_models.map((m) => `<option value="${esc(m)}">`).join('');
    $('#imageModels').innerHTML = r.image_models.map((m) => `<option value="${esc(m)}">`).join('');
    await loadState(); fillSettings();
    $('#gemResult').innerHTML = `<span class="status ok">✓ Text: ${esc(r.text_model)} · Image: ${esc(r.image_model || 'none available')}</span>`;
  }));
  $('#testImgBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    await saveSettings(true);
    $('#gemResult').textContent = 'Creating a test image (10–30 seconds)…';
    try {
      const r = await runJob('test_image', {}, { quiet: true });
      const img = $('#testImg'); img.src = r.image; img.classList.remove('hidden');
      $('#gemResult').innerHTML = '<span class="status ok">✓ AI images work</span>';
    } catch (err) { $('#gemResult').textContent = ''; throw err; }
  }));
  $('#testPxBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    await saveSettings(true);
    const r = await runJob('test_pexels', {}, { quiet: true });
    $('#pxResult').innerHTML = `<span class="status ok">✓ Pexels works</span> (photo by ${esc(r.credit)})`;
  }));

  $('#detectOaBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    await saveSettings(true);
    const r = await runJob('detect_openai', {}, { quiet: true });
    $('#oaModels').innerHTML = r.models.map((m) => `<option value="${esc(m)}">`).join('');
    await loadState(); fillSettings();
    $('#aiResult').innerHTML = `<span class="status ok">✓ OpenAI: ${esc(r.model)}</span>`;
  }));
  $('#detectAnBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    await saveSettings(true);
    const r = await runJob('detect_anthropic', {}, { quiet: true });
    $('#anModels').innerHTML = r.models.map((m) => `<option value="${esc(m)}">`).join('');
    await loadState(); fillSettings();
    $('#aiResult').innerHTML = `<span class="status ok">✓ Claude: ${esc(r.model)}</span>`;
  }));
  $('#checkUpdBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    await saveSettings(true);
    const u = await runJob('check_update', {}, { quiet: true });
    $('#updResult').textContent = !u.configured ? 'No update address set.' : u.available ? `Version ${u.latest} is available.` : 'You have the latest version.';
    showUpdate(u);
  }));

  // sites
  const afterSite = async (st, msg) => {
    S.cfg = st.config; S.usage = st.usage; S.wpOk = null; S.trends = [];
    S.article = null; store.set('article', null);
    await loadState(); fillSettings(); updatePill(); route();
    if (msg) toast(msg);
  };
  $('#siteSel').addEventListener('change', async (e) => {
    try { await afterSite(await api('profile', { action: 'switch', name: e.target.value }), 'Switched to ' + e.target.value); } catch (err) { toast(err.message, 'err'); }
  });
  const addSite = async () => {
    const name = prompt('Name of the new site (e.g. my food blog):');
    if (!name) return;
    try { await afterSite(await api('profile', { action: 'add', name, copy: true }), 'Site added. Now enter its WordPress details in Settings.'); location.hash = '#settings'; } catch (err) { toast(err.message, 'err'); }
  };
  $('#addSiteBtn').addEventListener('click', addSite);
  $('#newSiteBtn').addEventListener('click', addSite);
  $('#renameSiteBtn').addEventListener('click', async () => {
    const name = prompt('New name for this site:', S.cfg.profile);
    if (!name || name === S.cfg.profile) return;
    try { await afterSite(await api('profile', { action: 'rename', name }), 'Renamed'); } catch (err) { toast(err.message, 'err'); }
  });
  $('#delSiteBtn').addEventListener('click', async () => {
    if (!confirm(`Delete the site "${S.cfg.profile}" from this app? (Your WordPress site is not touched.)`)) return;
    try { await afterSite(await api('profile', { action: 'delete', name: S.cfg.profile }), 'Site removed from the app'); } catch (err) { toast(err.message, 'err'); }
  });

  // calendar
  $('#planAddBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    const r = await api('plan', { action: 'add', date: $('#planDate').value, topic: $('#planTopic').value, angle: $('#planAngle').value });
    $('#planTopic').value = ''; $('#planAngle').value = '';
    const used = new Set(r.items.map((x) => x.date));
    $('#planDate').value = r.suggested_dates.find((d) => !used.has(d)) || r.suggested_dates[0];
    loadPlan(r);
    toast('Added to calendar');
  }));

  // update old posts
  $('#postSearchBtn').addEventListener('click', searchPosts);
  $('#postSearch').addEventListener('keydown', (e) => { if (e.key === 'Enter') searchPosts(); });
  $$('#updTabs .tab').forEach((t) => t.addEventListener('click', () => {
    $$('#updTabs .tab').forEach((x) => x.classList.toggle('active', x === t));
    $$('[data-pane]', $('#updateBody')).forEach((p) => p.classList.toggle('hidden', p.dataset.pane !== t.dataset.tab));
  }));
  $('#updApplyBtn').addEventListener('click', (e) => busy(e.currentTarget, async () => {
    if (!S.upd) return;
    if (!confirm(`Apply these changes to the live post "${S.upd.post.title}"?\n\nWordPress keeps the old version under Revisions.`)) return;
    await runJob('update_apply', { post_id: S.upd.post.id, content: $('#updHtml').value, meta_description: $('#updMeta').value }, { quiet: true });
    toast('Post updated');
  }));

  // report
  $('#reportBtn').addEventListener('click', async () => {
    try {
      const rp = await api('report', {});
      $('#reportText').value = rp.text;
      const gh = $('#reportGh');
      gh.classList.toggle('hidden', !rp.issue_url);
      gh.href = rp.issue_url || '#';
    } catch (err) { $('#reportText').value = 'Could not create the report: ' + err.message; }
    $('#reportDlg').showModal();
  });
  $('#reportClose').addEventListener('click', () => $('#reportDlg').close());
  $('#reportGh').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('#reportText').value); toast('Report copied — paste it into the form'); } catch (err) { /* user can copy manually */ }
  });
  $('#reportCopy').addEventListener('click', async () => {
    const t = $('#reportText');
    try { await navigator.clipboard.writeText(t.value); toast('Report copied'); } catch (err) { t.select(); document.execCommand('copy'); toast('Report copied'); }
  });

  // guide + quit
  $$('#langSeg button').forEach((b) => b.addEventListener('click', () => { store.set('lang', b.dataset.lang); renderGuide(); }));
  $('#quitBtn').addEventListener('click', async () => {
    if (!confirm('Quit BlogDraft Studio?')) return;
    try { await fetch('/api/quit', { method: 'POST', headers: { 'X-Token': TOKEN } }); } catch (e) { /* server stopped */ }
    document.body.innerHTML = '<div style="font-family:system-ui;padding:60px;text-align:center"><h2>BlogDraft Studio has stopped.</h2><p>You can close this tab. Run the start file again to open it.</p></div>';
  });
}

(async function init() {
  paintIcons();
  try { await loadState(); } catch (e) { toast('Could not reach the app: ' + e.message, 'err'); return; }
  wire();
  if (S.article) showArticle(); else setStep(1);
  route();
})();
