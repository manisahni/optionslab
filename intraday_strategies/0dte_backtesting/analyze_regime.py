#!/usr/bin/env python
"""
Standalone Market Regime Analysis Script

This script analyzes market regimes using the ML regime classification module.
It can be run independently without affecting the main trading application.

Usage:
    python analyze_regime.py --train       # Train a new model
    python analyze_regime.py --predict     # Use existing model for predictions
    python analyze_regime.py --backtest    # Backtest regime predictions
"""

import sys
import os
import argparse
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ml_regime import RegimeClassifier, RegimePredictor
from trading_engine.data_manager import DataManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_data_manager():
    """Initialize data manager"""
    from configuration.app_settings import TradingConfig
    config = TradingConfig()
    return DataManager(config)


def train_regime_model(data_manager: DataManager, 
                      model_type: str = 'ensemble',
                      days_back: int = 365):
    """
    Train a new regime classification model
    
    Args:
        data_manager: Data manager instance
        model_type: Type of model to train
        days_back: Number of days of historical data to use
    """
    logger.info(f"Training {model_type} regime model with {days_back} days of data...")
    
    # Get historical data
    end_date = pd.Timestamp.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Fetch data
    df = data_manager.fetch_market_data(
        'SPY',
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        interval='5min'
    )
    
    if df.empty:
        logger.error("No data available for training")
        return None
    
    logger.info(f"Loaded {len(df)} data points from {df.index[0]} to {df.index[-1]}")
    
    # Create and train classifier
    classifier = RegimeClassifier(model_type=model_type)
    classifier.fit(df)
    
    # Save model
    model_dir = Path('ml_models')
    model_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_path = model_dir / f'regime_model_{model_type}_{timestamp}'
    classifier.save(str(model_path))
    
    logger.info(f"Model saved to {model_path}")
    
    # Get performance metrics
    predictions = classifier.predict(df)
    performance = classifier.analyze_performance(df, predictions)
    
    # Print performance summary
    print("\n" + "="*60)
    print(f"REGIME MODEL TRAINING COMPLETE - {model_type.upper()}")
    print("="*60)
    
    if 'regime_analysis' in performance:
        print("\nRegime Statistics:")
        for regime, stats in performance['regime_analysis'].items():
            print(f"\n{regime}:")
            print(f"  Frequency: {stats['frequency']:.2%}")
            print(f"  Mean Return: {stats['mean_return']:.4%}")
            print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
            print(f"  Win Rate: {stats['win_rate']:.2%}")
    
    if 'signal_analysis' in performance and 'overall' in performance['signal_analysis']:
        overall = performance['signal_analysis']['overall']
        print(f"\nOverall Strategy Performance:")
        print(f"  Total Return: {overall['total_return']:.2%}")
        print(f"  Sharpe Ratio: {overall['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {overall['max_drawdown']:.2%}")
    
    return classifier


def predict_current_regime(data_manager: DataManager, model_path: str = None):
    """
    Predict current market regime
    
    Args:
        data_manager: Data manager instance
        model_path: Path to saved model (optional)
    """
    # Load latest model if no path specified
    if not model_path:
        model_dir = Path('ml_models')
        if not model_dir.exists():
            logger.error("No models found. Please train a model first.")
            return
        
        # Find latest model
        model_files = list(model_dir.glob('regime_model_*.pkl'))
        if not model_files:
            logger.error("No model files found.")
            return
        
        model_path = str(max(model_files, key=lambda p: p.stat().st_mtime).with_suffix(''))
        logger.info(f"Using model: {model_path}")
    
    # Initialize predictor
    predictor = RegimePredictor(model_path)
    
    # Get recent data (last 5 days)
    end_date = pd.Timestamp.now()
    start_date = end_date - timedelta(days=5)
    
    df = data_manager.fetch_market_data(
        'SPY',
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        interval='5min'
    )
    
    if df.empty:
        logger.error("No data available for prediction")
        return
    
    # Get predictions
    predictions = predictor.predict(df)
    current_regime = predictor.get_current_regime(df)
    
    # Print results
    print("\n" + "="*60)
    print("CURRENT MARKET REGIME ANALYSIS")
    print("="*60)
    print(f"\nTimestamp: {current_regime['timestamp']}")
    print(f"Current Regime: {current_regime['regime']}")
    print(f"Confidence: {current_regime['confidence']:.2%}")
    print(f"Trading Signal: {['Short', 'Neutral', 'Long'][current_regime['signal'] + 1]}")
    
    if 'probabilities' in current_regime:
        print("\nRegime Probabilities:")
        for regime, prob in current_regime['probabilities'].items():
            print(f"  {regime.capitalize()}: {prob:.2%}")
    
    # Show recent regime changes
    print("\nRecent Regime History (last 10 periods):")
    recent = predictions.tail(10)[['regime_name', 'confidence']].copy()
    recent.index = pd.to_datetime(recent.index)
    print(recent.to_string())


