"""Core agent loop: one chat turn against Claude, with web search plus the
five custom tools that read/write trip_data.json.
"""

import json
import uuid
from datetime import date
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

BASE_DIR = Path(__file__).parent
SYSTEM_PROMPT_PATH = BASE_DIR / "system_prompt.txt"
TRIP_DATA_PATH = BASE_DIR / "trip_data.json"
HISTORY_PATH = BASE_DIR / "conversation_history.json"

MODEL = "claude-sonnet-5"
MAX_TOKENS = 16000
MAX_HISTORY_MESSAGES = 20

LOG_EXPENSE_TOOL = {
    "name": "log_expense",
    "description": "Log an expense in ILS and update spent_so_far_ils.",
    "input_schema": {
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "amount_ils": {"type": "number"},
            "category": {"type": "string", "description": "e.g. food, transport, activity, shopping"},
            "description": {"type": "string"},
        },
        "required": ["date", "amount_ils", "category", "description"],
    },
}

ADD_TODO_ITEM_TOOL = {
    "name": "add_todo_item",
    "description": "Add a new item to the pre-trip to-do list.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "deadline": {"type": "string", "description": "Optional, YYYY-MM-DD"},
        },
        "required": ["task"],
    },
}

COMPLETE_TODO_ITEM_TOOL = {
    "name": "complete_todo_item",
    "description": "Mark a to-do item as completed by its id.",
    "input_schema": {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    },
}

ADD_RECOMMENDATION_TOOL = {
    "name": "add_recommendation",
    "description": "Save a place recommendation, tagged with the relevant city.",
    "input_schema": {
        "type": "object",
        "properties": {
            "place_name": {"type": "string"},
            "city": {"type": "string", "description": "One of: Tokyo, Kyoto, Osaka, Koh Samui, Koh Phangan"},
            "priority": {
                "type": "string",
                "enum": ["must", "recommended", "nice_to_have"],
                "description": "How strongly this is recommended - ask the user if not stated",
            },
            "description": {"type": "string"},
            "maps_link": {"type": "string"},
            "source": {"type": "string"},
        },
        "required": ["place_name", "city", "priority", "description"],
    },
}

UPDATE_EXCHANGE_RATE_TOOL = {
    "name": "update_exchange_rate",
    "description": "Cache today's exchange rate for a currency to ILS.",
    "input_schema": {
        "type": "object",
        "properties": {
            "currency_code": {"type": "string", "description": "e.g. JPY or THB"},
            "rate_to_ils": {"type": "number"},
        },
        "required": ["currency_code", "rate_to_ils"],
    },
}

CUSTOM_TOOLS = [
    LOG_EXPENSE_TOOL,
    ADD_TODO_ITEM_TOOL,
    COMPLETE_TODO_ITEM_TOOL,
    ADD_RECOMMENDATION_TOOL,
    UPDATE_EXCHANGE_RATE_TOOL,
]

TOOLS = [{"type": "web_search_20260209", "name": "web_search"}] + CUSTOM_TOOLS


