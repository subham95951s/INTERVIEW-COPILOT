"""
Coding question pipeline (`backend/app/services/coding/pipeline.py`).
Accepts base64 problem screenshots, runs vision analysis (Groq with NVIDIA fallback),
extracts structured problem data + pseudocode + complexity, and generates complete solution code.
"""

import json
import structlog
from dataclasses import dataclass
from openai import AsyncOpenAI
from app.config import get_settings

log = structlog.get_logger()
settings = get_settings()


@dataclass
class CodingProblemAnalysis:
    problem_summary: str
    input_format: str
    output_format: str
    constraints: list[str]
    examples: list[dict]
    approach: str
    pseudocode: str
    time_complexity: str
    space_complexity: str
    edge_cases: list[str]
    follow_up_considerations: list[str]
    solution_code_python: str | None = None


VISION_PROMPT = """Analyze this coding interview problem screenshot carefully.
Extract all problem details and provide a structured algorithmic approach suitable for explaining to an interviewer.

Return JSON with exactly this format:
{
  "problem_summary": "one concise sentence description of the goal",
  "input_format": "description of input parameters and data types",
  "output_format": "description of expected return value",
  "constraints": ["list of constraints, bounds, e.g. 1 <= N <= 10^5"],
  "examples": [{"input": "...", "output": "...", "explanation": "..."}],
  "approach": "detailed strategic explanation of the optimal approach (2-3 clear paragraphs to verbally explain)",
  "pseudocode": "step-by-step clean pseudocode showing logic cleanly before coding",
  "time_complexity": "O(?) with brief justification",
  "space_complexity": "O(?) with brief justification",
  "edge_cases": ["edge cases or boundary inputs to handle carefully"],
  "follow_up_considerations": ["potential follow-up questions or optimizations the interviewer might ask next"]
}"""

CODE_GEN_PROMPT = """You are an expert technical interviewer and software engineer.
Based on the following coding problem approach and pseudocode, write clean, production-ready, highly optimized Python code that solves the problem.
Include helpful inline comments and ensure it handles all edge cases cleanly.

Problem: {problem_summary}
Approach: {approach}
Pseudocode:
{pseudocode}

Return ONLY valid Python code inside a markdown code block (or clean code without extra conversational text)."""


