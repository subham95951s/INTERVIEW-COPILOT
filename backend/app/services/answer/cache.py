"""Semantic Answer Cache using Redis and cosine similarity."""

import hashlib
import json
import numpy as np
import structlog

log = structlog.get_logger()

CACHE_TTL_SECONDS = 3600  # 1 hour
SIMILARITY_THRESHOLD = 0.92


class AnswerCache:
    """Redis-backed semantic answer cache for similar/repeated interview questions."""

    def __init__(self, redis) -> None:
        self.redis = redis

    async def get_cached_answer(
        self,
        session_id: str,
        question: str,
        question_embedding: list[float] | None = None,
    ) -> dict | None:
        """Check if a semantically similar question was already answered in this session.

        Returns dict containing 'answer', 'metadata', and 'similarity' if found, else None.
        """
        if not self.redis:
            return None

        try:
            pattern = f"answer_cache:{session_id}:*"
            cached_keys = []
            async for key in self.redis.scan_iter(match=pattern):
                cached_keys.append(key)

            if not cached_keys:
                return None

            # First check exact string match
            norm_q = question.strip().lower()
            for key in cached_keys:
                raw = await self.redis.get(key)
                if not raw:
                    continue
                data = json.loads(raw)
                if data.get("question", "").strip().lower() == norm_q:
                    log.info("Answer cache exact hit", session_id=session_id)
                    return {
                        "answer": data["answer"],
                        "metadata": data.get("metadata", {}),
                        "similarity": 1.0,
                    }

            # Next check cosine similarity if embedding provided
            if not question_embedding:
                return None

            q_emb = np.array(question_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_emb)
            if q_norm == 0:
                return None

            best_sim = -1.0
            best_entry = None

            for key in cached_keys:
                raw = await self.redis.get(key)
                if not raw:
                    continue
                data = json.loads(raw)
                cached_emb_list = data.get("embedding")
                if not cached_emb_list:
                    continue
                c_emb = np.array(cached_emb_list, dtype=np.float32)
                c_norm = np.linalg.norm(c_emb)
                if c_norm == 0:
                    continue

                sim = float(np.dot(q_emb, c_emb) / (q_norm * c_norm))
                if sim > best_sim:
                    best_sim = sim
                    best_entry = data

            if best_sim >= SIMILARITY_THRESHOLD and best_entry:
                log.info(
                    "Answer cache semantic hit",
                    similarity=best_sim,
                    session_id=session_id,
                )
                return {
                    "answer": best_entry["answer"],
                    "metadata": best_entry.get("metadata", {}),
                    "similarity": round(best_sim, 3),
                }
        except Exception as exc:
            log.warning("Answer cache lookup error", error=str(exc))

        return None

    async def cache_answer(
        self,
        session_id: str,
        question: str,
        answer: str,
        embedding: list[float] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Store generated answer and embedding in Redis cache."""
        if not self.redis:
            return

        try:
            q_hash = hashlib.md5(question.strip().lower().encode("utf-8")).hexdigest()
            key = f"answer_cache:{session_id}:{q_hash}"
            payload = {
                "question": question,
                "answer": answer,
                "embedding": embedding,
                "metadata": metadata or {},
            }
            await self.redis.set(key, json.dumps(payload), ex=CACHE_TTL_SECONDS)
        except Exception as exc:
            log.warning("Failed to store answer cache", error=str(exc))
