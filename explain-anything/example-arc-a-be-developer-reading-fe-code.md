# Example: Arc A — FE Bug Explained to a BE Developer

**When to use this example:** User identifies as a backend developer (or "mostly BE") asking to understand a frontend bug fix or code change.

**Key technique:** Map every frontend concept to a backend analogy before using it. Never assume React/browser knowledge.

---

## Audience adaptation table

| Frontend term | Backend analogy |
|---|---|
| `useState` | A mutable field whose setter triggers a re-render — like invalidating a cache entry |
| `useRef` | A plain instance variable — changing it does NOT trigger a re-render |
| `useEffect` + dependency array | A lifecycle hook with a cache key; re-runs when any dependency changes |
| `IntersectionObserver` | A database trigger / event listener — fires a callback when a DOM element enters or exits the viewport |
| `entries` in observer callback | A CDC (change-data-capture) stream — only delivers elements whose state *changed* |

---

## Example — CardCarousel.js (IMPL-200965 / ENG-187133)

**User prompt:** "I'm mostly a BE developer, can you explain the code changes you made?"

**Source:** `www/react/src/apps/careerHubHome/components/V2/CardCarousel.js`, branch `akshat/IMPL-200965`

---

### 1. What is this system?
A horizontally scrollable card carousel on the TM Career Interest tab. Its only non-rendering job: track which cards are on-screen so keyboard focus jumps to the newly visible card after each arrow click.

### 2. Happy path (call trace)
```
User clicks ">" button
    → pendingClick.current = "next"          (records the direction)
    → Octuple Carousel scrolls
    → onUpdate() fires
    → observer.observe(el) for all items     (registers elements with the observer)
    → IntersectionObserver fires
    → figures out which cards are visible
    → sets aria-hidden + tabIndex per card   (accessibility attributes)
    → handleAfterScrollButtonClick() focuses the newly visible card
    → pendingClick.current = null            (job done, clear the queue)
```

### 3. What broke
After several arrow clicks the carousel froze. Browser console showed `visibleItems Set(0)` — the visible-items tracker had emptied.

### 4. Root causes (4 bugs)

**Bug 1 — Observer torn down on every scroll**
`visibleItems` was `useState` sitting in the `useEffect` dependency array. Every observer callback called `setVisibleItems()` → re-render → dependency changed → old observer `disconnect()`ed → new observer created. Like dropping and recreating a DB listener after every event it fires.

**Bug 2 — CDC stream treated as a full snapshot**
```js
const newVisibleItems = new Set();  // blank slate every time
entries.forEach((entry) => {
    if (fullyVisible) newVisibleItems.add(entry.target);
});
```
`IntersectionObserver` only delivers *changed* elements. Starting blank drops every card not in the current batch. After a few clicks: `Set(0)`.

**Bug 3 — Re-observing already-watched elements**
`onUpdate` called `observer.observe(el)` on all items every click. Calling `observe()` on an already-observed element immediately re-fires the callback with the mid-animation intersection state — producing a gray visual flash on the visible card.

**Bug 4 — `pendingClick` consumed on the wrong batch**
`pendingClick.current = null` ran unconditionally after every callback. If the observer fired for the old card *leaving* before the new card *arrived* (two separate batches), the direction was consumed on the useless first batch — keyboard focus silently failed to move.

### 5. The fixes

| Change | Location | Why |
|---|---|---|
| `useState` → `useRef` for `visibleItems` | `CardCarousel.js:34–38` | Ref changes don't re-run effects — observer lives for component lifetime |
| Copy existing set, add/delete incrementally | `CardCarousel.js:144–162` | Preserves cards absent from the current `entries` batch |
| `observedElementsRef` registry in `onUpdate` | `CardCarousel.js:48–50, 191–194` | Skip `observe()` on already-watched elements — no spurious mid-animation re-fires |
| `pendingClick = null` only when consumed | `CardCarousel.js:164–166` | Direction persists until there's a newly visible card to focus |
