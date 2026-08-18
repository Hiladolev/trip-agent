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


@pytest.fixture
def trip_data_file(tmp_path, monkeypatch):
    path = tmp_path / "trip_data.json"
    monkeypatch.setattr(agent, "TRIP_DATA_PATH", path)
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


def test_root_serves_index_html():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Trip Agent" in response.text


def test_preview_page_serves_preview_html():
    response = client.get("/preview")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Trip Data Preview" in response.text


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


def test_get_todos_returns_todo_list(trip_data_file):
    trip_data_file.write_text(json.dumps({
        "todo_list": [
            {"id": "abc-1", "task": "Book ferry", "deadline": "2026-08-25", "completed": False},
        ],
    }), encoding="utf-8")

    response = client.get("/todos/data")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "abc-1", "task": "Book ferry", "deadline": "2026-08-25", "completed": False},
    ]


def test_post_todos_adds_new_item(trip_data_file):
    trip_data_file.write_text(json.dumps({"todo_list": []}), encoding="utf-8")

    response = client.post("/todos/data", json={"task": "Exchange currency", "deadline": None})

    assert response.status_code == 200
    todos = response.json()
    assert len(todos) == 1
    assert todos[0]["task"] == "Exchange currency"
    assert todos[0]["completed"] is False
    assert "id" in todos[0]


def test_complete_todos_marks_item_completed(trip_data_file):
    trip_data_file.write_text(json.dumps({
        "todo_list": [{"id": "abc-1", "task": "Book ferry", "deadline": None, "completed": False}],
    }), encoding="utf-8")

    response = client.post("/todos/data/abc-1/complete")

    assert response.status_code == 200
    assert response.json()[0]["completed"] is True


def test_complete_todos_unknown_id_returns_404(trip_data_file):
    trip_data_file.write_text(json.dumps({"todo_list": []}), encoding="utf-8")

    response = client.post("/todos/data/does-not-exist/complete")

    assert response.status_code == 404


def test_delete_todos_removes_item(trip_data_file):
    trip_data_file.write_text(json.dumps({
        "todo_list": [{"id": "abc-1", "task": "Book ferry", "deadline": None, "completed": False}],
    }), encoding="utf-8")

    response = client.delete("/todos/data/abc-1")

    assert response.status_code == 200
    assert response.json() == []


def test_delete_todos_unknown_id_returns_404(trip_data_file):
    trip_data_file.write_text(json.dumps({"todo_list": []}), encoding="utf-8")

    response = client.delete("/todos/data/does-not-exist")

    assert response.status_code == 404
