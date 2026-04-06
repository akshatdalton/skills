# Example: Story + Code Snippet Format

This is the reference example for the ideal `/review-pr-architecture` output format.
It combines a zero-context system explanation, a call-path diagram, story chapters with
inline code snippets and clickable file links, and a compact before-merge table.

Source: PR #103589 (EightfoldAI/vscode) — "[Tether] Integrate tether to manager agent"

---

## PR #103589 — [Tether] Integrate tether to manager agent

### What this system does

The manager agent panel is an AI chat panel inside CareerHub's Team Planning view. A manager
opens it from an employee's profile to ask questions like "What are this person's key skills?"
— and gets a streamed AI response. Before this PR, there was one backend: Digital Twin,
Eightfold's hosted AI service. This PR adds a second — **Tether** — a RAG service deployed
inside the customer's own VPC, and lets each org choose which one via config.

```
bootData.managerAgent.agentType  ←  career_hub_base_config  [NEW]
         │
         ▼
ManagerAgentContext  →  useSendMessage
         │
POST /api/.../agents/chat/{agentType}/ask/stream
         │
         ├── 'dt_manager'    →  DTManagerAgent  →  Digital Twin API
         └── 'tether_agent'  →  TetherAgent     →  Customer VPC     [NEW]
```

---

### 1. Config: picking the backend per org

