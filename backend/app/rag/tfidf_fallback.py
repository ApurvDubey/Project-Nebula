"""TF-IDF fallback retrieval.

Provides a lightweight TF-IDF-based retrieval fallback for cases where
the PageIndex tree is unavailable or still being built.
"""

from typing import Any


async def tfidf_retrieve(
    notebook_id: str, query: str, top_k: int = 5
) -> list[dict[str, Any]]:
    """Retrieve relevant passages using TF-IDF similarity as a fallback.

    TODO: Build TF-IDF index from document chunks in the notebook.
    TODO: Compute cosine similarity between query and indexed chunks.
    TODO: Return top-k matching passages with source metadata.

    Args:
        notebook_id: The notebook UUID.
        query: The user's search query.
        top_k: Number of top results to return.

    Returns:
        List of context dicts with keys: content, source_filename, score.
    """
    raise NotImplementedError("TF-IDF fallback not yet implemented")
