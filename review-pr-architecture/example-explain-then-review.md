# Example: Explain-then-Review Format

This is a reference example of the ideal output format for `/review-pr-architecture` when
combined with `/explain-anything`. Explain the system and PR intent first, then deliver
architectural findings grounded in that context.

Source: PR #22 (EightfoldAI/wipdp) — "query pii simplification and conversations update for e2e"

---

## PR #22 — Explained + Architectural Review

**ENG-187993 · Author: Sunny Zhang · +386 / -207**

### What is this system? (Zero-context story)

This is a **conversational RAG** system — think "company chatbot that can answer questions about
internal documents." Here's the full flow when a user sends a message:

```
User: "What is Q3 revenue?"
         │
         ▼
[1] Rewrite query using conversation history
         │  (if this is a follow-up: "How does that compare to Q2?" → standalone query)
         ▼
[2] Input guardrails  ── check: is the query too long? is it a prompt injection?
         │
         ▼  ← NEW step added in this PR
[2b] PII redact the search query  (strip emails, SSNs, phone numbers before searching)
         │
         ▼
[3-5] Search documents → rerank → diversify results
         │
         ▼
[6] Confidence check  ── is the top result confident enough to answer?
         │
         ▼
[7-8] Build LLM prompt with history + docs → call LLM
         │
         ▼
[9] PII redact the LLM answer  (strip any PII that leaked into the response)
         │
         ▼
User gets answer + sources
```

Code entry: `service.py:133` — you can follow all 11 steps there.

---

### What problem does this PR solve?

#### Problem A — PII scanning at query time was too slow

**Before:** Two separate guardrails handled PII:
- `PIIInputGuardrail` — scanned user queries using **Presidio + spaCy** (an NLP library)
- `PIIOutputGuardrail` — redacted PII from LLM answers, also using **Presidio + spaCy**

The problem: spaCy loads a full language model on first use. At **index time** that's fine.
At **query time** (a real user waiting), that's a multi-second penalty on the first request.

**After:** Both replaced by a single `PIIGuardrail` backed by `PIIStripper` — pure regex.
No model loading. Sub-millisecond. The tradeoff: regex won't catch `"John Smith, 123 Main St"`.
But since documents are already Presidio-cleaned at index time, query-time scrubbing is a safety
net — regex precision is enough.

The single `PIIGuardrail` is called **twice** in service.py:
- Line 177: on the **search query** (step 2b — new)
- Line 225: on the **LLM answer** (step 9 — was already there)

---

#### Problem B — Listing conversations required N+1 API calls

**Before:** `GET /v1/conversations` returned only IDs:
```json
{"conversations": [{"conversation_id": "abc"}, {"conversation_id": "def"}]}
```
A frontend wanting titles + timestamps had to call `GET /v1/conversations/conversation?id=X`
once per conversation — the N+1 problem.

**After:** Same endpoint returns full context in one shot. Server internally loads each
conversation from S3 and sorts by `updated_at` descending.

---

#### Problem C — Messages were loosely typed dicts

**Before:** `LLMMessage` was a `TypedDict` — effectively a plain dict. Code did `msg["role"]`.

**After:** `LLMMessage` is a Pydantic `BaseModel`. Code does `msg.role` (typed as `MessageRole`
enum). When litellm needs plain dicts it serialises explicitly: `[m.model_dump() for m in messages]`.

---

### Architectural Review

#### 🟡 The output pipeline is doing input work — naming hides it

`service.py:175-177`:
```python
# 2b. PII redaction on search query (output pipeline handles both query and answer PII)
if not self._output_guardrails.is_empty:
    search_query, _ = self._output_guardrails.run(search_query)
```

The system has two named pipelines: `_input_guardrails` and `_output_guardrails`. Their names
tell you *when* they run. Step 2b runs `_output_guardrails` on the search query — a user input.
The naming contract is broken.

A clean fix: add `PIIGuardrail` to `build_input_pipeline()` as well, or rename the pipeline to
stop lying about its scope.

---

#### 🟡 `strict` preset quietly lost PII detection/logging on queries

Before: `strict` had `detect_pii_in_query=True` which logged a `WARN` when PII appeared in a
user query. After: silent redaction, no log. The behavioral shift is **logged detection →
silent redaction**. If those logs fed a monitoring pipeline, that signal is now gone.
The PR description doesn't mention this change.

---

#### 🟡 LLM base class depends on conversation domain models — layer inversion

`libs/llm/base.py`:
```python
from operator_platform.libs.conversation.models import LLMMessage, MessageRole
```
`LLMMessage` is a general LLM primitive but lives in the conversation domain layer.
The dependency arrow points the wrong way. Fix: move to `libs/llm/models.py`.

---

#### 🟢 Server-side N+1 worth a TODO

```python
for cid in conversation_ids:
    ctx = self._store.load(enc_profile_id, cid)  # one S3 read per conversation
```
Right trade-off today. Worth a `# TODO: replace with bulk load if store supports it` comment.

---

#### 🟢 `pii_strip.py` lives in `output/` but is now used on both sides

The `output/` subdirectory implies output-only. Moving `pii_strip.py` to sit alongside
`pii.py` at `libs/guardrails/` would match location to actual scope.

---

### Summary table

| | Issue | File |
|---|---|---|
| 🟡 | Output pipeline called on user input — naming lies | service.py:177 |
| 🟡 | `strict` preset loses PII detection logging on queries | config.py:32 |
| 🟡 | `libs/llm/base.py` imports from `libs/conversation/` — layer inversion | base.py:5 |
| 🟢 | Server-side N+1 worth a TODO comment | service.py:276 |
| 🟢 | `pii_strip.py` location inconsistent with its scope | output/pii_strip.py |
