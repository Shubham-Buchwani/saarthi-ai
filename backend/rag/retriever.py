"""
FAISS-based retriever for Saarthi AI.
Loads the pre-built index and metadata, then does semantic search + re-ranking.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
INDEX_PATH = DATA_DIR / "gita_index.faiss"
METADATA_PATH = DATA_DIR / "gita_metadata.json"

_index = None
_metadata: list[dict] = []
_embeddings_cache: dict[str, list[float]] = {}

def load_index() -> None:
    """Load the FAISS index and metadata into memory. Call once at startup."""
    global _index, _metadata

    if not METADATA_PATH.exists():
        logger.warning(
            "gita_metadata.json not found. Run 'python scripts/build_index.py' first."
        )
        _metadata = []
        return

    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        _metadata = json.load(f)

    if INDEX_PATH.exists():
        try:
            import faiss
            _index = faiss.read_index(str(INDEX_PATH))
            logger.info(f"FAISS index loaded: {_index.ntotal} vectors")
        except ImportError:
            logger.warning("faiss-cpu not installed. Falling back to numpy search.")
            _index = None
    else:
        logger.warning("gita_index.faiss not found. Falling back to metadata-only search.")
        _index = None

    logger.info(f"Metadata loaded: {len(_metadata)} chunks")

def get_embedding(text: str, embed_client, model: str) -> list[float]:
    """Get embedding for a text string, with simple caching."""
    if text in _embeddings_cache:
        return _embeddings_cache[text]

    result = embed_client.models.embed_content(
        model=model,
        contents=text,
    )
    embedding = result.embeddings[0].values
    _embeddings_cache[text] = embedding
    return embedding

def _numpy_search(query_vec: list[float], top_k: int) -> list[tuple[int, float]]:
    """Fallback search using numpy cosine similarity when FAISS isn't available."""
    if not _metadata:
        return []

    emb_path = DATA_DIR / "embeddings.npy"
    if not emb_path.exists():
        logger.warning("embeddings.npy not found. Returning first chunks as fallback.")
        return [(i, 0.5) for i in range(min(top_k, len(_metadata)))]

    stored = np.load(str(emb_path)).astype("float32")
    q = np.array(query_vec, dtype="float32")

    norms = np.linalg.norm(stored, axis=1, keepdims=True)
    norms[norms == 0] = 1e-8
    stored_normalized = stored / norms
    q_norm = q / (np.linalg.norm(q) + 1e-8)
    scores = stored_normalized @ q_norm

    top_indices = np.argsort(scores)[::-1][:top_k]
    return [(int(idx), float(scores[idx])) for idx in top_indices]

def retrieve(
    query: str,
    embed_client,
    embed_model: str,
    top_k: int = 5,
    min_score: float = 0.25,
    emotion_filter: Optional[list[str]] = None,
) -> list[dict]:
    """
    Retrieve the most relevant Gita chunks for a user query.

    Args:
        query: User's message
        embed_client: Google GenAI client for embeddings
        embed_model: Embedding model name
        top_k: Number of candidates to retrieve before re-ranking
        min_score: Minimum similarity score threshold
        emotion_filter: Optional list of emotions to pre-filter by

    Returns:
        List of top-3 most relevant enriched chunk dicts
    """
    if not _metadata:
        logger.warning("No metadata loaded. Returning empty results.")
        return []

    query_vec = get_embedding(query, embed_client, embed_model)
    results: list[tuple[int, float]] = []
    if _index is not None:

        import faiss
        q_arr = np.array([query_vec], dtype="float32")
        faiss.normalize_L2(q_arr)
        scores_arr, indices_arr = _index.search(q_arr, top_k)
        results = [
            (int(idx), float(score))
            for idx, score in zip(indices_arr[0], scores_arr[0])
            if idx >= 0 and score >= min_score
        ]
    else:
        results = _numpy_search(query_vec, top_k)
        results = [(idx, score) for idx, score in results if score >= min_score]

    if not results:
        import random
        fallback = random.sample(_metadata, min(3, len(_metadata)))
        return fallback

    if emotion_filter:
        filtered = []
        for idx, score in results:
            chunk = _metadata[idx]
            chunk_emotions = chunk.get("emotions", [])
            if any(e in chunk_emotions for e in emotion_filter):
                filtered.append((idx, score + 0.05))  # boost filtered results
            else:
                filtered.append((idx, score))
        results = sorted(filtered, key=lambda x: x[1], reverse=True)

    from typing import cast
    import random

    candidates = sorted(results, key=lambda x: x[1], reverse=True)[:max(top_k, 12)]

    top_chunks = []
    seen_chapters = set()

    if candidates:
        idx_0, score_0 = candidates[0]
        chunk_0 = _metadata[idx_0].copy()
        chunk_0["_score"] = score_0
        top_chunks.append(chunk_0)
        seen_chapters.add(chunk_0.get("chapter", 0))

        remaining = candidates[1:]
        random.shuffle(remaining)

        for idx, score in remaining:
            if len(top_chunks) >= 3:
                break

            chunk = _metadata[idx].copy()
            chunk["_score"] = score
            ch = chunk.get("chapter", 0)

            if ch in seen_chapters and len(top_chunks) < 2:
                continue

            seen_chapters.add(ch)
            top_chunks.append(chunk)

    return top_chunks

def retrieve_with_vector(
    query_vec: list[float],
    top_k: int = 5,
    min_score: float = 0.25,
) -> list[dict]:
    """
    Retrieve chunks using a pre-computed embedding vector.
    Used by SaarthiChain which manages its own embedding call.
    """
    if not _metadata:
        return []

    if _index is not None:
        import faiss
        q_arr = np.array([query_vec], dtype="float32")
        faiss.normalize_L2(q_arr)
        scores_arr, indices_arr = _index.search(q_arr, top_k)
        results = [
            (int(idx), float(score))
            for idx, score in zip(indices_arr[0], scores_arr[0])
            if idx >= 0 and score >= min_score
        ]
    else:
        results = _numpy_search(query_vec, top_k)
        results = [(idx, score) for idx, score in results if score >= min_score]

    import random
    candidates = sorted(results, key=lambda x: x[1], reverse=True)[:max(top_k, 12)]

    top_chunks = []
    seen_chapters = set()

    if candidates:
        idx_0, score_0 = candidates[0]
        if idx_0 < len(_metadata):
            chunk_0 = _metadata[idx_0].copy()
            chunk_0["_score"] = score_0
            top_chunks.append(chunk_0)
            seen_chapters.add(chunk_0.get("chapter", 0))

        remaining = candidates[1:]
        random.shuffle(remaining)

        for idx, score in remaining:
            if len(top_chunks) >= 3:
                break
            if idx >= len(_metadata):
                continue

            chunk = _metadata[idx].copy()
            chunk["_score"] = score
            ch = chunk.get("chapter", 0)

            if ch in seen_chapters and len(top_chunks) < 2:
                continue

            seen_chapters.add(ch)
            top_chunks.append(chunk)

    return top_chunks

def get_random_chunk_by_theme(theme: str) -> Optional[dict]:
    """Get a random chunk matching a theme — used for daily wisdom."""
    import random
    matching = [c for c in _metadata if theme in c.get("themes", [])]
    if matching:
        return random.choice(matching)
    return random.choice(_metadata) if _metadata else None
