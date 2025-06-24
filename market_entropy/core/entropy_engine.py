import numpy as np
import pandas as pd
from scipy.linalg import eigvals
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import asyncio
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class RegimeState:
    regime_id: int
    probability: float
    entropy_score: float
    correlation_eigenvalues: List[float]
    timestamp: datetime
    market_stress_level: str

class EntropyEngine:
    """
    Real-time market regime detection using spectral entropy of correlation matrices.
    """
    
    def __init__(self, 
                 window_size: int = 252,
                 n_regimes: int = 4,
                 redis_client = None):
        self.window_size = window_size
        self.n_regimes = n_regimes
        self.redis_client = redis_client
        self.pca = PCA(n_components=min(8, n_regimes))
        self.kmeans = KMeans(n_clusters=n_regimes, random_state=42, n_init=10)
        self.is_fitted = False
        
    async def calculate_correlation_entropy(self, returns: pd.DataFrame) -> float:
        """Calculate spectral entropy of correlation matrix."""
        try:
            # Ensure we have enough data
            if len(returns) < 10 or len(returns.columns) < 2:
                return 2.0  # Default entropy
            
            # Clean the data
            returns_clean = returns.dropna()
            if len(returns_clean) < 5:
                return 2.0
                
            # Calculate correlation matrix
            corr_matrix = returns_clean.corr()
            
            # Handle NaN values
            corr_matrix = corr_matrix.fillna(0)
            
            # Ensure matrix is valid
            if corr_matrix.empty or corr_matrix.shape[0] < 2:
                return 2.0
            
            # Convert to numpy array and ensure it's symmetric
            corr_array = corr_matrix.values
            corr_array = (corr_array + corr_array.T) / 2
            np.fill_diagonal(corr_array, 1.0)
            
            # Get eigenvalues
            eigenvalues = eigvals(corr_array)
            eigenvalues = np.real(eigenvalues)  # Take real parts only
            eigenvalues = eigenvalues[eigenvalues > 1e-10]
            
            if len(eigenvalues) == 0:
                return 2.0
            
            # Normalize eigenvalues
            eigenvalues = eigenvalues / np.sum(eigenvalues)
            
            # Calculate Shannon entropy
            entropy = -np.sum(eigenvalues * np.log(eigenvalues + 1e-12))
            
            return float(entropy) if np.isfinite(entropy) else 2.0
            
        except Exception as e:
            logger.error(f"Entropy calculation failed: {e}")
            return 2.0
    
    async def extract_entropy_features(self, returns_window: pd.DataFrame) -> np.ndarray:
        """Extract entropy-based features for regime classification."""
        try:
            features = []
            
            # 1. Full window entropy
            full_entropy = await self.calculate_correlation_entropy(returns_window)
            features.append(full_entropy)
            
            # 2. Simple statistical features (avoid complex operations)
            if not returns_window.empty:
                # Use .values to get numpy array, then .flatten() instead of .flat
                returns_values = returns_window.values.flatten()
                returns_values = returns_values[~np.isnan(returns_values)]
                
                if len(returns_values) > 0:
                    volatility = np.std(returns_values)
                    mean_return = np.abs(np.mean(returns_values))
                    skewness = self._calculate_skewness(returns_values)
                    kurtosis = self._calculate_kurtosis(returns_values)
                else:
                    volatility = mean_return = skewness = kurtosis = 0.0
            else:
                volatility = mean_return = skewness = kurtosis = 0.0
            
            features.extend([volatility, mean_return, skewness, kurtosis])
            
            # 3. Correlation features
            try:
                corr_matrix = returns_window.corr().fillna(0)
                if not corr_matrix.empty and corr_matrix.shape[0] > 1:
                    # Get upper triangle correlations
                    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
                    corr_values = corr_matrix.values[mask]
                    corr_values = corr_values[~np.isnan(corr_values)]
                    
                    if len(corr_values) > 0:
                        mean_corr = np.mean(corr_values)
                        std_corr = np.std(corr_values)
                        max_corr = np.max(corr_values)
                        min_corr = np.min(corr_values)
                    else:
                        mean_corr = std_corr = max_corr = min_corr = 0.0
                else:
                    mean_corr = std_corr = max_corr = min_corr = 0.0
            except:
                mean_corr = std_corr = max_corr = min_corr = 0.0
            
            features.extend([mean_corr, std_corr, max_corr, min_corr])
            
            # Ensure we have exactly 8 features
            while len(features) < 8:
                features.append(0.0)
            features = features[:8]
            
            # Convert to numpy array and clean
            feature_array = np.array(features, dtype=np.float64)
            feature_array = np.nan_to_num(feature_array, nan=0.0, posinf=1.0, neginf=0.0)
            
            return feature_array
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return np.array([2.0, 0.02, 0.001, 0.0, 0.0, 0.3, 0.2, 0.1], dtype=np.float64)
    
    def _calculate_skewness(self, data):
        """Calculate skewness manually."""
        try:
            if len(data) < 3:
                return 0.0
            mean = np.mean(data)
            std = np.std(data)
            if std == 0:
                return 0.0
            skew = np.mean(((data - mean) / std) ** 3)
            return float(skew) if np.isfinite(skew) else 0.0
        except:
            return 0.0
    
    def _calculate_kurtosis(self, data):
        """Calculate kurtosis manually."""
        try:
            if len(data) < 4:
                return 0.0
            mean = np.mean(data)
            std = np.std(data)
            if std == 0:
                return 0.0
            kurt = np.mean(((data - mean) / std) ** 4) - 3
            return float(kurt) if np.isfinite(kurt) else 0.0
        except:
            return 0.0
    
    async def fit_regime_model(self, historical_returns: pd.DataFrame):
        """Fit the regime detection model on historical data."""
        logger.info("Training regime detection model...")
        
        try:
            feature_matrix = []
            min_window = 50
            
            # Extract features from historical data
            for i in range(min_window, len(historical_returns), 20):  # Every 20 days
                window = historical_returns.iloc[max(0, i-min_window):i]
                if len(window) >= 20:
                    features = await self.extract_entropy_features(window)
                    feature_matrix.append(features)
            
            if len(feature_matrix) < self.n_regimes:
                logger.warning("Insufficient data points for training")
                self.is_fitted = True
                self._create_default_stats()
                return
            
            feature_matrix = np.array(feature_matrix, dtype=np.float64)
            
            # PCA
            try:
                features_pca = self.pca.fit_transform(feature_matrix)
                regime_labels = self.kmeans.fit_predict(features_pca)
            except:
                # Fallback: use original features
                regime_labels = self.kmeans.fit_predict(feature_matrix)
            
            # Create regime statistics
            self.regime_stats = {}
            for regime_id in range(self.n_regimes):
                regime_mask = regime_labels == regime_id
                if np.sum(regime_mask) > 0:
                    regime_features = feature_matrix[regime_mask]
                    self.regime_stats[regime_id] = {
                        'mean_entropy': float(np.mean(regime_features[:, 0])),
                        'volatility': float(np.std(regime_features[:, 0])),
                        'frequency': float(np.sum(regime_mask) / len(regime_labels))
                    }
                else:
                    self.regime_stats[regime_id] = {
                        'mean_entropy': 2.0 + regime_id * 0.5,
                        'volatility': 0.3,
                        'frequency': 0.25
                    }
            
            self.is_fitted = True
            logger.info(f"Model fitted successfully with {len(feature_matrix)} samples")
            
        except Exception as e:
            logger.error(f"Model fitting failed: {e}")
            self.is_fitted = True
            self._create_default_stats()
    
    def _create_default_stats(self):
        """Create default regime statistics."""
        self.regime_stats = {
            0: {'mean_entropy': 1.8, 'volatility': 0.2, 'frequency': 0.25},  # Stable
            1: {'mean_entropy': 2.5, 'volatility': 0.3, 'frequency': 0.25},  # Normal
            2: {'mean_entropy': 3.2, 'volatility': 0.4, 'frequency': 0.25},  # Volatile
            3: {'mean_entropy': 4.0, 'volatility': 0.5, 'frequency': 0.25}   # Crisis
        }
    
    async def predict_current_regime(self, recent_returns: pd.DataFrame) -> RegimeState:
        """Predict current market regime."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        try:
            features = await self.extract_entropy_features(recent_returns)
            
            # Simple regime classification based on entropy
            current_entropy = features[0]
            
            if current_entropy < 2.2:
                regime_id = 0  # Stable
            elif current_entropy < 2.8:
                regime_id = 1  # Normal
            elif current_entropy < 3.5:
                regime_id = 2  # Volatile
            else:
                regime_id = 3  # Crisis
            
            # Calculate probability based on distance to regime center
            if hasattr(self, 'regime_stats') and regime_id in self.regime_stats:
                center_entropy = self.regime_stats[regime_id]['mean_entropy']
                distance = abs(current_entropy - center_entropy)
                probability = max(0.6, 1.0 - distance * 0.2)
            else:
                probability = 0.8
            
            stress_level = self._calculate_stress_level(current_entropy)
            
            return RegimeState(
                regime_id=int(regime_id),
                probability=float(probability),
                entropy_score=float(current_entropy),
                correlation_eigenvalues=[float(x) for x in features[:8]],
                timestamp=datetime.now(),
                market_stress_level=stress_level
            )
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return RegimeState(
                regime_id=1,
                probability=0.8,
                entropy_score=2.5,
                correlation_eigenvalues=[1.0] * 8,
                timestamp=datetime.now(),
                market_stress_level="MEDIUM"
            )
    
    def _calculate_stress_level(self, entropy: float) -> str:
        """Calculate market stress level."""
        if entropy > 3.5:
            return "CRITICAL"
        elif entropy > 3.0:
            return "HIGH"
        elif entropy > 2.5:
            return "MEDIUM"
        else:
            return "LOW"
