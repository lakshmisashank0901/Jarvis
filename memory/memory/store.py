from __future__ import annotations

import hashlib
import math
import sqlite3
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"
RERANK_CAP = 30
EMBED_DIM = 32


@dataclass(frozen=True)
class Fact:
    id: int
    subject: str
    fact: str
    valid_from: datetime
    valid_to: datetime | None
    observed_at: datetime


def _subject_of(fact: str) -> str:
    return " ".join(fact.lower().split()[:6])


def _embed(text: str) -> bytes:
    vec: list[float] = []
    for i in range(EMBED_DIM):
        digest = hashlib.blake2b(f"{i}:{text}".encode(), digest_size=8).digest()
        vec.append((int.from_bytes(digest, "little") % 10_000) / 10_000.0)
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    vec = [x / norm for x in vec]
    return struct.pack(f"{EMBED_DIM}f", *vec)


def _cosine(a: bytes, b: bytes) -> float:
    va = struct.unpack(f"{EMBED_DIM}f", a)
    vb = struct.unpack(f"{EMBED_DIM}f", b)
    return sum(x * y for x, y in zip(va, vb, strict=True))


def _rrf(rank_lists: list[list[int]], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for i, doc_id in enumerate(ranks):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + i + 1)
    return scores


class Store:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        # fts5 content= table is optional; keep a simple fts if content sync is messy
        try:
            self.conn.executescript(schema)
        except sqlite3.OperationalError:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    observed_at TEXT NOT NULL,
                    embedding BLOB
                );
                """
            )
        self.conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(fact, subject);
            """
        )
        self.conn.commit()

    def remember(
        self,
        fact: str,
        valid_from: datetime,
        observed_at: datetime,
        subject: str | None = None,
    ) -> int:
        subj = subject or _subject_of(fact)
        self.conn.execute(
            "UPDATE facts SET valid_to = ? WHERE subject = ? AND valid_to IS NULL",
            (observed_at.isoformat(), subj),
        )
        cur = self.conn.execute(
            """
            INSERT INTO facts (subject, fact, valid_from, valid_to, observed_at, embedding)
            VALUES (?, ?, ?, NULL, ?, ?)
            """,
            (subj, fact, valid_from.isoformat(), observed_at.isoformat(), _embed(fact)),
        )
        row_id = int(cur.lastrowid)
        self.conn.execute(
            "INSERT INTO facts_fts(rowid, fact, subject) VALUES (?, ?, ?)",
            (row_id, fact, subj),
        )
        self.conn.commit()
        return row_id

    def search(self, query: str, k: int = 20) -> list[Fact]:
        rerank_k = min(max(k, 1), RERANK_CAP)
        qvec = _embed(query)
        rows = list(
            self.conn.execute(
                "SELECT id, subject, fact, valid_from, valid_to, observed_at, embedding FROM facts WHERE valid_to IS NULL"
            )
        )
        vec_ranked = [
            r["id"]
            for r in sorted(rows, key=lambda r: _cosine(r["embedding"], qvec), reverse=True)
        ]
        try:
            fts_rows = list(
                self.conn.execute(
                    "SELECT rowid AS id FROM facts_fts WHERE facts_fts MATCH ? ORDER BY rank",
                    (query,),
                )
            )
            fts_ranked = [int(r["id"]) for r in fts_rows]
        except sqlite3.OperationalError:
            fts_ranked = []
        if not fts_ranked:
            fts_ranked = [r["id"] for r in rows]
        scores = _rrf([vec_ranked, fts_ranked])
        top_ids = sorted(scores, key=lambda i: scores[i], reverse=True)[:rerank_k]
        by_id = {r["id"]: r for r in rows}
        out: list[Fact] = []
        for doc_id in top_ids:
            r = by_id.get(doc_id)
            if r is None:
                continue
            out.append(
                Fact(
                    id=r["id"],
                    subject=r["subject"],
                    fact=r["fact"],
                    valid_from=datetime.fromisoformat(r["valid_from"]),
                    valid_to=datetime.fromisoformat(r["valid_to"]) if r["valid_to"] else None,
                    observed_at=datetime.fromisoformat(r["observed_at"]),
                )
            )
        return out
