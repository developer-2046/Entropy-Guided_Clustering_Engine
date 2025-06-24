import pytest
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, patch
from market_entropy.core.entropy_engine import EntropyEngine, RegimeState

class TestEntropyEngine:
    """Test cases for the entropy engine."""
    
    @pytest.mark.asyncio
    async def test_correlation_entropy_calculation(self, entropy_engine, mock_market_data):
        """Test basic entropy calculation from returns."""
        # Test with stable market data
        stable_data = mock_market_data.iloc[:50]  # First 50 days
        entropy = await entropy_engine.calculate_correlation_entropy(stable_data)
        
        assert isinstance(entropy, float)
        assert entropy > 0
        assert entropy < 10  # Reasonable upper bound
        
        # Test with volatile market data (March crisis period)
        volatile_data = mock_market_data.loc['2023-03-01':'2023-03-15']
        volatile_entropy = await entropy_engine.calculate_correlation_entropy(volatile_data)
        
        assert volatile_entropy > entropy  # Crisis should have higher entropy
    
    @pytest.mark.asyncio 
    async def test_entropy_features_extraction(self, entropy_engine, mock_market_data):
        """Test feature extraction for regime classification."""
        returns_window = mock_market_data.iloc[:252]  # One year of data
        features = await entropy_engine.extract_entropy_features(returns_window)
        
        assert isinstance(features, np.ndarray)
        assert len(features) >= 8  # Should have multiple features
        assert np.all(np.isfinite(features))  # No NaN or inf values
        assert np.all(features >= 0)  # Entropy features should be positive
    
    @pytest.mark.asyncio
    async def test_model_fitting(self, entropy_engine, mock_market_data):
        """Test regime model training."""
        # Ensure we have enough data
        assert len(mock_market_data) >= 300
        
        await entropy_engine.fit_regime_model(mock_market_data)
        
        assert entropy_engine.is_fitted
        assert hasattr(entropy_engine, 'regime_stats')
        assert len(entropy_engine.regime_stats) == entropy_engine.n_regimes
        
        # Check regime statistics are reasonable
        for regime_id, stats in entropy_engine.regime_stats.items():
            assert 'mean_entropy' in stats
            assert 'volatility' in stats
            assert 'frequency' in stats
            assert stats['mean_entropy'] > 0
            assert stats['volatility'] >= 0
            assert 0 <= stats['frequency'] <= 1
    
    @pytest.mark.asyncio
    async def test_regime_prediction(self, entropy_engine, mock_market_data):
        """Test regime prediction on fitted model."""
        # First fit the model
        await entropy_engine.fit_regime_model(mock_market_data)
        
        # Test prediction on recent data
        recent_data = mock_market_data.iloc[-252:]  # Last year
        regime_state = await entropy_engine.predict_current_regime(recent_data)
        
        # Validate regime state
        from tests import assert_valid_regime_state
        assert_valid_regime_state(regime_state)
        
        # Test crisis period prediction
        crisis_data = mock_market_data.loc['2023-03-01':'2023-04-01']
        crisis_state = await entropy_engine.predict_current_regime(crisis_data)
        
        # Crisis should have high entropy and stress
        assert crisis_state.entropy_score > regime_state.entropy_score
        assert crisis_state.market_stress_level in ['HIGH', 'CRITICAL']
    
    @pytest.mark.asyncio
    async def test_stress_level_calculation(self, entropy_engine):
        """Test market stress level determination."""
        # Test different entropy levels
        test_cases = [
            (1.5, 'LOW'),
            (2.5, 'MEDIUM'), 
            (3.2, 'HIGH'),
            (4.0, 'CRITICAL')
        ]
        
        for entropy_score, expected_stress in test_cases:
            stress_level = entropy_engine._calculate_stress_level(entropy_score)
            assert stress_level == expected_stress
    
    @pytest.mark.asyncio
    async def test_redis_caching(self, mock_redis):
        """Test Redis caching functionality."""
        entropy_engine = EntropyEngine(redis_client=mock_redis)
        
        # Test model state caching
        entropy_engine.is_fitted = True
        entropy_engine.pca = type('MockPCA', (), {
            'components_': np.random.randn(10, 8),
            'mean_': np.random.randn(8)
        })()
        entropy_engine.kmeans = type('MockKMeans', (), {
            'cluster_centers_': np.random.randn(4, 10)
        })()
        entropy_engine.regime_stats = {0: {'mean_entropy': 2.0}}
        
        await entropy_engine._cache_model_state()
        
        # Verify Redis calls
        mock_redis.hset.assert_called()
        
        # Test regime state caching
        regime_state = RegimeState(
            regime_id=1,
            probability=0.85,
            entropy_score=2.5,
            correlation_eigenvalues=[1.0, 0.8, 0.6],
            timestamp=pd.Timestamp.now(),
            market_stress_level='MEDIUM'
        )
        
        await entropy_engine._cache_regime_state(regime_state)
        
        # Verify caching and publishing
        assert mock_redis.hset.call_count >= 2
        mock_redis.publish.assert_called()

class TestEntropyEngineEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_data_handling(self, entropy_engine):
        """Test handling of empty or insufficient data."""
        empty_df = pd.DataFrame()
        entropy = await entropy_engine.calculate_correlation_entropy(empty_df)
        assert entropy == 0.0
        
        # Test with insufficient data
        small_df = pd.DataFrame({'A': [1, 2], 'B': [2, 3]})
        entropy = await entropy_engine.calculate_correlation_entropy(small_df)
        assert isinstance(entropy, float)
    
    @pytest.mark.asyncio
    async def test_prediction_without_fitting(self, entropy_engine, mock_market_data):
        """Test that prediction fails without fitting."""
        with pytest.raises(ValueError, match="Model must be fitted"):
            await entropy_engine.predict_current_regime(mock_market_data.iloc[-100:])
    
    @pytest.mark.asyncio
    async def test_numerical_stability(self, entropy_engine):
        """Test numerical stability with extreme values."""
        # Create data with extreme correlations
        extreme_data = pd.DataFrame({
            'A': [1, 1, 1, 1, 1],
            'B': [1, 1, 1, 1, 1],  # Perfect correlation
            'C': [1, -1, 1, -1, 1]  # Alternating pattern
        })
        
        entropy = await entropy_engine.calculate_correlation_entropy(extreme_data)
        assert isinstance(entropy, float)
        assert np.isfinite(entropy)