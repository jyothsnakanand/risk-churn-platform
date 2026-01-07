"""Unit tests for retraining pipeline."""

import os
import tempfile
import numpy as np
import pandas as pd
import pytest
from numpy.typing import NDArray

from risk_churn_platform.deployment.retraining import RetrainingPipeline


@pytest.fixture
def feedback_data() -> pd.DataFrame:
    """Generate feedback data for retraining.

    Returns:
        Feedback DataFrame with features and labels
    """
    np.random.seed(42)
    n_samples = 15000

    return pd.DataFrame({
        'customer_tenure': np.random.randint(1, 72, n_samples),
        'monthly_charges': np.random.uniform(20, 120, n_samples),
        'total_charges': np.random.uniform(100, 8000, n_samples),
        'contract_type': np.random.randint(0, 3, n_samples),
        'payment_method': np.random.randint(0, 4, n_samples),
        'internet_service': np.random.randint(0, 3, n_samples),
        'support_tickets': np.random.randint(0, 10, n_samples),
        'login_frequency': np.random.uniform(0, 10, n_samples),
        'label': np.random.randint(0, 2, n_samples),
    })


@pytest.fixture
def small_feedback_data() -> pd.DataFrame:
    """Generate small feedback data (insufficient for retraining).

    Returns:
        Small feedback DataFrame
    """
    np.random.seed(42)
    n_samples = 500

    return pd.DataFrame({
        'customer_tenure': np.random.randint(1, 72, n_samples),
        'monthly_charges': np.random.uniform(20, 120, n_samples),
        'total_charges': np.random.uniform(100, 8000, n_samples),
        'contract_type': np.random.randint(0, 3, n_samples),
        'payment_method': np.random.randint(0, 4, n_samples),
        'internet_service': np.random.randint(0, 3, n_samples),
        'support_tickets': np.random.randint(0, 10, n_samples),
        'login_frequency': np.random.uniform(0, 10, n_samples),
        'label': np.random.randint(0, 2, n_samples),
    })


