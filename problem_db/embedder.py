"""
Local embedding model wrapper for problem vectorization.
Uses sentence-transformers for local, offline embedding generation.
"""
import numpy as np
import os
from pathlib import Path
from typing import Optional

# Model choices (lightweight, good for Chinese+English)
MODELS = {
    "mini":  "paraphrase-multilingual-MiniLM-L12-v2",   # ~500MB, fast, 384d
    "bge":   "BAAI/bge-small-zh-v1.5",                  # ~100MB, fast, 512d
    "m3e":   "moka-ai/m3e-base",                         # ~400MB, good, 768d
}

DEFAULT_MODEL = "mini"


class Embedder:
    """Local embedding model wrapper."""

    def __init__(self, model_key: str = DEFAULT_MODEL, cache_dir: Optional[Path] = None):
        self.model_key = model_key
        self.model_name = MODELS.get(model_key, model_key)
        self.model = None
        self.dimension = None
        self.cache_dir = cache_dir

    def load(self):
        """Load the model (lazy loading)."""
        if self.model is not None:
            return

        print(f"📦 Loading embedding model: {self.model_name}")
        try:
            from sentence_transformers import SentenceTransformer
            restored_env = {}
            for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
                value = os.environ.get(key)
                if value:
                    try:
                        value.encode("ascii")
                    except UnicodeEncodeError:
                        restored_env[key] = value
                        os.environ.pop(key, None)
                        print(f"  ⚠ Ignoring non-ASCII {key} while loading public embedding model")
            try:
                allow_download = os.environ.get("CP_AGENT_ALLOW_MODEL_DOWNLOAD") == "1"
                self.model = SentenceTransformer(
                    self.model_name,
                    cache_folder=str(self.cache_dir) if self.cache_dir else None,
                    local_files_only=not allow_download,
                )
            finally:
                os.environ.update(restored_env)
            # Get dimension from a test encode
            test = self.model.encode(["test"])
            self.dimension = test.shape[1]
            print(f"  ✓ Model loaded (dim={self.dimension})")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Run:\n"
                "  pip install sentence-transformers\n"
                "Or for lighter install:\n"
                "  pip install sentence-transformers torch --no-deps && pip install transformers tokenizers"
            )

    def encode(self, texts: list[str], batch_size: int = 64,
               show_progress: bool = True) -> np.ndarray:
        """Encode a list of texts into vectors. Returns (N, dim) float32 array."""
        self.load()
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
        )
        return vectors.astype(np.float32)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text. Returns (dim,) float32 array."""
        self.load()
        vec = self.model.encode([text], normalize_embeddings=True)
        return vec[0].astype(np.float32)


def get_embedder(model_key: str = DEFAULT_MODEL) -> Embedder:
    """Get an embedder instance."""
    return Embedder(model_key=model_key)
