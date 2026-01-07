"""Automated retraining pipeline."""

import os
from datetime import datetime
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd
import structlog
from numpy.typing import NDArray
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from ..models.risk_scorer import RiskScorerV1, RiskScorerV2

logger = structlog.get_logger()


class RetrainingPipeline:
    """Automated model retraining pipeline."""

    def __init__(
        self,
        min_samples: int = 10000,
        performance_threshold: float = 0.85,
        auto_deploy: bool = False,
        model_save_path: str = "models",
    ) -> None:
        """Initialize retraining pipeline.

        Args:
            min_samples: Minimum samples required for retraining
            performance_threshold: Minimum performance threshold for deployment
            auto_deploy: Whether to automatically deploy retrained models
            model_save_path: Path to save trained models
        """
        self.min_samples = min_samples
        self.performance_threshold = performance_threshold
        self.auto_deploy = auto_deploy
        self.model_save_path = model_save_path
        self.training_history: list[Dict[str, Any]] = []

    def should_retrain(self, feedback_data: pd.DataFrame) -> bool:
        """Determine if model should be retrained.

        Args:
            feedback_data: Feedback data with labels

        Returns:
            Whether retraining should be triggered
        """
        if len(feedback_data) < self.min_samples:
            logger.info(
                "insufficient_samples_for_retraining",
                current_samples=len(feedback_data),
                required_samples=self.min_samples,
            )
            return False

        logger.info("retraining_triggered", samples=len(feedback_data))
        return True

    def prepare_training_data(
        self, feedback_data: pd.DataFrame
    ) -> tuple[NDArray[np.float64], NDArray[np.int_], NDArray[np.float64], NDArray[np.int_]]:
        """Prepare training and validation data.

        Args:
            feedback_data: Raw feedback data

        Returns:
            Tuple of (X_train, y_train, X_val, y_val)
        """
        # Extract features and labels
        feature_columns = [
            "customer_tenure",
            "monthly_charges",
            "total_charges",
            "contract_type",
            "payment_method",
            "internet_service",
            "support_tickets",
            "login_frequency",
        ]

        X = feedback_data[feature_columns].values
        y = feedback_data["label"].values

        # Split into train/validation
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        logger.info(
            "training_data_prepared",
            train_size=len(X_train),
            val_size=len(X_val),
            positive_ratio=np.mean(y_train),
        )

        return X_train, y_train, X_val, y_val

    def train_model(
        self,
        X_train: NDArray[np.float64],
        y_train: NDArray[np.int_],
        X_val: NDArray[np.float64],
        y_val: NDArray[np.int_],
        model_version: str = "v2",
    ) -> tuple[Any, Dict[str, float]]:
        """Train a new model.

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            model_version: Version identifier

        Returns:
            Tuple of (trained_model, metrics)
        """
        logger.info("training_model", version=model_version)

        # Select model class
        if model_version == "v1":
            model = RiskScorerV1()
            model.train(X_train, y_train)
        else:
            model = RiskScorerV2()
            model.train(X_train, y_train)

        # Evaluate on validation set
        y_pred = model.predict(X_val)
        y_pred_proba = model.predict_proba(X_val)[:, 1]

        metrics = {
            "accuracy": float(accuracy_score(y_val, y_pred)),
            "precision": float(precision_score(y_val, y_pred)),
            "recall": float(recall_score(y_val, y_pred)),
            "f1_score": float(f1_score(y_val, y_pred)),
            "roc_auc": float(roc_auc_score(y_val, y_pred_proba)),
        }

        logger.info("model_trained", version=model_version, **metrics)

        return model, metrics

    def evaluate_deployment_readiness(self, metrics: Dict[str, float]) -> bool:
        """Determine if model is ready for deployment.

        Args:
            metrics: Model performance metrics

        Returns:
            Whether model should be deployed
        """
        # Check if F1 score meets threshold
        meets_threshold = metrics["f1_score"] >= self.performance_threshold

        logger.info(
            "deployment_readiness_check",
            meets_threshold=meets_threshold,
            f1_score=metrics["f1_score"],
            threshold=self.performance_threshold,
        )

        return meets_threshold

    def save_model(
        self, model: Any, version: str, metrics: Dict[str, float]
    ) -> str:
        """Save trained model to disk.

        Args:
            model: Trained model
            version: Model version
            metrics: Model metrics

        Returns:
            Path to saved model
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_dir = os.path.join(self.model_save_path, version, timestamp)
        os.makedirs(model_dir, exist_ok=True)

        # Save model
        model_path = os.path.join(model_dir, "model.pkl")
        model.save(model_path)

        # Save metrics
        metrics_path = os.path.join(model_dir, "metrics.json")
        import json

        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        logger.info("model_saved", path=model_path, version=version)

        return model_path

    def run_retraining(
        self, feedback_data: pd.DataFrame, model_version: str = "v2"
    ) -> Dict[str, Any]:
        """Run the full retraining pipeline.

        Args:
            feedback_data: Feedback data for retraining
            model_version: Version to retrain

        Returns:
            Retraining results
        """
        timestamp = datetime.now()

        # Check if retraining should be triggered
        if not self.should_retrain(feedback_data):
            return {
                "status": "skipped",
                "reason": "insufficient_samples",
                "timestamp": timestamp.isoformat(),
            }

        # Prepare data
        X_train, y_train, X_val, y_val = self.prepare_training_data(feedback_data)

        # Train model
        model, metrics = self.train_model(X_train, y_train, X_val, y_val, model_version)

        # Check deployment readiness
        ready_for_deployment = self.evaluate_deployment_readiness(metrics)

        # Save model
        model_path = self.save_model(model, model_version, metrics)

        # Record training history
        result = {
            "status": "completed",
            "timestamp": timestamp.isoformat(),
            "model_version": model_version,
            "metrics": metrics,
            "model_path": model_path,
            "ready_for_deployment": ready_for_deployment,
            "deployed": False,
        }

        # Auto-deploy if enabled and ready
        if self.auto_deploy and ready_for_deployment:
            # In production, this would trigger deployment automation
            logger.info("auto_deployment_triggered", model_version=model_version)
            result["deployed"] = True

        self.training_history.append(result)

        return result

    def get_training_history(self) -> list[Dict[str, Any]]:
        """Get retraining history.

        Returns:
            List of training runs
        """
        return self.training_history
