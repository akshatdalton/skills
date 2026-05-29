---
name: visualize-via-html
description: Use when the user wants to understand any topic, plan, discussion, research finding, or system visually rather than through text. Triggers when user says "show me visually", "create an HTML", "help me understand via HTML", "I want to see this interactively", invokes the skill directly, or when any planning/research session ends and a markdown file would normally be written.
---

# Visualize via HTML

HTML is the new markdown. Trade a document you'd skim for one you'd actually read.

Inspired by Thariq Shihipar's (Claude Code team, Anthropic) "The Unreasonable Effectiveness of HTML" — 20 self-contained HTML files that replace markdown across every kind of work. The principle: **let the user experience information rather than parse it.**

---

## Core Rule

After any conversation, discussion, plan, research, or finding — instead of writing a markdown file, build a **self-contained HTML artifact**. No external network requests. Zero dependencies. Opens directly in any browser.

---

## Workflow

### 1. Extract the story

Pull context from all available sources in parallel:
- Current conversation thread (primary source)
- `~/.claude/plans/<slug>.md` if a plan exists
- `~/opensource/vault/wiki/projects/*/initiatives/<slug>/` — charter, decisions, learnings
- Any code, PRs, or system being discussed

Reduce to **3–7 beats**: the core things the user needs to understand, in a logical sequence. These beats drive the HTML structure.

### 2. Choose your expression

Pick freely. Mix and match. No template required — the content drives the form.

| What needs to be understood | HTML expression |
|---|---|
| Comparison / multiple options | Side-by-side panels, trade-off tags inline |
| Flow / process / steps | Animated SVG flow, click-through sequence |
| Before / after states | Split-screen or scroll-reveal transition |
| Research findings / insights | Scrollytelling — scroll position reveals each insight |
| Plan / implementation | Timeline + data-flow diagram + risk table |
| Concept explanation | Interactive widget + minimal prose |
| System architecture | Boxes-and-arrows, click to expand detail |
| Decisions made | Card layout, reasoning visible on hover/click |
| What to do vs. what not to do | Two-path visual — green vs. red, with examples |
| Status / report | Small chart + colored timeline |
| Slide deck for others | Arrow-key `<section>` navigation, no build step |
| Learning a new topic | Collapsible sections, tabbed examples, glossary |
| Code review / diff | Annotated diff with margin notes, severity color |

These are starting points. If a better expression exists, use it.

### 3. Build without limits

**You have no constraints on expression.** Use whatever makes the information land:

- **SVG** for diagrams, flows, illustrations, before/after
- **CSS animations** for transitions, scroll reveals, emphasis, state changes
- **Vanilla JS** for interactivity — sliders, toggles, tabs, click-to-expand, live demos
- **Scroll-driven reveals** (Intersection Observer, inline — no CDN)
- **Color, typography, whitespace** — design it, don't dump it
- **Interactive widgets** — a live ring you can add nodes to, a tuner with sliders, a drag board

**Non-negotiable constraints** (everything else is fair game):
- Self-contained: **zero external network requests** — no CDN links, no web fonts, no external images
- All CSS and JS inline in the file
- **Minimal text per section** — one strong headline + one supporting line max per panel; the visual carries the meaning
- If a section looks like a markdown bullet list, it is wrong — redo it as a visual
- **Every major section gets a stable `id`** — `<section id="findings">`, `<div id="risk-table">`, `<svg id="flow-diagram">`. This makes the inline feedback widget (below) able to anchor comments to specific blocks and survives future edits. No `id`s = fragile `nth-child` selectors when users comment.
- **Include the feedback widget** — see "Feedback Widget" section below; copy the `<style>` + `<button>` + `<aside>` + `<script>` block into every artifact

### 4. Output

**All artifacts live under a single, centralized root: `~/.claude/html-artifacts/`**

One folder per artifact (even for single-page ones) so the HTML, its `comments.json`, screenshots, and future versions all live together:

```
~/.claude/html-artifacts/
├── x-algorithm-field-guide/
│   ├── index.html
│   └── comments.json    ← created when user exports feedback
├── magnetx-scoring-explained/
│   └── index.html
└── wipdp-auth-flow/
    ├── index.html
    └── architecture.html  ← multi-page artifacts go here too
```