@pytest.fixture
def temp_model_dir() -> str:
    """Create temporary directory for models.

    Returns:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_retraining_pipeline_initialization() -> None:
    """Test retraining pipeline initialization."""
    pipeline = RetrainingPipeline(
        min_samples=10000,
        performance_threshold=0.85,
        auto_deploy=False
    )

    assert pipeline.min_samples == 10000
    assert pipeline.performance_threshold == 0.85
    assert pipeline.auto_deploy is False
    assert len(pipeline.training_history) == 0


def test_should_retrain_insufficient_samples(
    small_feedback_data: pd.DataFrame
) -> None:
    """Test should_retrain with insufficient samples."""
    pipeline = RetrainingPipeline(min_samples=10000)

    should_retrain = pipeline.should_retrain(small_feedback_data)

    assert should_retrain is False


def test_should_retrain_sufficient_samples(
    feedback_data: pd.DataFrame
) -> None:
    """Test should_retrain with sufficient samples."""
    pipeline = RetrainingPipeline(min_samples=10000)

    should_retrain = pipeline.should_retrain(feedback_data)

    assert should_retrain is True


def test_prepare_training_data(feedback_data: pd.DataFrame) -> None:
    """Test preparing training data."""
    pipeline = RetrainingPipeline()

    X_train, y_train, X_val, y_val = pipeline.prepare_training_data(feedback_data)

    # Check shapes
    assert len(X_train) + len(X_val) == len(feedback_data)
    assert X_train.shape[1] == 8  # 8 features
    assert len(X_train) == len(y_train)
    assert len(X_val) == len(y_val)

    # Check train/val split ratio (should be 80/20)
    expected_train_size = int(len(feedback_data) * 0.8)
    assert abs(len(X_train) - expected_train_size) < 10


def test_train_model_v1(feedback_data: pd.DataFrame) -> None:
    """Test training model v1."""
    pipeline = RetrainingPipeline()
    X_train, y_train, X_val, y_val = pipeline.prepare_training_data(feedback_data)

    model, metrics = pipeline.train_model(X_train, y_train, X_val, y_val, model_version='v1')

    # Check model is trained
    assert model is not None
    assert model.model is not None

    # Check metrics
    assert 'accuracy' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics
    assert 'f1_score' in metrics
    assert 'roc_auc' in metrics

    # Check metric values are reasonable
    assert 0 <= metrics['accuracy'] <= 1
    assert 0 <= metrics['f1_score'] <= 1


def test_train_model_v2(feedback_data: pd.DataFrame) -> None:
    """Test training model v2."""
    pipeline = RetrainingPipeline()
    X_train, y_train, X_val, y_val = pipeline.prepare_training_data(feedback_data)

    model, metrics = pipeline.train_model(X_train, y_train, X_val, y_val, model_version='v2')

    # Check model is trained
    assert model is not None
    assert model.model is not None

    # Check metrics exist
    assert 'f1_score' in metrics


def test_evaluate_deployment_readiness() -> None:
    """Test evaluating deployment readiness."""
    pipeline = RetrainingPipeline(performance_threshold=0.85)

    # Good metrics
    good_metrics = {'f1_score': 0.90}
    assert pipeline.evaluate_deployment_readiness(good_metrics) is True

    # Poor metrics
    poor_metrics = {'f1_score': 0.70}
    assert pipeline.evaluate_deployment_readiness(poor_metrics) is False

    # Borderline metrics
    borderline_metrics = {'f1_score': 0.85}
    assert pipeline.evaluate_deployment_readiness(borderline_metrics) is True


def test_save_model(
    feedback_data: pd.DataFrame, temp_model_dir: str
) -> None:
    """Test saving trained model."""
    pipeline = RetrainingPipeline(model_save_path=temp_model_dir)
    X_train, y_train, X_val, y_val = pipeline.prepare_training_data(feedback_data)

    model, metrics = pipeline.train_model(X_train, y_train, X_val, y_val, model_version='v1')

    model_path = pipeline.save_model(model, 'v1', metrics)

    # Check model was saved
    assert os.path.exists(model_path)

    # Check metrics were saved
    metrics_path = os.path.join(os.path.dirname(model_path), 'metrics.json')
    assert os.path.exists(metrics_path)


def test_run_retraining_insufficient_samples(
    small_feedback_data: pd.DataFrame
) -> None:
    """Test running retraining with insufficient samples."""
    pipeline = RetrainingPipeline(min_samples=10000)

    result = pipeline.run_retraining(small_feedback_data)

    assert result['status'] == 'skipped'
    assert result['reason'] == 'insufficient_samples'


def test_run_retraining_success(
    feedback_data: pd.DataFrame, temp_model_dir: str
) -> None:
    """Test successful retraining run."""
    pipeline = RetrainingPipeline(
        min_samples=10000,
        performance_threshold=0.70,  # Lower threshold for test
        auto_deploy=False,
        model_save_path=temp_model_dir
    )

    result = pipeline.run_retraining(feedback_data, model_version='v1')

    assert result['status'] == 'completed'
    assert 'metrics' in result
    assert 'model_path' in result
    assert 'ready_for_deployment' in result
    assert result['deployed'] is False

    # Check model was saved
    assert os.path.exists(result['model_path'])


def test_run_retraining_auto_deploy(
    feedback_data: pd.DataFrame, temp_model_dir: str
) -> None:
    """Test retraining with auto-deploy enabled."""
    pipeline = RetrainingPipeline(
        min_samples=10000,
        performance_threshold=0.70,
        auto_deploy=True,
        model_save_path=temp_model_dir
    )

    result = pipeline.run_retraining(feedback_data, model_version='v2')

    # If model meets threshold, should be marked as deployed
    if result['ready_for_deployment']:
        assert result['deployed'] is True
    else:
        assert result['deployed'] is False


def test_get_training_history(
    feedback_data: pd.DataFrame, temp_model_dir: str
) -> None:
    """Test getting training history."""
    pipeline = RetrainingPipeline(
        min_samples=10000,
        performance_threshold=0.70,
        model_save_path=temp_model_dir
    )

    # Run retraining twice
    pipeline.run_retraining(feedback_data, model_version='v1')
    pipeline.run_retraining(feedback_data, model_version='v2')

    history = pipeline.get_training_history()

    assert len(history) == 2
    assert history[0]['model_version'] == 'v1'
    assert history[1]['model_version'] == 'v2'


def test_run_retraining_poor_performance(
    feedback_data: pd.DataFrame, temp_model_dir: str
) -> None:
    """Test retraining with high performance threshold."""
    pipeline = RetrainingPipeline(
        min_samples=10000,
        performance_threshold=0.99,  # Very high threshold
        auto_deploy=False,
        model_save_path=temp_model_dir
    )

    result = pipeline.run_retraining(feedback_data, model_version='v1')

    assert result['status'] == 'completed'
    # Model likely won't meet 99% F1 score
    assert result['ready_for_deployment'] is False
