"""
RAG system for action retrieval.

Stores action embeddings in action_embeddings table (pgvector).
actions table is not modified.

Setup (run once at startup):
    await setup_rag()

Usage:
    actions = await search_actions("duplicate billing charge refund")
"""
import asyncpg
from openai import OpenAI
from pgvector.asyncpg import register_vector
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434/v1"
    embed_model: str = "nomic-embed-text"
    database_url: str = "postgresql://localhost/agent_db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
embedder = OpenAI(base_url=settings.ollama_url, api_key="ollama")


def get_embedding(text: str) -> list[float]:
    response = embedder.embeddings.create(model=settings.embed_model, input=text)
    return response.data[0].embedding


async def setup_rag():
    """Enable pgvector and index all actions that are not yet embedded."""
    conn = await asyncpg.connect(settings.database_url)
    await register_vector(conn)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # Find actions not yet indexed
        rows = await conn.fetch(
            """
            SELECT a.action_id, a.action_name, a.action_description
            FROM actions a
            LEFT JOIN action_embeddings ae ON ae.action_id = a.action_id
            WHERE ae.action_id IS NULL
            """
        )
        for row in rows:
            text = f"{row['action_name']}: {row['action_description']}"
            vector = get_embedding(text)
            await conn.execute(
                """
                INSERT INTO action_embeddings (action_id, embedding)
                VALUES ($1, $2)
                ON CONFLICT (action_id) DO UPDATE SET embedding = EXCLUDED.embedding
                """,
                row["action_id"],
                vector,
            )
        print(f"[rag] Indexed {len(rows)} actions")
    finally:
        await conn.close()


async def search_actions(query: str, top_k: int = 3) -> list[dict]:
    """Return top_k most relevant allowed actions for the given query."""
    query_vector = get_embedding(query)

    conn = await asyncpg.connect(settings.database_url)
    await register_vector(conn)
    try:
        rows = await conn.fetch(
            """
            SELECT a.action_id, a.action_name, a.action_description
            FROM actions a
            JOIN action_embeddings ae ON ae.action_id = a.action_id
            WHERE a.is_allowed = true
            ORDER BY ae.embedding <=> $1
            LIMIT $2
            """,
            query_vector,
            top_k,
        )
    finally:
        await conn.close()

    return [dict(r) for r in rows]