def backtest_regime_strategy(data_manager: DataManager, 
                           model_path: str = None,
                           days_back: int = 90):
    """
    Backtest regime-based trading strategy with accuracy metrics
    
    Args:
        data_manager: Data manager instance
        model_path: Path to saved model
        days_back: Number of days to backtest
    """
    # Load model
    if not model_path:
        model_dir = Path('ml_models')
        model_files = list(model_dir.glob('regime_model_*.pkl'))
        if not model_files:
            logger.error("No model files found.")
            return
        model_path = str(max(model_files, key=lambda p: p.stat().st_mtime).with_suffix(''))
    
    predictor = RegimePredictor(model_path)
    
    # Get backtest data
    end_date = pd.Timestamp.now()
    start_date = end_date - timedelta(days=days_back)
    
    df = data_manager.fetch_market_data(
        'SPY',
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        interval='5min'
    )
    
    if df.empty:
        logger.error("No data available for backtesting")
        return
    
    # Get predictions
    predictions = predictor.predict(df)
    
    # Calculate strategy returns
    returns = df['close'].pct_change()
    
    # === REGIME PREDICTION ACCURACY METRICS ===
    # Calculate forward returns for accuracy assessment
    forward_returns = {
        '1_bar': returns.shift(-1),
        '5_bars': returns.rolling(5).sum().shift(-5),
        '15_bars': returns.rolling(15).sum().shift(-15),
        '30_bars': returns.rolling(30).sum().shift(-30)
    }
    
    # Accuracy metrics for each regime
    accuracy_metrics = {}
    
    for period_name, fwd_returns in forward_returns.items():
        # Skip if not enough data
        if fwd_returns.isna().all():
            continue
            
        # Calculate accuracy: Did the regime correctly predict market direction?
        bull_mask = predictions['regime_name'] == 'Bull'
        bear_mask = predictions['regime_name'] == 'Bear'
        neutral_mask = predictions['regime_name'] == 'Neutral'
        
        # Bull regime accuracy (positive returns expected)
        bull_correct = (fwd_returns[bull_mask] > 0).sum()
        bull_total = bull_mask.sum()
        bull_accuracy = bull_correct / bull_total if bull_total > 0 else 0
        
        # Bear regime accuracy (negative returns expected)
        bear_correct = (fwd_returns[bear_mask] < 0).sum()
        bear_total = bear_mask.sum()
        bear_accuracy = bear_correct / bear_total if bear_total > 0 else 0
        
        # Overall directional accuracy
        correct_predictions = bull_correct + bear_correct
        total_predictions = bull_total + bear_total
        overall_accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
        
        accuracy_metrics[period_name] = {
            'bull_accuracy': bull_accuracy,
            'bear_accuracy': bear_accuracy,
            'overall_accuracy': overall_accuracy,
            'bull_avg_return': fwd_returns[bull_mask].mean() if bull_total > 0 else 0,
            'bear_avg_return': fwd_returns[bear_mask].mean() if bear_total > 0 else 0
        }
    
    # Regime transition accuracy
    regime_changes = predictions['regime_name'].ne(predictions['regime_name'].shift())
    transition_points = regime_changes[regime_changes].index
    
    # Check if significant moves follow regime changes
    transition_accuracy = []
    for idx in transition_points[:-5]:  # Skip last few to have forward data
        pos = predictions.index.get_loc(idx)
        if pos + 5 < len(predictions):
            next_return = returns.iloc[pos:pos+5].sum()
            new_regime = predictions.iloc[pos]['regime_name']
            
            if new_regime == 'Bull' and next_return > 0.001:  # 0.1% threshold
                transition_accuracy.append(1)
            elif new_regime == 'Bear' and next_return < -0.001:
                transition_accuracy.append(1)
            else:
                transition_accuracy.append(0)
    
    transition_acc = np.mean(transition_accuracy) if transition_accuracy else 0
    
    # === TRADING STRATEGY METRICS ===
    # Strategy returns based on signals
    strategy_returns = returns * predictions['signal'].shift(1)  # Use previous signal
    strategy_returns = strategy_returns.fillna(0)
    
    # Calculate metrics
    cumulative_returns = (1 + strategy_returns).cumprod()
    total_return = cumulative_returns.iloc[-1] - 1
    
    # Buy and hold comparison
    buy_hold_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
    
    # Win rate
    winning_trades = strategy_returns[strategy_returns > 0]
    losing_trades = strategy_returns[strategy_returns < 0]
    win_rate = len(winning_trades) / (len(winning_trades) + len(losing_trades))
    
    # Sharpe ratio
    sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252 * 78)  # Annualized
    
    # Maximum drawdown
    running_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Print results
    print("\n" + "="*60)
    print(f"REGIME STRATEGY BACKTEST RESULTS ({days_back} days)")
    print("="*60)
    
    # === REGIME PREDICTION ACCURACY ===
    print("\n🎯 REGIME PREDICTION ACCURACY:")
    print("-" * 40)
    
    for period, metrics in sorted(accuracy_metrics.items()):
        period_desc = period.replace('_', ' ')
        print(f"\n{period_desc.title()} Forward Prediction:")
        print(f"  Bull Regime Accuracy: {metrics['bull_accuracy']:.1%} (avg return: {metrics['bull_avg_return']:.3%})")
        print(f"  Bear Regime Accuracy: {metrics['bear_accuracy']:.1%} (avg return: {metrics['bear_avg_return']:.3%})")
        print(f"  Overall Directional Accuracy: {metrics['overall_accuracy']:.1%}")
    
    print(f"\nRegime Transition Accuracy: {transition_acc:.1%}")
    print(f"  (Accuracy of predicting significant moves after regime changes)")
    
    # Confidence analysis
    if 'confidence' in predictions.columns:
        high_conf_mask = predictions['confidence'] > 0.7
        high_conf_returns = strategy_returns[high_conf_mask]
        low_conf_mask = predictions['confidence'] < 0.5
        low_conf_returns = strategy_returns[low_conf_mask]
        
        print(f"\nConfidence-Based Performance:")
        print(f"  High Confidence (>70%) Win Rate: {(high_conf_returns > 0).sum() / len(high_conf_returns):.1%}" if len(high_conf_returns) > 0 else "  High Confidence: N/A")
        print(f"  Low Confidence (<50%) Win Rate: {(low_conf_returns > 0).sum() / len(low_conf_returns):.1%}" if len(low_conf_returns) > 0 else "  Low Confidence: N/A")
    
    # === TRADING STRATEGY PERFORMANCE ===
    print(f"\n📈 STRATEGY PERFORMANCE:")
    print("-" * 40)
    print(f"  Total Return: {total_return:.2%}")
    print(f"  Buy & Hold Return: {buy_hold_return:.2%}")
    print(f"  Outperformance: {(total_return - buy_hold_return):.2%}")
    
    print(f"\nRisk Metrics:")
    print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {max_drawdown:.2%}")
    print(f"  Win Rate: {win_rate:.2%}")
    
    # Regime distribution
    regime_counts = predictions['regime_name'].value_counts()
    print(f"\n📊 REGIME DISTRIBUTION:")
    print("-" * 40)
    for regime, count in regime_counts.items():
        pct = count/len(predictions)
        print(f"  {regime}: {pct:.2%} ({count:,} periods)")
    
    # Trading activity
    n_long = (predictions['signal'] == 1).sum()
    n_short = (predictions['signal'] == -1).sum()
    n_neutral = (predictions['signal'] == 0).sum()
    
    print(f"\nTrading Activity:")
    print(f"  Long positions: {n_long/len(predictions):.2%}")
    print(f"  Short positions: {n_short/len(predictions):.2%}")
    print(f"  Neutral (no position): {n_neutral/len(predictions):.2%}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Market Regime Analysis Tool')
    parser.add_argument('--train', action='store_true', help='Train a new regime model')
    parser.add_argument('--predict', action='store_true', help='Predict current regime')
    parser.add_argument('--backtest', action='store_true', help='Backtest regime strategy')
    parser.add_argument('--model-type', choices=['hmm', 'xgboost', 'ensemble'], 
                       default='ensemble', help='Model type to use')
    parser.add_argument('--days', type=int, default=365, 
                       help='Number of days of data to use')
    parser.add_argument('--model-path', type=str, help='Path to specific model file')
    
    args = parser.parse_args()
    
    # Initialize data manager
    try:
        data_manager = setup_data_manager()
    except Exception as e:
        logger.error(f"Failed to initialize data manager: {e}")
        logger.info("Please ensure API keys are configured properly")
        return
    
    # Execute requested action
    if args.train:
        train_regime_model(data_manager, args.model_type, args.days)
    elif args.predict:
        predict_current_regime(data_manager, args.model_path)
    elif args.backtest:
        backtest_regime_strategy(data_manager, args.model_path, args.days)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()