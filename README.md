# INT20H 2026 — Agent API

> Part of the **AI Support Agent** system built for the INT20H 2026 hackathon.

## What is this project?

Modern subscription services generate thousands of user events every day — failed logins, duplicate charges, suspicious activity. Investigating each one manually is slow and expensive.

This project automates that process with an AI agent that:

1. **Monitors logs** — scans user activity every 60 seconds looking for anomalies (duplicate charges, multiple failed logins, etc.)
2. **Initiates conversations** — when an anomaly is detected, automatically opens a support chat and sends the user a first message explaining the situation
3. **Conducts interviews** — an LLM-powered agent talks to the user in their language, asks clarifying questions, and decides what to do
4. **Takes action** — depending on the user's response, the agent either resolves the issue automatically (issues a refund, resets a password) or escalates to a human operator
5. **Back-office dashboard** — human operators can monitor all chats, review AI decisions, approve or reject action requests, and manage the agent's available actions

## System Architecture

```
┌─────────────┐     messages      ┌─────────────────┐
│   Frontend  │ ───────────────►  │    Back App      │
│  (React)    │ ◄───────────────  │   (port 8001)    │
└─────────────┘    chat replies   └────────┬─────────┘
                                           │ delegates to
                                           ▼
                                  ┌─────────────────┐
                                  │   Agent API      │
                                  │   (port 8000)    │
                                  │                  │
                                  │  ┌─────────────┐ │
                                  │  │  Analyzer   │ │  ◄── runs every 60s
                                  │  └─────────────┘ │
                                  │  ┌─────────────┐ │
                                  │  │ Chat Agent  │ │  ◄── LLM + RAG
                                  │  └─────────────┘ │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │   PostgreSQL     │
                                  │   + pgvector     │
                                  └─────────────────┘
                                           │
                                  ┌─────────────────┐
                                  │     Ollama       │
                                  │  llama3.1:8b     │
                                  └─────────────────┘
```

## Repos

| Repo | Description |
|------|-------------|
| [INT20H-2026-back-app](https://github.com/CommonLaw-ai/INT20H-2026-back-app) | Main backend — chats, users, anomalies, back-office API |
| [INT20H-2026-agent-api](https://github.com/CommonLaw-ai/INT20H-2026-agent-api) | AI service — anomaly detection, LLM agent, RAG |
| [INT20H-2026-front-app](https://github.com/CommonLaw-ai/INT20H-2026-front-app) | Frontend — client chat UI + back-office dashboard |

---

## Agent API

AI service responsible for anomaly detection and LLM-driven support conversations.

### Architecture

```
analyzer_service/   — scans logs every 60s, detects anomalies via LLM, triggers chats
chat_agent/         — handles support conversations (RAG + LLM + action execution)
main.py             — FastAPI app, proxy endpoints to back-app
```

### Agent conversation flow

1. Analyzer fetches logs and anomaly types from back-app every 60 seconds
2. LLM analyzes logs and detects anomalies
3. For each affected user, `POST /initiate_chat` is called on back-app
4. When user replies, back-app calls `POST /chat/{chat_id}/message` on this service
5. Agent builds context (user info, anomaly, logs, RAG-retrieved actions), calls LLM
6. LLM decides: ask for clarification, execute an action, or escalate to human
7. Agent saves messages and closes/escalates chat via back-app

### RAG (Retrieval-Augmented Generation)

Actions available to the agent are stored as vector embeddings in PostgreSQL (pgvector). On each turn, the agent retrieves the most relevant actions for the current anomaly type using semantic search, and injects them into the system prompt.

### Dependencies

- **back-app** — source of truth for DB (users, chats, logs, anomalies, actions)
- **Ollama** — local LLM (`llama3.1:8b`) and embeddings (`nomic-embed-text`)
- **PostgreSQL + pgvector** — stores action embeddings for RAG

### Setup

#### 1. Install dependencies
```bash
pip install -r requirements.txt
```

#### 2. Ollama models
```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

#### 3. PostgreSQL with pgvector
```bash
docker run -d --name pg-agent -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=agent_db -p 5432:5432 pgvector/pgvector:pg16
Get-Content schema.psql | docker exec -i pg-agent psql -U postgres -d agent_db
Get-Content seed.sql | docker exec -i pg-agent psql -U postgres -d agent_db
```

#### 4. Environment
```env
EXTERNAL_API_URL=http://localhost:8001
API_BASE_URL=http://localhost:8001
DATABASE_URL=postgresql://postgres:postgres@localhost/agent_db
OLLAMA_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1:8b
EMBED_MODEL=nomic-embed-text
```

#### 5. Run
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
