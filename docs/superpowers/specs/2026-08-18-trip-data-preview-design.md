# Trip Data Preview Design

## Purpose

The chat page can trigger an Excel export of recommendations and the trip
skeleton, but the only way to check its contents — or discuss changes with
the agent first — is to download and open the file. This adds a read-only
preview page showing the same two datasets as HTML tables, so they can be
checked in-browser without downloading anything.

## Architecture

A separate static page, not a tab/toggle on the chat page — `chat.js` is
already scoped tightly to the chat DOM, and keeping each page to one job
matches the existing split between `index.html`/`chat.js`.

- `GET /preview` — new FastAPI route, registered before the static mount
  (same ordering rule as the existing routes), returns `static/preview.html`
  via `FileResponse`.
- `GET /preview/data` — new JSON endpoint returning
  `{"recommendations": [...], "skeleton": [...]}`, read from
  `trip_data.json` — the same source `/export/excel` uses.
- `static/preview.html` + `static/preview.js` — new files, following the
  same fetch-then-render pattern `chat.js` already uses for `/history`.

### No new data logic

`export.py`'s `build_excel` currently builds the chronological hotel/flight
merge inline. That logic is extracted into
`build_skeleton_rows(trip_data) -> list[dict]` (keys: `date`, `type`,
`location_route`, `details`), so `build_excel` and `/preview/data` both call
the same function — one sort/merge implementation, two renderings
(spreadsheet rows vs. JSON).

Recommendations need no extraction: both the Excel export and
`/preview/data` read `trip_data["recommendations"]` directly, in stored
order — no re-sorting, matching the Excel sheet exactly.

## Page content

- **Header/nav** on both `index.html` and `preview.html`: title, a nav link
  to the other page ("Preview Trip Data" from chat / "Back to Chat" from
  preview), and the existing "Export to Excel" link — reachable from either
  page.
- **Recommendations table:** City, Place Name, Priority, Description, Maps
  Link, Source — same column set/order as the Excel sheet. Maps Link
  renders as a clickable `<a>` opening in a new tab.
- **Trip Skeleton table:** Date, Type, Location/Route, Details — same as
  the Excel sheet, already chronologically sorted by `build_skeleton_rows`.
- **Empty state:** if a list is empty, the table still shows its headers
  plus a single "No data yet." row spanning the columns.
- **Loading:** `preview.js` fetches `/preview/data` on page load and
  renders both tables. No forms, no typing indicators — read-only.

## Styling

Reuses the chat page's visual language: same fonts, colors, centered
max-width column, border color. `style.css` gains a generic `.data-table`
class (border, padding — same look as the Markdown tables already styled
inside chat bubbles, just not nested in `.message`) and a `.nav-link` class
for the header nav link, styled like the existing `#export-link` button. No
new colors or fonts.

## Out of scope for this round

- Editing recommendations or trip data from the preview page (read-only).
- Filtering/sorting/searching the tables.
- Pagination (trip data is small enough that it isn't needed).
