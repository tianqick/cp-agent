"""
FAISS index for problem vector similarity search.
"""
import json
import sqlite3
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None


class ProblemIndex:
    """FAISS index + SQLite metadata for problem search."""

    def __init__(self, db_path: Path, index_path: Path):
        self.db_path = db_path
        self.index_path = index_path
        self.index: Optional[faiss.Index] = None
        self.id_map: list[int] = []  # FAISS row -> problem DB id
        self.dimension: int = 0
        self.metadata: dict = {}

    def build(self, vectors: np.ndarray, problem_ids: list[int]):
        """
        Build FAISS index from vectors and corresponding problem IDs.
        vectors: (N, dim) float32, L2-normalized
        problem_ids: list of problem DB ids, same order as vectors
        """
        if faiss is None:
            raise ImportError("faiss not installed. Run: pip install faiss-cpu")

        self.dimension = vectors.shape[1]
        self.id_map = problem_ids

        # Use Inner Product (cosine similarity for normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(vectors)

        print(f"  ✓ FAISS index built: {self.index.ntotal} vectors, dim={self.dimension}")

    def save(self, metadata: Optional[dict] = None):
        """Save index and id map to disk."""
        if self.index is None:
            raise ValueError("Index not built yet")

        faiss.write_index(self.index, str(self.index_path))

        # Save id map
        map_path = self.index_path.with_suffix(".map.json")
        map_path.write_text(json.dumps(self.id_map))

        self.metadata = {
            "dimension": self.dimension,
            "ntotal": int(self.index.ntotal),
            **(metadata or {}),
        }
        meta_path = self.index_path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(self.metadata, ensure_ascii=False, indent=2))

        print(f"  ✓ Index saved: {self.index_path}")

    def load(self):
        """Load index and id map from disk."""
        if faiss is None:
            raise ImportError("faiss not installed. Run: pip install faiss-cpu")

        if not self.index_path.exists():
            raise FileNotFoundError(f"Index file not found: {self.index_path}")

        self.index = faiss.read_index(str(self.index_path))
        self.dimension = self.index.d

        map_path = self.index_path.with_suffix(".map.json")
        if map_path.exists():
            self.id_map = json.loads(map_path.read_text())
        else:
            self.id_map = list(range(self.index.ntotal))

        meta_path = self.index_path.with_suffix(".meta.json")
        if meta_path.exists():
            self.metadata = json.loads(meta_path.read_text())
        else:
            self.metadata = {}

        print(f"  ✓ Index loaded: {self.index.ntotal} vectors, dim={self.dimension}")

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> list[dict]:
        """
        Search for similar problems.
        query_vector: (dim,) float32, L2-normalized
        Returns: list of {problem_id, score, rank}
        """
        if self.index is None:
            self.load()

        if query_vector.shape[0] != self.dimension:
            model_hint = self.metadata.get("model_key") or self.metadata.get("model_name") or "unknown"
            raise ValueError(
                f"Query vector dim {query_vector.shape[0]} does not match "
                f"FAISS index dim {self.dimension}. Index model: {model_hint}. "
                "Rebuild the index with the same model used for search."
            )

        query = query_vector.reshape(1, -1).astype(np.float32)
        scores, indices = self.index.search(query, top_k)

        results = []
        for rank, (idx, score) in enumerate(zip(indices[0], scores[0])):
            if idx < 0 or idx >= len(self.id_map):
                continue
            results.append({
                "problem_db_id": self.id_map[idx],
                "score": float(score),
                "rank": rank + 1,
            })

        return results

    def get_problem_by_id(self, db_id: int) -> Optional[dict]:
        """Fetch problem metadata from SQLite by DB id."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM problems WHERE id = ?", (db_id,)
        ).fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def search_and_resolve(self, query_vector: np.ndarray,
                           top_k: int = 10) -> list[dict]:
        """Search and return full problem details."""
        results = self.search(query_vector, top_k)
        for r in results:
            problem = self.get_problem_by_id(r["problem_db_id"])
            if problem:
                r.update(problem)
        return results
