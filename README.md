# INT20H Agent API

AI service for automated anomaly detection and LLM-driven support conversations.

## Architecture

```
analyzer_service/   — scans logs every 60s, detects anomalies via LLM, triggers chats
chat_agent/         — handles support conversations (RAG + LLM + action execution)
main.py             — FastAPI app, proxy endpoints to back-app
```

## Flow

1. Analyzer fetches logs and anomaly types from back-app every 60 seconds
2. LLM (Ollama) analyzes logs and detects anomalies
3. For each affected user, `POST /initiate_chat` is called on back-app
4. When user replies, back-app calls `POST /chat/{chat_id}/message` on this service
5. Agent builds context (user, anomaly, logs, RAG actions), calls LLM
6. LLM decides to ask clarification, execute action, or escalate
7. Agent saves messages and closes/escalates chat via back-app

## Dependencies

- **back-app** — source of truth for DB (users, chats, logs, anomalies, actions)
- **Ollama** — local LLM (`llama3.1:8b`) and embeddings (`nomic-embed-text`)
- **PostgreSQL + pgvector** — stores action embeddings for RAG

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Ollama models
```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 3. PostgreSQL with pgvector
```bash
docker run -d --name pg-agent -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=agent_db -p 5432:5432 pgvector/pgvector:pg16
Get-Content schema.psql | docker exec -i pg-agent psql -U postgres -d agent_db
Get-Content seed.sql | docker exec -i pg-agent psql -U postgres -d agent_db
```

### 4. Environment
```env
EXTERNAL_API_URL=http://localhost:8001
API_BASE_URL=http://localhost:8001
DATABASE_URL=postgresql://postgres:postgres@localhost/agent_db
OLLAMA_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1:8b
EMBED_MODEL=nomic-embed-text
```

### 5. Run
```bash
uvicorn main:app --reload --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/logs` | Proxy: get logs from back-app |
| GET | `/anomalies` | Proxy: get anomaly types |
| POST | `/initiate_chat` | Proxy: create anomaly chat |
| POST | `/chat/{chat_id}/message` | Handle user message via LLM agent |
| POST | `/reset_password/{user_id}/` | Proxy: reset user password |
| POST | `/refund_charge/{user_id}/` | Proxy: refund duplicate charge |
| POST | `/notify_user/{user_id}/` | Proxy: notify user via email |

