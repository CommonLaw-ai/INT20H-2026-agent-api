"""
Chat agent: LLM-driven support conversation.

Two entry points:
- initiate(chat_id)      → called once after initiate_chat, first message already in DB
- handle_message(...)    → called on each user reply

Per turn the agent either:
  - replies with text (continues conversation)
  - invokes an action via JSON → action_executor → closes chat
"""
import json
import httpx
from openai import OpenAI
from pydantic_settings import BaseSettings

from chat_agent.context_builder import build_context
from chat_agent.rag import search_actions
from chat_agent.action_executor import execute_action


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b"
    api_base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
llm = OpenAI(base_url=settings.ollama_url, api_key="ollama")


def _extract_action(text: str) -> dict | None:
    """Try to parse the entire response as an action JSON."""
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict) and "action" in data:
            return data
    except json.JSONDecodeError:
        pass
    return None


async def handle_message(chat_id: int, user_message: str) -> str:
    """Process one user message, return agent reply."""

    # 1. Context + RAG
    ctx = await build_context(chat_id)
    rag_query = f"{ctx.anomaly_name} {ctx.anomaly_description}"
    ctx.available_actions = await search_actions(rag_query)

    # 2. Build messages: system + history (first_message already in history) + new user message
    messages = [{"role": "system", "content": ctx.build_system_prompt()}]
    for msg in ctx.chat_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    # 3. Call LLM
    response = llm.chat.completions.create(
        model=settings.ollama_model,
        messages=messages,
    )
    agent_reply = response.choices[0].message.content

    # 4. Execute action if detected
    action_call = _extract_action(agent_reply)
    if action_call:
        await execute_action(
            chat_id=chat_id,
            user_id=ctx.user_id,
            action_name=action_call["action"],
            reason=action_call.get("reason", ""),
        )

    # 5. Persist messages
    # TODO: confirm endpoint with backend teammate
    async with httpx.AsyncClient() as http:
        await http.post(
            f"{settings.api_base_url}/chat/{chat_id}/messages",
            json=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": agent_reply},
            ],
        )

        # 6. Close chat if action was executed (escalate sets pending, not resolved)
        if action_call and action_call["action"] != "escalate":
            await http.post(f"{settings.api_base_url}/bo/chat/{chat_id}/resolve")

    if action_call:
        return "Дякуємо, ми обробили ваш запит. Розмову завершено."
    return agent_reply
