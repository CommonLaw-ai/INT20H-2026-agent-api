"""
Manual test for chat_agent (RAG + LLM conversation).

Mocks all HTTP calls to external API, uses real Ollama + pgvector.

Usage:
    python test_chat.py
"""
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

# ---------------------------------------------------------------------------
# Mock data (mirrors seed.sql)
# ---------------------------------------------------------------------------

MOCK_CHAT = {
    "chat_id": 1,
    "user_id": 3,
    "anomaly_id": 1,
    "chat_messages": [
        {
            "role": "assistant",
            "content": "Ми виявили підозріле подвійне списання коштів з вашого рахунку. Будь ласка, перевірте деталі.",
        }
    ],
}

MOCK_ANOMALY = {
    "anomaly_id": 1,
    "anomaly_name": "duplicate_subscription_charge",
    "anomaly_description": "Two or more subscription charge events for the same user within 60 seconds.",
    "first_message": "Ми виявили підозріле подвійне списання коштів з вашого рахунку. Будь ласка, перевірте деталі.",
}

MOCK_USER = {
    "user_id": 3,
    "first_name": "Bob",
    "last_name": "Jones",
    "email": "bob@example.com",
    "has_subscription": True,
    "subscription_type": "basic",
    "created_at": "2024-01-01T00:00:00",
}

MOCK_LOGS = [
    {"created_at": "2024-01-15 10:15:30", "user_id": 3, "log_type": "BILLING", "log_message": "Subscription charge: 9.99 plan=basic"},
    {"created_at": "2024-01-15 10:15:33", "user_id": 3, "log_type": "BILLING", "log_message": "Subscription charge: 9.99 plan=basic"},
]


# ---------------------------------------------------------------------------
# HTTP mock: intercepts httpx calls in context_builder and agent
# ---------------------------------------------------------------------------

def make_mock_response(data):
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


class MockAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url, **kwargs):
        if "/chat/" in url:
            return make_mock_response(MOCK_CHAT)
        if "/anomaly/" in url:
            return make_mock_response(MOCK_ANOMALY)
        if "/user/" in url:
            return make_mock_response(MOCK_USER)
        if "/logs" in url:
            return make_mock_response(MOCK_LOGS)
        raise ValueError(f"Unmocked GET: {url}")

    async def post(self, url, **kwargs):
        print(f"  [mock] POST {url} body={kwargs.get('json')}")
        return make_mock_response({"ok": True})

    async def patch(self, url, **kwargs):
        print(f"  [mock] PATCH {url} body={kwargs.get('json')}")
        return make_mock_response({"ok": True})


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

MOCK_ACTIONS = [
    {"action_id": 1, "action_name": "reset_password",  "action_description": "Send password reset link to the user"},
    {"action_id": 2, "action_name": "refund_charge",   "action_description": "Initiate a refund for a duplicate charge"},
    {"action_id": 4, "action_name": "notify_user",     "action_description": "Send email notification to the user"},
]


async def chat_turn(chat_id: int, user_message: str, history: list) -> str:
    """One turn: send message, get reply. History updated in-place."""
    from chat_agent.agent import handle_message

    with patch("httpx.AsyncClient", MockAsyncClient):
        MOCK_CHAT["chat_messages"] = history.copy()
        reply = await handle_message(chat_id, user_message)

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    return reply


async def main():
    print("=" * 60)
    print("Chat agent test — duplicate charge scenario (user: Bob Jones)")
    print("=" * 60)
    print()
    print(f"[assistant]: {MOCK_CHAT['chat_messages'][0]['content']}")
    print()

    history = MOCK_CHAT["chat_messages"].copy()
    chat_id = 1

    # Scenario: user confirms the duplicate charge
    turns = [
        "Так, щось підозріле бачу",
        "9.99, від 15 січня",
        "Дякую, чекаю на повернення коштів",
    ]

    for msg in turns:
        print(f"[user]: {msg}")
        reply = await chat_turn(chat_id, msg, history)
        print(f"[assistant]: {reply}")
        print()

        # Stop if action was invoked (chat resolved)
        if any(kw in reply.lower() for kw in ["вирішено", "закрито", "resolved", "refund", "повернен"]):
            print("--- action detected, conversation closed ---")
            break


if __name__ == "__main__":
    asyncio.run(main())
