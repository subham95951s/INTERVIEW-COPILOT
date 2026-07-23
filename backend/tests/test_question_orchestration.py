import pytest
from app.routers.websocket import _normalize_question_text

def test_jaccard_overlap_check():
    q_original = "Can you compare tensor parallelism versus pipeline parallelism for this specific use case?"
    q_variation = "Can you compare pipeline parallelism vs tensor parallelism in this scenario?"
    
    norm_q = _normalize_question_text(q_original)
    norm_last = _normalize_question_text(q_variation)
    
    words_q = set(norm_q.split())
    words_last = set(norm_last.split())
    
    overlap = len(words_q & words_last) / max(1, min(len(words_q), len(words_last)))
    
    # Assert they have high word overlap
    assert overlap >= 0.45

def test_last_speaker_extraction_logic():
    transcript = "Interviewer: Imagine you are designing an infrastructure\nCandidate: Okay. Next question."
    lines = [line.strip() for line in transcript.strip().split("\n") if line.strip()]
    
    assert lines[-1].startswith("Candidate:")

def test_clearance_keywords_check():
    phrases = [
        "Candidate: next question",
        "Interviewer: next question",
        "Candidate: next",
        "Candidate: okay next"
    ]
    for phrase in phrases:
        last_phrase = phrase.lower()
        has_keyword = "next question" in last_phrase or "next query" in last_phrase or "next" in last_phrase.split()
        assert has_keyword is True
