export const meta = {
  name: 'yt-shorts-production',
  description: 'Rank viral highlights from podcast transcripts, then cut + face-track + caption + vision-verify 9:16 clips for X (@aksenHQ)',
  phases: [
    { title: 'Rank',    detail: 'one agent per source ranks the strongest viral 45-90s moments' },
    { title: 'Produce', detail: 'per candidate: 05_clip (9:16 face-track) + 06_caption + 08_verify scan' },
    { title: 'Verify',  detail: 'vision gate reads review frames, writes PASS/REJECT verify_result.json' },
  ],
}

// ---- config (passed verbatim via Workflow args) ----
let A = args
if (typeof A === 'string') { try { A = JSON.parse(A) } catch (e) { throw new Error('args not parseable JSON: ' + e.message) } }
if (!A || !A.sources) throw new Error('args.sources missing; got: ' + JSON.stringify(A).slice(0, 200))
const SRC = A.sources
const PROCESS_CAP = A.processCap || 16
const TARGET = A.target || 10
const PER = A.perSource || 10

// ---- schemas ----
const RANK_SCHEMA = {
  type: 'object',
  properties: {
    highlights: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          start_time: { type: 'number' },
          end_time: { type: 'number' },
          score: { type: 'number' },
          hook_sentence: { type: 'string' },
          virality_reason: { type: 'string' },
          key_quote: { type: 'string' },
          topic: { type: 'string' },
          single_speaker: { type: 'boolean' },
          screenshare_risk: { type: 'string', enum: ['low', 'med', 'high'] },
        },
        required: ['title', 'start_time', 'end_time', 'score', 'hook_sentence', 'virality_reason', 'screenshare_risk'],
      },
    },
  },
  required: ['highlights'],
}

const PRODUCE_SCHEMA = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    captioned_path: { type: 'string' },
    verify_json_path: { type: 'string' },
    error: { type: 'string' },
  },
  required: ['ok'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['PASS', 'REJECT'] },
    reason: { type: 'string' },
    frames_checked: { type: 'number' },
    worst_issue: { type: 'string' },
  },
  required: ['status', 'reason'],
}

// ---- prompts ----
function rankPrompt(s) {
  return `You are ranking the most VIRAL standalone clip moments from a podcast, for 9:16 vertical clips on the @aksenHQ X account.
@aksenHQ niche: AI building, indie hacking, solopreneur, building in public, startup ideas, X growth. Pick moments that land with THAT audience.

Source: ${s.label}
Channel: ${s.channel} | Speakers: ${s.speakers}
${s.desc}

Read this tab-separated transcript file (each line is "start_seconds<TAB>end_seconds<TAB>text"):
${s.rankfile}

Pick the ${PER} strongest clip-worthy moments. For each, set start_time and end_time (absolute seconds, snapped to segment boundaries from the file) so the clip:
- Opens with a strong HOOK in the first ~3s (bold claim, number, contrarian take, curiosity gap).
- Is a COMPLETE thought - never start or end mid-sentence.
- Is 45-90s ideal. Allowed 30-105s. HARD CAP 110s. Never below 25s.
- Lands on a viral signal: opinion bomb, counter-intuitive reframe, surprising stat/confession, story payoff, or a quotable one-liner.

CRITICAL framing heuristic (these become FACE-TRACKED vertical crops): PREFER moments where a single person delivers a take/opinion/story to camera. DEPRIORITIZE (lower score, mark screenshare_risk high) any moment whose text references on-screen visuals - phrases like "look at this", "as you can see", "this chart/deck/screen", "let me pull up", "on the screen", "if you scroll" - those are screenshare segments that crop badly.

Score 0-100 on VIRAL potential for @aksenHQ's audience (not general quality). Return the ${PER} best, highest score first.`
}

function produceCmd(c) {
  return [
    `export FFMPEG_BIN=${A.ffmpeg}`,
    `${A.venv} ${A.scripts}/05_clip.py "${c.mp4}" --start ${c.start_time} --end ${c.end_time} --out ${A.run}/clips/${c.cid}.mp4 --aspect 9:16 --blackout-bottom 0.12 --smoothing 0.06 --deadband 24 --scene-threshold 27 --stationary-mode auto`,
    `${A.venv} ${A.scripts}/06_caption.py ${A.run}/clips/${c.cid}.mp4 --transcript "${c.transcript}" --clip-start ${c.start_time} --clip-end ${c.end_time} --out ${A.run}/final/${c.cid}.mp4`,
    `${A.venv} ${A.scripts}/08_verify.py ${A.run}/final/${c.cid}.mp4 --scenes-from ${A.run}/clips/${c.cid}.scenes.json --srt ${A.run}/final/${c.cid}.derived.srt`,
  ].join(' && \\\n')
}

function producePrompt(c) {
  return `You are ONE deterministic stage of an automated clip pipeline. Run EXACTLY this single bash command and nothing else. Set the Bash tool timeout to 600000 (ms) because face-tracking is CPU-heavy. The command cuts a 9:16 face-tracked clip, burns captions, then runs a jitter scan.

COMMAND:
${produceCmd(c)}

Then confirm the file ${A.run}/final/${c.cid}.verify.json exists (ls it). Return:
- ok: true ONLY if the command exited 0 AND ${A.run}/final/${c.cid}.verify.json exists
- captioned_path: "${A.run}/final/${c.cid}.mp4"
- verify_json_path: "${A.run}/final/${c.cid}.verify.json"
- error: if it failed, the last ~12 lines of stderr; otherwise ""
Do NOT attempt fixes, retries, or alternate commands. Run once, check, report.`
}

