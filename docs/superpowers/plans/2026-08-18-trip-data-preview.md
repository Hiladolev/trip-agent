# Trip Data Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only `/preview` page showing recommendations and the trip skeleton as HTML tables, sourced from the same data and logic as the existing `/export/excel` endpoint, with navigation between it and the chat page.

**Architecture:** `export.py`'s inline hotel/flight merge-and-sort is extracted into `build_skeleton_rows()`, shared by `build_excel` and a new `GET /preview/data` JSON endpoint. `GET /preview` serves a new `static/preview.html` (registered before the static mount, like the other routes). `static/preview.js` fetches `/preview/data` and renders two tables. Both pages get a small header nav linking to each other, alongside the existing export link.

**Tech Stack:** FastAPI (`FileResponse`), vanilla JS (same pattern as `chat.js`), `openpyxl` (only touched via the existing `build_excel`, for the regression test).

**Testing note:** Backend changes (`build_skeleton_rows`, `/preview/data`, `/preview`) get pytest tests per the existing pattern. `preview.js` and the CSS additions are plain static assets with no test runner (matching the chat frontend's "no npm" decision) — verified manually in the final task.

Spec: `docs/superpowers/specs/2026-08-18-trip-data-preview-design.md`

---

### Task 1: Extract `build_skeleton_rows()` in `export.py`

**Files:**
- Modify: `export.py`
- Create: `tests/test_export.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_export.py`:

```python
"""Tests for export.py: build_skeleton_rows (the chronological hotel/flight
merge shared with the /preview/data endpoint) and its use inside build_excel.
"""

from openpyxl import load_workbook

import export

TRIP_DATA_WITH_SKELETON = {
    "recommendations": [],
    "hotels": [
        {
            "name": "Gracery Shinjuku",
            "city": "Tokyo",
            "check_in": "2026-09-04",
            "check_out": "2026-09-11",
        },
    ],
    "flights": [
        {
            "from": "TLV",
            "to": "NRT",
            "description": "Outbound",
            "departure": "2026-09-03 23:00",
            "arrival": "2026-09-04 18:00",
        },
    ],
}


def test_build_skeleton_rows_sorts_flights_and_hotels_chronologically():
    rows = export.build_skeleton_rows(TRIP_DATA_WITH_SKELETON)

    assert [row["type"] for row in rows] == ["Flight", "Hotel"]
    assert rows[0]["date"] == "2026-09-03"
    assert rows[0]["location_route"] == "TLV -> NRT"
    assert rows[1]["date"] == "2026-09-04"
    assert rows[1]["location_route"] == "Tokyo"


def test_build_excel_skeleton_sheet_matches_build_skeleton_rows():
    rows = export.build_skeleton_rows(TRIP_DATA_WITH_SKELETON)

    workbook = load_workbook(export.build_excel(TRIP_DATA_WITH_SKELETON))
    sheet = workbook["Trip Skeleton"]

    assert [cell.value for cell in sheet[1]] == ["Date", "Type", "Location/Route", "Details"]
    for row_cells, expected in zip(sheet.iter_rows(min_row=2), rows):
        assert [cell.value for cell in row_cells] == [
            expected["date"], expected["type"], expected["location_route"], expected["details"]
        ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./venv/Scripts/python.exe -m pytest tests/test_export.py -v`
Expected: FAIL — `AttributeError: module 'export' has no attribute 'build_skeleton_rows'`

- [ ] **Step 3: Extract the function and refactor `build_excel` to use it**

Replace the contents of `export.py`:

```python
"""Excel export: recommendations plus a chronological trip skeleton (hotels
and flights merged into one sorted list) for offline/printable reference.
"""

from io import BytesIO

from openpyxl import Workbook


def _date_only(date_str: str) -> str:
    """Extract the date portion from a 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM' string."""
    return date_str.split(" ")[0]


# Hotels only store a check-in date, no time. Assume a typical afternoon
# check-in for sort-ordering purposes only (never displayed or stored) - this
# breaks same-day ties against flight arrivals so the skeleton reads in the
# order things actually happen (e.g. arrive Koh Samui by flight, then check
# into the hotel), instead of an arbitrary insertion-order tiebreak.
ASSUMED_HOTEL_CHECKIN_TIME = "15:00"


def build_skeleton_rows(trip_data: dict) -> list[dict]:
    """Chronologically merged hotel/flight rows, shared by build_excel and
    the /preview/data endpoint."""
    rows = []
    for hotel in trip_data.get("hotels", []):
        sort_key = f"{hotel['check_in']} {ASSUMED_HOTEL_CHECKIN_TIME}"
        rows.append((sort_key, {
            "date": _date_only(hotel["check_in"]),
            "type": "Hotel",
            "location_route": hotel["city"],
            "details": f"{hotel['name']}: check-in {hotel['check_in']} -> check-out {hotel['check_out']}",
        }))
    for flight in trip_data.get("flights", []):
        sort_key = flight["departure"]  # already "YYYY-MM-DD HH:MM"
        rows.append((sort_key, {
            "date": _date_only(flight["departure"]),
            "type": "Flight",
            "location_route": f"{flight['from']} -> {flight['to']}",
            "details": f"{flight['description']}: depart {flight['departure']} -> arrive {flight['arrival']}",
        }))
    rows.sort(key=lambda item: item[0])
    return [row for _, row in rows]


def build_excel(trip_data: dict) -> BytesIO:
    wb = Workbook()

    recommendations_sheet = wb.active
    recommendations_sheet.title = "Recommendations"
    recommendations_sheet.append(
        ["City", "Place Name", "Priority", "Description", "Maps Link", "Source"]
    )
    for rec in trip_data.get("recommendations", []):
        recommendations_sheet.append([
            rec.get("city"),
            rec.get("place_name"),
            rec.get("priority"),
            rec.get("description"),
            rec.get("maps_link"),
            rec.get("source"),
        ])

    skeleton_sheet = wb.create_sheet("Trip Skeleton")
    skeleton_sheet.append(["Date", "Type", "Location/Route", "Details"])
    for row in build_skeleton_rows(trip_data):
        skeleton_sheet.append([row["date"], row["type"], row["location_route"], row["details"]])

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./venv/Scripts/python.exe -m pytest tests/test_export.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full test suite to confirm nothing else broke**

Run: `./venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS (all tests)

- [ ] **Step 6: Commit**

```bash
git add export.py tests/test_export.py
git commit -m "Extract build_skeleton_rows from build_excel for reuse"
```

---

### Task 2: Add `GET /preview/data` endpoint

**Files:**
- Modify: `main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_main.py`. First, add a `trip_data_file` fixture (parallel to `history_file`) near the top, right after the existing `history_file` fixture:

```python
@pytest.fixture
def trip_data_file(tmp_path, monkeypatch):
    path = tmp_path / "trip_data.json"
    monkeypatch.setattr(agent, "TRIP_DATA_PATH", path)
    return path
```

Then add the test at the bottom of the file:

```python
def test_preview_data_returns_recommendations_and_skeleton(trip_data_file):
    trip_data_file.write_text(json.dumps({
        "recommendations": [
            {
                "city": "Kyoto",
                "place_name": "Fushimi Inari",
                "priority": "must",
                "description": "shrine",
                "maps_link": "https://maps.example/x",
                "source": "friend",
            },
        ],
        "hotels": [
            {
                "name": "Gracery Shinjuku",
                "city": "Tokyo",
                "check_in": "2026-09-04",
                "check_out": "2026-09-11",
            },
        ],
        "flights": [],
    }), encoding="utf-8")

    response = client.get("/preview/data")

    assert response.status_code == 200
    data = response.json()
    assert data["recommendations"][0]["place_name"] == "Fushimi Inari"
    assert data["skeleton"] == [
        {
            "date": "2026-09-04",
            "type": "Hotel",
            "location_route": "Tokyo",
            "details": "Gracery Shinjuku: check-in 2026-09-04 -> check-out 2026-09-11",
        },
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_main.py::test_preview_data_returns_recommendations_and_skeleton -v`
Expected: FAIL with 404 (route doesn't exist yet)

- [ ] **Step 3: Add the endpoint**

In `main.py`, update the import line and add the route right after `history`:

```python
from agent import get_reply, load_history, load_trip_data
from export import build_excel, build_skeleton_rows
```

```python
@app.get("/preview/data")
def preview_data() -> dict:
    trip_data = load_trip_data()
    return {
        "recommendations": trip_data.get("recommendations", []),
        "skeleton": build_skeleton_rows(trip_data),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_main.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add main.py tests/test_main.py
git commit -m "Add GET /preview/data endpoint"
```

---

### Task 3: Add `GET /preview` page route + scaffold + chat-page nav link

**Files:**
- Modify: `main.py`
- Create: `static/preview.html`
- Modify: `static/index.html`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Create the preview page scaffold**

Create `static/preview.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trip Data Preview</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body class="preview-page">
  <header class="app-header">
    <h1>Trip Agent</h1>
    <nav class="header-nav">
      <a class="nav-link" href="/">Back to Chat</a>
      <a id="export-link" href="/export/excel">Export to Excel</a>
    </nav>
  </header>

  <main class="preview-content">
    <section>
      <h2>Recommendations</h2>
      <table class="data-table" id="recommendations-table">
        <thead>
          <tr>
            <th>City</th>
            <th>Place Name</th>
            <th>Priority</th>
            <th>Description</th>
            <th>Maps Link</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody id="recommendations-body"></tbody>
      </table>
    </section>

    <section>
      <h2>Trip Skeleton</h2>
      <table class="data-table" id="skeleton-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Type</th>
            <th>Location/Route</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody id="skeleton-body"></tbody>
      </table>
    </section>
  </main>

  <script src="/preview.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create a placeholder `preview.js` so the mount has something to serve**

Create `static/preview.js`:

```js
// filled in Task 5
```

- [ ] **Step 3: Add the chat page's nav link to the preview page**

In `static/index.html`, replace the header:

```html
  <header class="app-header">
    <h1>Trip Agent</h1>
    <a id="export-link" href="/export/excel">Export to Excel</a>
  </header>
```

with:

```html
  <header class="app-header">
    <h1>Trip Agent</h1>
    <nav class="header-nav">
      <a class="nav-link" href="/preview">Preview Trip Data</a>
      <a id="export-link" href="/export/excel">Export to Excel</a>
    </nav>
  </header>
```

- [ ] **Step 4: Write the failing test**

Add to `tests/test_main.py`, below `test_root_serves_index_html`:

```python
def test_preview_page_serves_preview_html():
    response = client.get("/preview")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Trip Data Preview" in response.text
```

- [ ] **Step 5: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_main.py::test_preview_page_serves_preview_html -v`
Expected: FAIL with 404 (route doesn't exist yet — the static mount only serves exact file paths, not `/preview` without `.html`)

- [ ] **Step 6: Add the route**

In `main.py`, add `FileResponse` to the existing `fastapi.responses` import:

```python
from fastapi.responses import FileResponse, StreamingResponse
```

Add the route, right after `preview_data` and before `export_excel`:

```python
@app.get("/preview")
def preview_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "preview.html")
```

- [ ] **Step 7: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_main.py -v`
Expected: PASS (all tests in the file)

- [ ] **Step 8: Run the full test suite**

Run: `./venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS (all tests)

- [ ] **Step 9: Commit**

```bash
git add main.py static/preview.html static/preview.js static/index.html tests/test_main.py
git commit -m "Add GET /preview page route and chat-page nav link"
```

---

### Task 4: Style the preview page

**Files:**
- Modify: `static/style.css`

No automated test for this task — pure CSS, verified visually in Task 6.

- [ ] **Step 1: Add the new styles**

Append to `static/style.css`:

```css
.header-nav {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.nav-link {
  font-size: 0.875rem;
  color: var(--accent);
  text-decoration: none;
}

.nav-link:hover {
  text-decoration: underline;
}

.preview-page .app-header {
  max-width: 900px;
}

.preview-content {
  width: 100%;
  max-width: 900px;
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.preview-content section {
  margin-bottom: 2rem;
}

.preview-content h2 {
  font-size: 1.05rem;
  margin: 0 0 0.5rem;
}

.data-table {
  border-collapse: collapse;
  width: 100%;
}

.data-table th,
.data-table td {
  border: 1px solid var(--border);
  padding: 0.5rem 0.75rem;
  text-align: start;
  font-size: 0.9rem;
}

.data-table th {
  background: var(--assistant-bg);
}

.data-table a {
  color: var(--accent);
}
```

- [ ] **Step 2: Run the backend test suite to confirm nothing broke**

Run: `./venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS (all tests)

- [ ] **Step 3: Commit**

```bash
git add static/style.css
git commit -m "Style the trip data preview page"
```

---

### Task 5: Preview page logic (fetch, render tables, empty state)

**Files:**
- Modify: `static/preview.js`

No automated test for this task — plain JS with no test runner configured (same reasoning as `chat.js`). Verified manually in Task 6.

- [ ] **Step 1: Write the rendering logic**

Replace the contents of `static/preview.js`:

```js
const recommendationsBody = document.getElementById("recommendations-body");
const skeletonBody = document.getElementById("skeleton-body");

function emptyRow(colSpan) {
  const row = document.createElement("tr");
  const td = document.createElement("td");
  td.colSpan = colSpan;
  td.textContent = "No data yet.";
  row.appendChild(td);
  return row;
}

function textCell(text) {
  const td = document.createElement("td");
  td.textContent = text ?? "";
  return td;
}

function linkCell(url) {
  const td = document.createElement("td");
  if (url) {
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = url;
    td.appendChild(a);
  }
  return td;
}

function renderRecommendations(recommendations) {
  if (recommendations.length === 0) {
    recommendationsBody.appendChild(emptyRow(6));
    return;
  }
  for (const rec of recommendations) {
    const row = document.createElement("tr");
    row.appendChild(textCell(rec.city));
    row.appendChild(textCell(rec.place_name));
    row.appendChild(textCell(rec.priority));
    row.appendChild(textCell(rec.description));
    row.appendChild(linkCell(rec.maps_link));
    row.appendChild(textCell(rec.source));
    recommendationsBody.appendChild(row);
  }
}

function renderSkeleton(skeleton) {
  if (skeleton.length === 0) {
    skeletonBody.appendChild(emptyRow(4));
    return;
  }
  for (const row of skeleton) {
    const tr = document.createElement("tr");
    tr.appendChild(textCell(row.date));
    tr.appendChild(textCell(row.type));
    tr.appendChild(textCell(row.location_route));
    tr.appendChild(textCell(row.details));
    skeletonBody.appendChild(tr);
  }
}

async function loadPreview() {
  const response = await fetch("/preview/data");
  const data = await response.json();
  renderRecommendations(data.recommendations);
  renderSkeleton(data.skeleton);
}

loadPreview();
```

- [ ] **Step 2: Run the backend test suite to confirm nothing broke**

Run: `./venv/Scripts/python.exe -m pytest tests/ -v`
Expected: PASS (all tests)

- [ ] **Step 3: Commit**

```bash
git add static/preview.js
git commit -m "Add preview page logic: fetch, render tables, empty state"
```

---

### Task 6: End-to-end manual verification

**Files:** none (verification only)

- [ ] **Step 1: Restart the server**

The server from the chat frontend work may still be running with the old code loaded. Stop it if so, then run: `./venv/Scripts/python.exe -m uvicorn main:app --port 8000`
Expected: server starts with no errors.

- [ ] **Step 2: Confirm chat page navigation**

Open `http://127.0.0.1:8000/`. Confirm the header now shows both "Preview Trip Data" and "Export to Excel" links, and clicking "Preview Trip Data" navigates to the preview page.

- [ ] **Step 3: Confirm the preview page renders real data**

On `http://127.0.0.1:8000/preview`, confirm:
- The Recommendations table shows the same rows (city, place name, priority, description, source) that are in `trip_data.json`, in the same order as the Excel export.
- Maps Link cells render as clickable links that open the URL in a new tab.
- The Trip Skeleton table shows hotels and flights merged and sorted chronologically, matching the "Trip Skeleton" sheet in a fresh Excel export.
- "Back to Chat" returns to the chat page; "Export to Excel" still downloads `trip_export.xlsx`.

- [ ] **Step 4: Confirm the empty state**

Temporarily back up `trip_data.json`, replace its `recommendations`, `hotels`, and `flights` with empty lists, restart the server, and reload `/preview`. Confirm both tables show a single "No data yet." row instead of being blank. Restore the original `trip_data.json` and restart the server afterward.

- [ ] **Step 5: Confirm existing functionality still works**

Send a chat message on `/` and confirm the reply still renders correctly (unaffected by this round's changes). Open `/docs` and confirm `/preview` and `/preview/data` are listed alongside the existing routes.

No commit for this task — it's verification only. If any step fails, fix the relevant file from Tasks 1-5 and re-run the failed step.
