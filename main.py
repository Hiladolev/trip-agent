"""FastAPI app exposing the trip-planning chat agent.

Minimal slice - no auth yet. Serves the chat frontend from static/ and
exposes /chat, /history, and /export/excel.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import get_reply, load_history, load_trip_data
from export import build_excel, build_skeleton_rows

app = FastAPI(title="Trip Agent")

STATIC_DIR = Path(__file__).parent / "static"


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


@app.get("/preview/data")
def preview_data() -> dict:
    trip_data = load_trip_data()
    return {
        "recommendations": trip_data.get("recommendations", []),
        "skeleton": build_skeleton_rows(trip_data),
    }


@app.get("/preview")
def preview_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "preview.html")


@app.get("/export/excel")
def export_excel() -> StreamingResponse:
    trip_data = load_trip_data()
    excel_file = build_excel(trip_data)
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=trip_export.xlsx"},
    )


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
