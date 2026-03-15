"""
Action executor: maps action_name → real API call.

Supported actions:
- reset_password  → POST /reset_password/{user_id}
- refund_charge   → POST /refund_charge/{user_id}   (TODO: confirm endpoint)
- notify_user     → POST /notify_user/{user_id}     (TODO: confirm endpoint)
- escalate        → PATCH /chat/{chat_id} {status: pending}
"""
import httpx
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


async def execute_action(
    chat_id: int,
    user_id: int,
    action_name: str,
    reason: str = "",
) -> bool:
    """Execute a support action. Returns True on success."""
    print(f"[action_executor] {action_name} user={user_id} chat={chat_id} reason={reason}")

    async with httpx.AsyncClient() as http:
        try:
            match action_name:
                case "reset_password":
                    resp = await http.post(
                        f"{settings.api_base_url}/reset_password/{user_id}/"
                    )

                case "refund_charge":
                    resp = await http.post(
                        f"{settings.api_base_url}/refund_charge/{user_id}/",
                        json={"chat_id": chat_id, "user_id": user_id},
                    )

                case "notify_user":
                    resp = await http.post(
                        f"{settings.api_base_url}/notify_user/{user_id}/",
                        json={"chat_id": chat_id, "user_id": user_id, "message": reason},
                    )

                case "escalate":
                    resp = await http.patch(
                        f"{settings.api_base_url}/bo/chat/{chat_id}",
                        json={"escalate_to_human": True, "message": reason},
                    )

                case _:
                    print(f"[action_executor] Unknown action: {action_name}")
                    return False

            resp.raise_for_status()
            print(f"[action_executor] {action_name} → {resp.status_code}")
            return True

        except httpx.HTTPStatusError as e:
            print(f"[action_executor] {action_name} failed: {e.response.status_code} {e.response.text}")
            return False
        except httpx.RequestError as e:
            print(f"[action_executor] {action_name} request error: {e}")
            return False
