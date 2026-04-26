# ClawMemory Skill

**Semantic memory management for OpenClaw.** Store unlimited memories with vector-based search — retrieve only the most relevant ones per conversation.

## Concept

OpenClaw's default memory is file-based (MEMORY.md, memory/*.md) and loads entirely into context (token cost grows with memory size). ClawMemory replaces this:

- **Unlimited storage**: Add memories without token cost
- **Semantic search**: Find relevant memories by meaning, not keywords
- **Constant overhead**: Always retrieve only top-K relevant memories (e.g., 5)
- **Local & offline**: SQLite + sentence-transformers, no external API

## Commands

### `memory search [query]`

Search for memories relevant to a query.

```bash
openclaw memory search "What projects has the user worked on?"
```

Returns top-5 most relevant memories with similarity scores.

### `memory add [text]`

Manually add a memory.

```bash
openclaw memory add "Completed the dashboard redesign project"
```

### `memory list`

List all stored memories (without embeddings).

```bash
openclaw memory list
```

Shows count, creation dates, and first 100 chars of each memory.

### `memory stats`

Show system statistics.

```bash
openclaw memory stats
```

Displays: total memories, database size, embedding model, token efficiency.

### `memory import [workspace-path]`

Import existing memories from MEMORY.md and memory/ directory.

```bash
openclaw memory import /root/.openclaw/workspace
```

## Installation

```bash
cd ~/.openclaw/workspace/clawmemory
pip install sentence-transformers numpy
python clawmemory.py import-existing /root/.openclaw/workspace
```

Or use the installer:

```bash
bash install.sh
```

## Integration with Main Agent

To use ClawMemory in your main agent loop:

1. **During context building**: Instead of loading all of MEMORY.md, query ClawMemory:
   ```python
   from openclaw_bridge import OpenClawBridge
   bridge = OpenClawBridge()
   relevant = bridge.search_relevant_memories(current_context, top_k=5)
   memory_injection = bridge.format_memories_for_prompt(relevant)
   ```

2. **Add new memories**: When the agent learns something important:
   ```python
   bridge.add_memory_from_event(
       "User loves Python and automation",
       event_type="learning"
   )
   ```

3. **Inject into system prompt**:
   ```
   Base system prompt + memory_injection + conversation
   ```

## How It Works

### Architecture

```
User Conversation
       ↓
   ClawMemory
   ├─ EmbeddingEngine (sentence-transformers)
   ├─ VectorStore (SQLite)
   └─ MemoryManager (search, add, delete)
       ↓
  Semantic Search (cosine similarity)
       ↓
 Top-K Relevant Memories
       ↓
System Prompt Injection
```

### Token Efficiency

**Without ClawMemory (current):**
- MEMORY.md grows to 5000 tokens
- Every conversation loads all 5000 tokens
- Cost: 5000 tokens * N conversations = 5000N tokens

**With ClawMemory:**
- 100 memories stored (can grow indefinitely)
- Each search retrieves top-5 relevant (~200 tokens)
- Cost: 200 tokens * N conversations = 200N tokens
- **25x more efficient, unlimited scaling**

### Search Quality

ClawMemory uses sentence-level embeddings (all-MiniLM-L6-v2):
- Fast: 6MB model, runs on-device
- Accurate: trained on semantic similarity
- Example:
  - Query: "What am I building?"
  - Results: memories about current projects (even if worded differently)

## Files

- `clawmemory.py` - Core engine
- `openclaw_bridge.py` - OpenClaw integration
- `demo.py` - Working example
- `install.sh` - One-command setup
- `README.md` - Full documentation

## Next Steps

1. Run `python demo.py` to see it in action
2. Import your existing memories: `python clawmemory.py import-existing /root/.openclaw/workspace`
3. Test search: `python clawmemory.py search "your query"`
4. Integrate with main agent (see Integration section above)
