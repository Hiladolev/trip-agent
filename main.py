"""FastAPI app exposing the trip-planning chat agent.

Minimal slice - no auth yet. Serves the chat, preview, and to-do frontend
pages from static/, and exposes /chat, /history, /preview*, /todos*, and
/export/excel.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import delete_todo_item, execute_tool, get_reply, load_history, load_trip_data
from export import build_excel, build_skeleton_rows

app = FastAPI(title="Trip Agent")

STATIC_DIR = Path(__file__).parent / "static"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class AddTodoRequest(BaseModel):
    task: str
    deadline: str | None = None


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = get_reply(request.message)
    return ChatResponse(reply=reply)


@app.get("/history")
def history() -> list[dict]:
    return load_history()


@app.get("/todos/data")
def todos_data() -> list[dict]:
    return load_trip_data().get("todo_list", [])


@app.post("/todos/data")
def add_todo(request: AddTodoRequest) -> list[dict]:
    execute_tool("add_todo_item", {"task": request.task, "deadline": request.deadline})
    return load_trip_data().get("todo_list", [])


@app.post("/todos/data/{item_id}/complete")
def complete_todo(item_id: str) -> list[dict]:
    _, is_error = execute_tool("complete_todo_item", {"id": item_id})
    if is_error:
        raise HTTPException(status_code=404, detail=f"No todo item found with id {item_id}.")
    return load_trip_data().get("todo_list", [])


@app.delete("/todos/data/{item_id}")
def delete_todo(item_id: str) -> list[dict]:
    if not delete_todo_item(item_id):
        raise HTTPException(status_code=404, detail=f"No todo item found with id {item_id}.")
    return load_trip_data().get("todo_list", [])


@app.get("/todos")
def todos_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "todos.html")


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
