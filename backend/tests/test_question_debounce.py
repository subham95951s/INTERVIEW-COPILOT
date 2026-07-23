import pytest
from app.routers.websocket import _normalize_question_text


def test_normalize_question_text():
    q1 = "Can you explain how Kubernetes handles rolling deployments?"
    q2 = "can you explain how kubernetes handles rolling deployments!"
    q3 = "Can you explain how   Kubernetes handles   rolling deployments"

    assert _normalize_question_text(q1) == _normalize_question_text(q2)
    assert _normalize_question_text(q1) == _normalize_question_text(q3)


def test_normalize_question_overlap():
    q1 = _normalize_question_text("Can you explain how Kubernetes handles rolling deployments?")
    q2 = _normalize_question_text("So can you explain how Kubernetes handles rolling deployments?")

    assert q1 in q2 or q2 in q1
