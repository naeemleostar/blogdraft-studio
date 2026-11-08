// Setup guide content (English and Roman Urdu). Each step: id, title, html.
const GUIDE = {
  en: [
    { id: 'guide-start', title: 'How the app works', html: `
      <p>BlogDraft Studio finds a topic for your niche, researches it on Google, writes an SEO-ready article,
      adds images and saves it in your WordPress as a <b>Draft</b>. Nothing is published automatically:
      you read it, add your own touch and click Publish yourself.</p>
      <p>You need three things: your <b>WordPress Application Password</b>, a <b>Gemini API key</b> (free to start)
      and, optionally, a <b>Pexels API key</b> for free photos. All keys stay on your computer.</p>
      <div class="callout info"><b>"Windows protected your PC"?</b> Click <b>More info</b> → <b>Run anyway</b>. The app is free and
      open source (github.com/naeemleostar/blogdraft-studio) but not code-signed yet, so Windows doesn't recognise it.</div>` },

    { id: 'guide-wp', title: 'WordPress Application Password', html: `
      <ol>
        <li>Log in to your WordPress dashboard (<code>yourblog.com/wp-admin</code>).</li>
        <li>Go to <b>Users → Profile</b> and scroll to the bottom, to <b>Application Passwords</b>.</li>
        <li>Type a name such as <code>BlogDraft Studio</code> and click <b>Add New Application Password</b>.</li>
        <li>Copy the password shown (like <code>abcd EFGH 1234 ijkl …</code>). It is shown only once.</li>
        <li>In the app: <b>Settings → Connections</b>, enter your site address, your WordPress <b>username</b>
            (or email) and this password, then click <b>Save &amp; test WordPress</b>.</li>
      </ol>
      <div class="callout warn"><b>Don't see "Application Passwords"?</b> Your site must use <code>https://</code>.
      Some hosts or security plugins switch it off: in <b>Hostinger</b> go to the Hostinger menu → Tools/Security and turn
      <i>off</i> "Disable application passwords"; in <b>Wordfence</b> check Login Security settings; in <b>Solid Security</b>
      check its API settings. Use your normal password nowhere in this app — only the Application Password.</div>` },

    { id: 'guide-gemini', title: 'Gemini API key (Google AI Studio)', html: `
      <ol>
        <li>Open <a class="link" href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a> and sign in with your Google account.</li>
        <li>Click <b>Create API key</b> (choose or create a project if asked) and copy the key.</li>
        <li>In the app: <b>Settings → Connections → Gemini API key</b>, paste it and click <b>Save &amp; detect models</b>.
            The app picks the best text and image models your key can use.</li>
        <li>Click <b>Test AI image</b>. If it fails with a "quota" message, read the note below.</li>
      </ol>
      <div class="callout info"><b>Free or paid?</b> Writing articles works on the free tier (with daily limits).
      <b>AI image generation usually needs billing turned on</b> for your project in Google AI Studio
      (Dashboard → Billing / "Set up billing"). Images then cost a small amount each — check Google's current
      pricing page. If you don't want to pay, choose <b>Free photos only (Pexels)</b> as the image source.</div>` },

    { id: 'guide-pexels', title: 'Pexels API key (free photos, optional)', html: `
      <ol>
        <li>Open <a class="link" href="https://www.pexels.com/api/" target="_blank" rel="noopener">pexels.com/api</a> and create a free account (or log in).</li>
        <li>Click <b>Your API Key</b> / request a key, fill the short form (website: your blog address) and copy the key.</li>
        <li>In the app: paste it in <b>Settings → Pexels API key</b> and click <b>Save &amp; test Pexels</b>.</li>
      </ol>
      <div class="callout info">Pexels photos are free to use. The app always credits the photographer under the photo.</div>` },

    { id: 'guide-bridge', title: 'SEO bridge plugin (optional)', html: `
      <p>Without it the app still works, but the meta description goes into the post excerpt. With it, the app also fills
      the <b>SEO title, meta description and focus keyword</b> of <b>Yoast SEO</b> or <b>Rank Math</b>.</p>
      <ol>
        <li>In WordPress go to <b>Plugins → Add New → Upload Plugin</b>.</li>
        <li>Choose <code>wp-plugin/blogdraft-studio-bridge.zip</code> from the app folder → <b>Install Now</b> → <b>Activate</b>.</li>
        <li>No upload button? Use your host's <b>File Manager</b>: open <code>public_html/wp-content/plugins/</code>,
            upload the zip, right-click → <b>Extract</b>, then activate it under Plugins.</li>
        <li>Click <b>Save &amp; test WordPress</b> again: it should say "SEO plugin bridge: installed".</li>
      </ol>` },

    { id: 'guide-daily', title: 'Daily use', html: `
      <ol>
        <li><b>Settings</b>: tick your niche and click <b>Apply recommended settings</b> (length, images, tone).</li>
        <li><b>Find Topics</b>: click <b>Hot in my niche</b> (the most-covered stories in your niche and country), or use AI / keyword ideas → <b>Write this</b>.</li>
        <li><b>Write Post</b>: add a few lines of <b>your own experience</b> → <b>Research &amp; Write</b>.</li>
        <li>Read the preview, fix anything in <b>Checks</b>, edit the SEO fields.</li>
        <li><b>Add images &amp; save Draft in WordPress</b> → open the draft → read once → <b>Publish</b> yourself.</li>
      </ol>
      <div class="callout warn"><b>For AdSense approval:</b> publish 2–3 good posts a week, stay in your niche, add your own
      photos, screenshots and experience, and check facts against the Sources list. Mass-publishing unedited AI posts is
      treated as spam by Google.</div>` },

    { id: 'guide-other', title: 'OpenAI or Claude for writing (optional)', html: `
      <p>Research always uses Gemini with Google Search. If you prefer, the article itself can be written by OpenAI (the ChatGPT API) or Claude.
      These are paid APIs, separate from a ChatGPT or Claude chat subscription.</p>
      <ol>
        <li><b>OpenAI:</b> <a class="link" href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">platform.openai.com/api-keys</a> → Create new secret key. Add credit under Billing.</li>
        <li><b>Claude:</b> <a class="link" href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com</a> → API Keys → Create Key. Add credit under Billing.</li>
        <li>In the app: Settings → <b>Who writes the article</b> → paste the key → <b>Save &amp; detect</b> → choose the writer.</li>
      </ol>` },

    { id: 'guide-features', title: 'More tools', html: `
      <ul>
        <li><b>Outline first</b>: on Write Post, click <b>Research &amp; make outline</b>, change the sections, then write.</li>
        <li><b>Your photos</b>: add screenshots or photos on Write Post; they go into the post before any stock or AI image.</li>
        <li><b>Fact-check</b>: in Checks, lists any claim that is not in the research.</li>
        <li><b>Calendar</b>: plan your posts; the app warns when you go above your weekly limit.</li>
        <li><b>Update Old Posts</b>: finds what changed since an old post was written and suggests edits.</li>
        <li><b>Links from older posts</b>: after publishing, finds older posts where a link to the new one fits.</li>
        <li><b>Several sites</b>: use the Site menu at the top left. Each site has its own niche and settings.</li>
        <li><b>Report a problem</b> (bottom left): copies a report without your keys, to send to whoever shared the app.</li>
      </ul>` },

    { id: 'guide-trouble', title: 'Problems and fixes', html: `
      <table class="cost">
        <tr><th>Message</th><th>Fix</th></tr>
        <tr><td>WordPress HTTP 401</td><td>Wrong username or Application Password. Create a new one and paste it again.</td></tr>
        <tr><td>WordPress HTTP 403 / blocked</td><td>A security plugin or host firewall blocks the REST API. Allow <code>/wp-json/</code> or your IP.</td></tr>
        <tr><td>Gemini 429 / quota</td><td>Free limit reached or images need billing. Wait, turn on billing, or use Pexels photos.</td></tr>
        <tr><td>Model not found</td><td>Google renamed its models. Click <b>Save &amp; detect models</b> again.</td></tr>
        <tr><td>Trends could not be loaded</td><td>Check your internet; turn off VPN; try again in a minute.</td></tr>
        <tr><td>App window closed</td><td>Run the start file again. Your drafts are saved in the drafts folder.</td></tr>
      </table>` },
  ],

  ur: [
    { id: 'guide-start', title: 'App kaise kaam karti hai', html: `
      <p>BlogDraft Studio aap ki niche ka topic dhoondti hai, Google par research karti hai, SEO wala article likhti hai,
      tasveerein lagati hai aur WordPress mein <b>Draft</b> bana deti hai. Khud kuch publish nahi hota: aap padhte hain,
      apna tajurba jodte hain aur <b>Publish</b> khud dabate hain.</p>
      <p>Teen cheezein chahiye: <b>WordPress Application Password</b>, <b>Gemini API key</b> (shuru mein free) aur
      (optional) free photos ke liye <b>Pexels API key</b>. Saari keys sirf aap ke computer par rehti hain.</p>
      <div class="callout info"><b>"Windows protected your PC" aaya?</b> <b>More info</b> → <b>Run anyway</b> dabayein. App free aur
      open source hai (github.com/naeemleostar/blogdraft-studio), bas abhi code-signed nahi, is liye Windows usay nahi pehchanta.</div>` },

    { id: 'guide-wp', title: 'WordPress Application Password', html: `
      <ol>
        <li>WordPress dashboard mein login karein (<code>aapkiblog.com/wp-admin</code>).</li>
        <li><b>Users → Profile</b> par jayein aur bilkul neeche <b>Application Passwords</b> tak scroll karein.</li>
        <li>Naam likhein, jaise <code>BlogDraft Studio</code>, aur <b>Add New Application Password</b> dabayein.</li>
        <li>Jo password dikhe (jaise <code>abcd EFGH 1234 ijkl …</code>) copy kar lein. Ye sirf ek dafa dikhta hai.</li>
        <li>App mein: <b>Settings → Connections</b> mein site address, WordPress <b>username</b> (ya email) aur ye password
            daalein, phir <b>Save &amp; test WordPress</b> dabayein.</li>
      </ol>
      <div class="callout warn"><b>"Application Passwords" nazar nahi aa raha?</b> Site <code>https://</code> par honi chahiye.
      Kuch hosting ya security plugins isay band kar dete hain: <b>Hostinger</b> mein Hostinger menu → Tools/Security mein
      "Disable application passwords" ko <i>OFF</i> karein; <b>Wordfence</b> mein Login Security settings dekhein.
      Apna asal WordPress password is app mein kahin na daalein, sirf Application Password.</div>` },

    { id: 'guide-gemini', title: 'Gemini API key (Google AI Studio)', html: `
      <ol>
        <li><a class="link" href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a> kholein aur Google account se sign in karein.</li>
        <li><b>Create API key</b> dabayein (project poochay to chun lein ya naya banayein) aur key copy karein.</li>
        <li>App mein: <b>Settings → Connections → Gemini API key</b> mein paste karein aur <b>Save &amp; detect models</b> dabayein.
            App khud behtareen text aur image model chun leti hai.</li>
        <li><b>Test AI image</b> dabayein. Agar "quota" ka error aaye to neeche wala note padhein.</li>
      </ol>
      <div class="callout info"><b>Free ya paid?</b> Article likhna free tier par chalta hai (rozana limit ke saath).
      <b>AI tasveerein banane ke liye aksar billing on karni padti hai</b> (Google AI Studio → Billing / "Set up billing").
      Har tasveer ke thode se paise lagte hain, Google ka pricing page dekh lein. Paise nahi lagane to image source
      <b>Free photos only (Pexels)</b> rakhein.</div>` },

    { id: 'guide-pexels', title: 'Pexels API key (free photos, optional)', html: `
      <ol>
        <li><a class="link" href="https://www.pexels.com/api/" target="_blank" rel="noopener">pexels.com/api</a> kholein aur free account banayein (ya login karein).</li>
        <li><b>Your API Key</b> par click karein, chhota sa form bharein (website mein apni blog ka address) aur key copy karein.</li>
        <li>App mein <b>Settings → Pexels API key</b> mein paste karke <b>Save &amp; test Pexels</b> dabayein.</li>
      </ol>
      <div class="callout info">Pexels ki photos free hain. App har photo ke neeche photographer ka naam khud likhti hai.</div>` },

    { id: 'guide-bridge', title: 'SEO bridge plugin (optional)', html: `
      <p>Iske baghair bhi app chalti hai, bas meta description post ke excerpt mein jati hai. Plugin ho to app
      <b>Yoast SEO</b> ya <b>Rank Math</b> ka <b>SEO title, meta description aur focus keyword</b> bhi khud bhar deti hai.</p>
      <ol>
        <li>WordPress mein <b>Plugins → Add New → Upload Plugin</b>.</li>
        <li>App folder se <code>wp-plugin/blogdraft-studio-bridge.zip</code> chunein → <b>Install Now</b> → <b>Activate</b>.</li>
        <li>Upload ka button nahi? Hosting ke <b>File Manager</b> mein <code>public_html/wp-content/plugins/</code> kholein,
            zip upload karein, right-click → <b>Extract</b>, phir Plugins mein Activate karein.</li>
        <li>Dobara <b>Save &amp; test WordPress</b> dabayein: "SEO plugin bridge: installed" aana chahiye.</li>
      </ol>` },

    { id: 'guide-daily', title: 'Roz ka kaam', html: `
      <ol>
        <li><b>Settings</b>: apni niche tick karein aur <b>Apply recommended settings</b> dabayein (length, tasveerein, tone).</li>
        <li><b>Find Topics</b>: <b>Hot in my niche</b> dabayein (aap ki niche aur mulk ki sab se zyada chalne wali khabrein), ya AI / keyword ideas → <b>Write this</b>.</li>
        <li><b>Write Post</b>: 2-3 line <b>apna tajurba</b> likhein → <b>Research &amp; Write</b>.</li>
        <li>Preview padhein, <b>Checks</b> mein jo likha ho theek karein, SEO fields dekh lein.</li>
        <li><b>Add images &amp; save Draft in WordPress</b> → draft kholein → ek dafa padhein → <b>Publish</b> khud dabayein.</li>
      </ol>
      <div class="callout warn"><b>AdSense approval ke liye:</b> hafte mein 2-3 achhi posts, sirf apni niche, apni photos,
      screenshots aur tajurba, aur Sources list se facts check karein. Bina padhe dher saari AI posts daalna Google spam
      samajhta hai.</div>` },

    { id: 'guide-other', title: 'Likhne ke liye OpenAI ya Claude (optional)', html: `
      <p>Research hamesha Gemini aur Google Search se hoti hai. Chahein to article OpenAI (ChatGPT API) ya Claude se likhwa sakte hain.
      Ye paid API hain, ChatGPT ya Claude ki chat subscription se alag.</p>
      <ol>
        <li><b>OpenAI:</b> <a class="link" href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">platform.openai.com/api-keys</a> → Create new secret key. Billing mein credit daalein.</li>
        <li><b>Claude:</b> <a class="link" href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com</a> → API Keys → Create Key. Billing mein credit daalein.</li>
        <li>App mein: Settings → <b>Who writes the article</b> → key paste karein → <b>Save &amp; detect</b> → writer chunein.</li>
      </ol>` },

    { id: 'guide-features', title: 'Mazeed tools', html: `
      <ul>
        <li><b>Pehle outline</b>: Write Post par <b>Research &amp; make outline</b> dabayein, headings badlein, phir likhwayein.</li>
        <li><b>Apni tasveerein</b>: Write Post par screenshots ya photos add karein, ye post mein stock/AI tasveeron se pehle lagengi.</li>
        <li><b>Fact-check</b>: Checks mein wo baatein dikhata hai jo research mein nahi thin.</li>
        <li><b>Calendar</b>: posts ka plan banayein. Hafte ki had se zyada hon to app khabardar karti hai.</li>
        <li><b>Update Old Posts</b>: purani post ke baad kya badla, dhoond kar tabdeeliyan tajweez karta hai.</li>
        <li><b>Links from older posts</b>: publish ke baad purani posts mein naye post ka link lagane ki jagah dhoondta hai.</li>
        <li><b>Kai sites</b>: upar left mein Site menu. Har site ki apni niche aur settings.</li>
        <li><b>Report a problem</b> (neeche left): keys ke baghair report copy karta hai, jo aap app dene wale ko bhej sakte hain.</li>
      </ul>` },

    { id: 'guide-trouble', title: 'Masle aur hal', html: `
      <table class="cost">
        <tr><th>Message</th><th>Hal</th></tr>
        <tr><td>WordPress HTTP 401</td><td>Username ya Application Password galat hai. Naya password bana kar dobara paste karein.</td></tr>
        <tr><td>WordPress HTTP 403 / blocked</td><td>Security plugin ya hosting firewall REST API rok raha hai. <code>/wp-json/</code> ko allow karein.</td></tr>
        <tr><td>Gemini 429 / quota</td><td>Free limit khatam ya tasveeron ke liye billing chahiye. Intezar karein, billing on karein, ya Pexels use karein.</td></tr>
        <tr><td>Model not found</td><td>Google ne model ka naam badla hai. <b>Save &amp; detect models</b> dobara dabayein.</td></tr>
        <tr><td>Trends could not be loaded</td><td>Internet check karein, VPN band karein, ek minute baad try karein.</td></tr>
        <tr><td>App ki window band ho gayi</td><td>Start file dobara chalayein. Drafts drafts folder mein save hain.</td></tr>
      </table>` },
  ],
};
