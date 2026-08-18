# Chat Frontend Design

## Purpose

The trip agent currently has a working FastAPI backend (`/chat`, `/export/excel`) but no
frontend — it can only be exercised via Swagger UI. This adds a simple, real chat
interface so the agent is actually usable day-to-day, and fixes the Markdown/line-break
formatting problem along the way: the agent's replies are real Markdown (headers, tables,
bold, emoji), which currently show up as raw text with literal `\n` and `##`/`|` characters
when read outside Swagger.

## Architecture

FastAPI serves the frontend directly — no separate server, no build step, no npm.

- New `static/` folder: `index.html`, `style.css`, `chat.js`.
- `main.py` mounts `static/` so `GET /` serves `index.html`.
- The page talks to the existing `/chat` and `/export/excel` endpoints, plus one new
  endpoint, all same-origin (no CORS setup needed).

### Backend changes

- `main.py`: mount `StaticFiles` at `/`.
- `main.py`: add `GET /history` returning conversation history as JSON:
  `[{"role": "user"|"assistant", "content": "..."}, ...]`, built from
  `agent.load_history()`. No new persistence logic — reuses what `agent.py` already writes.
- No changes to `agent.py`'s chat logic, tool loop, or system prompt.

## Chat flow

1. **On load:** `chat.js` calls `GET /history` and renders each past message as a bubble,
   so refreshing the browser doesn't lose context.
2. **Sending a message:**
   - User types in a bottom input bar; Enter or a Send button submits.
   - The user's message bubble is appended immediately.
   - Input is disabled and a small "typing…" indicator is shown.
   - `POST /chat` is called with `{"message": "..."}`.
   - On success, the indicator is replaced with the rendered reply and input is
     re-enabled.
   - On network/HTTP failure, an inline error bubble is shown ("Something went wrong,
     try again") and input is re-enabled — no retry logic, no queueing.
3. **Message alignment:** user bubbles align right, assistant bubbles align left —
   standard chat convention, independent of the text's own reading direction.

## Rendering

- **Markdown:** `marked.js`, loaded via CDN, converts each message's raw text to HTML.
  This is what fixes the line-break problem — Markdown paragraph/line-break handling is
  part of standard parsing, along with headers, tables, and bold rendering correctly for
  the first time.
- **Sanitization:** rendered HTML is inserted via `innerHTML`, so `DOMPurify` (CDN) runs
  over the Markdown output first as a safety measure, since Markdown-to-HTML output
  should never be trusted blindly even from a first-party backend.
- **RTL support:** since trip conversations are largely in Hebrew, each rendered bubble's
  `dir` attribute is set per-message by detecting the first strong-directional character
  (Hebrew/Arabic Unicode ranges vs. Latin) — so a Hebrew reply reads right-to-left and an
  English one reads left-to-right, regardless of which side (user/assistant) the bubble
  is aligned to.
- **Tables:** Markdown tables (used heavily for itineraries) get simple CSS borders and
  padding so multi-day plans stay readable.

## Export button

A header bar includes a plain `<a href="/export/excel">` link/button. The browser handles
the download via the existing `Content-Disposition` header on that endpoint — no
JavaScript needed.

## Styling

Minimal, not fancy — this is a v1:

- Centered column, max-width ~700px, light background.
- Header bar: title + export button.
- Scrollable message list; fixed input bar at the bottom.
- User bubbles: accent color. Assistant bubbles: neutral gray. Both rounded.
- No dark mode, no animations beyond a basic typing-indicator pulse.

## Out of scope for this round

- Streaming responses (backend `/chat` stays request/response; a loading indicator
  covers the wait).
- Auth / multi-user support.
- Editing or deleting past messages.
- Mobile-specific layout tuning beyond basic responsiveness.
