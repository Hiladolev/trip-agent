"""FastAPI app exposing the trip-planning chat agent.

Minimal slice - no auth yet, no frontend yet. Test via the auto-generated
Swagger UI at /docs once the server is running.
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import get_reply, load_trip_data
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


@app.get("/export/excel")
def export_excel() -> StreamingResponse:
    trip_data = load_trip_data()
    excel_file = build_excel(trip_data)
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=trip_export.xlsx"},
    )