Slug rules:
- Name after the **topic**, not the date
- Lowercase, hyphen-separated
- The main entry file is always `index.html`

Create the folder if it doesn't exist: `mkdir -p ~/.claude/html-artifacts/<slug>/`.

Surface on completion using **both** the file path and a `file://` URL so the user can click to open:
```
↳ Built: ~/.claude/html-artifacts/<slug>/index.html
   file:///Users/<you>/.claude/html-artifacts/<slug>/index.html
```

### 5. Iterate (don't rebuild)

When the user asks for changes to an artifact you've already built — **edit the existing file in place. Do not regenerate from scratch.**

Workflow:
1. **Read** `~/.claude/html-artifacts/<slug>/index.html` first to recover the current state
2. **If `comments.json` exists next to it**, read that too — those are user-left inline comments waiting to be addressed. Each entry has `{ id, selector, target_text, body }`. Use the `selector` to locate exactly what they're commenting on.
3. **Make surgical edits** with the Edit tool (not Write) — preserve the existing structure, ids, and styles
4. **Keep all `id` attributes stable** — they're anchors users have already commented against. Renaming `#findings` to `#key-findings` orphans every comment pointing at the old id.
5. **After processing comments.json**, mention which comment IDs you addressed and which you skipped (and why) so the user can verify

Anti-pattern: regenerating the HTML "to apply the user's feedback cleanly". This destroys ids and breaks the comment trail. Edit in place.

---

## Design System — Thariq / Anthropic Aesthetic

**Use this by default unless the user asks for something different.** Every HTML file Thariq published uses the same token set — warm ivory background, serif headings, terracotta accent. It feels considered without being loud.

### CSS Boilerplate (copy into every file)

```html
<style>
:root {
  --ivory:    #FAF9F5;  /* page background */
  --slate:    #141413;  /* h1 / dark headings */
  --clay:     #D97757;  /* accent — warm terracotta */
  --oat:      #E3DACC;  /* warm dividers, subtle fills */
  --olive:    #788C5D;  /* secondary accent — muted sage */
  --gray-150: #F0EEE6;  /* card / box backgrounds */
  --gray-300: #D1CFC5;  /* borders */
  --gray-500: #87867F;  /* labels, eyebrows, secondary text */
  --gray-700: #3D3D3A;  /* body text */
  --white:    #FFFFFF;

  --serif: ui-serif, Georgia, 'Times New Roman', serif;
  --sans:  system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --mono:  ui-monospace, 'SF Mono', Menlo, Monaco, monospace;
}

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--sans);
  background: var(--ivory);
  color: var(--gray-700);
  line-height: 1.55;
  padding: 56px 32px 96px;
  -webkit-font-smoothing: antialiased;
}

.page   { max-width: 1120px; margin: 0 auto; }
.page-head { margin-bottom: 48px; max-width: 760px; }

/* Typography */
.eyebrow { font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--gray-500); margin-bottom: 12px; }
h1       { font-family: var(--serif); font-weight: 500; font-size: 38px; line-height: 1.15; color: var(--slate); margin-bottom: 18px; letter-spacing: -0.01em; }
h2       { font-family: var(--serif); font-weight: 500; font-size: 22px; color: var(--slate); margin-bottom: 12px; }
.lead    { font-size: 17px; color: var(--gray-500); max-width: 640px; }
code     { font-family: var(--mono); font-size: 13px; background: var(--gray-150); padding: 2px 6px; border-radius: 4px; }

/* Cards / boxes */
.card    { background: var(--white); border: 1.5px solid var(--gray-300); border-radius: 12px; padding: 24px; }
.box     { background: var(--gray-150); border: 1.5px solid var(--gray-300); border-radius: 12px; padding: 16px 20px; }

/* Tags */
.tag     { display: inline-block; font-size: 11px; letter-spacing: 0.06em; text-transform: uppercase; padding: 3px 8px; border-radius: 4px; font-weight: 600; }
.tag-pro { background: #E8F0E0; color: var(--olive); }
.tag-con { background: #FAE8E2; color: #C0533A; }
.tag-clay{ background: #FAF0EA; color: var(--clay); }
</style>
```

