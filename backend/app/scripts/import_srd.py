from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import SrdChunk
from app.services.llm import get_embedding_provider

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
MAX_CHUNK_CHARS = 1600
MIN_CHUNK_CHARS = 200
EMBED_BATCH_SIZE = 32


@dataclass(frozen=True)
class ParsedChunk:
    source: str
    section: str
    title: str
    content: str
    license: str
    metadata: dict[str, Any]

    @property
    def chunk_key(self) -> str:
        raw = f"{self.source}|{self.section}|{self.content}".encode()
        return hashlib.sha256(raw).hexdigest()


def _split_long_text(text: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text)]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > limit:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(paragraph), limit):
                chunks.append(paragraph[start : start + limit].strip())
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > limit:
            chunks.append(current.strip())
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def _parse_markdown(
    text: str,
    *,
    source: str,
    license: str,
    metadata: dict[str, Any],
) -> list[ParsedChunk]:
    sections: list[tuple[str, str, list[str]]] = []
    stack: list[tuple[int, str]] = []
    current_title = "Введение"
    current_path: list[str] = []
    current_lines: list[str] = []

    def flush() -> None:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append((current_title, " / ".join(current_path) or current_title, [content]))

    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = match.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading))
            current_title = heading
            current_path = [item[1] for item in stack]
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    chunks: list[ParsedChunk] = []
    for title, path, contents in sections:
        for content in _split_long_text("\n".join(contents)):
            if (
                len(content) < MIN_CHUNK_CHARS
                and chunks
                and chunks[-1].section == path
            ):
                previous = chunks[-1]
                merged_content = f"{previous.content}\n\n{content}"
                if len(merged_content) <= MAX_CHUNK_CHARS:
                    chunks[-1] = ParsedChunk(
                        source=previous.source,
                        section=previous.section,
                        title=previous.title,
                        content=merged_content,
                        license=previous.license,
                        metadata=previous.metadata,
                    )
                    continue
            chunks.append(
                ParsedChunk(
                    source=source,
                    section=path,
                    title=title,
                    content=content,
                    license=license,
                    metadata={**metadata, "heading_path": path.split(" / ")},
                )
            )
    return chunks


def _parse_jsonl(
    text: str,
    *,
    source: str,
    license: str,
    metadata: dict[str, Any],
) -> list[ParsedChunk]:
    chunks: list[ParsedChunk] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Некорректный JSON в строке {line_number}") from exc
        content = str(row.get("content", "")).strip()
        if not content:
            continue
        row_source = str(row.get("source", source))
        section = str(row.get("section", row.get("title", "Раздел")))
        title = str(row.get("title", section))
        chunks.append(
            ParsedChunk(
                source=row_source,
                section=section,
                title=title,
                content=content,
                license=str(row.get("license", license)),
                metadata={**metadata, **row.get("metadata", {})},
            )
        )
    return chunks


def parse_corpus(
    path: Path,
    *,
    source: str,
    license: str,
    source_url: str,
) -> list[ParsedChunk]:
    text = path.read_text(encoding="utf-8")
    metadata = {"source_url": source_url, "license": license, "file": path.name}
    if path.suffix.lower() == ".jsonl":
        return _parse_jsonl(text, source=source, license=license, metadata=metadata)
    return _parse_markdown(text, source=source, license=license, metadata=metadata)


def _batches(items: list[ParsedChunk], size: int) -> Iterable[list[ParsedChunk]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def import_corpus(
    chunks: list[ParsedChunk],
    *,
    batch_size: int = EMBED_BATCH_SIZE,
) -> tuple[int, int]:
    created = 0
    skipped = 0
    embeddings = get_embedding_provider()

    async with SessionLocal() as db:
        keys = [chunk.chunk_key for chunk in chunks]
        existing: set[str] = set()
        for start in range(0, len(keys), 500):
            result = await db.scalars(
                select(SrdChunk.chunk_key).where(
                    SrdChunk.chunk_key.in_(keys[start : start + 500])
                )
            )
            existing.update(result)

        pending = [chunk for chunk in chunks if chunk.chunk_key not in existing]
        skipped = len(chunks) - len(pending)

        for batch in _batches(pending, batch_size):
            vectors = await embeddings.embed([chunk.content for chunk in batch])
            for chunk, vector in zip(batch, vectors, strict=True):
                db.add(
                    SrdChunk(
                        chunk_key=chunk.chunk_key,
                        source=chunk.source,
                        section=chunk.section,
                        title=chunk.title,
                        content=chunk.content,
                        embedding=vector,
                        license=chunk.license,
                        chunk_metadata=chunk.metadata,
                    )
                )
            await db.commit()
            created += len(batch)
            print(f"Импортировано: {created}, пропущено: {skipped}")

    return created, skipped


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Идемпотентно импортирует SRD-корпус в PostgreSQL/pgvector."
    )
    parser.add_argument("path", type=Path, help="Путь к .md, .txt или .jsonl файлу")
    parser.add_argument("--source", default="SRD 5.2.1", help="Название источника")
    parser.add_argument(
        "--license", default="CC BY 4.0", help="Лицензия корпуса"
    )
    parser.add_argument(
        "--source-url",
        default="https://www.dndbeyond.com/srd",
        help="Публичный URL источника",
    )
    parser.add_argument("--batch-size", type=int, default=EMBED_BATCH_SIZE)
    return parser


async def _main() -> None:
    args = _build_parser().parse_args()
    if not args.path.exists():
        raise SystemExit(f"Файл не найден: {args.path}")
    chunks = parse_corpus(
        args.path,
        source=args.source,
        license=args.license,
        source_url=args.source_url,
    )
    if not chunks:
        raise SystemExit("В корпусе не найдено текстовых фрагментов")
    print(f"Найдено фрагментов: {len(chunks)}")
    created, skipped = await import_corpus(chunks, batch_size=args.batch_size)
    print(f"Готово. Создано: {created}, уже существовало: {skipped}")


if __name__ == "__main__":
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(_main(), loop_factory=loop_factory)
