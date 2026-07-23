"""
Unit tests for Upgrade Phase F: Advanced Real-Time Coaching HUD & Proactive Interview Intelligence.
"""

import pytest
import time
from app.services.coaching import (
    SpeechAnalyticsEngine,
    CheatSheetGenerator,
    PostInterviewReportGenerator,
)


def test_speech_analytics_wpm_and_fillers():
    engine = SpeechAnalyticsEngine(window_seconds=30.0)

    # Utterance with filler words
    telemetry = engine.analyze_utterance(
        "Um well basically we designed a microservices architecture like Kubernetes",
        timestamp=time.time() - 10.0,
    )

    assert telemetry["filler_count"] >= 3  # "um", "basically", "like"
    assert telemetry["total_words"] == 9
    assert telemetry["pacing_status"] in ("optimal", "slow", "fast")


@pytest.mark.asyncio
async def test_cheat_sheet_heuristic_fallback():
    generator = CheatSheetGenerator(api_key=None)
    bullets = await generator.generate_bullets(
        question="How would you design a scalable PostgreSQL database cluster?",
        resume_context="Candidate worked on Redis and PostgreSQL migrations at Stripe.",
    )

    assert len(bullets) == 3
    assert any("•" in b for b in bullets)


def test_post_interview_report_generation():
    generator = PostInterviewReportGenerator()
    report = generator.generate_report(
        session_id="test-session-f",
        qa_exchanges=[
            {"question": "How do you design a scalable system?"},
            {"question": "Tell me about a time you handled a conflict."},
        ],
        candidate_name="Alex Rivera",
        interviewer_name="Sarah Chen",
    )

    assert report.overall_score > 0
    assert "System Design & Scalability" in report.topics_covered
    assert "Alex Rivera" in report.thank_you_email
    assert "Sarah Chen" in report.thank_you_email
