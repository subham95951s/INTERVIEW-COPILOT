"""
Parent-child chunking strategy for improved RAG retrieval.

Parent chunks: large (~800 chars) for full context sent to LLM.
Child chunks: small (~150 chars) for precise embedding retrieval.

Flow:
  1. Store both parent and child chunks
  2. Embed CHILD chunks (small = more precise retrieval)
  3. When a child chunk matches, return its PARENT (full context)

This gives precision of small chunks with context of large chunks.
"""

from dataclasses import dataclass, field
import uuid


@dataclass
class ParentChunk:
    """A large chunk that provides full context to the LLM."""
    id: str
    text: str
    section: str
    source_type: str
    children: list["ChildChunk"] = field(default_factory=list)


@dataclass
class ChildChunk:
    """A small chunk embedded for precise retrieval, linked to its parent."""
    id: str
    text: str
    parent_id: str
    section: str
    source_type: str
    embedding: list[float] | None = None


class ParentChildChunker:
    """
    Creates hierarchical chunk structure for better RAG retrieval.

    Instead of flat 500-char chunks, produces:
      - Parent chunks (~800 chars): sent to LLM for full context
      - Child chunks (~150 chars): embedded for precise matching
    """

    PARENT_CHUNK_SIZE = 800   # chars
    CHILD_CHUNK_SIZE = 150    # chars
    CHILD_OVERLAP = 30        # chars

    def chunk_document(
        self,
        text: str,
        section: str,
        source_type: str,
    ) -> list[ParentChunk]:
        """
        Split document text into parent-child chunk hierarchy.

        Args:
            text: Raw text content from a resume section or JD.
            section: Section label (e.g. "experience", "skills").
            source_type: "resume" or "jd".

        Returns:
            List of ParentChunks, each containing nested ChildChunks.
        """
        parent_texts = self._split_text(text, self.PARENT_CHUNK_SIZE, 100)
        parents = []

        for parent_text in parent_texts:
            parent_id = str(uuid.uuid4())
            child_texts = self._split_text(
                parent_text, self.CHILD_CHUNK_SIZE, self.CHILD_OVERLAP
            )

            children = [
                ChildChunk(
                    id=str(uuid.uuid4()),
                    text=child_text,
                    parent_id=parent_id,
                    section=section,
                    source_type=source_type,
                )
                for child_text in child_texts
                if child_text.strip()
            ]

            parents.append(ParentChunk(
                id=parent_id,
                text=parent_text,
                section=section,
                source_type=source_type,
                children=children,
            ))

        return parents

    def _split_text(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split text into overlapping windows of chunk_size characters."""
        if not text or not text.strip():
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap
            if start >= len(text):
                break
        return chunks
