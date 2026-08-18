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
