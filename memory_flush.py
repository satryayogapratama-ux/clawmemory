#!/usr/bin/env python3
"""
memory_flush.py — Idempotent auto-flush from daily memory files to ClawMemory.
Tracks file checksum to skip unchanged files. Logs to flush_audit.log.
Run via cron every 6h.
"""

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from clawmemory import MemoryManager

WORKSPACE = Path("/root/.openclaw/workspace")
DB_PATH   = str(Path(__file__).parent / "memories.db")
STATE_FILE = Path(__file__).parent / "flush_state.json"
LOG_FILE  = Path(__file__).parent / "flush_audit.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)


def file_checksum(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_daily_files() -> list[Path]:
    memory_dir = WORKSPACE / "memory"
    if not memory_dir.exists():
        return []
    return sorted(memory_dir.glob("*.md"))[-7:]  # last 7 days only


def extract_key_facts(content: str) -> list[str]:
    """Split daily file into meaningful chunks — one per ## section."""
    facts = []
    current = []
    for line in content.splitlines():
        if line.startswith("## ") and current:
            chunk = "\n".join(current).strip()
            if len(chunk) > 80:  # skip tiny sections
                facts.append(chunk[:600])
            current = [line]
        else:
            current.append(line)
    if current:
        chunk = "\n".join(current).strip()
        if len(chunk) > 80:
            facts.append(chunk[:600])
    return facts


def main():
    state = load_state()
    manager = MemoryManager(db_path=DB_PATH)
    total_added = 0
    files_processed = 0

    for f in get_daily_files():
        checksum = file_checksum(f)
        if state.get(str(f)) == checksum:
            log.info("SKIP (unchanged): %s", f.name)
            continue

        log.info("PROCESSING: %s", f.name)
        content = f.read_text(encoding="utf-8")
        facts = extract_key_facts(content)

        added = 0
        for fact in facts:
            try:
                manager.add_memory(fact, metadata={"source": f.name, "flushed_at": datetime.now(timezone.utc).isoformat()})
                added += 1
            except Exception as e:
                log.error("Failed to add memory from %s: %s", f.name, e)

        state[str(f)] = checksum
        total_added += added
        files_processed += 1
        log.info("DONE: %s — %d facts added", f.name, added)

    save_state(state)
    manager.close()

    log.info("FLUSH COMPLETE: %d files, %d memories added", files_processed, total_added)
    print(f"✅ Flushed {files_processed} files, {total_added} memories added")


if __name__ == "__main__":
    main()
