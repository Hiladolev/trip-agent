# Chat Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the trip agent a real, usable chat page — served directly by FastAPI, rendering the agent's Markdown replies correctly (fixing the current raw-`\n`/`##` display problem), with RTL support for the mostly-Hebrew conversations.

**Architecture:** A `static/` folder (`index.html`, `style.css`, `chat.js`) is mounted by FastAPI at `/`. A new `GET /history` endpoint exposes the existing conversation log. No build tooling, no npm — `marked.js` and `DOMPurify` are pulled from CDN in `index.html`.

**Tech Stack:** FastAPI (`StaticFiles`), vanilla JS, `marked.js` (CDN) for Markdown parsing, `DOMPurify` (CDN) for sanitizing rendered HTML before `innerHTML` insertion.

**Testing note:** The backend change (`/history`, static mount) gets pytest tests per the project's existing `TestClient`-based pattern. `style.css` and `chat.js` are plain static assets with no build/test tooling (per the design's "no npm" decision) — those are verified manually in Task 5 by running the server and using the page in a browser, per the project's frontend verification requirement.

Spec: `docs/superpowers/specs/2026-08-18-chat-frontend-design.md`

---

### Task 1: Add `GET /history` endpoint

**Files:**
- Modify: `main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_main.py`:

```python
"""Tests for the FastAPI endpoints in main.py. /chat and /export/excel are
exercised manually (they call the live Anthropic API / build binary Excel
output) - this file covers /history and the static frontend mount.
"""

import json

import pytest
from fastapi.testclient import TestClient

import agent
import main

client = TestClient(main.app)


@pytest.fixture
def history_file(tmp_path, monkeypatch):
    path = tmp_path / "conversation_history.json"
    monkeypatch.setattr(agent, "HISTORY_PATH", path)
    return path


def test_history_returns_empty_list_when_no_file(history_file):
    response = client.get("/history")

    assert response.status_code == 200
    assert response.json() == []


def test_history_returns_saved_messages(history_file):
    saved = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    history_file.write_text(json.dumps(saved), encoding="utf-8")

    response = client.get("/history")

    assert response.status_code == 200
    assert response.json() == saved
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/Scripts/activate && python -m pytest tests/test_main.py -v`
Expected: FAIL — `AttributeError` or `404` on `/history` (route doesn't exist yet), and possibly an import error if `static/` doesn't exist yet (it doesn't — that's fine, this task doesn't mount it).

- [ ] **Step 3: Add the endpoint**

In `main.py`, change the import line and add the route. Full updated file:

```python
"""FastAPI app exposing the trip-planning chat agent.

Minimal slice - no auth yet. Serves the chat frontend from static/ and
exposes /chat, /history, and /export/excel.
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import get_reply, load_history, load_trip_data
from export import build_excel

app = FastAPI(title="Trip Agent")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = get_reply(request.message)
    return ChatResponse(reply=reply)


@app.get("/history")
def history() -> list[dict]:
    return load_history()


@app.get("/export/excel")
def export_excel() -> StreamingResponse:
    trip_data = load_trip_data()
    excel_file = build_excel(trip_data)
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=trip_export.xlsx"},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `source venv/Scripts/activate && python -m pytest tests/test_main.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "Add GET /history endpoint"
```

---

### Task 2: Serve the frontend (static mount + index.html)

**Files:**
- Create: `static/index.html`
- Modify: `main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Create the page structure**

Create `static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trip Agent</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header class="app-header">
    <h1>Trip Agent</h1>
    <a id="export-link" href="/export/excel">Export to Excel</a>
  </header>

  <main id="messages" class="messages"></main>

  <form id="chat-form" class="chat-form">
    <input id="chat-input" type="text" autocomplete="off" placeholder="Type a message..." required>
    <button type="submit">Send</button>
  </form>

  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js"></script>
  <script src="/chat.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create placeholder assets so the mount has something to serve**

Create `static/style.css` (empty for now, filled in Task 3):

```css
/* filled in Task 3 */
```

Create `static/chat.js` (empty for now, filled in Task 4):

```js
// filled in Task 4
```

- [ ] **Step 3: Write the failing test**

Add to `tests/test_main.py` (below the existing tests):

```python
def test_root_serves_index_html():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Trip Agent" in response.text
```

- [ ] **Step 4: Run test to verify it fails**

Run: `source venv/Scripts/activate && python -m pytest tests/test_main.py::test_root_serves_index_html -v`
Expected: FAIL with 404 (nothing mounted at `/` yet)

- [ ] **Step 5: Mount the static directory**

In `main.py`, add the import and the mount call. The mount **must** be added after every `@app.get`/`@app.post` route so those specific routes take priority over the catch-all static mount:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import get_reply, load_history, load_trip_data
from export import build_excel

app = FastAPI(title="Trip Agent")

STATIC_DIR = Path(__file__).parent / "static"
```

(keep `ChatRequest`, `ChatResponse`, `chat`, `history`, `export_excel` exactly as in Task 1), then at the very end of the file:

```python
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `source venv/Scripts/activate && python -m pytest tests/test_main.py -v`
Expected: PASS (4 passed)

- [ ] **Step 7: Commit**

```bash
git add main.py static/index.html static/style.css static/chat.js tests/test_main.py
git commit -m "Serve chat frontend as static files from FastAPI"
```

---

### Task 3: Style the chat UI

**Files:**
- Modify: `static/style.css`

No automated test for this task — pure CSS, verified visually in Task 5.

- [ ] **Step 1: Write the stylesheet**

Replace the contents of `static/style.css`:

```css
:root {
  --accent: #2563eb;
  --accent-text: #ffffff;
  --assistant-bg: #f1f3f5;
  --assistant-text: #1a1a1a;
  --error-bg: #fee2e2;
  --error-text: #991b1b;
  --border: #e2e8f0;
}

* {
  box-sizing: border-box;
}

html, body {
  height: 100%;
  margin: 0;
}

body {
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100vh;
}

.app-header,
.messages,
.chat-form {
  width: 100%;
  max-width: 700px;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border);
}

.app-header h1 {
  font-size: 1.25rem;
  margin: 0;
}

#export-link {
  font-size: 0.875rem;
  color: var(--accent);
  text-decoration: none;
  border: 1px solid var(--accent);
  border-radius: 6px;
  padding: 0.4rem 0.75rem;
}

