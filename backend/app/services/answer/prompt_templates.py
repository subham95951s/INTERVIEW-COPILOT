"""Question-Type-Specific Prompt Templates and Ultra-Fast Regex Classifier."""

import re
from dataclasses import dataclass
from enum import Enum


class QuestionType(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    CODING = "coding"
    SITUATIONAL = "situational"
    MOTIVATION = "motivation"
    CULTURE_FIT = "culture_fit"
    CONVERSATIONAL = "conversational"


@dataclass
class QuestionTypeConfig:
    name: str
    ideal_length_words: tuple[int, int]
    structure: str
    special_instructions: str
    system_prompt_suffix: str


QUESTION_TYPE_CONFIGS: dict[QuestionType, QuestionTypeConfig] = {
    QuestionType.BEHAVIORAL: QuestionTypeConfig(
        name="Behavioral",
        ideal_length_words=(100, 180),
        structure="STAR (Situation -> Task -> Action -> Result)",
        special_instructions="""
- Structure your answer using STAR (Situation -> Task -> Action -> Result) ONLY drawing from situations/projects explicitly documented in the Candidate Background context below.
- CRITICAL: DO NOT fabricate or invent past roles, companies, projects, or metrics that are not in the candidate's actual background.
- If the candidate's background contains a relevant project/experience, cite it clearly ("In my work on [Project]...").
- If the candidate's background does NOT contain a matching past scenario, DO NOT invent a fake past story starting with "In my previous role I...". Instead, answer professionally using your engineering approach, methodology, or first-person strategy ("When approaching [problem], my strategy is to...").
""",
        system_prompt_suffix="Ground STAR structure strictly in actual background. Never invent fake past experiences.",
    ),
    QuestionType.TECHNICAL: QuestionTypeConfig(
        name="Technical Depth",
        ideal_length_words=(120, 220),
        structure="Context -> Core Mechanics -> Implementation Details -> Trade-offs",
        special_instructions="""
- Show deep engineering expertise appropriate to senior/lead roles
- Explicitly reference specific algorithms, data structures, frameworks, or protocols
- Explain the underlying mechanics and trade-offs considered
- Conclude with practical edge cases or scalability considerations
- Do not fabricate personal anecdotes ("In my previous role..."); answer directly and authoritatively.
""",
        system_prompt_suffix="Explain technical mechanics cleanly. Address engineering trade-offs and edge cases.",
    ),
    QuestionType.SYSTEM_DESIGN: QuestionTypeConfig(
        name="System Design",
        ideal_length_words=(180, 320),
        structure="Requirements -> High-Level Architecture -> Deep Dive -> Scale & Bottlenecks",
        special_instructions="""
- Start by clarifying key functional and non-functional assumptions (latency, throughput, consistency)
- Walk through the core components (API gateways, caching layers, database schemas, message queues)
- Discuss horizontal scaling and how the architecture handles 10x spike load
- Explicitly analyze potential failure modes and disaster recovery
- Do not invent fake personal backstories; structure authoritatively as an architectural solution.
""",
        system_prompt_suffix="Structure systematically: requirements -> architecture -> scale -> fault tolerance.",
    ),
    QuestionType.CODING: QuestionTypeConfig(
        name="Coding / Algorithmic",
        ideal_length_words=(100, 200),
        structure="Approach & Complexity -> Clean Implementation Strategy -> Edge Cases",
        special_instructions="""
- State the optimal time and space complexity upfront (Big-O notation)
- Walk through the algorithm step-by-step cleanly
- Highlight key edge cases (null inputs, boundary limits, overflow, concurrency)
""",
        system_prompt_suffix="Focus on optimal Big-O complexity, clean algorithmic approach, and edge cases.",
    ),
    QuestionType.SITUATIONAL: QuestionTypeConfig(
        name="Situational Problem Solving",
        ideal_length_words=(100, 180),
        structure="Initial Assessment -> Action Plan -> Contingency -> Retrospective",
        special_instructions="""
- Walk logically through how you would evaluate and prioritize the challenge
- Give concrete steps based on engineering best practices
- Do not fabricate a past scenario ("In my previous role..."); answer hypothetically and professionally ("To address this, I would...").
""",
        system_prompt_suffix="Walk through systematic prioritization and problem solving steps directly.",
    ),
    QuestionType.MOTIVATION: QuestionTypeConfig(
        name="Motivation & Alignment",
        ideal_length_words=(80, 140),
        structure="Why This Mission -> Role Fit -> Immediate Value Add",
        special_instructions="""
- Connect specific career goals and technical passions to the company's domain
- Reference concrete technologies or challenges mentioned in the Job Description
""",
        system_prompt_suffix="Be authentic, concise, and connect specific skills to company mission.",
    ),
    QuestionType.CULTURE_FIT: QuestionTypeConfig(
        name="Culture & Leadership Fit",
        ideal_length_words=(80, 150),
        structure="Concrete Story -> Reflection -> Alignment with Core Values",
        special_instructions="""
- Use collaborative principles and authentic examples grounded in your actual background
- Show empathy, clear communication, and accountability
""",
        system_prompt_suffix="Demonstrate collaborative leadership and accountability.",
    ),
    QuestionType.CONVERSATIONAL: QuestionTypeConfig(
        name="Conversational & Direct",
        ideal_length_words=(60, 130),
        structure="Direct Response -> Clear Explanation -> Thoughtful Follow-up",
        special_instructions="""
- Answer directly, naturally, and concisely without forcing STAR structure or inventing past scenarios
- If asked "Do you have any questions for me?", ask 1-2 insightful questions about the team, tech stack, or day-to-day role
- If asked a factual question ("Who is...", "What are..."), provide a crisp, accurate factual answer
""",
        system_prompt_suffix="Answer directly, naturally, and concisely.",
    ),
}


def classify_question_type(question: str) -> QuestionType:
    """Ultra-fast regex-based question classifier (< 0.1ms, 0 MB RAM overhead)."""
    text = question.strip().lower()

    # 1. Conversational / Factual / Interpersonal
    if re.search(
        r"\b(who is|who was|do you have any questions|does that give you a good sense|how are you|tell me about the team|what does a typical day|any questions for me)\b",
        text,
    ):
        return QuestionType.CONVERSATIONAL

    # 2. System Design & Infrastructure
    if re.search(
        r"\b(system design|design a|design the|architecture|scale|distributed|microservice|database schema|high availability|throughput|load balancer|caching|synchronization|failover|downtime|infrastructure|hardware failure)\b",
        text,
    ):
        return QuestionType.SYSTEM_DESIGN

    # 3. Coding / Algorithmic
    if re.search(
        r"\b(write a function|time complexity|space complexity|big o|algorithm|array|linked list|binary tree|hash map|dynamic programming|sort|invert)\b",
        text,
    ):
        return QuestionType.CODING

    # 4. Behavioral (Explicit requests for past situations)
    if re.search(
        r"\b(tell me about a time|describe a situation|give an example|how did you handle a|time when you|conflict|disagreement|proudest|mistake|failure|challenge you faced)\b",
        text,
    ):
        return QuestionType.BEHAVIORAL

    # 5. Motivation
    if re.search(
        r"\b(why do you want to work|why are you interested|why this company|why our team|where do you see yourself|why should we hire)\b",
        text,
    ):
        return QuestionType.MOTIVATION

    # 6. Culture Fit
    if re.search(
        r"\b(work style|management style|team culture|feedback|mentor|collaboration|strengths and weaknesses)\b",
        text,
    ):
        return QuestionType.CULTURE_FIT

    # 7. Situational Problem Solving
    if re.search(
        r"\b(what would you do if|how would you handle|imagine|suppose|if you were tasked|how would you debug|how would you evaluate|how would you choose|how would you communicate|how would you approach|would you approach)\b",
        text,
    ):
        return QuestionType.SITUATIONAL

    # 8. Technical / Factual
    if re.search(
        r"\b(how does|what is|what are|difference between|explain|how do you|how would you implement|async|thread|concurrency|memory|garbage collection|protocol|api|cache|pipeline|model|parameter)\b",
        text,
    ):
        return QuestionType.TECHNICAL

    # Default fallback to Technical/Direct format rather than forcing fabricated STAR stories
    return QuestionType.TECHNICAL


def get_type_specific_prompt(
    base_prompt: str,
    question_type: QuestionType,
    question: str,
) -> str:
    """Enhance prompt with structured formatting rules tailored to the question type."""
    config = QUESTION_TYPE_CONFIGS.get(question_type, QUESTION_TYPE_CONFIGS[QuestionType.BEHAVIORAL])

    return f"""{base_prompt}

## Target Interview Question Type: {config.name.upper()}
## Target Answer Structure: {config.structure}
## Recommended Length: {config.ideal_length_words[0]}-{config.ideal_length_words[1]} words

## Type-Specific Guidelines:
{config.special_instructions}

## Interview Question to Answer:
{question}

Generate a clear, highly structured {config.name} interview answer directly following the required structure above:"""
