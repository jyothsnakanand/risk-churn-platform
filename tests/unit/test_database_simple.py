"""Simple tests for database repository."""

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from risk_churn_platform.database.models import Base, PredictionFeedback
from risk_churn_platform.database.repository import FeedbackRepository


@pytest.fixture
def db_engine():
    """Create in-memory database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create database session."""
    session = Session(db_engine)
    yield session
    session.close()


def test_prediction_feedback_model(db_session: Session) -> None:
    """Test creating PredictionFeedback."""
    feedback = PredictionFeedback(
        request_id="test-1",
        features={"total_orders": 10},
        predicted_probability=0.75,
        predicted_label=1,
        risk_score=75.0,
        model_version="v1",
        routing_strategy="shadow",
    )

    db_session.add(feedback)
    db_session.commit()

    result = db_session.query(PredictionFeedback).filter_by(request_id="test-1").first()
    assert result is not None
    assert result.predicted_probability == 0.75


def test_feedback_repository_store_prediction(db_session: Session) -> None:
    """Test storing prediction."""
    repo = FeedbackRepository(db_session)

    repo.store_prediction(
        request_id="repo-1",
        features={"total_orders": 15},
        predicted_probability=0.65,
        predicted_label=1,
        risk_score=65.0,
        model_version="v1",
        routing_strategy="shadow",
        latency_ms=10.5,
    )

    prediction = db_session.query(PredictionFeedback).filter_by(request_id="repo-1").first()
    assert prediction is not None
    assert prediction.predicted_probability == 0.65


def test_feedback_repository_update_feedback(db_session: Session) -> None:
    """Test updating prediction with actual label."""
    repo = FeedbackRepository(db_session)

    repo.store_prediction(
        request_id="repo-2",
        features={"total_orders": 20},
        predicted_probability=0.80,
        predicted_label=1,
        risk_score=80.0,
        model_version="v1",
        routing_strategy="shadow",
        latency_ms=11.0,
    )

    repo.update_feedback(request_id="repo-2", actual_label=1)

    prediction = db_session.query(PredictionFeedback).filter_by(request_id="repo-2").first()
    assert prediction.actual_label == 1
    assert prediction.feedback_timestamp is not None


def test_feedback_repository_get_for_retraining(db_session: Session) -> None:
    """Test getting data for retraining."""
    repo = FeedbackRepository(db_session)

    for i in range(5):
        request_id = f"retrain-{i}"
        repo.store_prediction(
            request_id=request_id,
            features={"total_orders": i * 10},
            predicted_probability=0.5 + i * 0.1,
            predicted_label=i % 2,
            risk_score=50.0 + i * 10,
            model_version="v1",
            routing_strategy="shadow",
            latency_ms=10.0,
        )
        repo.update_feedback(request_id=request_id, actual_label=i % 2)

    df = repo.get_feedback_for_retraining(min_samples=3, days_back=7, model_version="v1")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5
