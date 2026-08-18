# To-Do Page Design

## Purpose

`todo_list` already gets populated by the agent during chat (booking
attractions/ferries, pre-trip errands like exchanging currency, etc.), but
the only way to mark something done or add/remove an item is by asking
Claude to do it through chat. This adds a page to view and directly edit
the to-do list — mark items done, add new ones, delete ones — without going
through a conversation.

## Architecture

Same page-route-plus-JSON-route pattern as the preview page, plus mutation
routes hung off the data route:

- `GET /todos` — serves `static/todos.html`.
- `GET /todos/data` — returns the full `todo_list` from `trip_data.json`.
- `POST /todos/data` — body `{task, deadline?}`; calls
  `execute_tool("add_todo_item", {...})` (exact reuse of the existing
  chat-facing logic), returns the updated list.
- `POST /todos/data/{item_id}/complete` — calls
  `execute_tool("complete_todo_item", {"id": item_id})`, returns the
  updated list; 404 if the id doesn't exist.
- `DELETE /todos/data/{item_id}` — delete doesn't exist as a tool today.
  A small `delete_todo_item(item_id)` function is added to `agent.py`
  alongside the other trip-data mutation logic, but kept a plain function —
  **not** added to `CUSTOM_TOOLS` — so Claude's tool set in chat is
  unchanged; deletion is page-only. Returns the updated list; 404 if the id
  doesn't exist.
- `static/todos.html` + `static/todos.js` — new files, following the same
  fetch-then-render pattern `preview.js` already uses. Every mutation
  (add/complete/delete) gets the full updated list back in the response and
  just re-renders the table — no client-side state tracking to get out of
  sync.
- Delete triggers a native `confirm()` prompt before firing, since it's
  irreversible.

## Page content

- **Header nav, unified across all three pages:** Chat / Preview Trip Data
  / To-Do List links plus the existing "Export to Excel" link, so every
  page reaches every other page. `index.html` and `preview.html` both get
  the new "To-Do List" link added to their nav.
- **Add-todo form:** a text input for the task (required), an optional date
  input for the deadline, and an "Add" button, above the table.
- **Todo table:** columns Task, Deadline, Status/Actions. Incomplete items
  get a "Mark Done" button; completed items show strikethrough styling with
  no button. Every row also gets a "Delete" button regardless of completion
  state.
- **Empty state:** matches the preview page's pattern — if `todo_list` is
  empty, the table shows its headers plus a single "No to-dos yet." row.

## Styling

Reuses the existing `.data-table`, `.header-nav`, `.nav-link`, and
preview-page container classes (generalized where they're just "page with
a table" styling, so `todos.html` can share them instead of duplicating).
New additions: a small inline form style for the add-todo inputs (matching
the chat input's look), a `.done` class for strikethrough text, and small
button styles for "Mark Done" (subtle) and "Delete" (a muted red, since
it's destructive) — consistent sizing with existing buttons.

## Out of scope for this round

- The packing list — explicitly deferred to a separate follow-up.
- Editing a to-do's task text or deadline after creation (only add,
  complete, delete).
- Making delete (or any todo mutation) available to Claude in chat.
- Sorting/filtering the to-do list (shown in stored order).
