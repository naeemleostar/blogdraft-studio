// App language: English (default) or Roman Urdu. Texts are translated by exact match, so data such as
// post titles is never changed. Technical names (WordPress, SEO, API key, Gemini) stay in English on purpose.
const UR = {
  // navigation
  'Site': 'Site', 'Add another site': 'Nayi site add karein', 'Dashboard': 'Dashboard', 'Find Topics': 'Topic dhoondein',
  'Write Post': 'Post likhein', 'My Drafts': 'Meray drafts', 'Calendar': 'Calendar', 'Update Old Posts': 'Purani posts update',
  'Settings': 'Settings', 'Setup Guide': 'Setup guide', 'Not connected': 'Connect nahi', 'No site connected': 'Koi site connect nahi',
  'Report a problem': 'Masla report karein', 'Quit app': 'App band karein',
  // dashboard
  'Welcome back': 'Khush aamdeed',
  'Find a topic, write a researched draft, check it, save it to WordPress.': 'Topic dhoondein, research ke saath draft likhwayein, check karein aur WordPress mein save karein.',
  'Setup wizard': 'Setup wizard', 'Write a post': 'Post likhein', 'Posts published (last 7 days)': 'Publish posts (pichle 7 din)',
  'Drafts waiting in WordPress': 'WordPress mein drafts', 'Drafts saved on this computer': 'Is computer par drafts',
  'AI use this month': 'Is mahine AI ka istemal', 'Setup checklist': 'Setup checklist', 'Setup guide →': 'Setup guide →',
  'Posting pace': 'Post karne ki raftaar', '2–3 good posts a week': 'Hafte mein 2-3 achhi posts',
  'beats 10 rushed ones. Google treats mass AI posting as spam.': '10 jaldbazi wali posts se behtar hain. Google dher saari AI posts ko spam samajhta hai.',
  'Add': 'Har post mein', 'your own experience': 'apna tajurba', ', screenshots or photos to every post.': ', screenshots ya photos zaroor daalein.',
  'Stay in': 'Sirf', 'your niche': 'apni niche', '. Off-topic trending posts hurt AdSense approval.': ' par likhein. Niche se bahar ki posts AdSense approval kharab karti hain.',
  'Always': 'Hamesha', 'read the draft': 'draft padhein',
  'and check facts against the Sources list before publishing.': 'aur publish se pehle Sources list se facts check karein.',
  "This week's plan": 'Is hafte ka plan', 'Calendar →': 'Calendar →', 'Recent drafts': 'Naye drafts', 'All drafts →': 'Saare drafts →',
  'Your niche': 'Aap ki niche', 'Change →': 'Badlein →', 'Choose your niche': 'Apni niche chunein', 'Connect WordPress': 'WordPress connect karein',
  'Add your Gemini API key': 'Gemini API key daalein', 'Detect Gemini models': 'Gemini models detect karein',
  'Free photos (Pexels key)': 'Free photos (Pexels key)', 'Set up': 'Set up karein', 'Done': 'Ho gaya',
  'Connect WordPress to see your posting pace.': 'Raftaar dekhne ke liye WordPress connect karein.',
  'Not set': 'Set nahi', 'Needed for research and writing': 'Research aur likhne ke liye zaroori',
  'Optional, for free stock photos': 'Optional, free stock photos ke liye', 'Settings → Your blog & niche': 'Settings → Blog aur niche',
  'Settings → Save & detect models': 'Settings → Save & detect models',
  // wizard
  'Five short steps. You can change everything later in Settings.': 'Paanch chhote steps. Baad mein sab kuch Settings mein badal sakte hain.',
  'Skip for now': 'Abhi chhod dein', 'Language': 'Zabaan', 'Gemini key': 'Gemini key', 'Images': 'Tasveerein',
  'Which language do you want for the app?': 'App kis zabaan mein chahiye?',
  'This changes the buttons and menus. Articles are written in the language you choose in step 2.': 'Ye buttons aur menu ki zabaan badalta hai. Article ki zabaan step 2 mein chunein.',
  'What is your blog about?': 'Aap ka blog kis baare mein hai?',
  'Tick one or more. The app finds topics and writes only for these.': 'Ek ya zyada tick karein. App sirf inhi ke topic dhoondti aur likhti hai.',
  'Blog name': 'Blog ka naam', 'Your name': 'Aap ka naam', "Readers' country": 'Readers ka mulk', 'Article language': 'Article ki zabaan',
  'Connect your WordPress site': 'Apni WordPress site connect karein', 'Open': 'Kholein', 'At the bottom, under': 'Bilkul neeche,',
  ', type': ' mein likhein', 'Copy the password and paste it below.': 'Password copy karke neeche paste karein.', 'More help': 'Mazeed madad',
  'Site address': 'Site ka address', 'WordPress username': 'WordPress username', 'Test connection': 'Connection test karein',
  'and sign in with Google.': 'kholein aur Google se sign in karein.', 'Click': 'Dabayein:', 'and copy it.': 'aur copy karein.',
  'Paste it below and click': 'Neeche paste karke dabayein:', '. Writing works on the free plan.': '. Likhna free plan par chalta hai.',
  'Check key': 'Key check karein', 'Saver mode: fewer AI requests (best for the free plan)': 'Saver mode: kam AI requests (free plan ke liye behtar)',
  'Pictures for your posts': 'Posts ke liye tasveerein', 'Free photos (Pexels)': 'Free photos (Pexels)', 'Free. Needs a free Pexels key.': 'Free. Free Pexels key chahiye.',
  'Free photo, else AI image': 'Free photo, warna AI tasveer', 'AI images need Gemini billing.': 'AI tasveeron ke liye Gemini billing chahiye.',
  'AI images (Gemini)': 'AI tasveerein (Gemini)', 'Needs billing in Google AI Studio.': 'Google AI Studio mein billing chahiye.',
  'No images': 'Koi tasveer nahi', 'Add your own photos per post.': 'Har post mein apni photos lagayein.', 'Get a free key at': 'Free key yahan se lein:',
  'Test Pexels': 'Pexels test karein', "You're ready!": 'Sab tayyar hai!', 'Next: find a topic in your niche and write your first draft.': 'Ab apni niche ka topic dhoondein aur pehla draft likhwayein.',
  'Find my first topic': 'Pehla topic dhoondein', 'Go to Dashboard': 'Dashboard par jayein', '← Back': '← Wapas', 'Next →': 'Aagay →', 'Finish': 'Mukammal',
  'Tick at least one niche.': 'Kam az kam ek niche tick karein.', 'Testing…': 'Test ho raha hai…',
  // topics
  "Today's Google trends and search ideas, filtered to your niche.": 'Aaj ke Google trends aur search ideas, aap ki niche ke hisaab se.',
  'Tick one or more. Results are filtered to these.': 'Ek ya zyada tick karein. Results inhi ke hisaab se aayenge.',
  "What's hot": 'Kya chal raha hai', 'Hot in my niche': 'Meri niche mein hot', 'Top Google searches': 'Top Google searches', 'Open Google Trends': 'Google Trends kholein',
  'Only my niche': 'Sirf meri niche', 'AI ideas': 'AI ideas', 'Keyword ideas': 'Keyword ideas',
  'Gemini picks topics that fit your niche. Trend ideas are timely; evergreen ideas get searched all year.': 'Gemini aap ki niche ke topics chunta hai. Trend ideas abhi ke hain; evergreen saal bhar search hote hain.',
  "From today's trends": 'Aaj ke trends se', 'Evergreen ideas': 'Evergreen ideas', 'What people actually type into Google after your keyword.': 'Log aap ke keyword ke baad Google mein kya likhte hain.',
  'Search': 'Search', 'Write this': 'Ye likhein',
  // write
  'Research on Google, write, check, then save as a': 'Google par research, likhna, check, phir save karein bataur', 'Draft': 'Draft',
  '. You publish it yourself.': '. Publish aap khud karte hain.', 'New': 'Naya', 'Topic': 'Topic', 'Outline': 'Outline', 'Write': 'Likhein',
  'Review & edit': 'Check aur edit', 'Save draft': 'Draft save', 'Angle': 'Angle', '(optional)': '(optional)', 'Your own experience': 'Aap ka apna tajurba',
  '(any language, a few lines)': '(kisi bhi zabaan mein, 2-3 line)', 'Research & make outline': 'Research + outline banayein', 'Skip outline, write now': 'Outline chhodein, abhi likhein',
  'The outline lets you change the sections and add your own points before the full article is written.': 'Outline mein aap poora article likhne se pehle headings badal sakte hain aur apne points jod sakte hain.',
  'Edit freely:': 'Aazadi se badlein:', 'and': 'aur', 'lines': 'lines', 'Write from this outline': 'Is outline se likhein', 'Takes about a minute.': 'Takreeban ek minute lagta hai.',
  'Your photos & screenshots': 'Aap ki photos aur screenshots', 'Add images': 'Tasveerein add karein',
  'Your own pictures make a post trustworthy and help with AdSense. They are uploaded with the draft, before any stock or AI images.': 'Apni tasveerein post ko qabil-e-aitmaad banati hain aur AdSense mein madad karti hain. Ye draft ke saath, stock ya AI tasveeron se pehle lagti hain.',
  'No images yet.': 'Abhi koi tasveer nahi.', 'Title': 'Title', 'SEO title': 'SEO title', 'Slug': 'Slug', 'Focus keyword': 'Focus keyword', 'Meta description': 'Meta description',
  'Category': 'Category', 'Tags': 'Tags', '(comma separated)': '(comma se alag)', 'Checks': 'Checks', 'Fact-check': 'Fact-check', 'Re-check': 'Dobara check',
  'Readability & SEO': 'Parhne mein asaani & SEO', 'Preview': 'Preview', 'Edit HTML': 'HTML edit', 'Sources': 'Sources', 'Social': 'Social',
  'Write social posts': 'Social posts likhein', 'Save on computer': 'Computer par save', 'Add images & save Draft in WordPress': 'Tasveerein laga kar WordPress mein Draft save karein',
  'Open draft in WordPress': 'WordPress mein draft kholein', 'Links from your older posts': 'Purani posts se links',
  'After you publish this post, paste its link and the app finds older posts where a link to it fits naturally. You approve each one.': 'Post publish hone ke baad us ka link daalein; app purani posts mein link lagane ki munasib jagah dhoondegi. Har link aap khud approve karenge.',
  'Find places': 'Jagah dhoondein', 'Activity': 'Kaam ki tafseel', 'Clear': 'Saaf karein', 'Progress shows here.': 'Progress yahan dikhegi.',
  'No problems found. Still read it once and check the facts.': 'Koi masla nahi mila. Phir bhi ek dafa padh kar facts check karein.',
  // drafts, calendar, update
  'Every article is saved on this computer automatically.': 'Har article is computer par khud save hota hai.', 'No drafts yet.': 'Abhi koi draft nahi.',
  'Content Calendar': 'Content calendar', 'Plan your posts. Steady posting beats bursts.': 'Posts ka plan banayein. Mustaqil posting achhi hai, ek dam dher nahi.',
  'Plan a post': 'Post plan karein', 'Date': 'Tareekh', 'What will you write about?': 'Kis baare mein likhenge?', 'Add to calendar': 'Calendar mein daalein',
  'Google likes fresh content. Find what changed since a post was written and update it.': 'Google taaza content pasand karta hai. Dekhein post ke baad kya badla aur update karein.',
  'Search your posts': 'Apni posts search karein', 'Apply': 'Apply',
  'Pick a post on the left. The app searches Google for what changed and suggests edits. Nothing changes on your site until you click': 'Left se post chunein. App Google par dekhegi kya badla aur tabdeeliyan tajweez karegi. Site par kuch nahi badlega jab tak aap na dabayein:',
  'View post ↗': 'Post dekhein ↗', "What's new": 'Kya naya hai', 'Changes applied in the preview': 'Preview mein ki gayi tabdeeliyan', 'New meta description': 'Nayi meta description',
  'Apply update to the post': 'Post par update lagayein', 'WordPress keeps the old version under Revisions.': 'WordPress purana version Revisions mein rakhta hai.',
  // settings
  'Saved only on this computer. Keys are never shown again after saving.': 'Sirf is computer par save. Save ke baad keys dobara nahi dikhti.',
  'Save settings': 'Settings save karein', 'Your sites': 'Aap ki sites', 'Each site has its own niche, WordPress login and settings. API keys are shared.': 'Har site ki apni niche, WordPress login aur settings hain. API keys sab ke liye ek hain.',
  'Now editing:': 'Abhi edit ho rahi hai:', 'Rename': 'Naam badlein', 'Add site': 'Site add karein', 'Delete this site': 'Ye site hatayein',
  '1. Your blog & niche': '1. Aap ka blog aur niche', 'Extra niche detail': 'Niche ki mazeed tafseel', 'Readers (audience)': 'Readers (audience)',
  'Author name': 'Author ka naam', 'Author city/country': 'Author ka shehar/mulk', 'Trends country': 'Trends ka mulk', 'Posts per week (limit)': 'Hafte mein posts (had)',
  'Writing tone': 'Likhne ka andaaz', 'Friendly (knowledgeable friend)': 'Dostana (samajhdar dost)', 'Professional (expert)': 'Professional (expert)', 'Simple (for beginners)': 'Asaan (naye logon ke liye)',
  'Use AI to double-check that trends fit my niche (more accurate, uses Gemini)': 'AI se double-check karein ke trends meri niche ke hain (zyada sahi, Gemini use hota hai)',
  'Saver mode: fewer AI requests (no AI trend check, free photos only, max 1 image) — best for the free Gemini plan': 'Saver mode: kam AI requests (AI trend check nahi, sirf free photos, max 1 tasveer) — free Gemini plan ke liye behtar',
  'App language': 'App ki zabaan', '2. Article': '2. Article', 'Article length:': 'Article ki lambai:', 'words': 'alfaaz', '600 short': '600 chhota', '1400 standard': '1400 aam', '3000 long guide': '3000 lambi guide',
  'Images inside the article': 'Article ke andar tasveerein', 'Also add a featured image': 'Featured image bhi lagayein', 'Image source': 'Tasveer kahan se',
  'Free photo first, AI image if none found': 'Pehle free photo, na mile to AI tasveer', 'Free photos only (Pexels)': 'Sirf free photos (Pexels)',
  'AI images only (Gemini)': 'Sirf AI tasveerein (Gemini)', 'AI images only (OpenAI)': 'Sirf AI tasveerein (OpenAI)', 'Caption under AI images': 'AI tasveer ke neeche caption',
  'Max internal links': 'Zyada se zyada internal links', 'Max external links': 'Zyada se zyada external links', 'FAQ section': 'FAQ hissa', 'Sources list at the end': 'Aakhir mein Sources list',
  'Space for my own experience': 'Mere tajurbe ki jagah', '3. Connections & API keys': '3. Connections aur API keys', 'How to get these →': 'Ye kaise milengi →',
  'Username': 'Username', 'where?': 'kahan?', 'Save & test WordPress': 'Save karke WordPress test karein', 'required': 'zaroori', 'Text model': 'Text model', 'Image model': 'Image model',
  'Save & detect models': 'Save karke models detect karein', 'Test AI image': 'AI tasveer test karein', 'free photos, optional': 'free photos, optional', 'Save & test Pexels': 'Save karke Pexels test karein',
  'Who writes the article': 'Article kaun likhe', 'optional': 'optional',
  'Research always uses Gemini with Google Search. The writing can use Gemini, OpenAI (ChatGPT API) or Claude.': 'Research hamesha Gemini aur Google Search se hoti hai. Likhne ke liye Gemini, OpenAI (ChatGPT API) ya Claude.',
  'Writer': 'Likhne wala', 'Save & detect OpenAI': 'Save karke OpenAI detect', 'Save & detect Claude': 'Save karke Claude detect',
  '4. Cost estimate & updates': '4. Kharche ka andaza aur updates',
  "Optional: enter your prices (from your provider's pricing page) to see an estimated monthly cost on the Dashboard.": 'Optional: apni prices (provider ke pricing page se) daalein taake Dashboard par mahine ka andazan kharcha dikhe.',
  'Update check address': 'Update check ka address', 'Check for new versions when the app starts': 'App start hone par naya version check karein', 'Check now': 'Abhi check karein',
  'Settings saved': 'Settings save ho gayin',
  // guide, report
  'One-time setup, about 10 minutes.': 'Ek dafa ka setup, takreeban 10 minute.', 'This report has your app version, settings and recent errors.': 'Is report mein app ka version, settings aur haal ke errors hain.',
  'Keys and passwords are removed.': 'Keys aur passwords nikaal diye gaye hain.',
  'Copy it and send it to the person who gave you the app (for example in a YouTube comment or WhatsApp).': 'Ise copy karke app dene wale ko bhej dein (jaise YouTube comment ya WhatsApp mein).',
  'Close': 'Band karein', 'Copy report': 'Report copy karein', 'Copy & open bug form on GitHub': 'Copy karke GitHub par form kholein',
  'Copied': 'Copy ho gaya', 'Draft ready — review it': 'Draft tayyar — check karein', 'Outline ready': 'Outline tayyar', 'Draft saved in WordPress': 'WordPress mein draft save ho gaya',
  'Saved on this computer': 'Computer par save ho gaya', 'Checked': 'Check ho gaya', 'Added to calendar': 'Calendar mein add ho gaya', 'Post updated': 'Post update ho gayi',
  'Enter a topic first': 'Pehle topic likhein', 'Search Console': 'Search Console', 'Open Search Console export': 'Search Console ki file kholein',
  'How to get the file (1 minute)': 'File kaise milegi (1 minute)', 'Clicks': 'Clicks', 'Impressions': 'Impressions', 'Pages in Google': 'Google mein pages', 'Imported': 'Kab load hui',
  'Almost on page 1 — update these first': 'Page 1 ke qareeb — pehle inhein update karein', 'Seen but rarely clicked — improve title & description': 'Dikhti hain magar click kam — title aur description behtar karein',
  'People search this — you have no post yet': 'Log ye search karte hain — aap ki post abhi nahi', 'Your best pages': 'Aap ke behtareen pages', 'Update': 'Update',
  '5. Backup': '5. Backup', 'Download backup': 'Backup download karein', 'Restore from backup': 'Backup se wapas laayein',
  'Make images light (WebP) for a faster site': 'Tasveerein halki karein (WebP), site tez hogi', 'Add FAQ schema (structured data)': 'FAQ schema add karein (structured data)',
  'Backup downloaded': 'Backup download ho gaya', 'Search Console data loaded': 'Search Console data load ho gaya', 'Nothing here — good.': 'Yahan kuch nahi — achha hai.',
};

