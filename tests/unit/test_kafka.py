"""Unit tests for Kafka components."""

import pytest
from unittest.mock import MagicMock, patch, call
from kafka.errors import KafkaError

from risk_churn_platform.kafka.producer import PredictionProducer
from risk_churn_platform.kafka.consumer import FeedbackConsumer, PredictionConsumer


@pytest.fixture
def mock_kafka_producer() -> MagicMock:
    """Create mock Kafka producer.

    Returns:
        Mock KafkaProducer
    """
    with patch('risk_churn_platform.kafka.producer.KafkaProducer') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_kafka_consumer() -> MagicMock:
    """Create mock Kafka consumer.

    Returns:
        Mock KafkaConsumer
    """
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


# Producer Tests


def test_prediction_producer_initialization(mock_kafka_producer: MagicMock) -> None:
    """Test PredictionProducer initialization."""
    with patch('risk_churn_platform.kafka.producer.KafkaProducer'):
        producer = PredictionProducer(
            bootstrap_servers=['localhost:9092'],
            predictions_topic='test.predictions',
            drift_alerts_topic='test.drift',
            outliers_topic='test.outliers'
        )

        assert producer.predictions_topic == 'test.predictions'
        assert producer.drift_alerts_topic == 'test.drift'
        assert producer.outliers_topic == 'test.outliers'


def test_send_prediction(mock_kafka_producer: MagicMock) -> None:
    """Test sending prediction event."""
    with patch('risk_churn_platform.kafka.producer.KafkaProducer') as mock_producer_class:
        mock_producer_class.return_value = mock_kafka_producer

        # Setup mock future
        mock_future = MagicMock()
        mock_kafka_producer.send.return_value = mock_future

        producer = PredictionProducer(bootstrap_servers=['localhost:9092'])

        producer.send_prediction(
            request_id='test-123',
            features={'feature1': 1.0},
            predictions=[0.3, 0.7],
            model_version='v1',
            metadata={'strategy': 'shadow'}
        )

        # Verify send was called
        assert mock_kafka_producer.send.called
        call_args = mock_kafka_producer.send.call_args

        # Check topic
        assert call_args[0][0] == 'ml.predictions'

        # Check key
        assert call_args[1]['key'] == 'test-123'

        # Check value structure
        value = call_args[1]['value']
        assert value['request_id'] == 'test-123'
        assert value['model_version'] == 'v1'
        assert 'timestamp' in value


def test_send_drift_alert(mock_kafka_producer: MagicMock) -> None:
    """Test sending drift alert."""
    with patch('risk_churn_platform.kafka.producer.KafkaProducer') as mock_producer_class:
        mock_producer_class.return_value = mock_kafka_producer

        mock_future = MagicMock()
        mock_kafka_producer.send.return_value = mock_future

        producer = PredictionProducer(bootstrap_servers=['localhost:9092'])

        drift_result = {'is_drift': True, 'p_value': 0.01}
        producer.send_drift_alert(drift_result, severity='warning')

        # Verify send was called
        assert mock_kafka_producer.send.called
        call_args = mock_kafka_producer.send.call_args

        # Check topic
        assert call_args[0][0] == 'ml.drift-alerts'

        # Check value
        value = call_args[1]['value']
        assert value['event_type'] == 'drift_detected'
        assert value['severity'] == 'warning'


def test_send_outlier_event(mock_kafka_producer: MagicMock) -> None:
    """Test sending outlier event."""
    with patch('risk_churn_platform.kafka.producer.KafkaProducer') as mock_producer_class:
        mock_producer_class.return_value = mock_kafka_producer

        mock_future = MagicMock()
        mock_kafka_producer.send.return_value = mock_future

        producer = PredictionProducer(bootstrap_servers=['localhost:9092'])

        outlier_result = {'num_outliers': 5, 'outlier_rate': 0.05}
        producer.send_outlier_event(outlier_result, severity='info')

        # Verify send was called
        assert mock_kafka_producer.send.called
        call_args = mock_kafka_producer.send.call_args

        # Check topic
        assert call_args[0][0] == 'ml.outliers'


def test_producer_flush(mock_kafka_producer: MagicMock) -> None:
    """Test flushing producer."""
    with patch('risk_churn_platform.kafka.producer.KafkaProducer') as mock_producer_class:
        mock_producer_class.return_value = mock_kafka_producer

        producer = PredictionProducer(bootstrap_servers=['localhost:9092'])
        producer.flush()

        mock_kafka_producer.flush.assert_called_once()


def test_producer_close(mock_kafka_producer: MagicMock) -> None:
    """Test closing producer."""
    with patch('risk_churn_platform.kafka.producer.KafkaProducer') as mock_producer_class:
        mock_producer_class.return_value = mock_kafka_producer

        producer = PredictionProducer(bootstrap_servers=['localhost:9092'])
        producer.close()

        mock_kafka_producer.close.assert_called_once()


