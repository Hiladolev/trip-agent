"""FastAPI app exposing the trip-planning chat agent.

Minimal slice - no auth yet, no frontend yet. Test via the auto-generated
Swagger UI at /docs once the server is running.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from agent import get_reply

app = FastAPI(title="Trip Agent")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    reply = get_reply(request.message)
    return ChatResponse(reply=reply)
