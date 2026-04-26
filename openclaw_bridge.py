#!/usr/bin/env python3
"""
OpenClaw Bridge - Integration layer for ClawMemory with OpenClaw system.
Provides hooks to search memories and inject results into system prompt.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from clawmemory import MemoryManager


class OpenClawBridge:
    """Bridge between ClawMemory and OpenClaw system."""
    
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace",
                 db_path: Optional[str] = None):
        """Initialize bridge with OpenClaw workspace."""
        self.workspace_path = Path(workspace_path)
        
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                "memories.db"
            )
        
        self.manager = MemoryManager(db_path=db_path)
        self._last_import_hash = None
    
    def sync_workspace_memories(self) -> int:
        """Detect and import new memories from workspace."""
        # Check MEMORY.md and memory/ directory for changes
        new_count = 0
        
        memory_file = self.workspace_path / "MEMORY.md"
        if memory_file.exists():
            with open(memory_file, 'r') as f:
                content = f.read()
            # Simple heuristic: if file was modified and not yet imported
            if content.strip():
                # In a real implementation, track modification times
                pass
        
        return new_count
    
    def search_relevant_memories(self, conversation_context: str, 
                                top_k: int = 5) -> List[Dict]:
        """
        Search for memories relevant to current conversation context.
        Returns memories formatted for injection into system prompt.
        """
        results = self.manager.search(conversation_context, top_k=top_k)
        return results
    
    def format_memories_for_prompt(self, memories: List[Dict]) -> str:
        """
        Format search results into a system prompt injection.
        Ready to include in OpenClaw system message.
        """
        if not memories:
            return ""
        
        lines = ["## Relevant Memories (from ClawMemory)\n"]
        for i, memory in enumerate(memories, 1):
            lines.append(f"### Memory {i} (relevance: {memory.get('similarity', 0):.2%})")
            lines.append(memory['text'][:500])  # Truncate long memories
            if len(memory['text']) > 500:
                lines.append("... [truncated]")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_memory_stats(self) -> Dict:
        """Get statistics about the memory system."""
        return self.manager.get_stats()
    
    def add_memory_from_event(self, text: str, event_type: str, **kwargs) -> str:
        """Add a memory from an OpenClaw event (conversation, learning, etc)."""
        metadata = {
            'event_type': event_type,
            'source': 'openclaw_event',
            **kwargs
        }
        return self.manager.add_memory(text, metadata)
    
    def close(self):
        """Close resources."""
        self.manager.close()


def inject_memories_into_context(conversation_history: str, 
                                workspace_path: str = "/root/.openclaw/workspace",
                                top_k: int = 5) -> str:
    """
    Utility function: given conversation context, return system prompt injection
    with relevant memories.
    
    Usage:
        memory_injection = inject_memories_into_context(current_conversation)
        system_prompt = base_system_prompt + memory_injection
    """
    bridge = OpenClawBridge(workspace_path)
    try:
        memories = bridge.search_relevant_memories(conversation_history, top_k)
        return bridge.format_memories_for_prompt(memories)
    finally:
        bridge.close()


if __name__ == '__main__':
    # Demo: search memories based on current context
    bridge = OpenClawBridge()
    
    test_query = "What am I working on right now?"
    results = bridge.search_relevant_memories(test_query, top_k=3)
    
    print("Search Results:")
    print(json.dumps(results, indent=2))
    
    print("\nFormatted for Prompt:")
    print(bridge.format_memories_for_prompt(results))
    
    print("\nStatistics:")
    print(json.dumps(bridge.get_memory_stats(), indent=2))
    
    bridge.close()
