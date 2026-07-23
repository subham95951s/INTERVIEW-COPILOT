"""
Semantic Session Memory and Topic Extractor for Interview Sessions.
Stores and retrieves past Q&A pairs by semantic similarity and prevents story repetition.
"""

import json
import math
import re
import time
from dataclasses import dataclass, asdict
import structlog

log = structlog.get_logger()


@dataclass
class MemoryEntry:
    question: str
    answer: str
    question_type: str
    timestamp_ms: int
    question_embedding: list[float]
    topics_covered: list[str]
    projects_mentioned: list[str]
    skills_demonstrated: list[str]


class SemanticSessionMemory:
    """
    Semantic memory that retrieves relevant past context based on vector similarity
    to the current question and generates explicit anti-repetition guidance.
    """

    MAX_ENTRIES = 30
    TOP_K_RELEVANT = 3

    def __init__(self, session_id: str, redis=None) -> None:
        self.session_id = session_id
        self.redis = redis
        self._memory_key = f"session:{session_id}:semantic_memory"
        self._local_store: list[dict] = []

    async def add_entry(self, entry: MemoryEntry) -> None:
        """Store a Q&A pair in semantic memory."""
        entry_dict = asdict(entry)
        entries = await self._get_all_entries()
        entries.append(entry_dict)

        if len(entries) > self.MAX_ENTRIES:
            entries = entries[-self.MAX_ENTRIES:]

        if self.redis:
            try:
                await self.redis.set(
                    self._memory_key,
                    json.dumps(entries),
                    ex=4 * 3600,  # 4 hr TTL
                )
            except Exception as e:
                log.warning("Redis write failed for semantic memory, using local store", error=str(e))
                self._local_store = entries
        else:
            self._local_store = entries

    async def get_relevant_context(
        self,
        current_question: str,
        current_embedding: list[float] | None = None,
    ) -> tuple[str, dict]:
        """
        Retrieve past Q&A pairs relevant to the current question.
        Returns (formatted_context_string, metadata_dict).
        """
        entries = await self._get_all_entries()
        if not entries:
            return "No previous exchanges.", {"recalled_count": 0, "projects_avoided": []}

        scored_entries: list[tuple[float, dict]] = []

        if current_embedding and len(current_embedding) > 0:
            for entry in entries:
                past_emb = entry.get("question_embedding")
                if past_emb and len(past_emb) == len(current_embedding):
                    sim = self._cosine_similarity(current_embedding, past_emb)
                    scored_entries.append((sim, entry))
                else:
                    scored_entries.append((0.0, entry))
            # Sort by similarity descending
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            relevant = [entry for _, entry in scored_entries[: self.TOP_K_RELEVANT]]
        else:
            # Fallback to most recent K entries if no embedding provided
            relevant = entries[-self.TOP_K_RELEVANT:]
            scored_entries = [(0.0, entry) for entry in entries]

        if not relevant:
            return "No previous exchanges.", {"recalled_count": 0, "projects_avoided": []}

        lines = []
        for entry in relevant:
            q_type = entry.get("question_type", "behavioral").upper()
            q_text = entry.get("question", "")
            a_text = entry.get("answer", "")
            # Truncate answer snippet to 250 characters for token efficiency
            a_snippet = a_text[:250] + "..." if len(a_text) > 250 else a_text
            lines.append(f"Q ({q_type}): {q_text}\nA: {a_snippet}")

        # Aggregate projects and skills across all session entries to prevent repetition
        all_projects: set[str] = set()
        all_skills: set[str] = set()
        for entry in entries:
            for proj in entry.get("projects_mentioned", []):
                if proj and proj.strip():
                    all_projects.add(proj.strip())
            for skill in entry.get("skills_demonstrated", []):
                if skill and skill.strip():
                    all_skills.add(skill.strip())

        repetition_warning = ""
        sorted_projects = sorted(list(all_projects))
        sorted_skills = sorted(list(all_skills))
        if sorted_projects or sorted_skills:
            repetition_warning = (
                f"\n\n[AVOID REPETITION: Already mentioned projects={sorted_projects}, "
                f"skills={sorted_skills}. Reference DIFFERENT examples where possible.]"
            )

        formatted_context = "\n\n".join(lines) + repetition_warning
        metadata = {
            "recalled_count": len(relevant),
            "projects_avoided": sorted_projects,
        }
        return formatted_context, metadata

    async def _get_all_entries(self) -> list[dict]:
        if self.redis:
            try:
                raw = await self.redis.get(self._memory_key)
                if raw:
                    return json.loads(raw)
            except Exception as e:
                log.warning("Redis read failed for semantic memory, using local store", error=str(e))
        return list(self._local_store)

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


class TopicExtractor:
    """
    Extracts structured information (topics, projects, skills) from Q&A pairs
    using fast keyword heuristics and optional lightweight LLM extraction.
    """

    # Common technical/project keyword patterns for instant local extraction
    COMMON_PROJECT_PATTERNS = [
        re.compile(r"\b([A-Z][A-Za-z0-9\-_]+(?: Platform| Engine| Pipeline| Service| Portal| App| System| API))\b"),
        re.compile(r"\bproject (?:called |named )?([A-Z][A-Za-z0-9\-_]+)\b", re.IGNORECASE),
    ]

    COMMON_SKILLS = {
        "Python", "JavaScript", "TypeScript", "React", "Node.js", "FastAPI", "Django",
        "PostgreSQL", "Redis", "Docker", "Kubernetes", "AWS", "GCP", "Azure",
        "GraphQL", "REST API", "Kafka", "RabbitMQ", "Microservices", "System Design",
        "CI/CD", "Testing", "Leadership", "Communication", "Agile", "Scrum",
    }

    async def extract(
        self,
        question: str,
        answer: str,
        groq_api_key: str | None = None,
    ) -> dict:
        """
        Extract structured metadata from Q&A.
        Returns dict with: topics_covered, projects_mentioned, skills_demonstrated.
        """
        # Fast local extraction baseline
        projects_found: set[str] = set()
        skills_found: set[str] = set()

        for pattern in self.COMMON_PROJECT_PATTERNS:
            for match in pattern.findall(answer):
                projects_found.add(match.strip())

        for skill in self.COMMON_SKILLS:
            if re.search(rf"\b{re.escape(skill)}\b", answer, re.IGNORECASE):
                skills_found.add(skill)

        # Attempt lightweight Groq extraction if API key provided
        if groq_api_key:
            try:
                llm_extracted = await self._extract_llm(question, answer, groq_api_key)
                for p in llm_extracted.get("projects_mentioned", []):
                    if isinstance(p, str) and p.strip():
                        projects_found.add(p.strip())
                for s in llm_extracted.get("skills_demonstrated", []):
                    if isinstance(s, str) and s.strip():
                        skills_found.add(s.strip())
            except Exception as e:
                log.debug("LLM topic extraction failed, relying on heuristics", error=str(e))

        return {
            "topics_covered": sorted(list(skills_found)[:5]),
            "projects_mentioned": sorted(list(projects_found)),
            "skills_demonstrated": sorted(list(skills_found)),
        }

    async def _extract_llm(self, question: str, answer: str, api_key: str) -> dict:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=api_key)
        prompt = f"""Extract structured information from this interview Q&A.
Question: {question}
Answer: {answer}

Return JSON with exact keys:
{{
  "topics_covered": ["list of broad topics discussed"],
  "projects_mentioned": ["specific project names or systems mentioned"],
  "skills_demonstrated": ["technical or soft skills shown"]
}}"""
        response = await client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
