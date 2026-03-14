"""
Context builder for the chat agent.

Given a chat_id, fetches all relevant data from the external API and assembles
a structured context object + system prompt for the LLM.

Data gathered:
- chat       → user_id, anomaly_id, chat_messages history
- anomaly    → name, description, first_message
- user       → name, subscription type, member since
- user logs  → events that triggered the anomaly
- actions    → injected by agent.py via RAG (not fetched here)
"""
from pathlib import Path

import httpx
from dataclasses import dataclass, field
from pydantic_settings import BaseSettings

PROMPT_TEMPLATE = (Path(__file__).parent / "prompt.md").read_text()


class Settings(BaseSettings):
    api_base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


@dataclass
class ChatContext:
    chat_id: int
    user_id: int
    anomaly_id: int
    anomaly_name: str
    anomaly_description: str
    first_message: str
    user_name: str
    has_subscription: bool
    subscription_type: str
    user_since: str
    chat_messages: list
    user_logs: list
    available_actions: list[dict] = field(default_factory=list)

    def build_system_prompt(self) -> str:
        logs_text = "\n".join(
            f"  [{l['created_at']}] type={l['log_type']} msg={l['log_message']}"
            for l in self.user_logs
        ) or "  (no logs available)"

        actions_text = "\n".join(
            f"- {a['action_name']}: {a['action_description']}"
            for a in self.available_actions
        ) or "  (no actions available)"

        return PROMPT_TEMPLATE.format(
            user_name=self.user_name,
            subscription_type=self.subscription_type,
            has_subscription=self.has_subscription,
            user_since=self.user_since,
            anomaly_name=self.anomaly_name,
            anomaly_description=self.anomaly_description,
            anomaly_logs=logs_text,
            available_actions=actions_text,
        )


async def build_context(chat_id: int) -> ChatContext:
    """Fetch all data for a chat and return a ChatContext."""
    async with httpx.AsyncClient() as http:
        # TODO: replace with real external API endpoint paths once confirmed
        chat_resp = await http.get(f"{settings.api_base_url}/chat/{chat_id}")
        chat_resp.raise_for_status()
        chat = chat_resp.json()

        user_id = chat["user_id"]
        anomaly_id = chat["anomaly_id"]

        anomaly_resp = await http.get(f"{settings.api_base_url}/anomaly/{anomaly_id}")
        anomaly_resp.raise_for_status()
        anomaly = anomaly_resp.json()

        user_resp = await http.get(f"{settings.api_base_url}/user/{user_id}")
        user_resp.raise_for_status()
        user = user_resp.json()

        logs_resp = await http.get(
            f"{settings.api_base_url}/logs",
            params={"user_id": user_id, "for_seconds": 3600},
        )
        logs_resp.raise_for_status()
        user_logs = logs_resp.json()

    return ChatContext(
        chat_id=chat_id,
        user_id=user_id,
        anomaly_id=anomaly_id,
        anomaly_name=anomaly["anomaly_name"],
        anomaly_description=anomaly["anomaly_description"],
        first_message=anomaly["first_message"],
        user_name=f"{user['first_name']} {user['last_name']}",
        has_subscription=user["has_subscription"],
        subscription_type=user.get("subscription_type", "unknown"),
        user_since=str(user.get("created_at", "unknown")),
        chat_messages=chat.get("chat_messages") or [],
        user_logs=user_logs,
        # available_actions is injected by agent.py after RAG search
    )