def load_trip_data() -> dict:
    with open(TRIP_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_trip_data(trip_data: dict) -> None:
    with open(TRIP_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(trip_data, f, ensure_ascii=False, indent=2)


def load_history() -> list:
    if not HISTORY_PATH.exists():
        return []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history: list) -> None:
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def compute_days_remaining(trip_data: dict) -> int:
    today = date.today()
    trip_start = date.fromisoformat(trip_data["trip_start_date"])
    trip_end = date.fromisoformat(trip_data["trip_end_date"])
    reference = trip_start if today < trip_start else today
    return (trip_end - reference).days + 1


def build_system_prompt(trip_data: dict) -> str:
    base_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    trip_data_json = json.dumps(trip_data, ensure_ascii=False, indent=2)
    today = date.today().isoformat()
    days_remaining = compute_days_remaining(trip_data)
    return (
        f"{base_prompt}\n\n"
        f"Today's date is: {today}\n"
        f"Days remaining in the trip: {days_remaining} (use this exact number - "
        f"do not recalculate it yourself from trip_start_date/trip_end_date)\n\n"
        f"CURRENT trip_data.json:\n{trip_data_json}"
    )


def execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    trip_data = load_trip_data()

    if name == "log_expense":
        trip_data["logged_expenses"].append({
            "date": tool_input["date"],
            "amount_ils": tool_input["amount_ils"],
            "category": tool_input["category"],
            "description": tool_input["description"],
        })
        trip_data["budget"]["spent_so_far_ils"] = sum(
            e["amount_ils"] for e in trip_data["logged_expenses"]
        )
        save_trip_data(trip_data)
        return (
            f"Logged {tool_input['amount_ils']} ILS. "
            f"spent_so_far_ils is now {trip_data['budget']['spent_so_far_ils']}.",
            False,
        )

    if name == "add_todo_item":
        item = {
            "id": str(uuid.uuid4()),
            "task": tool_input["task"],
            "deadline": tool_input.get("deadline"),
            "completed": False,
        }
        trip_data["todo_list"].append(item)
        save_trip_data(trip_data)
        return f"Added todo item {item['id']}.", False

    if name == "complete_todo_item":
        for item in trip_data["todo_list"]:
            if item["id"] == tool_input["id"]:
                item["completed"] = True
                save_trip_data(trip_data)
                return f"Marked {tool_input['id']} as completed.", False
        return f"No todo item found with id {tool_input['id']}.", True

    if name == "add_recommendation":
        rec = {
            "id": str(uuid.uuid4()),
            "place_name": tool_input["place_name"],
            "city": tool_input["city"],
            "priority": tool_input["priority"],
            "description": tool_input["description"],
            "maps_link": tool_input.get("maps_link"),
            "source": tool_input.get("source"),
            "date_added": date.today().isoformat(),
        }
        trip_data["recommendations"].append(rec)
        save_trip_data(trip_data)
        return f"Added recommendation: {rec['place_name']} ({rec['city']}).", False

    if name == "update_exchange_rate":
        trip_data["exchange_rates"][tool_input["currency_code"]] = {
            "rate_to_ils": tool_input["rate_to_ils"],
            "fetched_date": date.today().isoformat(),
        }
        save_trip_data(trip_data)
        return (
            f"Cached {tool_input['currency_code']} -> ILS rate: {tool_input['rate_to_ils']}.",
            False,
        )

    return f"Unknown tool: {name}", True


def delete_todo_item(item_id: str) -> bool:
    """Remove a to-do item by id. Page-only mutation (not in CUSTOM_TOOLS) -
    Claude cannot call this from chat."""
    trip_data = load_trip_data()
    for i, item in enumerate(trip_data["todo_list"]):
        if item["id"] == item_id:
            del trip_data["todo_list"][i]
            save_trip_data(trip_data)
            return True
    return False


def get_reply(user_message: str) -> str:
    trip_data = load_trip_data()
    system_prompt = build_system_prompt(trip_data)

    full_history = load_history()
    recent_history = full_history[-MAX_HISTORY_MESSAGES:]
    api_messages = [
        {"role": m["role"], "content": m["content"]} for m in recent_history
    ]
    api_messages.append({"role": "user", "content": user_message})

    container_id = None
    while True:
        create_kwargs = dict(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=api_messages,
            tools=TOOLS,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
        )
        if container_id:
            create_kwargs["container"] = container_id
        response = client.messages.create(**create_kwargs)
        if response.container:
            container_id = response.container.id
        api_messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "pause_turn":
            # web_search's server-side loop hit its iteration cap; resending
            # as-is tells the API to resume where it left off.
            continue

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                content, is_error = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                })
            api_messages.append({"role": "user", "content": tool_results})
            continue

        break

    reply_text = "\n".join(
        block.text for block in response.content if block.type == "text"
    )

    full_history.append({"role": "user", "content": user_message})
    full_history.append({"role": "assistant", "content": reply_text})
    save_history(full_history)

    return reply_text