#export-link:hover {
  background: var(--accent);
  color: var(--accent-text);
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.message {
  max-width: 80%;
  padding: 0.6rem 0.9rem;
  border-radius: 12px;
  line-height: 1.4;
  word-wrap: break-word;
}

.message-user {
  align-self: flex-end;
  background: var(--accent);
  color: var(--accent-text);
}

.message-assistant {
  align-self: flex-start;
  background: var(--assistant-bg);
  color: var(--assistant-text);
}

.message-error {
  align-self: flex-start;
  background: var(--error-bg);
  color: var(--error-text);
}

.typing-indicator {
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.message p {
  margin: 0.4rem 0;
}

.message table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5rem 0;
}

.message th,
.message td {
  border: 1px solid var(--border);
  padding: 0.4rem 0.6rem;
  text-align: start;
}

.chat-form {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid var(--border);
}

#chat-input {
  flex: 1;
  padding: 0.6rem 0.8rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 1rem;
}

.chat-form button {
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: 8px;
  background: var(--accent);
  color: var(--accent-text);
  font-size: 1rem;
  cursor: pointer;
}

.chat-form button:hover {
  opacity: 0.9;
}
```

- [ ] **Step 2: Run the backend test suite to confirm nothing broke**

Run: `source venv/Scripts/activate && python -m pytest tests/ -v`
Expected: PASS (all tests, CSS changes don't affect Python tests)

- [ ] **Step 3: Commit**

```bash
git add static/style.css
git commit -m "Style the chat UI"
```

---

### Task 4: Chat logic (history load, send message, Markdown render, RTL)

**Files:**
- Modify: `static/chat.js`

No automated test for this task — plain JS with no test runner configured (per design, no npm/build tooling). Verified manually in Task 5.

- [ ] **Step 1: Write the chat logic**

Replace the contents of `static/chat.js`:

```js
const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");