# Consumer Tests


def test_feedback_consumer_initialization(mock_kafka_consumer: MagicMock) -> None:
    """Test FeedbackConsumer initialization."""
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer'):
        consumer = FeedbackConsumer(
            bootstrap_servers=['localhost:9092'],
            topic='test.feedback',
            group_id='test-group',
            auto_offset_reset='earliest'
        )

        assert consumer.topic == 'test.feedback'


def test_feedback_consumer_consume(mock_kafka_consumer: MagicMock) -> None:
    """Test consuming feedback messages."""
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer') as mock_consumer_class:
        # Setup mock messages
        mock_message = MagicMock()
        mock_message.value = {'customer_id': '123', 'label': 1}
        mock_message.offset = 100
        mock_message.partition = 0

        mock_kafka_consumer.__iter__.return_value = [mock_message]
        mock_consumer_class.return_value = mock_kafka_consumer

        consumer = FeedbackConsumer(bootstrap_servers=['localhost:9092'])

        # Mock callback
        callback = MagicMock()

        # Consume with max 1 message
        consumer.consume(callback, max_messages=1)

        # Verify callback was called
        callback.assert_called_once_with(mock_message.value)

        # Verify commit was called
        mock_kafka_consumer.commit.assert_called_once()


def test_feedback_consumer_error_handling(mock_kafka_consumer: MagicMock) -> None:
    """Test consumer error handling."""
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer') as mock_consumer_class:
        # Setup mock message that will cause processing error
        mock_message = MagicMock()
        mock_message.value = {'data': 'test'}
        mock_message.offset = 100
        mock_message.partition = 0

        mock_kafka_consumer.__iter__.return_value = [mock_message]
        mock_consumer_class.return_value = mock_kafka_consumer

        consumer = FeedbackConsumer(bootstrap_servers=['localhost:9092'])

        # Callback that raises error
        def error_callback(message):
            raise ValueError("Processing error")

        # Should not raise, just log error
        consumer.consume(error_callback, max_messages=1)

        # Verify close was called
        mock_kafka_consumer.close.assert_called_once()


def test_feedback_consumer_close(mock_kafka_consumer: MagicMock) -> None:
    """Test closing feedback consumer."""
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer') as mock_consumer_class:
        mock_consumer_class.return_value = mock_kafka_consumer

        consumer = FeedbackConsumer(bootstrap_servers=['localhost:9092'])
        consumer.close()

        mock_kafka_consumer.close.assert_called_once()


def test_prediction_consumer_initialization(mock_kafka_consumer: MagicMock) -> None:
    """Test PredictionConsumer initialization."""
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer'):
        consumer = PredictionConsumer(
            bootstrap_servers=['localhost:9092'],
            topic='test.predictions',
            group_id='test-eval-group'
        )

        assert consumer.topic == 'test.predictions'
        assert len(consumer.predictions_buffer) == 0


def test_prediction_consumer_collect_predictions(mock_kafka_consumer: MagicMock) -> None:
    """Test collecting predictions."""
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer') as mock_consumer_class:
        # Setup mock messages
        mock_messages = []
        for i in range(5):
            mock_msg = MagicMock()
            mock_msg.value = {
                'request_id': f'test-{i}',
                'predictions': [0.3, 0.7],
                'model_version': 'v1'
            }
            mock_messages.append(mock_msg)

        mock_kafka_consumer.__iter__.return_value = mock_messages
        mock_consumer_class.return_value = mock_kafka_consumer

        consumer = PredictionConsumer(bootstrap_servers=['localhost:9092'])

        predictions = consumer.collect_predictions(max_messages=3)

        # Should collect exactly 3 messages
        assert len(predictions) == 3
        assert predictions[0]['request_id'] == 'test-0'
        assert predictions[2]['request_id'] == 'test-2'


def test_prediction_consumer_close(mock_kafka_consumer: MagicMock) -> None:
    """Test closing prediction consumer."""
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer') as mock_consumer_class:
        mock_consumer_class.return_value = mock_kafka_consumer

        consumer = PredictionConsumer(bootstrap_servers=['localhost:9092'])
        consumer.close()

        mock_kafka_consumer.close.assert_called_once()


def test_prediction_consumer_error_handling(mock_kafka_consumer: MagicMock) -> None:
    """Test prediction consumer error handling."""
    with patch('risk_churn_platform.kafka.consumer.KafkaConsumer') as mock_consumer_class:
        # Make consumer raise error
        mock_kafka_consumer.__iter__.side_effect = KafkaError("Connection error")
        mock_consumer_class.return_value = mock_kafka_consumer

        consumer = PredictionConsumer(bootstrap_servers=['localhost:9092'])

        predictions = consumer.collect_predictions(max_messages=10)

        # Should return empty list on error
        assert len(predictions) == 0
