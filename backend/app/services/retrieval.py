from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SrdChunk
from app.services.llm import EmbeddingProvider


async def retrieve_srd_chunks(
    db: AsyncSession,
    embeddings: EmbeddingProvider,
    query: str,
    *,
    limit: int,
) -> list[SrdChunk]:
    query = query.strip()
    if not query:
        return []

    vectors = await embeddings.embed([query])
    if not vectors:
        return []

    distance = SrdChunk.embedding.cosine_distance(vectors[0])
    result = await db.scalars(
        select(SrdChunk).order_by(distance, SrdChunk.id).limit(limit)
    )
    return list(result)


def source_payload(chunk: SrdChunk) -> dict[str, str]:
    excerpt = chunk.content.strip()
    if len(excerpt) > 400:
        excerpt = excerpt[:397].rstrip() + "..."
    return {
        "id": str(chunk.id),
        "source": chunk.source,
        "section": chunk.section,
        "title": chunk.title,
        "license": chunk.license,
        "excerpt": excerpt,
    }
