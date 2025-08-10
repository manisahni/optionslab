"""
Main Regime Classification Interface

Provides a unified interface for market regime detection and prediction.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Union, List
import logging
from pathlib import Path
import json
from datetime import datetime

from .feature_engineering import FeatureEngineer
from .models import HMMRegimeDetector, XGBoostRegimeClassifier, EnsembleRegimeModel

logger = logging.getLogger(__name__)


class RegimeClassifier:
    """Main interface for regime classification"""
    
    def __init__(self, 
                 model_type: str = 'ensemble',
                 n_hmm_states: int = 3,
                 xgb_params: Optional[Dict] = None,
                 feature_config: Optional[Dict] = None):
        """
        Initialize regime classifier
        
        Args:
            model_type: Type of model ('hmm', 'xgboost', 'ensemble')
            n_hmm_states: Number of HMM states
            xgb_params: XGBoost parameters
            feature_config: Feature engineering configuration
        """
        self.model_type = model_type
        self.feature_engineer = FeatureEngineer()
        self.feature_config = feature_config or {}
        
        # Initialize model based on type
        if model_type == 'hmm':
            self.model = HMMRegimeDetector(n_states=n_hmm_states)
        elif model_type == 'xgboost':
            self.model = XGBoostRegimeClassifier(params=xgb_params)
        elif model_type == 'ensemble':
            self.model = EnsembleRegimeModel(n_hmm_states=n_hmm_states, xgb_params=xgb_params)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        self.fitted = False
        self.training_history = []
        
    def fit(self, df: pd.DataFrame, validation_split: float = 0.2):
        """
        Fit the regime classifier
        
        Args:
            df: DataFrame with OHLCV data
            validation_split: Validation split ratio
        """
        logger.info(f"Fitting {self.model_type} regime classifier...")
        
        # Extract features
        features = self.feature_engineer.extract_all_features(df)
        
        # Store training metadata
        training_info = {
            'timestamp': datetime.now().isoformat(),
            'n_samples': len(df),
            'n_features': len(features.columns),
            'model_type': self.model_type,
            'start_date': str(df.index[0]) if hasattr(df.index[0], 'date') else str(df.iloc[0]['date']),
            'end_date': str(df.index[-1]) if hasattr(df.index[-1], 'date') else str(df.iloc[-1]['date'])
        }
        
        # Fit model based on type
        if self.model_type == 'hmm':
            returns = df['close'].pct_change()
            volatility = returns.rolling(window=20).std()
            self.model.fit(returns, volatility)
            
        elif self.model_type == 'xgboost':
            returns = df['close'].pct_change()
            labels = self.model.prepare_labels(returns)
            self.model.fit(features, labels, validation_split)
            
            # Store feature importance
            if hasattr(self.model, 'get_feature_importance'):
                training_info['top_features'] = self.model.get_feature_importance(10).to_dict()
                
        elif self.model_type == 'ensemble':
            self.model.fit(df, features)
        
        self.fitted = True
        self.training_history.append(training_info)
        
        logger.info("Model fitting complete")
        
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict regime for new data
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with predictions and probabilities
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Extract features
        features = self.feature_engineer.extract_all_features(df)
        
        # Get predictions based on model type
        if self.model_type == 'hmm':
            returns = df['close'].pct_change()
            volatility = returns.rolling(window=20).std()
            states, probs = self.model.predict(returns, volatility)
            
            # Create results dataframe
            results = pd.DataFrame(index=df.index)
            results['regime'] = states
            results['regime_name'] = pd.Series(states).map({
                0: 'Bear', 1: 'Neutral', 2: 'Bull'
            }).values
            
            for i in range(self.model.n_states):
                results[f'prob_state_{i}'] = probs[:, i]
                
        elif self.model_type == 'xgboost':
            predictions, probs = self.model.predict(features)
            
            results = pd.DataFrame(index=df.index)
            results['regime'] = predictions
            results['regime_name'] = pd.Series(predictions).map({
                0: 'Bear', 1: 'Neutral', 2: 'Bull'
            }).values
            results['bull_prob'] = probs[:, 2]
            results['neutral_prob'] = probs[:, 1]
            results['bear_prob'] = probs[:, 0]
            
        elif self.model_type == 'ensemble':
            ensemble_results = self.model.predict(df, features)
            
            results = pd.DataFrame(index=df.index)
            results['regime'] = ensemble_results['xgb_predictions']
            results['regime_name'] = ensemble_results['regime_names']
            results['bull_prob'] = ensemble_results['bull_probability']
            results['neutral_prob'] = ensemble_results['neutral_probability']
            results['bear_prob'] = ensemble_results['bear_probability']
            results['hmm_state'] = ensemble_results['hmm_states']
            
            # Add HMM probabilities
            hmm_probs = ensemble_results['hmm_probabilities']
            for i in range(hmm_probs.shape[1]):
                results[f'hmm_prob_state_{i}'] = hmm_probs[:, i]
        
        # Add confidence score
        if 'bull_prob' in results.columns:
            results['confidence'] = results[['bull_prob', 'neutral_prob', 'bear_prob']].max(axis=1)
        else:
            # For HMM, use max probability
            prob_cols = [col for col in results.columns if col.startswith('prob_state_')]
            if prob_cols:
                results['confidence'] = results[prob_cols].max(axis=1)
        
        # Add trading signals
        results['signal'] = self._generate_signals(results)
        
        return results
    
    def _generate_signals(self, predictions: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals based on regime predictions
        
        Args:
            predictions: DataFrame with regime predictions
            
        Returns:
            Series with trading signals (1=Long, -1=Short, 0=Neutral)
        """
        signals = pd.Series(0, index=predictions.index)
        
        # Basic signal generation
        if 'regime' in predictions.columns:
            signals[predictions['regime'] == 2] = 1  # Bull -> Long
            signals[predictions['regime'] == 0] = -1  # Bear -> Short
        
        # Apply confidence threshold
        if 'confidence' in predictions.columns:
            confidence_threshold = 0.6
            signals[predictions['confidence'] < confidence_threshold] = 0
        
        return signals
    
    def evaluate_accuracy(self, df: pd.DataFrame, predictions: pd.DataFrame) -> Dict:
        """
        Evaluate regime prediction accuracy
        
        Args:
            df: Original OHLCV data
            predictions: Regime predictions
            
        Returns:
            Dict with accuracy metrics
        """
        returns = df['close'].pct_change()
        
        # Calculate forward returns at different horizons
        accuracy_results = {}
        
        horizons = [1, 5, 15, 30, 78]  # 1 bar to 1 day (78 5-min bars)
        
        for horizon in horizons:
            fwd_returns = returns.rolling(horizon).sum().shift(-horizon)
            
            # Skip if not enough forward data
            valid_mask = ~fwd_returns.isna()
            if valid_mask.sum() == 0:
                continue
            
            # Directional accuracy by regime
            results = {}
            
            for regime in ['Bull', 'Bear', 'Neutral']:
                regime_mask = (predictions['regime_name'] == regime) & valid_mask
                
                if regime_mask.sum() == 0:
                    continue
                
                regime_fwd_returns = fwd_returns[regime_mask]
                
                if regime == 'Bull':
                    # Bull regime should predict positive returns
                    correct = (regime_fwd_returns > 0).sum()
                    accuracy = correct / len(regime_fwd_returns)
                elif regime == 'Bear':
                    # Bear regime should predict negative returns
                    correct = (regime_fwd_returns < 0).sum()
                    accuracy = correct / len(regime_fwd_returns)
                else:
                    # Neutral regime - smaller moves expected
                    threshold = regime_fwd_returns.std() * 0.5
                    correct = (regime_fwd_returns.abs() < threshold).sum()
                    accuracy = correct / len(regime_fwd_returns)
                
                results[regime] = {
                    'accuracy': accuracy,
                    'count': regime_mask.sum(),
                    'avg_return': regime_fwd_returns.mean(),
                    'avg_abs_return': regime_fwd_returns.abs().mean()
                }
            
            # Overall directional accuracy (excluding neutral)
            bull_mask = predictions['regime_name'] == 'Bull'
            bear_mask = predictions['regime_name'] == 'Bear'
            
            bull_correct = ((fwd_returns > 0) & bull_mask & valid_mask).sum()
            bear_correct = ((fwd_returns < 0) & bear_mask & valid_mask).sum()
            
            total_directional = (bull_mask | bear_mask).sum()
            if total_directional > 0:
                overall_accuracy = (bull_correct + bear_correct) / total_directional
            else:
                overall_accuracy = 0
            
            results['overall'] = {
                'directional_accuracy': overall_accuracy,
                'total_predictions': valid_mask.sum()
            }
            
            accuracy_results[f'{horizon}_bars'] = results
        
        # Add confidence-based accuracy
        if 'confidence' in predictions.columns:
            confidence_results = {}
            
            for threshold in [0.5, 0.6, 0.7, 0.8]:
                high_conf_mask = predictions['confidence'] > threshold
                
                if high_conf_mask.sum() > 0:
                    # Check 5-bar forward returns for high confidence predictions
                    fwd_returns_5 = returns.rolling(5).sum().shift(-5)
                    
                    bull_high_conf = (predictions['regime_name'] == 'Bull') & high_conf_mask
                    bear_high_conf = (predictions['regime_name'] == 'Bear') & high_conf_mask
                    
                    bull_accuracy = ((fwd_returns_5 > 0) & bull_high_conf).sum() / bull_high_conf.sum() if bull_high_conf.sum() > 0 else 0
                    bear_accuracy = ((fwd_returns_5 < 0) & bear_high_conf).sum() / bear_high_conf.sum() if bear_high_conf.sum() > 0 else 0
                    
                    confidence_results[f'conf_{int(threshold*100)}'] = {
                        'threshold': threshold,
                        'count': high_conf_mask.sum(),
                        'bull_accuracy': bull_accuracy,
                        'bear_accuracy': bear_accuracy
                    }
            
            accuracy_results['confidence_based'] = confidence_results
        
        return accuracy_results
    
    def analyze_performance(self, df: pd.DataFrame, predictions: pd.DataFrame) -> Dict:
        """
        Analyze regime prediction performance
        
        Args:
            df: Original OHLCV data
            predictions: Regime predictions
            
        Returns:
            Dict with performance metrics
        """
        # Calculate returns
        returns = df['close'].pct_change()
        
        # Analyze returns by regime
        regime_analysis = {}
        
        if 'regime_name' in predictions.columns:
            for regime in predictions['regime_name'].unique():
                regime_mask = predictions['regime_name'] == regime
                regime_returns = returns[regime_mask]
                
                regime_analysis[regime] = {
                    'count': regime_mask.sum(),
                    'frequency': regime_mask.sum() / len(predictions),
                    'mean_return': regime_returns.mean(),
                    'std_return': regime_returns.std(),
                    'sharpe_ratio': regime_returns.mean() / regime_returns.std() if regime_returns.std() > 0 else 0,
                    'total_return': (1 + regime_returns).prod() - 1,
                    'win_rate': (regime_returns > 0).sum() / len(regime_returns) if len(regime_returns) > 0 else 0
                }
        
        # Analyze trading signals if available
        if 'signal' in predictions.columns:
            signal_analysis = {}
            
            # Long positions
            long_mask = predictions['signal'] == 1
            long_returns = returns[long_mask]
            signal_analysis['long'] = {
                'count': long_mask.sum(),
                'mean_return': long_returns.mean(),
                'total_return': (1 + long_returns).prod() - 1,
                'win_rate': (long_returns > 0).sum() / len(long_returns) if len(long_returns) > 0 else 0
            }
            
            # Short positions
            short_mask = predictions['signal'] == -1
            short_returns = -returns[short_mask]  # Inverse for short
            signal_analysis['short'] = {
                'count': short_mask.sum(),
                'mean_return': short_returns.mean(),
                'total_return': (1 + short_returns).prod() - 1,
                'win_rate': (short_returns > 0).sum() / len(short_returns) if len(short_returns) > 0 else 0
            }
            
            # Overall strategy
            strategy_returns = pd.Series(index=returns.index)
            strategy_returns[long_mask] = returns[long_mask]
            strategy_returns[short_mask] = -returns[short_mask]
            strategy_returns.fillna(0, inplace=True)
            
            signal_analysis['overall'] = {
                'total_return': (1 + strategy_returns).prod() - 1,
                'sharpe_ratio': strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() > 0 else 0,
                'max_drawdown': self._calculate_max_drawdown(strategy_returns)
            }
        else:
            signal_analysis = {}
        
        return {
            'regime_analysis': regime_analysis,
            'signal_analysis': signal_analysis,
            'model_type': self.model_type,
            'n_predictions': len(predictions)
        }
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from returns"""
        cum_returns = (1 + returns).cumprod()
        running_max = cum_returns.cummax()
        drawdown = (cum_returns - running_max) / running_max
        return drawdown.min()
    
    def save(self, filepath: str):
        """Save model and configuration"""
        save_path = Path(filepath)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = save_path.with_suffix('.pkl')
        self.model.save(str(model_path))
        
        # Save configuration and metadata
        config = {
            'model_type': self.model_type,
            'feature_config': self.feature_config,
            'training_history': self.training_history,
            'feature_names': self.feature_engineer.get_feature_names()
        }
        
        config_path = save_path.with_suffix('.json')
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
        logger.info(f"Configuration saved to {config_path}")
    
    def load(self, filepath: str):
        """Load model and configuration"""
        load_path = Path(filepath)
        
        # Load configuration
        config_path = load_path.with_suffix('.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        self.model_type = config['model_type']
        self.feature_config = config['feature_config']
        self.training_history = config['training_history']
        
        # Load model
        model_path = load_path.with_suffix('.pkl')
        self.model.load(str(model_path))
        self.fitted = True
        
        logger.info(f"Model loaded from {model_path}")


class RegimePredictor:
    """Simplified interface for regime prediction"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize predictor
        
        Args:
            model_path: Path to saved model (optional)
        """
        self.classifier = None
        
        if model_path:
            self.load(model_path)
    
    def train(self, df: pd.DataFrame, model_type: str = 'ensemble') -> RegimeClassifier:
        """
        Train a new regime classifier
        
        Args:
            df: Training data
            model_type: Type of model to use
            
        Returns:
            Trained classifier
        """
        self.classifier = RegimeClassifier(model_type=model_type)
        self.classifier.fit(df)
        return self.classifier
    
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get regime predictions
        
        Args:
            df: Data to predict on
            
        Returns:
            DataFrame with predictions
        """
        if not self.classifier:
            raise ValueError("No model loaded. Train a model or load from file.")
        
        return self.classifier.predict(df)
    
    def get_current_regime(self, df: pd.DataFrame) -> Dict:
        """
        Get current market regime
        
        Args:
            df: Recent market data
            
        Returns:
            Dict with current regime info
        """
        predictions = self.predict(df)
        
        # Get latest prediction
        latest = predictions.iloc[-1]
        
        current_regime = {
            'regime': latest['regime_name'],
            'confidence': latest.get('confidence', None),
            'signal': latest.get('signal', 0),
            'timestamp': df.index[-1] if hasattr(df.index[-1], 'date') else df.iloc[-1]['date']
        }
        
        # Add probabilities if available
        if 'bull_prob' in latest:
            current_regime['probabilities'] = {
                'bull': latest['bull_prob'],
                'neutral': latest['neutral_prob'],
                'bear': latest['bear_prob']
            }
        
        return current_regime
    
    def save(self, filepath: str):
        """Save the classifier"""
        if not self.classifier:
            raise ValueError("No model to save")
        
        self.classifier.save(filepath)
    
    def load(self, filepath: str):
        """Load a saved classifier"""
        self.classifier = RegimeClassifier()
        self.classifier.load(filepath)