### Color Usage Guide

| Token | Hex | Use for |
|---|---|---|
| `--ivory` | `#FAF9F5` | Page background |
| `--slate` | `#141413` | H1, strong headings, dark emphasis |
| `--clay` | `#D97757` | Primary accent — highlights, active states, CTAs |
| `--oat` | `#E3DACC` | Dividers, warm-tinted fills, timeline tracks |
| `--olive` | `#788C5D` | Secondary accent — "pro", success, positive |
| `--gray-150` | `#F0EEE6` | Card backgrounds, code boxes, subtle fills |
| `--gray-300` | `#D1CFC5` | Borders, separators |
| `--gray-500` | `#87867F` | Eyebrow labels, secondary text, metadata |
| `--gray-700` | `#3D3D3A` | Body text |

### Typography Rules

- **Page title (h1):** serif font, 38px, weight 500, `--slate`
- **Section headers (h2):** serif font, 22px, weight 500
- **Eyebrow labels** (the small uppercase tag above h1): 12px, 0.08em tracking, `--gray-500`
- **Body:** sans, 16px, 1.55 line-height, `--gray-700`
- **Lead text** (subtitle under h1): 17px, `--gray-500`
- **Code:** mono, 13px, `--gray-150` background pill

### When to Override

Override the color system when:
- The content has strong brand color requirements (e.g. a company's design system explainer)
- A dark/dramatic mood fits better (e.g. incident post-mortem, security topic)
- The user explicitly asks for different colors

Otherwise, stay on the Anthropic palette — it looks intentional without effort.

---

## Feedback Widget (paste into every artifact)

HTML artifacts aren't one-and-done. Users want to highlight a chart and say "wrong number", click a section and say "expand this", or leave a free-form note — without context-switching back to chat to type out what they're referring to.

The widget below is **self-contained, zero-dependency, and ~220 lines inline**. It gives every artifact:

- **Floating 💬 button** bottom-right with a comment count badge — opens the sidebar
- **Text-selection comments (Notion-style)** — highlight any text → small 💬 icon appears next to the selection → click the icon → popup with textarea → save. The icon dismisses when you click elsewhere, so selecting text never blocks the page.
- **Element comments** — Alt-click any section with an `id` → popup opens directly (the gesture is explicit, no intermediate icon needed) → save
- **Sidebar panel** listing all comments with delete + clear
- **Export JSON** — downloads `comments.json` (drop next to `index.html`, then ask Claude to address them)
- **Copy as prompt** — copies a Claude-ready prompt to the clipboard with all comments
- **localStorage persistence** — keyed by `location.pathname`, survives reload

### Why ids matter for this to work

The widget records a CSS selector for each comment. If you give every major section a stable `id`, comments anchor cleanly (`#findings`, `#timeline`). Without ids, it falls back to brittle `section:nth-of-type(3) > div.card` paths that break the moment you edit the structure.

### Paste this into every artifact (before `</body>`)

```html
<!-- ===== Feedback widget (self-contained, no deps) ===== -->
<style>
  #vh-fb-toggle{position:fixed;bottom:20px;right:20px;z-index:10000;width:44px;height:44px;border-radius:50%;background:var(--clay,#D97757);color:#fff;border:none;cursor:pointer;font-size:20px;box-shadow:0 4px 12px rgba(0,0,0,.15);display:flex;align-items:center;justify-content:center}
  #vh-fb-toggle .count{position:absolute;top:-4px;right:-4px;background:var(--slate,#141413);color:#fff;border-radius:10px;padding:2px 6px;font-size:11px;font-weight:600;min-width:18px;display:none}
  #vh-fb-toggle .count.show{display:block}
  #vh-fb-panel{position:fixed;top:0;right:0;bottom:0;width:360px;background:#fff;box-shadow:-4px 0 20px rgba(0,0,0,.1);transform:translateX(100%);transition:transform .25s ease;z-index:9999;display:flex;flex-direction:column;font-family:var(--sans,system-ui,sans-serif)}
  #vh-fb-panel.open{transform:translateX(0)}
  #vh-fb-panel header{padding:16px 20px;border-bottom:1px solid #e5e5e5;display:flex;justify-content:space-between;align-items:center}
  #vh-fb-panel header h3{margin:0;font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:#666}
  #vh-fb-panel header button{background:none;border:none;cursor:pointer;font-size:20px;color:#999;line-height:1}
  #vh-fb-list{flex:1;overflow-y:auto;padding:12px 20px}
  .vh-fb-item{border-left:3px solid var(--clay,#D97757);padding:8px 12px;margin-bottom:10px;background:#f9f9f7;border-radius:0 4px 4px 0;font-size:13px}
  .vh-fb-item .target{color:#888;font-size:11px;margin-bottom:4px;font-family:var(--mono,monospace);word-break:break-all}
  .vh-fb-item .body{color:#333;line-height:1.4}
  .vh-fb-item .del{float:right;background:none;border:none;cursor:pointer;color:#c33;font-size:14px;padding:0 4px}
  #vh-fb-actions{padding:12px 20px;border-top:1px solid #e5e5e5;display:flex;gap:6px;flex-wrap:wrap}
  #vh-fb-actions button{flex:1;min-width:80px;padding:8px 10px;border-radius:6px;border:1px solid #ddd;background:#fff;cursor:pointer;font-size:12px;font-weight:500}
  #vh-fb-actions button:hover{background:#f5f5f5}
  #vh-fb-popup{position:absolute;z-index:10001;background:var(--slate,#141413);color:#fff;border-radius:6px;padding:8px;box-shadow:0 4px 16px rgba(0,0,0,.2);display:none;min-width:260px}
  #vh-fb-popup.show{display:block}
  #vh-fb-popup .ctx{font-size:11px;color:#aaa;margin-bottom:6px;font-family:var(--mono,monospace);max-height:40px;overflow:hidden}
  #vh-fb-popup textarea{width:100%;min-height:60px;border-radius:4px;border:none;padding:6px 8px;font-family:inherit;font-size:13px;resize:vertical;box-sizing:border-box}
  #vh-fb-popup .actions{display:flex;gap:6px;margin-top:6px;justify-content:flex-end}
  #vh-fb-popup button{background:var(--clay,#D97757);color:#fff;border:none;border-radius:4px;padding:4px 10px;cursor:pointer;font-size:12px}
  #vh-fb-popup button.cancel{background:transparent;color:#aaa}
  .vh-fb-highlight{background:rgba(217,119,87,.18)!important;transition:background .3s}
  #vh-fb-toast{position:fixed;bottom:80px;right:20px;background:var(--slate,#141413);color:#fff;padding:10px 16px;border-radius:6px;font-size:13px;font-family:var(--sans,system-ui,sans-serif);box-shadow:0 4px 12px rgba(0,0,0,.2);opacity:0;transform:translateY(8px);transition:all .2s;z-index:10002;pointer-events:none}
  #vh-fb-toast.show{opacity:1;transform:translateY(0)}
  #vh-fb-selicon{position:absolute;z-index:10001;background:var(--slate,#141413);color:#fff;border:none;border-radius:6px;width:30px;height:30px;cursor:pointer;font-size:14px;display:none;align-items:center;justify-content:center;box-shadow:0 2px 10px rgba(0,0,0,.25);transition:transform .12s}
  #vh-fb-selicon:hover{transform:scale(1.1);background:var(--clay,#D97757)}
  #vh-fb-selicon.show{display:flex}
</style>
<button id="vh-fb-toggle" title="Comments (Alt-click any section to comment)">💬<span class="count"></span></button>
<aside id="vh-fb-panel">
  <header><h3>Comments</h3><button onclick="vhFb.toggle()">×</button></header>
  <div id="vh-fb-list"></div>
  <div id="vh-fb-actions">
    <button onclick="vhFb.copyPrompt()">Copy prompt</button>
    <button onclick="vhFb.exportJson()">Export JSON</button>
    <button onclick="vhFb.clear()">Clear</button>
  </div>
</aside>
<button id="vh-fb-selicon" title="Comment on selection">💬</button>
<div id="vh-fb-popup">
  <div class="ctx" id="vh-fb-ctx"></div>
  <textarea id="vh-fb-input" placeholder="Add a comment… (Cmd/Ctrl+Enter to save)"></textarea>
  <div class="actions">
    <button class="cancel" onclick="vhFb.cancelPopup()">Cancel</button>
    <button onclick="vhFb.savePopup()">Save</button>
  </div>
</div>
<div id="vh-fb-toast"></div>
<script>
(function(){
  const KEY='vh-fb-'+location.pathname;
  let comments=JSON.parse(localStorage.getItem(KEY)||'[]');
  let pending=null;
  const $=s=>document.querySelector(s);
  function save(){localStorage.setItem(KEY,JSON.stringify(comments));render();}
  function selectorFor(el){
    if(!el||el.nodeType!==1)return '';
    if(el.id)return '#'+el.id;
    const path=[];
    while(el&&el.nodeType===1&&el!==document.body){
      let p=el.tagName.toLowerCase();
      if(el.id){path.unshift('#'+el.id);break;}
      const sibs=Array.from(el.parentNode.children).filter(c=>c.tagName===el.tagName);
      if(sibs.length>1)p+=':nth-of-type('+(sibs.indexOf(el)+1)+')';
      path.unshift(p);
      el=el.parentNode;
    }
    return path.join(' > ');
  }
  function render(){
    const list=$('#vh-fb-list');
    if(comments.length===0){
      list.innerHTML='<p style="color:#999;font-size:13px;text-align:center;padding:20px;line-height:1.5">No comments yet.<br>Select text or Alt-click a section.</p>';
    }else{
      list.innerHTML=comments.map((c,i)=>{
        const ctx=c.target_text?'"'+c.target_text.slice(0,60).replace(/</g,'&lt;')+(c.target_text.length>60?'…':'')+'"':c.selector;
        return '<div class="vh-fb-item"><button class="del" onclick="vhFb.del('+i+')">×</button><div class="target">'+ctx+'</div><div class="body">'+c.body.replace(/</g,'&lt;')+'</div></div>';
      }).join('');
    }
    const c=$('#vh-fb-toggle .count');
    c.textContent=comments.length;
    c.classList.toggle('show',comments.length>0);
  }
  function showPopup(x,y,target){
    pending=target;
    const popup=$('#vh-fb-popup');
    $('#vh-fb-ctx').textContent=target.target_text?'"'+target.target_text.slice(0,80)+(target.target_text.length>80?'…':'')+'"':target.selector;
    popup.style.left=Math.min(x,window.innerWidth-280)+'px';
    popup.style.top=(y+window.scrollY+8)+'px';
    popup.classList.add('show');
    setTimeout(()=>$('#vh-fb-input').focus(),50);
  }
  function cleanText(t){return (t||'').replace(/\s+/g,' ').trim();}
  function slugFromUrl(){
    const parts=location.pathname.split('/').filter(p=>p&&p!=='index.html');
    return parts.pop()||document.title||location.pathname;
  }
  function toast(msg){
    const t=$('#vh-fb-toast');
    t.textContent=msg;t.classList.add('show');
    clearTimeout(t._timer);
    t._timer=setTimeout(()=>t.classList.remove('show'),1800);
  }
  function showSelIcon(x,y){
    const icon=$('#vh-fb-selicon');
    icon.style.left=Math.min(x+6,window.innerWidth-50)+'px';
    icon.style.top=(y+window.scrollY+4)+'px';
    icon.classList.add('show');
  }
  function hideSelIcon(){$('#vh-fb-selicon').classList.remove('show');}
  let pendingSel=null;
  document.addEventListener('mouseup',e=>{
    if(e.target.closest('#vh-fb-popup,#vh-fb-panel,#vh-fb-toggle,#vh-fb-selicon'))return;
    // tiny delay so selection state is settled
    setTimeout(()=>{
      const sel=window.getSelection();
      const text=cleanText(sel.toString());
      if(!text){hideSelIcon();pendingSel=null;return;}
      const range=sel.getRangeAt(0);
      const rect=range.getBoundingClientRect();
      const p=range.commonAncestorContainer;
      const parent=p.nodeType===1?p:p.parentNode;
      pendingSel={type:'selection',selector:selectorFor(parent),target_text:text};
      showSelIcon(rect.right,rect.bottom);
    },1);
  });
  document.addEventListener('mousedown',e=>{
    if(!e.target.closest('#vh-fb-selicon,#vh-fb-popup'))hideSelIcon();
  });
  document.addEventListener('click',e=>{
    if(!e.altKey)return;
    if(e.target.closest('#vh-fb-popup,#vh-fb-panel,#vh-fb-toggle,#vh-fb-selicon'))return;
    e.preventDefault();
    const el=e.target.closest('[id],section,.card,.box')||e.target;
    const rect=el.getBoundingClientRect();
    showPopup(rect.left,rect.top,{type:'element',selector:selectorFor(el),target_text:cleanText(el.textContent).slice(0,100)});
  });
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape')vhFb.cancelPopup();
    if((e.metaKey||e.ctrlKey)&&e.key==='Enter'&&pending)vhFb.savePopup();
  });
  window.vhFb={
    toggle(){$('#vh-fb-panel').classList.toggle('open');},
    savePopup(){
      const body=$('#vh-fb-input').value.trim();
      if(!body||!pending)return this.cancelPopup();
      comments.push({id:'c-'+Date.now().toString(36),...pending,body,timestamp:new Date().toISOString()});
      save();this.cancelPopup();
    },
    cancelPopup(){
      $('#vh-fb-popup').classList.remove('show');
      $('#vh-fb-input').value='';pending=null;
    },
    del(i){comments.splice(i,1);save();},
    clear(){if(comments.length&&!confirm('Clear all comments?'))return;comments=[];save();},
    exportJson(){
      if(!comments.length)return toast('No comments to export.');
      const blob=new Blob([JSON.stringify(comments,null,2)],{type:'application/json'});
      const a=document.createElement('a');
      a.href=URL.createObjectURL(blob);
      a.download='comments.json';a.click();
      toast('Exported comments.json');
    },
    copyPrompt(){
      if(!comments.length)return toast('No comments to copy.');
      const slug=slugFromUrl();
      const lines=comments.map((c,i)=>(i+1)+'. ['+c.selector+'] '+(c.target_text?'"'+c.target_text.slice(0,80)+'"':'')+'\n   → '+c.body).join('\n\n');
      const prompt='Update the HTML artifact "'+slug+'" (path: '+location.pathname+') to address these inline comments. Edit in place — do not regenerate. Keep all existing ids stable.\n\n'+lines;
      navigator.clipboard.writeText(prompt).then(()=>toast('Copied prompt to clipboard'));
    },
  };
  $('#vh-fb-toggle').addEventListener('click',()=>vhFb.toggle());
  $('#vh-fb-selicon').addEventListener('click',e=>{
    e.stopPropagation();
    if(!pendingSel)return;
    const rect=$('#vh-fb-selicon').getBoundingClientRect();
    hideSelIcon();
    showPopup(rect.left,rect.bottom,pendingSel);
  });
  render();
})();
</script>
```

### How a feedback round trip works

1. You build the artifact → ships with widget baked in
2. User opens it, highlights a chart number → leaves comment "where does this come from?"
3. User clicks **Export JSON** → `comments.json` lands in Downloads → they move it next to `index.html`
4. User asks Claude: *"address the comments on the x-algorithm artifact"*
5. Claude reads `~/.claude/html-artifacts/x-algorithm/comments.json`, locates each `selector` in the HTML, edits in place

Faster path: user clicks **Copy prompt** → pastes into Claude directly. No file handling.

---

## Thariq's 20 Examples — Reference & Inspiration

Full set: **[thariqs.github.io/html-effectiveness](https://thariqs.github.io/html-effectiveness)**

These are real Claude-generated files. Study them to understand what's possible.

### Exploration & Planning
| Example | What it demonstrates | Link |
|---|---|---|
| Three code approaches | Side-by-side panels, pro/con tags inline, no prose | [01-exploration-code-approaches.html](https://thariqs.github.io/html-effectiveness/01-exploration-code-approaches.html) |
| Visual design directions | Live layout + palette options to react to, not imagine | [02-exploration-visual-designs.html](https://thariqs.github.io/html-effectiveness/02-exploration-visual-designs.html) |
| Implementation plan | Timeline, data-flow diagram, risk table — the handoff artifact | [16-implementation-plan.html](https://thariqs.github.io/html-effectiveness/16-implementation-plan.html) |

### Code Review & Understanding
| Example | What it demonstrates | Link |
|---|---|---|
| Annotated PR diff | Margin notes, severity color tags, jump links | [03-code-review-pr.html](https://thariqs.github.io/html-effectiveness/03-code-review-pr.html) |
| Module map | Unknown package as boxes + arrows, hot path highlighted | [04-code-understanding.html](https://thariqs.github.io/html-effectiveness/04-code-understanding.html) |
| PR writeup for reviewers | Motivation, before/after, file-by-file tour with the why | [17-pr-writeup.html](https://thariqs.github.io/html-effectiveness/17-pr-writeup.html) |

### Research & Learning
| Example | What it demonstrates | Link |
|---|---|---|
| Feature explainer | TL;DR box, collapsible steps, tabbed config snippets, FAQ | [14-research-feature-explainer.html](https://thariqs.github.io/html-effectiveness/14-research-feature-explainer.html) |
| Concept explainer | **Best example** — consistent hashing with a live interactive ring, comparison table, hover-linked glossary | [15-research-concept-explainer.html](https://thariqs.github.io/html-effectiveness/15-research-concept-explainer.html) |

### Diagrams & Slides
| Example | What it demonstrates | Link |
|---|---|---|
| Annotated flowchart | Deploy pipeline as real flowchart, click any step for details + failure paths | [13-flowchart-diagram.html](https://thariqs.github.io/html-effectiveness/13-flowchart-diagram.html) |
| Slide deck | Arrow-key navigation, no Keynote, no export step | [09-slide-deck.html](https://thariqs.github.io/html-effectiveness/09-slide-deck.html) |

### Custom Editors (most ambitious)
| Example | What it demonstrates | Link |
|---|---|---|
| Ticket triage board | Drag across Now/Next/Later/Cut — exports back to markdown | [18-editor-triage-board.html](https://thariqs.github.io/html-effectiveness/18-editor-triage-board.html) |
| Prompt tuner | Editable template + variable slots + live preview | [20-editor-prompt-tuner.html](https://thariqs.github.io/html-effectiveness/20-editor-prompt-tuner.html) |

**Most relevant for your use case:** `15-research-concept-explainer.html` (interactive widget for a complex concept) and `16-implementation-plan.html` (plan as visual timeline, not bullet list).

---

## Prompts That Work Well (internal reference)

When turning a discussion into HTML:
> "Create an HTML artifact that conveys [topic]. I'm most trying to understand [specific aspect]. Use visual/interactive elements — minimal text, no walls. Self-contained, no external deps."

When turning a plan into HTML:
> "Turn this plan into an HTML artifact — milestones on a timeline, data-flow diagram, risky sections highlighted, risk table at the bottom. Something navigable, not skimmable."

When explaining code or architecture:
> "Explain [system/PR] as an HTML artifact. Draw the module as boxes and arrows, annotate the hot path, show before/after the change. Render, don't describe."

---

## Anti-Patterns

| Avoid | Why |
|---|---|
| Markdown walls inside `<div>` | Defeats the purpose — use visual instead |
| External CDN links (`unpkg`, `cdnjs`, etc.) | Breaks offline; embed everything inline |
| Generic template repeated every time | Every HTML fits its content, not a mold |
| Asking for approval before building | Build first, show it, iterate after |
| Bullet-point-heavy sections | If it looks like markdown, it is wrong — redo as visual |
| One massive scroll with no navigation | Add in-page anchors, tabs, or sections for long content |
| Skipping `id` attributes on sections | Feedback widget falls back to `nth-child` selectors that break on edit |
| Regenerating artifact instead of editing | Destroys ids → orphans every user comment. Always Edit in place. |
| Renaming an existing `id` during iteration | Same as above — `#findings` → `#key-findings` breaks the comment trail |
| Saving artifacts to project root or random dirs | Use `~/.claude/html-artifacts/<slug>/index.html` so `comments.json` has a home |
| Omitting the feedback widget | Users can't leave inline notes — they have to context-switch back to chat |
