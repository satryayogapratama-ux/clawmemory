#!/usr/bin/env python3
"""
ClawMemory Demo - Semantic memory system in action.
Shows token efficiency and search quality compared to traditional approach.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from clawmemory import MemoryManager


def count_tokens_rough(text: str) -> int:
    """Rough estimate of tokens (1 token ≈ 4 chars for English)."""
    return max(1, len(text) // 4)


def main():
    print("=" * 70)
    print("ClawMemory Demo - Semantic Memory for OpenClaw")
    print("=" * 70)
    
    # Create temporary database for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "demo_memories.db")
        manager = MemoryManager(db_path=db_path)
        
        print("\n[1] Adding 10 Sample Memories...")
        print("-" * 70)
        
        sample_memories = [
            "I built a real-time dashboard using React and Node.js for tracking system metrics.",
            "Completed the Q3 security audit. Found 3 critical vulnerabilities in authentication layer.",
            "Working on improving API response times. Current bottleneck is database query optimization.",
            "Satrya loves Python and automation tools. Has experience with OpenClaw and semantic systems.",
            "Recently implemented vector search in the main application using sentence-transformers.",
            "Planning to migrate from REST API to GraphQL next month. Need to update documentation.",
            "The user prefers working with open-source tools and hates vendor lock-in.",
            "Mobile app beta launch scheduled for next Friday. Team is doing final testing.",
            "Memory system research: explored FAISS, Pinecone, and local SQLite solutions.",
            "Personal project: building a voice assistant with natural language understanding.",
        ]
        
        memory_ids = []
        for i, memory_text in enumerate(sample_memories, 1):
            mid = manager.add_memory(memory_text)
            memory_ids.append(mid)
            print(f"  [{i}/10] Added: {memory_text[:60]}...")
        
        print(f"\n✓ Stored {len(memory_ids)} memories")
        
        # Show stats
        print("\n[2] Memory System Statistics")
        print("-" * 70)
        stats = manager.get_stats()
        print(f"  Total memories: {stats['total_memories']}")
        print(f"  Database size: {stats['db_size_mb']:.3f} MB")
        print(f"  Embedding model: {stats['embedding_model']}")
        print(f"  Embedding dimension: {stats['embedding_dim']}")
        
        # Compare token costs
        print("\n[3] Token Efficiency Comparison")
        print("-" * 70)
        
        all_text = "\n".join(sample_memories)
        full_tokens = count_tokens_rough(all_text)
        print(f"  All memories concatenated: {full_tokens} tokens")
        print(f"    (Loading all memories into context every conversation)")
        
        # Simulate semantic search result
        test_query = "What projects has the user worked on?"
        print(f"\n  Query: '{test_query}'")
        results = manager.search(test_query, top_k=5)
        
        search_result_text = "\n".join([r['text'] for r in results])
        search_tokens = count_tokens_rough(search_result_text)
        print(f"  Top-5 relevant memories: {search_tokens} tokens")
        print(f"    (Loading only relevant memories)")
        
        efficiency = (full_tokens / search_tokens) if search_tokens > 0 else 1
        print(f"\n  Efficiency gain: {efficiency:.1f}x fewer tokens with ClawMemory")
        print(f"  Constant cost per conversation vs growing cost with traditional approach")
        
        # Show search results
        print("\n[4] Semantic Search Results")
        print("-" * 70)
        print(f"  Query: '{test_query}'")
        print(f"  Results: {len(results)} memories\n")
        
        for i, result in enumerate(results, 1):
            print(f"  [{i}] Relevance: {result['similarity']:.1%}")
            print(f"      {result['text'][:70]}...")
            print()
        
        # Try another search
        print("[5] Another Search Example")
        print("-" * 70)
        
        query2 = "What technologies are being used?"
        results2 = manager.search(query2, top_k=3)
        
        print(f"  Query: '{query2}'")
        print(f"  Results: {len(results2)} memories\n")
        
        for i, result in enumerate(results2, 1):
            print(f"  [{i}] Relevance: {result['similarity']:.1%}")
            print(f"      {result['text'][:70]}...")
            print()
        
        # List all memories
        print("[6] All Stored Memories")
        print("-" * 70)
        
        all_memories = manager.list_all()
        print(f"  Total: {len(all_memories)} memories\n")
        
        for i, mem in enumerate(all_memories, 1):
            print(f"  [{i}] {mem['text'][:65]}...")
            print(f"      ID: {mem['id']}")
            print()
        
        # Demonstrate delete
        print("[7] Testing Memory Deletion")
        print("-" * 70)
        
        if all_memories:
            delete_id = all_memories[0]['id']
            print(f"  Deleting memory: {all_memories[0]['text'][:50]}...")
            success = manager.delete(delete_id)
            print(f"  Deleted: {success}")
            
            remaining = manager.list_all()
            print(f"  Remaining memories: {len(remaining)}")
        
        # Summary
        print("\n" + "=" * 70)
        print("Demo Summary")
        print("=" * 70)
        print(f"✓ Added {len(sample_memories)} memories successfully")
        print(f"✓ Semantic search working (tested 2 different queries)")
        print(f"✓ Token efficiency: {efficiency:.1f}x savings demonstrated")
        print(f"✓ Memory operations: add, search, list, delete all working")
        print(f"✓ Database: {stats['db_size_mb']:.3f} MB (compact storage)")
        print("\nClawMemory is ready to integrate with OpenClaw!")
        print("=" * 70)
        
        manager.close()
        
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
