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

### 4. Output

Save to: `<current-project-dir>/<slug>.html`

If no project context: `~/opensource/vault/html-artifacts/<slug>.html`

Name after the topic, not the date:
- `x-algorithm-field-guide.html`
- `magnetx-scoring-explained.html`
- `wipdp-auth-flow.html`

Surface on completion:
```
↳ Built: path/to/file.html — open in browser.
```

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