function verifyPrompt(prod, c) {
  const vrp = prod.captioned_path.replace(/\.mp4$/, '.verify_result.json')
  return `You are the VISION QUALITY GATE for a 9:16 vertical clip that will be posted PUBLICLY on X under the @aksenHQ brand. Be strict: a badly-framed clip damages the brand.

Clip: "${c.title}" (source: ${c.source}, cid: ${c.cid})

STEP 1: Read the JSON file ${prod.verify_json_path}. It has "review_frames": an array of {path, label, t_seconds, transcript_at_t}.
STEP 2: Use the Read tool to open EVERY image at each review_frames[].path. Look at them.
STEP 3: Judge each frame:
  - Is the speaker's face roughly centered horizontally, with head + shoulders visible (NOT cut off, NOT a tiny picture-in-picture)?
  - Are the burned-in captions readable, fully on-screen, not clipped at the edges, not garbled?
  - Any bad framing: a screenshare / slide / text filling the frame, a split-screen seam down the middle, two faces fighting for the crop, an intrusive logo or name-label?
STEP 4: Cross-frame: within one shot, is framing consistent? At scene cuts, is the change clean (different speaker/angle), not chaotic chasing?

PASS only if ALL frames are good (face centered + head/shoulders visible + captions clean + no screenshare/tiny-face/bad-split + stable). Otherwise REJECT.

STEP 5: WRITE your verdict as JSON to this exact path: ${vrp}
shape: {"status":"PASS" or "REJECT","verified_at":"2026-05-29T00:00:00Z","verifier":"claude-vision","clip":"${c.cid}.mp4","frames_checked":<int>,"per_frame":[{"label":"...","t":0.0,"centered":true,"head_visible":true,"captions_clean":true,"issues":[]}],"cross_frame_check":{"consistent_within_speaker_segments":true,"scene_cuts_handled_cleanly":true,"notes":"..."},"reason":"<short summary>"}

Return: {status, reason, frames_checked, worst_issue}`
}

// ---- helpers ----
function overlapFrac(a, b) {
  const s = Math.max(a.start_time, b.start_time)
  const e = Math.min(a.end_time, b.end_time)
  const inter = Math.max(0, e - s)
  const shorter = Math.min(a.end_time - a.start_time, b.end_time - b.start_time)
  return shorter > 0 ? inter / shorter : 0
}

function dedupe(cands) {
  const sorted = [...cands].sort((a, b) => b.score - a.score)
  const kept = []
  for (const c of sorted) {
    if (kept.some(k => k.source === c.source && overlapFrac(k, c) > 0.5)) continue
    kept.push(c)
  }
  return kept
}

// ============ PHASE 1: RANK ============
phase('Rank')
const ranked = await parallel(SRC.map(s => () =>
  agent(rankPrompt(s), { label: `rank:${s.id}`, phase: 'Rank', schema: RANK_SCHEMA })
))

let cands = []
ranked.forEach((r, i) => {
  if (!r || !r.highlights) return
  const s = SRC[i]
  r.highlights.forEach((h, j) => {
    const dur = h.end_time - h.start_time
    if (dur < 20 || dur > 130) return
    cands.push({
      ...h,
      source: s.id, mp4: s.mp4, transcript: s.transcript, label: s.label,
      cid: `${s.id}_${String(j + 1).padStart(2, '0')}`,
    })
  })
})
log(`rank: ${cands.length} raw candidates from ${SRC.length} sources`)

cands = dedupe(cands)
const bySrc = {}
for (const c of cands) (bySrc[c.source] ||= []).push(c)
const perProc = Math.ceil(PROCESS_CAP / Math.max(1, Object.keys(bySrc).length))
let toProcess = []
for (const k in bySrc) {
  bySrc[k].sort((a, b) => b.score - a.score)
  toProcess.push(...bySrc[k].slice(0, perProc))
}
toProcess.sort((a, b) => b.score - a.score)
log(`processing ${toProcess.length} candidates (cap ${PROCESS_CAP}, balanced across ${Object.keys(bySrc).length} sources)`)

// ============ PHASE 2+3: PRODUCE -> VERIFY (pipeline, no barrier) ============
const results = await pipeline(
  toProcess,
  (c) => agent(producePrompt(c), { label: `cut:${c.cid}`, phase: 'Produce', schema: PRODUCE_SCHEMA }),
  (prod, c) => {
    const base = {
      cid: c.cid, source: c.source, score: c.score, title: c.title,
      hook_sentence: c.hook_sentence, virality_reason: c.virality_reason,
      key_quote: c.key_quote || '', topic: c.topic || '',
      start_time: c.start_time, end_time: c.end_time,
    }
    if (!prod || !prod.ok) {
      return { ...base, status: 'PRODUCE_FAIL', reason: (prod && prod.error) || 'produce failed' }
    }
    return agent(verifyPrompt(prod, c), { label: `verify:${c.cid}`, phase: 'Verify', schema: VERDICT_SCHEMA })
      .then(v => ({
        ...base,
        captioned_path: prod.captioned_path,
        verify_json: prod.verify_json_path,
        status: (v && v.status) || 'REJECT',
        reason: (v && v.reason) || '',
        frames_checked: (v && v.frames_checked) || 0,
        worst_issue: (v && v.worst_issue) || '',
      }))
  }
)

const clean = results.filter(Boolean)
const passed = clean.filter(r => r.status === 'PASS').sort((a, b) => b.score - a.score)
log(`verify: ${passed.length} PASS / ${clean.length} processed`)

return {
  raw_candidates: cands.length,
  processed: toProcess.length,
  passed_count: passed.length,
  target: TARGET,
  passed,
  all: clean,
}
