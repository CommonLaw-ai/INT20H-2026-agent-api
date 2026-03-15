import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class Settings(BaseSettings):
    external_api_url: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from analyzer_service.analyzer import run_analysis
    from chat_agent.rag import setup_rag
    await setup_rag()
    scheduler.add_job(run_analysis, "interval", seconds=60)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="LLM Tool API", lifespan=lifespan)


@app.get("/logs")
async def get_logs(for_seconds: int = 3600):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.external_api_url}/get_logs",
                params={"for_seconds": for_seconds},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
    return response.json()


@app.get("/anomalies")
async def get_anomalies():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.external_api_url}/get_anomaly_list")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
    return response.json()


class InitiateChatRequest(BaseModel):
    user_id: int
    anomaly_id: int


@app.post("/initiate_chat")
async def initiate_chat(body: InitiateChatRequest):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.external_api_url}/initiate_chat",
                json={"user_id": body.user_id, "anomaly_id": body.anomaly_id},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
    return response.json()


class ChatMessageRequest(BaseModel):
    message: str


@app.post("/chat/{chat_id}/message")
async def chat_message(chat_id: int, body: ChatMessageRequest):
    from chat_agent.agent import handle_message
    try:
        reply = await handle_message(chat_id, body.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"reply": reply}


@app.post("/reset_password/{user_id}")
async def reset_password(user_id: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.external_api_url}/reset_password/{user_id}/"
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
    return response.json()


class ActionRequest(BaseModel):
    chat_id: int
    user_id: int


class NotifyRequest(BaseModel):
    chat_id: int
    user_id: int
    message: str = ""


@app.post("/refund_charge/{user_id}/")
async def refund_charge(user_id: int, body: ActionRequest):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.external_api_url}/bo/execute_action/refund_charge",
                json={"chat_id": body.chat_id, "user_id": user_id},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
    return response.json()


@app.post("/notify_user/{user_id}/")
async def notify_user(user_id: int, body: NotifyRequest):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{settings.external_api_url}/bo/execute_action/notify_user",
                json={"chat_id": body.chat_id, "user_id": user_id, "message": body.message},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
    return response.json()
