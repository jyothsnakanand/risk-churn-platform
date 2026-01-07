"""REST API for risk/churn scoring platform."""

import uuid
from typing import Any, Dict, List

import structlog
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# Prometheus metrics
PREDICTION_COUNTER = Counter(
    "predictions_total", "Total number of predictions", ["model_version", "status"]
)
PREDICTION_LATENCY = Histogram(
    "prediction_latency_seconds", "Prediction latency in seconds", ["model_version"]
)


class PredictionRequest(BaseModel):
    """Prediction request schema."""

    customer_tenure: float = Field(..., description="Customer tenure in months", ge=0)
    monthly_charges: float = Field(..., description="Monthly charges", ge=0)
    total_charges: float = Field(..., description="Total charges", ge=0)
    contract_type: str = Field(..., description="Contract type")
    payment_method: str = Field(..., description="Payment method")
    internet_service: str = Field(..., description="Internet service type")
    support_tickets: int = Field(..., description="Number of support tickets", ge=0)
    login_frequency: float = Field(..., description="Login frequency per week", ge=0)


class PredictionResponse(BaseModel):
    """Prediction response schema."""

    request_id: str
    predictions: List[float]
    model_version: str
    strategy: str
    latency_ms: float
    churn_probability: float
    risk_score: float


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    models: Dict[str, bool]


def create_app(
    model_router: Any,
    transformer: Any,
    explainer: Any | None = None,
    kafka_producer: Any | None = None,
) -> FastAPI:
    """Create FastAPI application.

    Args:
        model_router: Model router instance
        transformer: Feature transformer instance
        explainer: Optional explainer instance
        kafka_producer: Optional Kafka producer instance

    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="Risk/Churn Scoring Platform",
        description="ML platform for risk and churn prediction with A/B testing and monitoring",
        version="0.1.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    @app.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint.

        Returns:
            Health status
        """
        return HealthResponse(
            status="healthy",
            version="0.1.0",
            models={
                "v1": True,
                "v2": True,
            },
        )

    @app.post("/predict", response_model=PredictionResponse)
    async def predict(request: PredictionRequest) -> PredictionResponse:
        """Make a prediction.

        Args:
            request: Prediction request

        Returns:
            Prediction response
        """
        request_id = str(uuid.uuid4())

        try:
            # Transform features
            features_dict = request.model_dump()
            features = transformer.transform(features_dict)

            # Route to appropriate model
            result = model_router.route(features, request_id=request_id)

            # Extract predictions
            predictions = result["predictions"][0]  # First sample
            churn_prob = float(predictions[1])  # Probability of churn
            risk_score = churn_prob * 100  # Convert to risk score (0-100)

            # Send to Kafka for offline evaluation
            if kafka_producer:
                kafka_producer.send_prediction(
                    request_id=request_id,
                    features=features_dict,
                    predictions=predictions.tolist(),
                    model_version=result["model_version"],
                    metadata={"strategy": result["strategy"]},
                )

            # Record metrics
            PREDICTION_COUNTER.labels(
                model_version=result["model_version"], status="success"
            ).inc()
            PREDICTION_LATENCY.labels(model_version=result["model_version"]).observe(
                result["latency_ms"] / 1000
            )

            logger.info(
                "prediction_made",
                request_id=request_id,
                model_version=result["model_version"],
                churn_prob=churn_prob,
            )

            return PredictionResponse(
                request_id=request_id,
                predictions=predictions.tolist(),
                model_version=result["model_version"],
                strategy=result["strategy"],
                latency_ms=result["latency_ms"],
                churn_probability=churn_prob,
                risk_score=risk_score,
            )

        except Exception as e:
            logger.error("prediction_failed", request_id=request_id, error=str(e))
            PREDICTION_COUNTER.labels(model_version="unknown", status="error").inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prediction failed: {str(e)}",
            )

    @app.post("/explain")
    async def explain_prediction(request: PredictionRequest) -> Dict[str, Any]:
        """Explain a prediction.

        Args:
            request: Prediction request

        Returns:
            Explanation response
        """
        if not explainer:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Explainer not available",
            )

        try:
            # Transform features
            features_dict = request.model_dump()
            features = transformer.transform(features_dict)

            # Get explanation
            explanation = explainer.explain(features)

            logger.info("explanation_generated", method=explanation["method"])

            return explanation

        except Exception as e:
            logger.error("explanation_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Explanation failed: {str(e)}",
            )

    @app.get("/router/metrics")
    async def get_router_metrics() -> Dict[str, Any]:
        """Get routing metrics.

        Returns:
            Routing metrics
        """
        return model_router.get_metrics()

    @app.get("/router/shadow-analysis")
    async def get_shadow_analysis() -> Dict[str, Any]:
        """Get shadow deployment analysis.

        Returns:
            Shadow analysis results
        """
        return model_router.get_shadow_analysis()

    @app.post("/router/promote-v2")
    async def promote_v2() -> Dict[str, str]:
        """Promote v2 to production.

        Returns:
            Success message
        """
        model_router.promote_v2()
        logger.info("v2_promoted")
        return {"message": "v2 promoted to production"}

    @app.post("/router/rollback")
    async def rollback_to_v1() -> Dict[str, str]:
        """Rollback to v1.

        Returns:
            Success message
        """
        model_router.rollback_to_v1()
        logger.info("rolled_back_to_v1")
        return {"message": "Rolled back to v1"}

    return app
