"""
Scenario runner for chat agent testing.

Runs predefined conversation scenarios against the live back-app + agent-api,
saves results to scenarios_output.json for review.

Usage:
    python run_scenarios.py

Requirements:
    - back-app running on localhost:8001
    - agent-api running on localhost:8000
"""
import asyncio
import json
import sys
import httpx
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BACK_APP = "http://localhost:8001"

SCENARIOS = [
    {
        "name": "duplicate_charge_happy_path",
        "description": "User confirms duplicate charge, expects refund",
        "anomaly_id": 1,
        "user_id": 3,
        "turns": [
            "Так, я бачу підозрілі списання",
            "9.99 від 15 січня",
        ],
    },
    {
        "name": "duplicate_charge_denial",
        "description": "User denies all charges despite logs showing activity - should escalate",
        "anomaly_id": 1,
        "user_id": 3,
        "turns": [
            "Я взагалі не робив жодних платежів і не знаю що це таке",
            "Ні, я нічого не купував, це все неправда",
        ],
    },
    {
        "name": "failed_logins_was_me",
        "description": "User confirms failed logins were them, expects password reset",
        "anomaly_id": 2,
        "user_id": 6,
        "turns": [
            "Так, це був я, забув пароль",
            "bob@example.com",
        ],
    },
    {
        "name": "failed_logins_not_me",
        "description": "User says logins were not them - should escalate",
        "anomaly_id": 2,
        "user_id": 6,
        "turns": [
            "Ні, це не я намагався зайти, хтось намагається зламати мій акаунт",
            "Я взагалі не відкривав застосунок сьогодні",
        ],
    },
    {
        "name": "unresponsive_user",
        "description": "User gives unrelated/unhelpful responses - should escalate after 2 messages",
        "anomaly_id": 1,
        "user_id": 5,
        "turns": [
            "...",
            "не знаю",
            "може",
        ],
    },
]


async def run_scenario(client: httpx.AsyncClient, scenario: dict) -> dict:
    print(f"\n[{scenario['name']}] Starting...")

    # Create chat
    r = await client.post(
        f"{BACK_APP}/initiate_chat",
        json={"user_id": scenario["user_id"], "anomaly_id": scenario["anomaly_id"]},
        timeout=15,
    )
    r.raise_for_status()
    chat_id = r.json()["chat"]["chat_id"]
    print(f"  chat_id={chat_id}")

    turns = []
    final_status = None

    for user_text in scenario["turns"]:
        print(f"  [user] {user_text}")
        r = await client.post(
            f"{BACK_APP}/chat/{chat_id}",
            json={"text": user_text},
            timeout=120,
        )

        if r.status_code != 200:
            print(f"  [error] {r.status_code} {r.text}")
            turns.append({"user": user_text, "assistant": None, "error": r.text})
            break

        reply = r.json().get("reply", "")
        print(f"  [assistant] {reply}")
        turns.append({"user": user_text, "assistant": reply})

        # Check if chat was closed
        chat_r = await client.get(f"{BACK_APP}/chat/{chat_id}", timeout=10)
        status_id = chat_r.json()["data"]["chat_status_id"]
        if status_id in (2, 3):  # pending or resolved
            final_status = {2: "escalated", 3: "resolved"}.get(status_id)
            print(f"  [chat closed] status={final_status}")
            break

    # Final chat status
    chat_r = await client.get(f"{BACK_APP}/chat/{chat_id}", timeout=10)
    chat_data = chat_r.json()["data"]
    status_map = {1: "open", 2: "escalated", 3: "resolved", 4: "closed"}
    final_status = status_map.get(chat_data["chat_status_id"], "unknown")

    return {
        "scenario": scenario["name"],
        "description": scenario["description"],
        "chat_id": chat_id,
        "final_status": final_status,
        "turns": turns,
        "expected_outcome": _expected_outcome(scenario["name"]),
        "passed": _check_passed(scenario["name"], final_status, turns),
    }


def _expected_outcome(name: str) -> str:
    mapping = {
        "duplicate_charge_happy_path": "resolved",
        "duplicate_charge_denial": "escalated",
        "failed_logins_was_me": "resolved",
        "failed_logins_not_me": "escalated",
        "unresponsive_user": "escalated",
    }
    return mapping.get(name, "unknown")


def _check_passed(name: str, final_status: str, turns: list) -> bool:
    expected = _expected_outcome(name)
    return final_status == expected


async def main():
    results = []
    async with httpx.AsyncClient() as client:
        # Check services are up
        try:
            await client.get(f"{BACK_APP}/docs", timeout=5)
        except Exception:
            print("ERROR: back-app not reachable at", BACK_APP)
            return

        for scenario in SCENARIOS:
            try:
                result = await run_scenario(client, scenario)
                results.append(result)
            except Exception as e:
                print(f"  [EXCEPTION] {e}")
                results.append({
                    "scenario": scenario["name"],
                    "error": str(e),
                    "passed": False,
                })

    # Summary
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed")
    for r in results:
        status = "PASS" if r.get("passed") else "FAIL"
        print(f"  [{status}] {r['scenario']} — final: {r.get('final_status', 'error')}, expected: {r.get('expected_outcome', '?')}")

    # Save to JSON
    output = {
        "run_at": datetime.now().isoformat(),
        "summary": {"passed": passed, "total": total},
        "results": results,
    }
    with open("scenarios_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to scenarios_output.json")


if __name__ == "__main__":
    asyncio.run(main())
