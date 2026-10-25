"""Framework-Aware, Tier-Filtered Regulatory Retrieval Engine.
Traceability: REQ-4.6, REQ-5.2
"""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from services.common.models import RegChunk
from services.rag.indexer import EmbeddingManager, cosine_similarity

DISCLAIMER = "Decision-support information only; not legal advice."


class RegulatoryRetriever:
    """Retrieves relevant statutory obligations filtered by framework and risk tier."""

    def __init__(self, embedder: Optional[EmbeddingManager] = None):
        self.embedder = embedder or EmbeddingManager()

    def retrieve(
        self,
        db: Session,
        query: str,
        tier: str = "high",
        frameworks: Optional[List[str]] = None,
        instrument: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve obligation chunks matching tier and framework filters.
        Traceability: REQ-4.6, REQ-5.2
        """
        active_frameworks = frameworks or ["india"]
        tier_clean = tier.lower()

        # Query all active chunks from DB
        sql_query = db.query(RegChunk)
        if instrument:
            sql_query = sql_query.filter(RegChunk.instrument.ilike(f"%{instrument}%"))

        candidates = sql_query.all()
        filtered_candidates: List[RegChunk] = []

        for chunk in candidates:
            chunk_frameworks = chunk.frameworks if isinstance(chunk.frameworks, list) else []
            chunk_tiers = [t.lower() for t in (chunk.tiers if isinstance(chunk.tiers, list) else [])]

            # Filter 1: Framework filter (India only vs India + EU)
            framework_match = any(f in active_frameworks for f in chunk_frameworks)
            if not framework_match:
                continue

            # Filter 2: Risk Tier filter
            tier_match = tier_clean in chunk_tiers
            if not tier_match:
                continue

            filtered_candidates.append(chunk)

        if not filtered_candidates:
            return []

        # Embed query
        query_vec = self.embedder.embed_text(query)

        scored_results: List[Dict[str, Any]] = []
        for chunk in filtered_candidates:
            chunk_vec = self.embedder.embed_text(chunk.text)
            sim = cosine_similarity(query_vec, chunk_vec)
            scored_results.append({
                "chunk_id": chunk.id,
                "instrument": chunk.instrument,
                "section_id": chunk.section_id,
                "text": chunk.text,
                "tiers": chunk.tiers,
                "frameworks": chunk.frameworks,
                "similarity_score": round(sim, 4),
            })

        # Sort by similarity score descending
        scored_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_results[:top_k]
