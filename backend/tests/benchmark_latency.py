"""
Latency benchmark for the full pipeline.
Run: python -m tests.benchmark_latency
Must pass: < 2000ms end-to-end
"""
import asyncio
import time
import structlog
from app.services.question_detector import QuestionDetector
from app.services.llm_router import get_llm_provider, LLMContext

log = structlog.get_logger()

TEST_QUESTIONS = [
    "Tell me about a time you had to solve a difficult technical problem.",
    "How do you handle disagreements with your team?",
    "What's your approach to system design for high-traffic applications?",
]


async def benchmark_question_detector() -> None:
    detector = QuestionDetector()
    latencies: list[float] = []

    for question in TEST_QUESTIONS:
        start = time.perf_counter()
        result = await detector.classify(f"Interviewer: {question}")
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
        log.info(
            "Classifier",
            question=question[:50],
            latency_ms=round(latency),
            is_question=result.is_question,
        )
        assert result.is_question, f"Failed to classify: {question}"

    avg = sum(latencies) / len(latencies)
    log.info("Question classifier avg latency", avg_ms=round(avg))
    assert avg < 300, f"Classifier too slow: {avg:.0f}ms (target: <300ms)"


async def benchmark_llm_ttft() -> None:
    """Time-to-first-token benchmark."""
    provider = get_llm_provider()
    latencies: list[float] = []

    for question in TEST_QUESTIONS:
        context = LLMContext(
            candidate_name="John Doe",
            rag_chunks="Senior engineer with 5 years at Google. Led backend systems.",
            jd_summary="Backend engineer role requiring Python, distributed systems.",
            conversation_history="No previous exchanges.",
            question=question,
        )

        start = time.perf_counter()
        first_token_received = False

        async for token in provider.generate_stream(context):
            if not first_token_received:
                ttft = (time.perf_counter() - start) * 1000
                latencies.append(ttft)
                log.info("TTFT", latency_ms=round(ttft))
                first_token_received = True
                break  # Only measure first token

    avg = sum(latencies) / len(latencies)
    log.info("LLM TTFT avg", avg_ms=round(avg))
    assert avg < 600, f"TTFT too slow: {avg:.0f}ms (target: <600ms)"


async def main() -> None:
    log.info("Starting latency benchmark")
    log.info("=" * 50)

    log.info("Benchmarking question detector...")
    await benchmark_question_detector()

    log.info("Benchmarking LLM TTFT...")
    await benchmark_llm_ttft()

    log.info("=" * 50)
    log.info("All benchmarks PASSED ✓")


if __name__ == "__main__":
    asyncio.run(main())
