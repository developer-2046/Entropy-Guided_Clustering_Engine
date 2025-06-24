import asyncio
import logging
from celery import Celery
from datetime import datetime, timedelta
import redis.asyncio as redis
from ..core.entropy_engine import EntropyEngine
from ..services.market_data import MarketDataService
import os

# Celery configuration
celery_app = Celery(
    "market_entropy_worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'update-regime-every-5-minutes': {
            'task': 'market_entropy.worker.tasks.update_market_regime',
            'schedule': 300.0,  # 5 minutes
        },
        'train-model-daily': {
            'task': 'market_entropy.worker.tasks.retrain_model',
            'schedule': 86400.0,  # Daily
        },
    }
)

logger = logging.getLogger(__name__)

@celery_app.task
def update_market_regime():
    """Update market regime detection in background."""
    asyncio.run(_update_market_regime_async())

async def _update_market_regime_async():
    """Async version of regime update."""
    try:
        # Initialize services
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        entropy_engine = EntropyEngine(redis_client=redis_client)
        
        # Check if model is fitted
        model_exists = await redis_client.exists("entropy_model")
        if not model_exists:
            logger.warning("Model not found, skipping regime update")
            return
        
        # Get latest market data
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not api_key:
            logger.error("Missing Alpha Vantage API key")
            return
            
        async with MarketDataService(api_key) as market_service:
            returns_data = await market_service.get_latest_returns()
            
            if returns_data.empty:
                logger.warning("No market data available")
                return
            
            # Predict regime
            regime_state = await entropy_engine.predict_current_regime(returns_data)
            logger.info(f"Updated regime: {regime_state.regime_id}, "
                       f"entropy: {regime_state.entropy_score:.3f}, "
                       f"stress: {regime_state.market_stress_level}")
        
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"Failed to update market regime: {e}")

@celery_app.task  
def retrain_model():
    """Retrain the entropy model daily."""
    asyncio.run(_retrain_model_async())

async def _retrain_model_async():
    """Async model retraining."""
    try:
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        entropy_engine = EntropyEngine(redis_client=redis_client)
        
        api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        async with MarketDataService(api_key) as market_service:
            # Get extended historical data for training
            historical_data = await market_service.get_latest_returns(lookback_days=1000)
            
            if len(historical_data) < 500:
                logger.warning("Insufficient data for retraining")
                return
            
            # Retrain model
            await entropy_engine.fit_regime_model(historical_data)
            logger.info("Model retrained successfully")
        
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"Failed to retrain model: {e}")


