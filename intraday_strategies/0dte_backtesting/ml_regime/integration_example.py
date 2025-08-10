"""
Example: Optional Integration of ML Regime Classification

This file demonstrates how to integrate regime predictions into existing strategies
without breaking the code if the ML module is not available.
"""

import logging
from typing import Optional, Dict
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import ML regime module
try:
    from ml_regime import RegimePredictor
    ML_REGIME_AVAILABLE = True
except ImportError:
    ML_REGIME_AVAILABLE = False
    logger.info("ML Regime module not available. Strategies will run without regime adjustments.")


class RegimeAwareStrategy:
    """Example of a strategy that optionally uses regime predictions"""
    
    def __init__(self, regime_model_path: Optional[str] = None):
        """
        Initialize strategy with optional regime awareness
        
        Args:
            regime_model_path: Path to trained regime model (optional)
        """
        self.regime_predictor = None
        
        if ML_REGIME_AVAILABLE and regime_model_path:
            try:
                self.regime_predictor = RegimePredictor(regime_model_path)
                logger.info("Regime predictor loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load regime model: {e}")
                self.regime_predictor = None
    
    def adjust_position_size(self, base_size: float, df: pd.DataFrame) -> float:
        """
        Adjust position size based on regime prediction
        
        Args:
            base_size: Base position size
            df: Recent market data
            
        Returns:
            Adjusted position size
        """
        if not self.regime_predictor:
            # No regime adjustment available
            return base_size
        
        try:
            # Get current regime
            regime_info = self.regime_predictor.get_current_regime(df)
            
            # Adjust size based on regime and confidence
            regime = regime_info['regime']
            confidence = regime_info['confidence']
            
            if confidence < 0.6:
                # Low confidence, reduce position size
                return base_size * 0.5
            
            if regime == 'Bull':
                # Increase long positions in bull regime
                return base_size * 1.2
            elif regime == 'Bear':
                # Reduce position size in bear regime
                return base_size * 0.8
            else:
                # Neutral regime, use base size
                return base_size
                
        except Exception as e:
            logger.error(f"Error getting regime prediction: {e}")
            return base_size
    
    def should_take_trade(self, signal_type: str, df: pd.DataFrame) -> bool:
        """
        Filter trades based on regime
        
        Args:
            signal_type: 'long' or 'short'
            df: Recent market data
            
        Returns:
            Whether to take the trade
        """
        if not self.regime_predictor:
            # No regime filter, take all trades
            return True
        
        try:
            regime_info = self.regime_predictor.get_current_regime(df)
            regime = regime_info['regime']
            confidence = regime_info['confidence']
            
            # Very low confidence, skip trade
            if confidence < 0.5:
                return False
            
            # Filter based on regime alignment
            if signal_type == 'long' and regime == 'Bear':
                return False  # Don't take longs in bear regime
            elif signal_type == 'short' and regime == 'Bull':
                return False  # Don't take shorts in bull regime
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking regime filter: {e}")
            return True  # Default to taking trade if error


def enhance_existing_strategy(original_strategy_function):
    """
    Decorator to add regime awareness to existing strategies
    
    Usage:
        @enhance_existing_strategy
        def my_strategy(df, params):
            # Original strategy logic
            return signals
    """
    def wrapper(df, params, regime_model_path=None):
        # Get original signals
        signals = original_strategy_function(df, params)
        
        if not ML_REGIME_AVAILABLE or not regime_model_path:
            return signals
        
        try:
            # Load regime predictor
            predictor = RegimePredictor(regime_model_path)
            regime_predictions = predictor.predict(df)
            
            # Adjust signals based on regime
            adjusted_signals = signals.copy()
            
            # Example adjustments:
            # 1. Reduce signal strength in low confidence regimes
            confidence_mask = regime_predictions['confidence'] < 0.5
            adjusted_signals[confidence_mask] = 0
            
            # 2. Filter against-the-trend signals
            bull_regime = regime_predictions['regime_name'] == 'Bull'
            bear_regime = regime_predictions['regime_name'] == 'Bear'
            
            # Remove shorts in bull regime
            adjusted_signals[(adjusted_signals < 0) & bull_regime] = 0
            
            # Remove longs in bear regime  
            adjusted_signals[(adjusted_signals > 0) & bear_regime] = 0
            
            return adjusted_signals
            
        except Exception as e:
            logger.error(f"Error applying regime filter: {e}")
            return signals  # Return original signals on error
    
    return wrapper


# Example usage in existing strategy files:
"""
# In your existing strategy file (e.g., opening_range_breakout.py):

# At the top of the file:
try:
    from ml_regime.integration_example import enhance_existing_strategy
    REGIME_ENHANCE_AVAILABLE = True
except ImportError:
    REGIME_ENHANCE_AVAILABLE = False

# In your strategy function:
def calculate_signals(df, params):
    # Your existing strategy logic
    signals = existing_logic(df, params)
    
    # Optional regime enhancement
    if REGIME_ENHANCE_AVAILABLE and params.get('use_regime_filter', False):
        signals = enhance_existing_strategy(existing_logic)(df, params, 
                                                           params.get('regime_model_path'))
    
    return signals
"""