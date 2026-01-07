"""Database repository for feedback and metrics."""

from datetime import datetime, timedelta

import pandas as pd
import structlog
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from .models import (
    DriftEvent,
    OutlierEvent,
    PredictionFeedback,
    RetrainingJob,
)

logger = structlog.get_logger()


class FeedbackRepository:
    """Repository for prediction feedback."""

    def __init__(self, session: Session) -> None:
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    def store_prediction(
        self,
        request_id: str,
        features: dict,
        predicted_probability: float,
        predicted_label: int,
        risk_score: float,
        model_version: str,
        routing_strategy: str,
        latency_ms: float | None = None,
        metadata: dict | None = None,
    ) -> PredictionFeedback:
        """Store a prediction.

        Args:
            request_id: Unique request ID
            features: Customer features
            predicted_probability: Churn probability
            predicted_label: Binary prediction (0/1)
            risk_score: Risk score (0-100)
            model_version: Model version
            routing_strategy: Routing strategy used
            latency_ms: Prediction latency
            metadata: Additional metadata

        Returns:
            Created PredictionFeedback record
        """
        feedback = PredictionFeedback(
            request_id=request_id,
            features=features,
            predicted_probability=predicted_probability,
            predicted_label=predicted_label,
            risk_score=risk_score,
            model_version=model_version,
            routing_strategy=routing_strategy,
            latency_ms=latency_ms,
            metadata=metadata,
        )

        self.session.add(feedback)
        self.session.commit()
        logger.info("prediction_stored", request_id=request_id)

        return feedback

    def update_feedback(self, request_id: str, actual_label: int) -> PredictionFeedback | None:
        """Update prediction with ground truth label.

        Args:
            request_id: Request ID
            actual_label: Ground truth label (0/1)

        Returns:
            Updated PredictionFeedback or None if not found
        """
        feedback = (
            self.session.query(PredictionFeedback)
            .filter(PredictionFeedback.request_id == request_id)
            .first()
        )

        if feedback:
            feedback.actual_label = actual_label
            feedback.feedback_timestamp = datetime.utcnow()
            self.session.commit()
            logger.info("feedback_updated", request_id=request_id, actual_label=actual_label)

        return feedback

    def get_feedback_for_retraining(
        self,
        min_samples: int = 10000,
        days_back: int = 90,
        model_version: str | None = None,
    ) -> pd.DataFrame:
        """Get feedback data for retraining.

        Args:
            min_samples: Minimum number of samples required
            days_back: Look back this many days
            model_version: Filter by model version

        Returns:
            DataFrame with features and labels
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        query = self.session.query(PredictionFeedback).filter(
            and_(
                PredictionFeedback.actual_label.isnot(None),
                PredictionFeedback.prediction_timestamp >= cutoff_date,
            )
        )

        if model_version:
            query = query.filter(PredictionFeedback.model_version == model_version)

        results = query.all()

        if len(results) < min_samples:
            logger.warning(
                "insufficient_feedback_samples",
                found=len(results),
                required=min_samples,
            )
            return pd.DataFrame()

        # Convert to DataFrame
        data = []
        for result in results:
            row = result.features.copy()
            row["label"] = result.actual_label
            row["request_id"] = result.request_id
            row["prediction_timestamp"] = result.prediction_timestamp
            data.append(row)

        df = pd.DataFrame(data)
        logger.info("feedback_data_retrieved", samples=len(df))

        return df

    def get_prediction_accuracy(
        self,
        model_version: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, float]:
        """Calculate prediction accuracy for a time period.

        Args:
            model_version: Model version
            start_time: Start of time period
            end_time: End of time period

        Returns:
            Dictionary with accuracy metrics
        """
        query = self.session.query(PredictionFeedback).filter(
            and_(
                PredictionFeedback.model_version == model_version,
                PredictionFeedback.prediction_timestamp >= start_time,
                PredictionFeedback.prediction_timestamp <= end_time,
                PredictionFeedback.actual_label.isnot(None),
            )
        )

        results = query.all()

        if not results:
            return {}

        correct = sum(1 for r in results if r.predicted_label == r.actual_label)
        total = len(results)

        return {
            "accuracy": correct / total if total > 0 else 0,
            "total_predictions": total,
            "correct_predictions": correct,
        }


class MonitoringRepository:
    """Repository for monitoring events."""

    def __init__(self, session: Session) -> None:
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    def store_drift_event(
        self,
        event_id: str,
        drift_detected: bool,
        drift_method: str,
        p_value: float | None = None,
        severity: str = "warning",
        affected_features: list[str] | None = None,
    ) -> DriftEvent:
        """Store a drift detection event.

        Args:
            event_id: Unique event ID
            drift_detected: Whether drift was detected
            drift_method: Detection method (ks, mmd, tabular)
            p_value: Statistical p-value
            severity: Event severity
            affected_features: List of affected features

        Returns:
            Created DriftEvent
        """
        event = DriftEvent(
            event_id=event_id,
            drift_detected=drift_detected,
            drift_method=drift_method,
            p_value=p_value,
            severity=severity,
            affected_features=affected_features,
        )

        self.session.add(event)
        self.session.commit()
        logger.info("drift_event_stored", event_id=event_id, detected=drift_detected)

        return event

    def store_outlier_event(
        self,
        event_id: str,
        request_id: str | None,
        is_outlier: bool,
        outlier_score: float,
        outlier_method: str,
        features: dict,
        severity: str = "info",
    ) -> OutlierEvent:
        """Store an outlier detection event.

        Args:
            event_id: Unique event ID
            request_id: Related prediction request ID
            is_outlier: Whether sample is outlier
            outlier_score: Outlier score
            outlier_method: Detection method
            features: Sample features
            severity: Event severity

        Returns:
            Created OutlierEvent
        """
        event = OutlierEvent(
            event_id=event_id,
            request_id=request_id,
            is_outlier=is_outlier,
            outlier_score=outlier_score,
            outlier_method=outlier_method,
            features=features,
            severity=severity,
        )

        self.session.add(event)
        self.session.commit()
        logger.info("outlier_event_stored", event_id=event_id, is_outlier=is_outlier)

        return event

    def get_recent_drift_events(
        self, days: int = 7, drift_detected_only: bool = True
    ) -> list[DriftEvent]:
        """Get recent drift events.

        Args:
            days: Look back this many days
            drift_detected_only: Only return events where drift was detected

        Returns:
            List of DriftEvent records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = self.session.query(DriftEvent).filter(DriftEvent.detected_at >= cutoff_date)

        if drift_detected_only:
            query = query.filter(DriftEvent.drift_detected)

        return query.order_by(desc(DriftEvent.detected_at)).all()


