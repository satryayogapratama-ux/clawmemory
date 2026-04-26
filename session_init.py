#!/usr/bin/env python3
"""
ClawMemory Session Init — runs at every OpenClaw session start.
Replaces reading MEMORY.md. Returns relevant memories in one shot.
Usage: python3 session_init.py ["<first user message>"]
"""

import hashlib
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from clawmemory import MemoryManager, EmbeddingEngine

DB_PATH = str(Path(__file__).parent / "memories.db")
TOP_K_RECENT = 5   # recency-based (no semantic query needed)
TOP_K_TOPIC  = 5   # semantic match on user message
MIN_SCORE    = 0.28  # tuned for all-MiniLM-L6-v2 (0.25 too permissive)
MAX_TOKENS   = 800   # hard token budget for output (rough: 4 chars ≈ 1 token)
MAX_CHARS    = MAX_TOKENS * 4

# Prompt injection patterns — strip from retrieved memories
INJECTION_RE = re.compile(
    r'<\s*/?\s*(system|human|assistant)\s*>|'
    r'ignore\s+(all\s+)?previous\s+instructions?|'
    r'disregard\s+(all\s+)?previous\s+instructions?|'
    r'\[\s*INST\s*\]|###\s*System',
    re.IGNORECASE
)

def normalize(text: str) -> str:
    """Normalize for dedup: lowercase, collapse whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())

def sanitize(text: str) -> str:
    return INJECTION_RE.sub('[filtered]', text)

def truncate_to_budget(results: list, max_chars: int) -> list:
    """Trim results to fit within token budget."""
    out, used = [], 0
    for r in results:
        chunk = r["text"][:400]  # per-entry cap
        if used + len(chunk) > max_chars:
            break
        out.append({**r, "text": chunk})
        used += len(chunk)
    return out

def get_recent_memories(conn, n: int) -> list:
    """Recency-based: fetch N most recently added memories."""
    rows = conn.execute(
        "SELECT id, text, created_at FROM memories ORDER BY created_at DESC LIMIT ?", (n,)
    ).fetchall()
    return [{"id": r[0], "text": sanitize(r[1]), "created_at": r[2], "label": "recent", "score": None}
            for r in rows]

def get_topic_memories(manager: MemoryManager, query: str, n: int) -> list:
    """Semantic search for user's topic."""
    if not query or len(query.strip()) < 4:
        return []
    results = manager.search(query.strip(), top_k=n)
    out = []
    for r in results:
        score = r.get("similarity", 0)
        if score < MIN_SCORE:
            continue
        out.append({
            "id": r["id"],
            "text": sanitize(r["text"]),
            "label": "topic",
            "score": round(score, 3),
        })
    return out

def main():
    user_query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""

    try:
        conn = sqlite3.connect(DB_PATH)
        manager = MemoryManager(db_path=DB_PATH)
    except Exception as e:
        print(f"[ClawMemory] DB unavailable: {e}", file=sys.stderr)
        sys.exit(0)  # Degrade gracefully — don't break session

    results = []
    seen = set()

    def add_unique(items):
        for item in items:
            key = hashlib.md5(normalize(item["text"]).encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                results.append(item)

    # 1. Recency-based (always runs — gives "what's been happening" context)
    add_unique(get_recent_memories(conn, TOP_K_RECENT))

    # 2. Semantic topic search (if user said something meaningful)
    add_unique(get_topic_memories(manager, user_query, TOP_K_TOPIC))

    conn.close()
    manager.close()

    # Enforce hard token budget
    results = truncate_to_budget(results, MAX_CHARS)

    if not results:
        print("[ClawMemory] No memories loaded — starting fresh.")
        return

    print("## Context from ClawMemory\n")
    for i, r in enumerate(results, 1):
        score_str = f" | score {r['score']}" if r["score"] is not None else " | most recent"
        print(f"**[{i}]** _{r['label']}{score_str}_")
        print(r["text"])
        print()

if __name__ == "__main__":
    main()
