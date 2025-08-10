# ML Regime Classification Module

This module provides machine learning-based market regime classification for 0DTE trading strategies. It's designed as a completely isolated addon that won't interfere with existing trading code.

## Features

- **Hidden Markov Model (HMM)**: Detects market regimes based on returns and volatility patterns
- **XGBoost Classifier**: Provides refined regime predictions using comprehensive feature engineering
- **Ensemble Model**: Combines HMM and XGBoost for robust predictions
- **Comprehensive Feature Engineering**: Includes technical indicators, volume patterns, volatility measures (HAR-RV), and market microstructure features

## Installation

The module requires additional dependencies:

```bash
pip install hmmlearn xgboost
```

## Usage

### Standalone Script

Use the `analyze_regime.py` script for regime analysis:

```bash
# Train a new model
python analyze_regime.py --train --model-type ensemble --days 365

# Predict current regime
python analyze_regime.py --predict

# Backtest regime strategy
python analyze_regime.py --backtest --days 90
```

### Programmatic Usage

```python
from ml_regime import RegimeClassifier, RegimePredictor

# Train a new model
classifier = RegimeClassifier(model_type='ensemble')
classifier.fit(df)  # df is your OHLCV data

# Make predictions
predictions = classifier.predict(df)

# Get current regime
predictor = RegimePredictor()
current_regime = predictor.get_current_regime(df)
```

## Model Types

1. **HMM**: Good for detecting broad market states
2. **XGBoost**: Better for refined predictions with many features
3. **Ensemble**: Combines both approaches (recommended)

## Features Used

- **Technical Indicators**: EMAs (20, 50, 200), RSI, Bollinger Bands
- **Volume Features**: OBV, volume ratios, dollar volume
- **Volatility**: HAR-RV components (daily, weekly, monthly)
- **Market Microstructure**: Spread, efficiency ratio, tick momentum
- **Time Features**: Time of day, opening range periods

## Integration with Existing Strategies

The module is designed to be optional. To integrate regime predictions into existing strategies:

```python
# In your strategy file
try:
    from ml_regime import RegimePredictor
    predictor = RegimePredictor('path/to/saved/model')
    regime_info = predictor.get_current_regime(df)
    
    # Use regime info to adjust strategy
    if regime_info['regime'] == 'Bull' and regime_info['confidence'] > 0.7:
        # Favor long positions
        pass
except ImportError:
    # ML regime module not available, continue normally
    pass
```

## Model Performance

The module provides comprehensive performance analysis:
- Regime statistics (frequency, returns, Sharpe ratio)
- Trading signal performance (win rate, total return)
- Backtest results vs buy-and-hold

## Files

- `feature_engineering.py`: Feature extraction pipeline
- `models.py`: HMM, XGBoost, and Ensemble model implementations
- `regime_classifier.py`: Main interface and utilities
- `analyze_regime.py`: Standalone analysis script

## Notes

- Models are saved in the `ml_models/` directory
- The module is completely isolated and won't break existing code
- All dependencies are optional with proper fallbacks