const UI_LANG = (() => { try { return JSON.parse(localStorage.getItem('bds_uiLang')) || 'en'; } catch (e) { return 'en'; } })();

function t(s) { return UI_LANG === 'ur' && UR[s] ? UR[s] : s; }

function setUiLang(lang) {
  try {
    localStorage.setItem('bds_uiLang', JSON.stringify(lang));
    localStorage.setItem('bds_lang', JSON.stringify(lang));   // the Setup Guide follows the app language
  } catch (e) { /* storage unavailable: stays English */ }
  location.reload();
}

const SKIP = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'CODE', 'PRE', 'INPUT', 'IFRAME']);

function translateTree(root) {
  if (UI_LANG !== 'ur' || !root) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  let n = root;
  while (n) {
    if (n.nodeType === 1) {
      if (SKIP.has(n.tagName) || n.closest('.log, .trend-news, .serp, #guideBody, .social-box')) {
        if (n.placeholder && UR[n.placeholder]) n.placeholder = UR[n.placeholder];
      } else {
        if (n.placeholder && UR[n.placeholder]) n.placeholder = UR[n.placeholder];
        if (n.title && UR[n.title]) n.title = UR[n.title];
      }
    } else if (n.nodeType === 3) {
      const raw = n.nodeValue;
      const key = raw.replace(/\s+/g, ' ').trim();
      const p = n.parentElement;
      if (key && UR[key] && p && !SKIP.has(p.tagName) && !p.closest('.log, .trend-news, .serp, #guideBody, .social-box')) {
        n.nodeValue = raw.replace(raw.trim(), UR[key]);
      }
    }
    n = walker.nextNode();
  }
}

if (UI_LANG === 'ur') {
  document.documentElement.lang = 'ur-Latn';
  document.addEventListener('DOMContentLoaded', () => {
    translateTree(document.body);
    new MutationObserver((muts) => muts.forEach((m) => m.addedNodes.forEach((node) => {
      if (node.nodeType === 1) translateTree(node);
      else if (node.nodeType === 3 && node.parentElement) translateTree(node.parentElement);
    }))).observe(document.body, { childList: true, subtree: true });
  });
}
