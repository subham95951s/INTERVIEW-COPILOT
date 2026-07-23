import re
import structlog
import pdfplumber
from docx import Document
from dataclasses import dataclass
from io import BytesIO

log = structlog.get_logger()

SECTION_HEADERS = [
    "experience", "work experience", "employment", "professional experience",
    "education", "projects", "skills", "technical skills", "summary",
    "objective", "certifications", "achievements", "publications",
]

MAX_CHUNK_SIZE = 500  # characters
CHUNK_OVERLAP = 50


@dataclass
class ParsedChunk:
    """A chunk of text from a parsed document."""
    text: str
    section: str
    source_type: str  # "resume" | "jd"


class DocumentParser:
    """Parse PDF/DOCX resumes and JD text into structured chunks."""

    def parse_resume(self, file_bytes: bytes, file_type: str) -> str:
        """Extract raw text from resume file."""
        if file_type == "pdf":
            return self._parse_pdf(file_bytes)
        elif file_type in ("docx", "doc"):
            return self._parse_docx(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _parse_pdf(self, file_bytes: bytes) -> str:
        text_parts = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)

    def _parse_docx(self, file_bytes: bytes) -> str:
        doc = Document(BytesIO(file_bytes))
        return "\n".join(
            para.text for para in doc.paragraphs if para.text.strip()
        )

    def chunk_resume(self, text: str) -> list[ParsedChunk]:
        """Split resume text into semantic section-based chunks."""
        sections = self._split_by_sections(text)
        chunks = []

        for section_name, section_text in sections.items():
            sub_chunks = self._split_text(section_text, MAX_CHUNK_SIZE)
            for chunk_text in sub_chunks:
                if chunk_text.strip():
                    chunks.append(ParsedChunk(
                        text=chunk_text.strip(),
                        section=section_name,
                        source_type="resume",
                    ))

        log.info("Resume chunked", num_chunks=len(chunks))
        return chunks

    def chunk_jd(self, text: str) -> list[ParsedChunk]:
        """Split JD text into chunks."""
        chunks = self._split_text(text, MAX_CHUNK_SIZE)
        return [
            ParsedChunk(
                text=chunk.strip(),
                section="job_description",
                source_type="jd",
            )
            for chunk in chunks if chunk.strip()
        ]

    def _split_by_sections(self, text: str) -> dict[str, str]:
        """Detect resume sections by header keywords."""
        lines = text.split("\n")
        sections: dict[str, list[str]] = {"general": []}
        current_section = "general"

        for line in lines:
            line_lower = line.lower().strip()
            is_header = any(
                header in line_lower
                for header in SECTION_HEADERS
            ) and len(line.strip()) < 50

            if is_header:
                current_section = line.strip().lower()
                sections[current_section] = []
            else:
                sections.setdefault(current_section, []).append(line)

        return {k: "\n".join(v) for k, v in sections.items() if v}

    def _split_text(self, text: str, max_size: int) -> list[str]:
        """Split text into overlapping chunks by sentence boundaries."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk: list[str] = []
        current_size = 0

        for sentence in sentences:
            if current_size + len(sentence) > max_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep last sentence for overlap
                current_chunk = current_chunk[-1:] if CHUNK_OVERLAP else []
                current_size = sum(len(s) for s in current_chunk)

            current_chunk.append(sentence)
            current_size += len(sentence)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks
