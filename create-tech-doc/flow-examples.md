# Flow Diagram Conventions & Examples

Use these patterns to make flows visible and scannable in tech doc sections.

---

## Linear Flow (sequence of steps)

```
Request → Auth Middleware → Rate Limiter → Handler → DB → Response
```

Or as numbered steps when each step needs explanation:

```
1. Client sends POST /apply with resume payload
2. API gateway validates JWT and routes to ApplyService
3. ApplyService deduplicates the candidate (email + group_id)
4. If new → creates CandidateProfile, emits profile.created event
5. If existing → merges fields, emits profile.updated event
6. Event consumed by RankingWorker → triggers async score computation
```

---

## Branching Flow (conditionals)

```
Incoming Request
      │
      ▼
  Cache hit? ──Yes──→ Return cached result (< 5ms)
      │
      No
      │
      ▼
  DB query
      │
      ▼
  Write to cache → Return result
```

---

## Before / After Comparison

Use when the solution changes an existing flow.

**Before:**
```
User submits form → sync validation → sync DB write → response (2–4s)
```

**After:**
```
User submits form → async queue → immediate 202 response (< 100ms)
                         │
                         ▼ (background)
                    Worker picks up → validates → DB write → webhook callback
```

---

## Component / System Boundary Diagram

```
┌─────────────────────────────────────────┐
│              Frontend (React)           │
│   ApplyWidget → Redux → API client      │
└──────────────────────┬──────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────┐
│           API Server (Flask)            │
│   /apply → ApplyView → ApplyService     │
└──────────┬──────────────────────────────┘
           │                   │
    ┌──────▼──────┐    ┌───────▼───────┐
    │  Postgres   │    │  SQS Queue    │
    │  (profiles) │    │  (async jobs) │
    └─────────────┘    └───────────────┘
```

---

## State Machine / Lifecycle

Use when an entity transitions through states.

```
[draft] → [submitted] → [under_review] → [approved]
                                │
                                └──→ [rejected]
```

---

## Tips

- Keep diagrams narrow — max ~60 chars wide
- Label every arrow with the action or data being passed
- Show the happy path first; add error/edge paths after
- When showing a change, always pair Before and After side by side
