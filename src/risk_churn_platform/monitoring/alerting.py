"""Alerting system for monitoring events."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure."""

    alert_type: str
    severity: AlertSeverity
    message: str
    details: dict[str, Any]
    timestamp: datetime
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary.

        Returns:
            Dictionary representation of alert
        """
        return {
            "alert_type": self.alert_type,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }


class AlertHandler(ABC):
    """Abstract base class for alert handlers."""

    @abstractmethod
    def send_alert(self, alert: Alert) -> None:
        """Send an alert.

        Args:
            alert: Alert to send
        """
        pass


class LogAlertHandler(AlertHandler):
    """Send alerts to structured logs."""

    def send_alert(self, alert: Alert) -> None:
        """Send alert to logs.

        Args:
            alert: Alert to send
        """
        logger_method = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(alert.severity, logger.info)

        logger_method(
            alert.alert_type,
            message=alert.message,
            severity=alert.severity.value,
            source=alert.source,
            **alert.details,
        )


class KafkaAlertHandler(AlertHandler):
    """Send alerts to Kafka topic."""

    def __init__(self, kafka_producer: Any, topic: str) -> None:
        """Initialize Kafka alert handler.

        Args:
            kafka_producer: Kafka producer instance
            topic: Kafka topic for alerts
        """
        self.producer = kafka_producer
        self.topic = topic

    def send_alert(self, alert: Alert) -> None:
        """Send alert to Kafka.

        Args:
            alert: Alert to send
        """
        try:
            alert_json = json.dumps(alert.to_dict())
            self.producer.send(self.topic, value=alert_json.encode())
            logger.debug("alert_sent_to_kafka", alert_type=alert.alert_type)
        except Exception as e:
            logger.error("failed_to_send_alert_to_kafka", error=str(e))


class AlertManager:
    """Manage and route alerts to various handlers."""

    def __init__(self) -> None:
        """Initialize alert manager."""
        self.handlers: list[AlertHandler] = []
        self.alert_history: list[Alert] = []
        self.max_history_size = 1000

    def add_handler(self, handler: AlertHandler) -> None:
        """Add an alert handler.

        Args:
            handler: Alert handler to add
        """
        self.handlers.append(handler)
        logger.info("alert_handler_added", handler_type=type(handler).__name__)

    def send_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        details: dict[str, Any] | None = None,
        source: str = "risk-churn-platform",
    ) -> None:
        """Create and send an alert.

        Args:
            alert_type: Type of alert
            severity: Alert severity
            message: Alert message
            details: Additional details
            source: Source of alert
        """
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details or {},
            timestamp=datetime.now(),
            source=source,
        )

        # Send to all handlers
        for handler in self.handlers:
            try:
                handler.send_alert(alert)
            except Exception as e:
                logger.error(
                    "alert_handler_failed",
                    handler_type=type(handler).__name__,
                    error=str(e),
                )

        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size :]

    def get_recent_alerts(
        self, limit: int = 100, severity: AlertSeverity | None = None
    ) -> list[dict[str, Any]]:
        """Get recent alerts.

        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity level

        Returns:
            List of recent alerts
        """
        alerts = self.alert_history
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return [a.to_dict() for a in alerts[-limit:]]


# Global alert manager instance
alert_manager = AlertManager()
alert_manager.add_handler(LogAlertHandler())