class CodingQuestionPipeline:
    """
    Orchestrates screenshot vision extraction and solution generation.
    Primary: Groq Vision (`llama-3.2-90b-vision-preview`).
    Fallback: NVIDIA API (`meta/llama-3.2-90b-vision-instruct`).
    """

    def __init__(self) -> None:
        self._groq_client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self._nvidia_client = AsyncOpenAI(
            api_key=settings.nvidia_api_key or "placeholder",
            base_url="https://integrate.api.nvidia.com/v1",
        )

    async def analyze_screenshot(
        self,
        screenshot_base64: str,
    ) -> CodingProblemAnalysis:
        """
        Analyze a coding problem screenshot and return structured analysis.
        Uses Groq Vision primary, falling back to NVIDIA Vision API if Groq fails or rate limits.
        """
        # Strip data URL prefix if present
        clean_base64 = screenshot_base64
        if clean_base64.startswith("data:image"):
            clean_base64 = clean_base64.split(",", 1)[-1]

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{clean_base64}"
                        },
                    },
                ],
            }
        ]

        # 1. Try Groq Vision Primary
        try:
            log.info("Analyzing screenshot with Groq Vision primary")
            response = await self._groq_client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=messages,
                temperature=0.1,
                max_tokens=1500,
            )
            content = response.choices[0].message.content or ""
            return self._parse_response(content)
        except Exception as groq_error:
            log.warning("Groq Vision failed or rate limited, falling back to NVIDIA API", error=str(groq_error))

        # 2. Try NVIDIA API Fallback
        try:
            if not settings.nvidia_api_key or settings.nvidia_api_key == "placeholder":
                raise ValueError("NVIDIA API key not configured for vision fallback")

            log.info("Analyzing screenshot with NVIDIA Vision API fallback")
            response = await self._nvidia_client.chat.completions.create(
                model="meta/llama-3.2-90b-vision-instruct",
                messages=messages,
                temperature=0.1,
                max_tokens=1500,
            )
            content = response.choices[0].message.content or ""
            return self._parse_response(content)
        except Exception as nvidia_error:
            log.error("Both Groq and NVIDIA Vision failed during screenshot analysis", error=str(nvidia_error))
            return self._fallback_error_analysis(str(nvidia_error))

    async def generate_solution_code(
        self,
        analysis: CodingProblemAnalysis,
        language: str = "python",
    ) -> str:
        """
        Generate complete runnable solution code based on extracted approach and pseudocode.
        Uses Groq primary (`llama-3.3-70b-versatile`), falling back to NVIDIA API.
        """
        prompt = CODE_GEN_PROMPT.format(
            problem_summary=analysis.problem_summary,
            approach=analysis.approach,
            pseudocode=analysis.pseudocode,
        )
        messages = [{"role": "user", "content": prompt}]

        # 1. Try Groq Primary
        try:
            response = await self._groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.2,
                max_tokens=1000,
            )
            code = response.choices[0].message.content or ""
            return self._clean_code_block(code)
        except Exception as groq_error:
            log.warning("Groq code generation failed, falling back to NVIDIA API", error=str(groq_error))

        # 2. Try NVIDIA Fallback
        try:
            if not settings.nvidia_api_key or settings.nvidia_api_key == "placeholder":
                return "# Code generation failed: NVIDIA API key not configured."

            response = await self._nvidia_client.chat.completions.create(
                model=settings.nvidia_model or "meta/llama-3.3-70b-instruct",
                messages=messages,
                temperature=0.2,
                max_tokens=1000,
            )
            code = response.choices[0].message.content or ""
            return self._clean_code_block(code)
        except Exception as nvidia_error:
            log.error("Both Groq and NVIDIA failed during code generation", error=str(nvidia_error))
            return f"# Error generating code: {nvidia_error}"

    def _parse_response(self, content: str) -> CodingProblemAnalysis:
        """Parse structured JSON response into CodingProblemAnalysis."""
        try:
            # Locate JSON bounds if enclosed in markdown backticks
            clean_json = content.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```", 1)[1].split("```", 1)[0].strip()

            data = json.loads(clean_json)
            return CodingProblemAnalysis(
                problem_summary=data.get("problem_summary", "Problem analysis extracted"),
                input_format=data.get("input_format", ""),
                output_format=data.get("output_format", ""),
                constraints=data.get("constraints", []),
                examples=data.get("examples", []),
                approach=data.get("approach", content),
                pseudocode=data.get("pseudocode", ""),
                time_complexity=data.get("time_complexity", "O(N)"),
                space_complexity=data.get("space_complexity", "O(1)"),
                edge_cases=data.get("edge_cases", []),
                follow_up_considerations=data.get("follow_up_considerations", []),
            )
        except Exception as parse_error:
            log.warning("Failed to parse JSON from vision response, using raw text fallback", error=str(parse_error))
            return CodingProblemAnalysis(
                problem_summary="Extracted problem (raw text)",
                input_format="",
                output_format="",
                constraints=[],
                examples=[],
                approach=content,
                pseudocode="",
                time_complexity="O(?)",
                space_complexity="O(?)",
                edge_cases=[],
                follow_up_considerations=[],
            )

    def _fallback_error_analysis(self, error_msg: str) -> CodingProblemAnalysis:
        return CodingProblemAnalysis(
            problem_summary="Vision extraction encountered an error",
            input_format="",
            output_format="",
            constraints=[],
            examples=[],
            approach=f"Could not analyze screenshot: {error_msg}. Please check API keys or network connection.",
            pseudocode="",
            time_complexity="O(1)",
            space_complexity="O(1)",
            edge_cases=[],
            follow_up_considerations=[],
        )

    def _clean_code_block(self, text: str) -> str:
        """Strip markdown code fence wrappers from generated code."""
        cleaned = text.strip()
        if cleaned.startswith("```python"):
            cleaned = cleaned.split("```python", 1)[1].split("```", 1)[0].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        return cleaned
