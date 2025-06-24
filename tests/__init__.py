"""
Test suite for MarketEntropy.

This module contains all tests for the market regime detection system.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
TEST_CONFIG = {
    "redis_url": "redis://localhost:6379/1",  # Use different DB for tests
    "test_db_url": "postgresql://test_user:test_pass@localhost:5432/test_marketentropy",
    "alpha_vantage_key": "test_key",
    "test_timeout": 30,
}

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.hget.return_value = None
    redis_mock.hset.return_value = True
    redis_mock.publish.return_value = 1
    redis_mock.exists.return_value = False
    return redis_mock

@pytest.fixture
def mock_market_data():
    """Mock market data for testing."""
    import pandas as pd
    import numpy as np
    
    # Generate synthetic market data
    dates = pd.date_range('2023-01-01', periods=300, freq='D')
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NFLX', 'NVDA']
    
    # Create realistic return patterns
    np.random.seed(42)  # For reproducible tests
    returns = pd.DataFrame(
        np.random.multivariate_normal(
            mean=[0.001] * len(symbols),
            cov=np.eye(len(symbols)) * 0.02 + np.ones((len(symbols), len(symbols))) * 0.005,
            size=len(dates)
        ),
        index=dates,
        columns=symbols
    )
    
    # Add some volatility clusters (regime changes)
    crisis_period = returns.loc['2023-03-01':'2023-03-15']
    returns.loc['2023-03-01':'2023-03-15'] = crisis_period * 3  # 3x volatility
    
    return returns

@pytest.fixture
async def entropy_engine(mock_redis):
    """Create entropy engine instance for testing."""
    from market_entropy.core.entropy_engine import EntropyEngine
    engine = EntropyEngine(redis_client=mock_redis)
    return engine

# Utility functions for testing
def assert_valid_regime_state(regime_state):
    """Assert that a regime state object is valid."""
    assert hasattr(regime_state, 'regime_id')
    assert hasattr(regime_state, 'probability')
    assert hasattr(regime_state, 'entropy_score')
    assert hasattr(regime_state, 'market_stress_level')
    assert hasattr(regime_state, 'timestamp')
    
    assert 0 <= regime_state.regime_id <= 3
    assert 0 <= regime_state.probability <= 1
    assert regime_state.entropy_score > 0
    assert regime_state.market_stress_level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

def create_test_correlation_matrix(size=8, regime_type='stable'):
    """Create test correlation matrices for different regime types."""
    import numpy as np
    
    if regime_type == 'stable':
        # Low correlation, stable market
        base_corr = 0.2
        noise = 0.1
    elif regime_type == 'volatile':
        # Medium correlation, volatile market  
        base_corr = 0.5
        noise = 0.2
    elif regime_type == 'crisis':
        # High correlation, crisis market
        base_corr = 0.8
        noise = 0.1
    else:
        base_corr = 0.3
        noise = 0.15
    
    # Generate correlation matrix
    corr_matrix = np.eye(size)
    for i in range(size):
        for j in range(i+1, size):
            corr = base_corr + np.random.normal(0, noise)
            corr = np.clip(corr, -0.95, 0.95)  # Keep correlations in valid range
            corr_matrix[i, j] = corr_matrix[j, i] = corr
    
    return corr_matrix