class RetrainingRepository:
    """Repository for retraining jobs."""

    def __init__(self, session: Session) -> None:
        """Initialize repository.

        Args:
            session: Database session
        """
        self.session = session

    def create_job(self, job_id: str, model_version: str, trigger: str) -> RetrainingJob:
        """Create a new retraining job.

        Args:
            job_id: Unique job ID
            model_version: Model version being trained
            trigger: What triggered retraining

        Returns:
            Created RetrainingJob
        """
        job = RetrainingJob(
            job_id=job_id,
            model_version=model_version,
            trigger=trigger,
            status="pending",
        )

        self.session.add(job)
        self.session.commit()
        logger.info("retraining_job_created", job_id=job_id)

        return job

    def update_job_status(
        self,
        job_id: str,
        status: str,
        metrics: dict | None = None,
        error_message: str | None = None,
    ) -> RetrainingJob | None:
        """Update retraining job status.

        Args:
            job_id: Job ID
            status: New status
            metrics: Training metrics
            error_message: Error message if failed

        Returns:
            Updated RetrainingJob or None
        """
        job = self.session.query(RetrainingJob).filter(RetrainingJob.job_id == job_id).first()

        if job:
            job.status = status

            if metrics:
                job.metrics = metrics

            if error_message:
                job.error_message = error_message

            if status in ["completed", "failed"]:
                job.completed_at = datetime.utcnow()
                if job.started_at:
                    duration = (job.completed_at - job.started_at).total_seconds()
                    job.duration_seconds = duration

            self.session.commit()
            logger.info("retraining_job_updated", job_id=job_id, status=status)

        return job

    def get_recent_jobs(self, limit: int = 10) -> list[RetrainingJob]:
        """Get recent retraining jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of RetrainingJob records
        """
        return (
            self.session.query(RetrainingJob)
            .order_by(desc(RetrainingJob.started_at))
            .limit(limit)
            .all()
        )
