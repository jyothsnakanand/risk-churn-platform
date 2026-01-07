"""REST API for risk/churn scoring platform."""

import uuid
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
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
    """E-commerce customer churn prediction request schema."""

    # Customer Demographics & Tenure
    customer_age_days: int = Field(..., description="Days since first purchase", ge=0)
    account_age_days: int = Field(..., description="Days since account creation", ge=0)

    # Purchase Behavior
    total_orders: int = Field(..., description="Total number of orders", ge=0)
    total_revenue: float = Field(..., description="Total customer lifetime value", ge=0)
    avg_order_value: float = Field(..., description="Average order value", ge=0)
    days_since_last_order: int = Field(..., description="Days since last purchase", ge=0)
    order_frequency: float = Field(..., description="Orders per month", ge=0)

    # Engagement Metrics
    website_visits_30d: int = Field(..., description="Website visits in last 30 days", ge=0)
    email_open_rate: float = Field(..., description="Email open rate (0-1)", ge=0, le=1)
    cart_abandonment_rate: float = Field(..., description="Cart abandonment rate (0-1)", ge=0, le=1)
    product_views_30d: int = Field(..., description="Product views in last 30 days", ge=0)

    # Customer Service
    support_tickets_total: int = Field(..., description="Total support tickets", ge=0)
    support_tickets_open: int = Field(..., description="Currently open tickets", ge=0)
    returns_count: int = Field(..., description="Number of returns", ge=0)
    refunds_count: int = Field(..., description="Number of refunds", ge=0)

    # Product Preferences
    favorite_category: str = Field(..., description="Most purchased category")
    discount_usage_rate: float = Field(..., description="Discount usage rate (0-1)", ge=0, le=1)
    premium_product_rate: float = Field(..., description="Premium products rate (0-1)", ge=0, le=1)

    # Payment & Shipping
    payment_method: str = Field(..., description="Primary payment method")
    shipping_method: str = Field(..., description="Primary shipping preference")
    failed_payment_count: int = Field(..., description="Failed payment attempts", ge=0)


class PredictionResponse(BaseModel):
    """Prediction response schema."""

    request_id: str
    predictions: list[float]
    model_version: str
    strategy: str
    latency_ms: float
    churn_probability: float
    risk_score: float


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    models: dict[str, bool]


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
        title="E-Commerce Customer Churn Prediction Platform",
        description="ML platform for predicting e-commerce customer churn and spending risk with A/B testing, drift detection, and automated retraining",
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
                # predictions is already a list from router
                pred_list = predictions if isinstance(predictions, list) else predictions.tolist()
                kafka_producer.send_prediction(
                    request_id=request_id,
                    features=features_dict,
                    predictions=pred_list,
                    model_version=result["model_version"],
                    metadata={"strategy": result["strategy"]},
                )

            # Record metrics
            PREDICTION_COUNTER.labels(model_version=result["model_version"], status="success").inc()
            PREDICTION_LATENCY.labels(model_version=result["model_version"]).observe(
                result["latency_ms"] / 1000
            )

            logger.info(
                "prediction_made",
                request_id=request_id,
                model_version=result["model_version"],
                churn_prob=churn_prob,
            )

            # predictions is already a list from result["predictions"][0]
            pred_list = predictions if isinstance(predictions, list) else predictions.tolist()

            return PredictionResponse(
                request_id=request_id,
                predictions=pred_list,
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
            ) from e

    @app.post("/explain")
    async def explain_prediction(request: PredictionRequest) -> dict[str, Any]:
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
            ) from e

    @app.get("/router/metrics")
    async def get_router_metrics() -> dict[str, Any]:
        """Get routing metrics.

        Returns:
            Routing metrics
        """
        return model_router.get_metrics()

    @app.get("/router/shadow-analysis")
    async def get_shadow_analysis() -> dict[str, Any]:
        """Get shadow deployment analysis.

        Returns:
            Shadow analysis results
        """
        return model_router.get_shadow_analysis()

    @app.post("/router/promote-v2")
    async def promote_v2() -> dict[str, str]:
        """Promote v2 to production.

        Returns:
            Success message
        """
        model_router.promote_v2()
        logger.info("v2_promoted")
        return {"message": "v2 promoted to production"}

    @app.post("/router/rollback")
    async def rollback_to_v1() -> dict[str, str]:
        """Rollback to v1.

        Returns:
            Success message
        """
        model_router.rollback_to_v1()
        logger.info("rolled_back_to_v1")
        return {"message": "Rolled back to v1"}

    return app


# Initialize default app instance for uvicorn
def _initialize_app() -> FastAPI:
    """Initialize the app with loaded models and components."""
    from pathlib import Path

    import yaml

    from risk_churn_platform.models.risk_scorer import RiskScorerV1, RiskScorerV2
    from risk_churn_platform.routers.model_router import ModelRouter, RoutingStrategy
    from risk_churn_platform.transformers.feature_transformer import FeatureTransformer

    # Load config
    config_path = Path("config/config.yaml")
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        # Default config
        config = {
            "transformer": {
                "features": [
                    "customer_age_days",
                    "account_age_days",
                    "total_orders",
                    "total_revenue",
                    "avg_order_value",
                    "days_since_last_order",
                    "order_frequency",
                    "website_visits_30d",
                    "email_open_rate",
                    "cart_abandonment_rate",
                    "product_views_30d",
                    "support_tickets_total",
                    "support_tickets_open",
                    "returns_count",
                    "refunds_count",
                    "favorite_category",
                    "discount_usage_rate",
                    "premium_product_rate",
                    "payment_method",
                    "shipping_method",
                    "failed_payment_count",
                ]
            },
            "router": {"strategy": "shadow"},
        }

    # Initialize and load transformer
    transformer_path = Path("models/transformer.pkl")
    if transformer_path.exists():
        import pickle

        with open(transformer_path, "rb") as f:
            transformer = pickle.load(f)  # nosec B301
        logger.info("loaded_transformer", path=str(transformer_path))
    else:
        # Create new transformer (won't be fitted)
        transformer = FeatureTransformer(feature_names=config["transformer"]["features"])
        logger.warning("transformer_not_found", message="Creating unfitted transformer")

    # Load models
    model_v1 = RiskScorerV1()
    model_v2 = RiskScorerV2()

    v1_path = Path("models/v1/model.pkl")
    v2_path = Path("models/v2/model.pkl")

    if v1_path.exists():
        model_v1.load(str(v1_path))
        logger.info("loaded_model_v1", path=str(v1_path))

    if v2_path.exists():
        model_v2.load(str(v2_path))
        logger.info("loaded_model_v2", path=str(v2_path))

    # Initialize router
    strategy_str = config["router"].get("strategy", "shadow")
    strategy_map = {
        "shadow": RoutingStrategy.SHADOW,
        "canary": RoutingStrategy.CANARY,
        "blue-green": RoutingStrategy.BLUE_GREEN,
    }
    model_router = ModelRouter(
        model_v1=model_v1,
        model_v2=model_v2,
        strategy=strategy_map.get(strategy_str, RoutingStrategy.SHADOW),
    )

    return create_app(
        model_router=model_router, transformer=transformer, explainer=None, kafka_producer=None
    )


# Create default app instance for uvicorn
app = _initialize_app()
