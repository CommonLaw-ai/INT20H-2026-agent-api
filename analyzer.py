import json
import httpx
from openai import OpenAI
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:7b"
    api_base_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
llm = OpenAI(base_url=settings.ollama_url, api_key="ollama")
SYSTEM_PROMPT = Path("anomalies.md").read_text()


async def run_analysis():
    async with httpx.AsyncClient() as http:
        try:
            logs_resp = await http.get(
                f"{settings.api_base_url}/logs", params={"for_seconds": 3600}
            )
            logs_resp.raise_for_status()
            logs = logs_resp.json()

            anomalies_resp = await http.get(f"{settings.api_base_url}/anomalies")
            anomalies_resp.raise_for_status()
            anomalies = anomalies_resp.json()
        except httpx.RequestError as e:
            print(f"[analyzer] Failed to fetch data: {e}")
            return

    if not logs:
        print("[analyzer] No logs to analyze")
        return

    anomalies_text = "\n".join(
        f"- ID {a['anomaly_id']}: {a['anomaly_name']} — {a['anomaly_description']}"
        for a in anomalies
    )
    logs_text = "\n".join(
        f"[{l['created_at']}] user_id={l['user_id']} type={l['log_type']} msg={l['log_message']}"
        for l in logs
    )

    user_message = f"""Known anomaly types:
{anomalies_text}

Logs to analyze:
{logs_text}

Return a JSON object with this exact structure:
{{
  "anomalies_found": [
    {{"anomaly_id": <int>, "user_ids": [<int>, ...]}}
  ]
}}
If no anomalies are found, return {{"anomalies_found": []}}.
Return only the JSON, no explanation."""

    try:
        response = llm.chat.completions.create(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)
    except Exception as e:
        print(f"[analyzer] LLM error: {e}")
        return

    found = result.get("anomalies_found", [])

    if not found:
        print("[analyzer] No anomalies found")
        return

    print(f"[analyzer] Found anomalies: {found}")

    async with httpx.AsyncClient() as http:
        for entry in found:
            for user_id in entry.get("user_ids", []):
                try:
                    resp = await http.post(
                        f"{settings.api_base_url}/initiate_chat",
                        json={"user_id": user_id, "anomaly_id": entry["anomaly_id"]},
                    )
                    print(
                        f"[analyzer] initiate_chat user={user_id} "
                        f"anomaly={entry['anomaly_id']} → {resp.status_code}"
                    )
                except httpx.RequestError as e:
                    print(f"[analyzer] initiate_chat failed: {e}")