// Hebrew + Arabic Unicode ranges, used to pick each bubble's text direction.
const RTL_CHAR_RE = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]/;
const LTR_CHAR_RE = /[a-zA-Z]/;

function detectDirection(text) {
  for (const char of text) {
    if (LTR_CHAR_RE.test(char)) return "ltr";
    if (RTL_CHAR_RE.test(char)) return "rtl";
  }
  return "ltr";
}

function renderMarkdown(text) {
  const html = marked.parse(text);
  return DOMPurify.sanitize(html);
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `message message-${role}`;
  bubble.dir = detectDirection(content);
  bubble.innerHTML = renderMarkdown(content);
  messagesEl.appendChild(bubble);
  scrollToBottom();
  return bubble;
}

function appendTypingIndicator() {
  const bubble = document.createElement("div");
  bubble.className = "message message-assistant typing-indicator";
  bubble.textContent = "...";
  messagesEl.appendChild(bubble);
  scrollToBottom();
  return bubble;
}

function appendError(text) {
  const bubble = document.createElement("div");
  bubble.className = "message message-error";
  bubble.textContent = text;
  messagesEl.appendChild(bubble);
  scrollToBottom();
}

async function loadHistory() {
  const response = await fetch("/history");
  const history = await response.json();
  for (const message of history) {
    appendMessage(message.role, message.content);
  }
}

async function sendMessage(text) {
  appendMessage("user", text);
  inputEl.disabled = true;
  const indicator = appendTypingIndicator();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    indicator.remove();
    appendMessage("assistant", data.reply);
  } catch (err) {
    indicator.remove();
    appendError("Something went wrong, try again.");
  } finally {
    inputEl.disabled = false;
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  sendMessage(text);
});

loadHistory();
```

- [ ] **Step 2: Run the backend test suite to confirm nothing broke**

Run: `source venv/Scripts/activate && python -m pytest tests/ -v`
Expected: PASS (all tests)

- [ ] **Step 3: Commit**

```bash
git add static/chat.js
git commit -m "Add chat frontend logic: history load, send, Markdown render, RTL"
```

---

### Task 5: End-to-end manual verification

**Files:** none (verification only)

- [ ] **Step 1: Start the server**

Run: `source venv/Scripts/activate && uvicorn main:app --reload`
Expected: server starts on `http://127.0.0.1:8000` with no errors.

- [ ] **Step 2: Open the page and confirm history loads**

Open `http://127.0.0.1:8000/` in a browser. Confirm:
- The page loads with the "Trip Agent" header and an "Export to Excel" button.
- Past messages from `conversation_history.json` appear as bubbles (user right-aligned, assistant left-aligned).
- Hebrew messages read right-to-left; any English/number content within them still reads left-to-right.
- A message containing a Markdown table (e.g. an itinerary reply) renders as an actual bordered table, not raw `|` characters.

- [ ] **Step 3: Send a new message**

Type a message and send it. Confirm:
- The user bubble appears immediately.
- A typing indicator appears while waiting.
- The reply renders with working Markdown (headers, bold, tables) and correct text direction, replacing the typing indicator.
- The input re-enables and refocuses after the reply arrives.

- [ ] **Step 4: Confirm error handling**

Stop the server (Ctrl+C) mid-session, then try sending another message from the still-open page. Confirm an inline error bubble appears ("Something went wrong, try again.") instead of the page hanging or throwing an unhandled error in the console. Restart the server afterward.

- [ ] **Step 5: Confirm the export button works**

With the server running again, click "Export to Excel". Confirm the browser downloads `trip_export.xlsx`.

- [ ] **Step 6: Confirm existing API surface still works**

Open `http://127.0.0.1:8000/docs`. Confirm Swagger UI still loads and lists `/chat`, `/history`, and `/export/excel` (the static mount must not shadow these).

No commit for this task — it's verification only. If any step fails, fix the relevant file from Tasks 1-4 and re-run the failed step.
