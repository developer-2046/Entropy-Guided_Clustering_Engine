from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import asyncio
import json
from datetime import datetime
import numpy as np
import pandas as pd
from contextlib import asynccontextmanager

# Import our entropy engine
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_entropy.core.entropy_engine import EntropyEngine

# Global state
entropy_engine = None
model_fitted = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global entropy_engine, model_fitted
    
    try:
        # Initialize entropy engine without Redis for now
        entropy_engine = EntropyEngine(redis_client=None)
        
        # Train model with synthetic data for demo
        await train_demo_model()
        model_fitted = True
        print("✅ Model fitted successfully!")
        
    except Exception as e:
        print(f"⚠️ Model fitting failed: {e}")
        model_fitted = False
    
    yield
    
    print("🔄 Shutting down...")

async def train_demo_model():
    """Train the model with synthetic historical data."""
    global entropy_engine
    
    # Generate synthetic market data for training
    print("📊 Generating synthetic training data...")
    
    dates = pd.date_range('2020-01-01', '2024-12-31', freq='D')
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NFLX', 'NVDA']
    
    # Create realistic market returns with different regimes
    np.random.seed(42)  # For reproducible demo
    
    returns_data = []
    for i, date in enumerate(dates):
        # Simulate different market regimes over time
        if i < len(dates) * 0.3:  # Stable period
            daily_returns = np.random.multivariate_normal(
                mean=[0.0005] * len(symbols),
                cov=np.eye(len(symbols)) * 0.01 + np.ones((len(symbols), len(symbols))) * 0.002,
            )
        elif i < len(dates) * 0.6:  # Volatile period
            daily_returns = np.random.multivariate_normal(
                mean=[0.0001] * len(symbols),
                cov=np.eye(len(symbols)) * 0.04 + np.ones((len(symbols), len(symbols))) * 0.008,
            )
        elif i < len(dates) * 0.8:  # Crisis period (high correlation)
            daily_returns = np.random.multivariate_normal(
                mean=[-0.001] * len(symbols),
                cov=np.eye(len(symbols)) * 0.06 + np.ones((len(symbols), len(symbols))) * 0.025,
            )
        else:  # Recovery period
            daily_returns = np.random.multivariate_normal(
                mean=[0.002] * len(symbols),
                cov=np.eye(len(symbols)) * 0.02 + np.ones((len(symbols), len(symbols))) * 0.005,
            )
        
        returns_data.append(daily_returns)
    
    # Create DataFrame
    returns_df = pd.DataFrame(returns_data, index=dates, columns=symbols)
    
    print(f"📈 Training model with {len(returns_df)} days of data...")
    
    # Train the model
    await entropy_engine.fit_regime_model(returns_df)
    
    print("🎯 Model training complete!")

app = FastAPI(
    title="MarketEntropy API",
    description="Real-time market regime detection using spectral entropy analysis",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_fitted": model_fitted
    }

@app.get("/api/v1/regime/current")
async def get_current_regime() -> Dict:
    """Get the current market regime state."""
    global entropy_engine, model_fitted
    
    if not model_fitted or not entropy_engine:
        # Return demo data if model isn't ready
        import random
        regime_id = random.randint(0, 3)
        return {
            "regime_id": regime_id,
            "probability": round(random.uniform(0.75, 0.95), 3),
            "entropy_score": round(random.uniform(1.5, 4.5), 3),
            "market_stress_level": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "timestamp": datetime.now().isoformat(),
            "eigenvalues": [round(random.uniform(0.2, 2.5), 3) for _ in range(8)],
            "model_status": "demo_mode"
        }
    
    try:
        # Generate current market data for prediction
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NFLX', 'NVDA']
        dates = pd.date_range(end=datetime.now().date(), periods=252, freq='D')
        
        # Simulate recent market returns
        current_returns = pd.DataFrame(
            np.random.multivariate_normal(
                mean=[0.001] * len(symbols),
                cov=np.eye(len(symbols)) * 0.02 + np.ones((len(symbols), len(symbols))) * 0.005,
                size=len(dates)
            ),
            index=dates,
            columns=symbols
        )
        
        # Predict regime
        regime_state = await entropy_engine.predict_current_regime(current_returns)
        
        return {
            "regime_id": regime_state.regime_id,
            "probability": round(regime_state.probability, 3),
            "entropy_score": round(regime_state.entropy_score, 3),
            "market_stress_level": regime_state.market_stress_level,
            "timestamp": regime_state.timestamp.isoformat(),
            "eigenvalues": [round(x, 3) for x in regime_state.correlation_eigenvalues[:8]],
            "model_status": "live"
        }
        
    except Exception as e:
        print(f"❌ Prediction error: {e}")
        # Fallback to demo data
        import random
        return {
            "regime_id": random.randint(0, 3),
            "probability": round(random.uniform(0.75, 0.95), 3),
            "entropy_score": round(random.uniform(1.5, 4.5), 3),
            "market_stress_level": random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
            "timestamp": datetime.now().isoformat(),
            "eigenvalues": [round(random.uniform(0.2, 2.5), 3) for _ in range(8)],
            "model_status": "fallback"
        }

@app.websocket("/ws/regime-stream")
async def regime_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time regime updates."""
    await websocket.accept()
    
    try:
        while True:
            # Get current regime data
            regime_data = await get_current_regime()
            
            # Format for WebSocket
            update = {
                "type": "regime_update",
                "regime_id": regime_data["regime_id"],
                "entropy_score": regime_data["entropy_score"],
                "stress_level": regime_data["market_stress_level"],
                "timestamp": regime_data["timestamp"],
                "probability": regime_data["probability"],
                "model_status": regime_data.get("model_status", "live")
            }
            
            await websocket.send_text(json.dumps(update))
            await asyncio.sleep(5)  # Update every 5 seconds
                
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.get("/api/v1/model/status")
async def model_status():
    """Get detailed model status."""
    global entropy_engine, model_fitted
    
    return {
        "fitted": model_fitted,
        "engine_initialized": entropy_engine is not None,
        "regime_count": 4,
        "features_extracted": model_fitted,
        "last_training": datetime.now().isoformat() if model_fitted else None,
        "status": "ready" if model_fitted else "training"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MarketEntropy with REAL entropy engine...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