A new `manager_agent` block in `career_hub_base_config` is the operator's switch. It flows
through [career_hub_config.py:906](www/career_hub/career_hub_config.py#L906) →
[career_hub_view.py:484](www/apps/career_hub_app/career_hub_view.py#L484) → bootdata →
[BootDataContext.tsx:42](www/react/src/apps/careerHub/contexts/BootDataContext.tsx#L42),
and lands here:

```ts
// ManagerAgentContext.tsx:121
const agentType = bootData?.managerAgent?.agentType || 'dt_manager';
```

Existing orgs fall back to `'dt_manager'` — no config change needed for them.

> `agentType` is set once in `initialState` and never re-synced, unlike `profile` and
> `profileLoading` which have a `useEffect`. Fine in practice since bootdata is stable
> after load, but worth a comment for consistency.

---

### 2. Factory: routing to the right class

The agent type from the URL lands in [agent_factory.py:13-17](www/career_hub/agents/chat/agent_factory.py#L13-L17):

```python
CHAT_AGENT_REGISTRY = {
    'manager':      ManagerAgent,
    'dt_manager':   DTManagerAgent,    # refactored from ManagerAgent
    'tether_agent': TetherAgent,       # NEW
}
```

The URL on the frontend ([constants.ts:261](www/react/src/libs/careerhub/constants.ts#L261))
embeds the type directly: `.../agents/chat/{agentType}/ask/stream` — so agent type travels
config → bootdata → context → URL → registry with no other routing logic.

---

### 3. TetherService: auth + HTTP to the data plane

[tether_service.py](www/career_hub/agents/chat/tether_service.py) is the HTTP client. Two
things to note.

**Finding the endpoint** — the base URL is read as
[tether_service.py:108](www/career_hub/agents/chat/tether_service.py#L108)
`tether_config.get('subdomain')` but used as a full URL (`f"{base_url}/v1/conversations/..."`).
The name `subdomain` implies just a hostname prefix — if an operator sets it without `https://`,
it silently breaks. Worth renaming to `base_url` in the config schema.

**Auth** — every HTTP call mints a fresh RS256 JWT:

```python
# tether_service.py:151
def _auth_headers(self) -> dict:
    token = _create_signed_token(
        sub=self.current_user.get_profile().get_enc_id(),
        aud=self.current_user.group_id,
        private_key_b64=TETHER_RS256_PRIVATE_KEY_B64,
    )
    return {"Authorization": f"Bearer {token}"}
```

Tokens are valid 10 hours — minting one per call is unnecessary. A time-based cache would
eliminate the repeated crypto work.

**The private key** comes from [tether_constants.py:14](www/career_hub/agents/chat/tether_constants.py#L14):

```python
TETHER_RS256_PRIVATE_KEY_B64 = "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0t..."
# Comment says: "local dev/testing, remove once #103677 merges"
```

**This must be fixed before merge.** A key committed to git lives in history forever — even
after deletion. Rotate the key pair now, and have the replacement read from env or a secrets
store at startup, never from source.

---

### 4. TetherAgent: implementing the interface

[tether_agent.py](www/career_hub/agents/chat/tether_agent.py) wraps `TetherService` and
satisfies the same `BaseChatAgent` interface as `DTManagerAgent`. `ask()` and
`get_conversation_history()` ([tether_agent.py:38](www/career_hub/agents/chat/tether_agent.py#L38),
[tether_agent.py:66](www/career_hub/agents/chat/tether_agent.py#L66)) are clean. The concern
is `ask_stream()`:

```python
# tether_agent.py:50
def ask_stream(self, request):
    """Synthetic streaming: emit Thinking status, then full response.
    TODO: Replace with real SSE consumption from data plane.
    """
    yield self.format_sse(StreamEvent(event_type=STATUS, status_text="Thinking..."))
    response = self.ask(request)    # ← blocking — Flask worker held the entire time
    yield self.format_sse(StreamEvent(event_type=CONTENT_COMPLETE, content=response.message))
```

This is fake streaming — the worker blocks for the full round-trip, then the whole message
drops at once. The DT agent streams token by token. The TODO is acknowledged; it should be a
tracked ticket, not just a comment — code TODOs tend to stay.

Also: [tether_agent.py:99](www/career_hub/agents/chat/tether_agent.py#L99) hardcodes
`has_more=False`. The DT agent reads it from the response. If the Tether API genuinely doesn't
paginate, a short comment there would make it intentional rather than overlooked.

---

### 5. DTManagerAgent: the refactor

The existing DT logic was cleanly extracted into
[dt_manager_agent.py](www/career_hub/agents/chat/dt_manager_agent.py) — real SSE streaming,
proper event transformation, no concerns with the new code itself.

One thing to remove: [dt_manager_agent.py:300–415](www/career_hub/agents/chat/dt_manager_agent.py#L300-L415)
is a 115-line `if __name__ == '__main__':` debug block sitting at the bottom of a production
class file, with hardcoded `imalhotra@eightfold.ai` and `volkscience.com`. Dev scaffolding
that wasn't cleaned up — delete it.

---

### 6. Frontend: useStream + useSendMessage

[useStream.ts](www/react/src/libs/common/hooks/useStream.ts) is a new reusable hook — SSE
over POST using `fetch` (since `EventSource` only supports GET). It parses the standardized
event protocol and surfaces `onContent`, `onStatus`, `onComplete`, `onError` callbacks so the
frontend stays backend-agnostic. Clean abstraction.

One subtle behaviour at [useStream.ts:285](www/react/src/libs/common/hooks/useStream.ts#L285)
— when the user cancels, `AbortError` is caught and `onComplete` fires with whatever partial
content accumulated. In [useSendMessage.ts:117](www/react/src/apps/careerHub/teamPlanning/components/ManagerWorkflows/ManagerAgentPanel/hooks/useSendMessage.ts#L117),
`onComplete` marks the message `loadingState: 'success'` — so a cancelled message looks
identical to a completed one. Worth deciding if that's the intended UX.

---

### Before merge

| | File | Issue |
|--|------|-------|
| 🔴 | [tether_constants.py:14](www/career_hub/agents/chat/tether_constants.py#L14) | Private key in source — rotate + read from env |
| 🔴 | [dt_manager_agent.py:300–415](www/career_hub/agents/chat/dt_manager_agent.py#L300-L415) | Delete `__main__` debug block with hardcoded emails |
| 🟡 | [tether_service.py:108](www/career_hub/agents/chat/tether_service.py#L108) | Rename `subdomain` → `base_url` in config schema |
| 🟡 | [tether_agent.py:50–64](www/career_hub/agents/chat/tether_agent.py#L50-L64) | Fake streaming — file a follow-up ticket |
| 🟡 | [tether_agent.py:99](www/career_hub/agents/chat/tether_agent.py#L99) | `has_more=False` — add comment if intentional |
| 🟢 | [useStream.ts:285](www/react/src/libs/common/hooks/useStream.ts#L285) | Cancel fires `onComplete` — clarify intended UX |
