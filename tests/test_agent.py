"""Tests for execute_tool - the deterministic trip_data.json read/write logic
behind each of the five custom tools. No API calls involved.
"""

import copy
import json
from datetime import date

import pytest

import agent

BASE_TRIP_DATA = {
    "trip_composition": "honeymoon - a couple, adult-oriented recommendations only",
    "destinations": ["Japan", "Thailand"],
    "trip_start_date": "2026-09-03",
    "trip_end_date": "2026-10-05",
    "flights": [],
    "hotels": [],
    "booked_activities": [],
    "budget": {"total_ils": 45000, "spent_so_far_ils": 0},
    "exchange_rates": {},
    "todo_list": [],
    "recommendations": [],
    "logged_expenses": [],
}


@pytest.fixture
def trip_data_file(tmp_path, monkeypatch):
    path = tmp_path / "trip_data.json"
    path.write_text(json.dumps(copy.deepcopy(BASE_TRIP_DATA)), encoding="utf-8")
    monkeypatch.setattr(agent, "TRIP_DATA_PATH", path)
    return path


def test_log_expense_appends_and_recomputes_budget(trip_data_file):
    agent.execute_tool(
        "log_expense",
        {"date": "2026-09-05", "amount_ils": 100, "category": "food", "description": "lunch"},
    )
    agent.execute_tool(
        "log_expense",
        {"date": "2026-09-06", "amount_ils": 50, "category": "transport", "description": "taxi"},
    )

    data = agent.load_trip_data()
    assert len(data["logged_expenses"]) == 2
    assert data["budget"]["spent_so_far_ils"] == 150


def test_add_todo_item_creates_incomplete_item(trip_data_file):
    result, is_error = agent.execute_tool(
        "add_todo_item", {"task": "book tickets", "deadline": "2026-08-25"}
    )

    assert is_error is False
    item = agent.load_trip_data()["todo_list"][0]
    assert item["task"] == "book tickets"
    assert item["deadline"] == "2026-08-25"
    assert item["completed"] is False
    assert "id" in item


def test_add_todo_item_without_deadline_is_none(trip_data_file):
    agent.execute_tool("add_todo_item", {"task": "pack bags"})

    assert agent.load_trip_data()["todo_list"][0]["deadline"] is None


def test_complete_todo_item_marks_completed(trip_data_file):
    agent.execute_tool("add_todo_item", {"task": "book tickets"})
    item_id = agent.load_trip_data()["todo_list"][0]["id"]

    result, is_error = agent.execute_tool("complete_todo_item", {"id": item_id})

    assert is_error is False
    assert agent.load_trip_data()["todo_list"][0]["completed"] is True


def test_complete_todo_item_unknown_id_is_error(trip_data_file):
    result, is_error = agent.execute_tool("complete_todo_item", {"id": "does-not-exist"})

    assert is_error is True
    assert "no todo item" in result.lower()


def test_add_recommendation_stores_all_fields(trip_data_file):
    result, is_error = agent.execute_tool(
        "add_recommendation",
        {
            "place_name": "Fushimi Inari",
            "city": "Kyoto",
            "priority": "must",
            "description": "famous shrine",
            "maps_link": "https://maps.example/fushimi",
            "source": "friend",
        },
    )

    assert is_error is False
    rec = agent.load_trip_data()["recommendations"][0]
    assert rec["place_name"] == "Fushimi Inari"
    assert rec["city"] == "Kyoto"
    assert rec["priority"] == "must"
    assert rec["maps_link"] == "https://maps.example/fushimi"
    assert rec["source"] == "friend"
    assert "id" in rec
    assert "date_added" in rec


def test_add_recommendation_without_optional_fields(trip_data_file):
    agent.execute_tool(
        "add_recommendation",
        {"place_name": "Random Cafe", "city": "Osaka", "priority": "nice_to_have", "description": "coffee"},
    )

    rec = agent.load_trip_data()["recommendations"][0]
    assert rec["maps_link"] is None
    assert rec["source"] is None


def test_update_exchange_rate_caches_with_today(trip_data_file):
    result, is_error = agent.execute_tool(
        "update_exchange_rate", {"currency_code": "JPY", "rate_to_ils": 0.024}
    )

    assert is_error is False
    entry = agent.load_trip_data()["exchange_rates"]["JPY"]
    assert entry["rate_to_ils"] == 0.024
    assert entry["fetched_date"] == date.today().isoformat()


def test_update_exchange_rate_overwrites_existing(trip_data_file):
    agent.execute_tool("update_exchange_rate", {"currency_code": "JPY", "rate_to_ils": 0.024})
    agent.execute_tool("update_exchange_rate", {"currency_code": "JPY", "rate_to_ils": 0.025})

    assert agent.load_trip_data()["exchange_rates"]["JPY"]["rate_to_ils"] == 0.025


def test_unknown_tool_name_is_error(trip_data_file):
    result, is_error = agent.execute_tool("not_a_real_tool", {})

    assert is_error is True


def test_build_system_prompt_includes_today_and_trip_data(trip_data_file):
    data = agent.load_trip_data()
    prompt = agent.build_system_prompt(data)

    assert date.today().isoformat() in prompt
    assert "CURRENT trip_data.json" in prompt
    assert "TOOLS FOR UPDATING TRIP DATA" in prompt
