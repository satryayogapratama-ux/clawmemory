#!/usr/bin/env python3
"""
ClawMemory - Unlimited Semantic Memory for OpenClaw
Vector-based semantic search for unlimited memory storage with constant token cost.
"""

import json
import os
import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import hashlib

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

# Module-level model cache — load once, reuse across MemoryManager instances
_MODEL_CACHE: dict = {}

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class EmbeddingEngine:
    """Convert text to vector embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding engine with specified model. Uses module-level cache."""
        if not HAS_SENTENCE_TRANSFORMERS:
            raise ImportError("sentence-transformers required: pip install sentence-transformers")

        self.model_name = model_name
        if model_name not in _MODEL_CACHE:
            _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
        self.model = _MODEL_CACHE[model_name]

        # Handle both old and new method names for compatibility
        if hasattr(self.model, 'get_embedding_dimension'):
            self.embedding_dim = self.model.get_embedding_dimension()
        else:
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed(self, text: str) -> List[float]:
        """Convert text to embedding vector."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """Convert multiple texts to embeddings."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


class VectorStore:
    """SQLite-based vector store for memory embeddings."""
    
    def __init__(self, db_path: str):
        """Initialize vector store."""
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Create tables
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                metadata TEXT,
                embedding BLOB NOT NULL,
                embedding_dim INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        self.conn.commit()
    
    def add_memory(self, memory_id: str, text: str, embedding: List[float], 
                   metadata: Optional[Dict] = None) -> bool:
        """Add a memory with embedding to the store."""
        try:
            embedding_bytes = self._serialize_embedding(embedding)
            metadata_json = json.dumps(metadata or {})
            
            self.conn.execute("""
                INSERT OR REPLACE INTO memories 
                (id, text, metadata, embedding, embedding_dim, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (memory_id, text, metadata_json, embedding_bytes, len(embedding)))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding memory: {e}", file=sys.stderr)
            return False
    
    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Retrieve a memory by ID."""
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?", 
            (memory_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return {
            'id': row['id'],
            'text': row['text'],
            'metadata': json.loads(row['metadata']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        try:
            self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting memory: {e}", file=sys.stderr)
            return False
    
    def list_all_memories(self) -> List[Dict]:
        """List all memories (without embeddings)."""
        rows = self.conn.execute(
            "SELECT id, text, metadata, created_at, updated_at FROM memories ORDER BY created_at DESC"
        ).fetchall()
        
        return [
            {
                'id': row['id'],
                'text': row['text'],
                'metadata': json.loads(row['metadata']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            for row in rows
        ]
    
    def search_similar(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar memories using cosine similarity."""
        if not HAS_NUMPY:
            raise ImportError("numpy required for search: pip install numpy")
        
        # Get all memories with embeddings
        rows = self.conn.execute(
            "SELECT id, embedding, embedding_dim FROM memories"
        ).fetchall()
        
        if not rows:
            return []
        
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        
        if query_norm == 0:
            return []
        
        similarities = []
        for row in rows:
            embedding = self._deserialize_embedding(row['embedding'], row['embedding_dim'])
            memory_vec = np.array(embedding, dtype=np.float32)
            memory_norm = np.linalg.norm(memory_vec)
            
            if memory_norm == 0:
                similarity = 0.0
            else:
                # Cosine similarity
                similarity = float(np.dot(query_vec, memory_vec) / (query_norm * memory_norm))
            
            similarities.append((row['id'], similarity))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _serialize_embedding(self, embedding: List[float]) -> bytes:
        """Serialize embedding to bytes."""
        if not HAS_NUMPY:
            raise ImportError("numpy required: pip install numpy")
        return np.array(embedding, dtype=np.float32).tobytes()
    
    def _deserialize_embedding(self, data: bytes, dim: int) -> List[float]:
        """Deserialize embedding from bytes."""
        if not HAS_NUMPY:
            raise ImportError("numpy required: pip install numpy")
        return np.frombuffer(data, dtype=np.float32).tolist()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


class MemoryManager:
    """High-level memory management with embedding and search."""
    
    def __init__(self, db_path: str = None, embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize memory manager."""
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                "memories.db"
            )
        
        self.db_path = db_path
        self.embedding_engine = EmbeddingEngine(embedding_model)
        self.vector_store = VectorStore(db_path)
    
    def add_memory(self, text: str, metadata: Optional[Dict] = None) -> str:
        """Add a memory with automatic embedding."""
        # Generate ID from hash of text + timestamp
        timestamp = datetime.now().isoformat()
        hash_input = f"{text}{timestamp}".encode()
        memory_id = hashlib.sha256(hash_input).hexdigest()[:16]
        
        # Embed the text
        embedding = self.embedding_engine.embed(text)
        
        # Store in vector store
        self.vector_store.add_memory(memory_id, text, embedding, metadata)
        return memory_id
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant memories."""
        # Embed the query
        query_embedding = self.embedding_engine.embed(query)
        
        # Search in vector store
        results = self.vector_store.search_similar(query_embedding, top_k)
        
        # Fetch full memory data
        memories = []
        for memory_id, similarity in results:
            memory = self.vector_store.get_memory(memory_id)
            if memory:
                memory['similarity'] = round(similarity, 4)
                memories.append(memory)
        
        return memories
    
    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        return self.vector_store.delete_memory(memory_id)
    
    def list_all(self) -> List[Dict]:
        """List all stored memories."""
        return self.vector_store.list_all_memories()
    
    def get_stats(self) -> Dict:
        """Get statistics about stored memories."""
        all_memories = self.list_all()
        return {
            'total_memories': len(all_memories),
            'db_size_mb': os.path.getsize(self.db_path) / (1024 * 1024),
            'embedding_model': self.embedding_engine.model_name,
            'embedding_dim': self.embedding_engine.embedding_dim,
            'db_path': self.db_path
        }
    
    def import_from_files(self, workspace_path: str):
        """Import memories from MEMORY.md and memory/ directory."""
        workspace_path = Path(workspace_path)
        imported_count = 0
        
        # Import from MEMORY.md
        memory_file = workspace_path / "MEMORY.md"
        if memory_file.exists():
            with open(memory_file, 'r') as f:
                content = f.read()
            if content.strip():
                self.add_memory(content, {'source': 'MEMORY.md'})
                imported_count += 1
        
        # Import from memory/ directory
        memory_dir = workspace_path / "memory"
        if memory_dir.exists() and memory_dir.is_dir():
            for md_file in sorted(memory_dir.glob("*.md")):
                with open(md_file, 'r') as f:
                    content = f.read()
                if content.strip():
                    self.add_memory(content, {'source': md_file.name})
                    imported_count += 1
        
        return imported_count
    
    def close(self):
        """Close resources."""
        self.vector_store.close()


def main():
    """CLI interface."""
    parser = argparse.ArgumentParser(description="ClawMemory - Semantic Memory for OpenClaw")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Add memory
    add_parser = subparsers.add_parser('add', help='Add a memory')
    add_parser.add_argument('text', help='Memory text')
    add_parser.add_argument('--metadata', help='JSON metadata')
    
    # Search
    search_parser = subparsers.add_parser('search', help='Search memories')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--top-k', type=int, default=5, help='Number of results')
    
    # List
    subparsers.add_parser('list', help='List all memories')
    
    # Stats
    subparsers.add_parser('stats', help='Show statistics')
    
    # Delete
    delete_parser = subparsers.add_parser('delete', help='Delete a memory')
    delete_parser.add_argument('id', help='Memory ID')
    
    # Import
    import_parser = subparsers.add_parser('import-existing', help='Import existing memories')
    import_parser.add_argument('workspace_path', help='Path to OpenClaw workspace')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = MemoryManager()
    
    try:
        if args.command == 'add':
            metadata = {}
            if args.metadata:
                metadata = json.loads(args.metadata)
            memory_id = manager.add_memory(args.text, metadata)
            print(f"Memory added: {memory_id}")
        
        elif args.command == 'search':
            results = manager.search(args.query, args.top_k)
            print(json.dumps(results, indent=2))
        
        elif args.command == 'list':
            memories = manager.list_all()
            print(f"Total memories: {len(memories)}")
            for memory in memories:
                print(f"\nID: {memory['id']}")
                print(f"Text: {memory['text'][:100]}...")
                print(f"Created: {memory['created_at']}")
        
        elif args.command == 'stats':
            stats = manager.get_stats()
            print(json.dumps(stats, indent=2))
        
        elif args.command == 'delete':
            success = manager.delete(args.id)
            print(f"Memory deleted: {success}")
        
        elif args.command == 'import-existing':
            count = manager.import_from_files(args.workspace_path)
            print(f"Imported {count} memories from {args.workspace_path}")
    
    finally:
        manager.close()


if __name__ == '__main__':
    main()
