"""
Machine Learning Models for Regime Classification

Implements:
- Hidden Markov Model (HMM) for base regime detection
- XGBoost for refined regime classification
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
import logging
import pickle
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Optional imports with fallback
try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logging.warning("hmmlearn not installed. Install with: pip install hmmlearn")

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    logging.warning("xgboost not installed. Install with: pip install xgboost")

logger = logging.getLogger(__name__)


class HMMRegimeDetector:
    """Hidden Markov Model for market regime detection"""
    
    def __init__(self, n_states: int = 3, random_state: int = 42):
        """
        Initialize HMM regime detector
        
        Args:
            n_states: Number of hidden states (regimes)
            random_state: Random seed for reproducibility
        """
        self.n_states = n_states
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.fitted = False
        
        if not HMM_AVAILABLE:
            raise ImportError("hmmlearn is required for HMM. Install with: pip install hmmlearn")
    
    def prepare_features(self, returns: pd.Series, volatility: pd.Series) -> np.ndarray:
        """
        Prepare features for HMM training
        
        Args:
            returns: Series of returns
            volatility: Series of volatility measures
            
        Returns:
            Scaled feature matrix
        """
        # Combine returns and volatility as observations
        features = pd.DataFrame({
            'returns': returns,
            'volatility': volatility
        }).dropna()
        
        return features
    
    def fit(self, returns: pd.Series, volatility: pd.Series):
        """
        Fit HMM model to historical data
        
        Args:
            returns: Series of returns
            volatility: Series of volatility measures
        """
        logger.info(f"Fitting HMM with {self.n_states} states...")
        
        # Prepare features
        features = self.prepare_features(returns, volatility)
        
        # Scale features
        X = self.scaler.fit_transform(features)
        
        # Initialize and fit HMM
        self.model = hmm.GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            n_iter=100,
            random_state=self.random_state
        )
        
        self.model.fit(X)
        self.fitted = True
        
        # Log model parameters
        logger.info(f"Transition matrix:\n{self.model.transmat_}")
        logger.info(f"State means:\n{self.model.means_}")
        
    def predict(self, returns: pd.Series, volatility: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict regime states
        
        Args:
            returns: Series of returns
            volatility: Series of volatility measures
            
        Returns:
            states: Predicted state sequence
            probabilities: Probability of each state at each time
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Prepare features
        features = self.prepare_features(returns, volatility)
        
        # Scale features
        X = self.scaler.transform(features)
        
        # Predict states
        states = self.model.predict(X)
        
        # Get state probabilities
        probabilities = self.model.predict_proba(X)
        
        return states, probabilities
    
    def get_regime_characteristics(self, returns: pd.Series, volatility: pd.Series) -> Dict:
        """
        Analyze characteristics of each regime
        
        Returns:
            Dict with regime statistics
        """
        if not self.fitted:
            raise ValueError("Model must be fitted first")
        
        states, _ = self.predict(returns, volatility)
        
        # Create dataframe for analysis
        data = pd.DataFrame({
            'returns': returns,
            'volatility': volatility,
            'state': states
        })
        
        # Calculate statistics for each state
        regime_stats = {}
        for state in range(self.n_states):
            state_data = data[data['state'] == state]
            regime_stats[f'regime_{state}'] = {
                'mean_return': state_data['returns'].mean(),
                'std_return': state_data['returns'].std(),
                'mean_volatility': state_data['volatility'].mean(),
                'frequency': len(state_data) / len(data),
                'sharpe': state_data['returns'].mean() / state_data['returns'].std() if state_data['returns'].std() > 0 else 0
            }
        
        return regime_stats
    
    def save(self, filepath: str):
        """Save model to file"""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'n_states': self.n_states,
                'fitted': self.fitted
            }, f)
    
    def load(self, filepath: str):
        """Load model from file"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.n_states = data['n_states']
            self.fitted = data['fitted']


class XGBoostRegimeClassifier:
    """XGBoost classifier for refined regime prediction"""
    
    def __init__(self, params: Optional[Dict] = None, random_state: int = 42):
        """
        Initialize XGBoost regime classifier
        
        Args:
            params: XGBoost parameters
            random_state: Random seed
        """
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.fitted = False
        self.feature_importance = None
        
        if not XGB_AVAILABLE:
            raise ImportError("xgboost is required. Install with: pip install xgboost")
        
        # Default parameters optimized for regime classification
        self.params = params or {
            'objective': 'multi:softprob',
            'num_class': 3,  # Bull, Bear, Neutral
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': self.random_state,
            'use_label_encoder': False,
            'eval_metric': 'mlogloss'
        }
    
    def prepare_labels(self, returns: pd.Series, 
                      bull_threshold: float = 0.001, 
                      bear_threshold: float = -0.001) -> pd.Series:
        """
        Create regime labels from returns
        
        Args:
            returns: Series of returns
            bull_threshold: Threshold for bullish regime
            bear_threshold: Threshold for bearish regime
            
        Returns:
            Series of regime labels (0=Bear, 1=Neutral, 2=Bull)
        """
        # Use forward returns for labeling
        forward_returns = returns.shift(-1)
        
        labels = pd.Series(1, index=returns.index)  # Default to neutral
        labels[forward_returns > bull_threshold] = 2  # Bull
        labels[forward_returns < bear_threshold] = 0  # Bear
        
        return labels
    
    def fit(self, features: pd.DataFrame, labels: pd.Series, 
            validation_split: float = 0.2):
        """
        Fit XGBoost model
        
        Args:
            features: Feature matrix
            labels: Regime labels
            validation_split: Validation set size
        """
        logger.info("Fitting XGBoost regime classifier...")
        
        # Remove NaN values
        valid_idx = features.notna().all(axis=1) & labels.notna()
        X = features[valid_idx]
        y = labels[valid_idx]
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=validation_split, 
            random_state=self.random_state, stratify=y
        )
        
        # Create DMatrix
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dval = xgb.DMatrix(X_val, label=y_val)
        
        # Train model
        evallist = [(dtrain, 'train'), (dval, 'eval')]
        self.model = xgb.train(
            self.params,
            dtrain,
            num_boost_round=self.params.get('n_estimators', 100),
            evals=evallist,
            early_stopping_rounds=10,
            verbose_eval=False
        )
        
        self.fitted = True
        
        # Get feature importance
        importance = self.model.get_score(importance_type='gain')
        self.feature_importance = pd.Series(importance).sort_values(ascending=False)
        
        # Log performance
        logger.info(f"Training complete. Best score: {self.model.best_score}")
        
    def predict(self, features: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict regime states
        
        Args:
            features: Feature matrix
            
        Returns:
            predictions: Predicted regime classes
            probabilities: Probability of each regime
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Scale features
        X_scaled = self.scaler.transform(features)
        
        # Create DMatrix
        dtest = xgb.DMatrix(X_scaled)
        
        # Get probabilities
        probabilities = self.model.predict(dtest)
        
        # Get class predictions
        predictions = np.argmax(probabilities, axis=1)
        
        return predictions, probabilities
    
    def get_feature_importance(self, top_n: int = 20) -> pd.Series:
        """Get top feature importances"""
        if self.feature_importance is None:
            raise ValueError("Model must be fitted first")
        
        return self.feature_importance.head(top_n)
    
    def save(self, filepath: str):
        """Save model to file"""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'scaler': self.scaler,
                'params': self.params,
                'fitted': self.fitted,
                'feature_importance': self.feature_importance
            }, f)
    
    def load(self, filepath: str):
        """Load model from file"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.scaler = data['scaler']
            self.params = data['params']
            self.fitted = data['fitted']
            self.feature_importance = data.get('feature_importance')


class EnsembleRegimeModel:
    """Ensemble model combining HMM and XGBoost"""
    
    def __init__(self, n_hmm_states: int = 3, xgb_params: Optional[Dict] = None):
        """
        Initialize ensemble model
        
        Args:
            n_hmm_states: Number of HMM states
            xgb_params: XGBoost parameters
        """
        self.hmm_model = HMMRegimeDetector(n_states=n_hmm_states)
        self.xgb_model = XGBoostRegimeClassifier(params=xgb_params)
        self.fitted = False
    
    def fit(self, df: pd.DataFrame, features: pd.DataFrame):
        """
        Fit ensemble model
        
        Args:
            df: DataFrame with price data
            features: Feature matrix from FeatureEngineer
        """
        logger.info("Fitting ensemble regime model...")
        
        # Fit HMM on returns and volatility
        returns = df['close'].pct_change()
        volatility = returns.rolling(window=20).std()
        
        self.hmm_model.fit(returns, volatility)
        
        # Get HMM predictions
        hmm_states, hmm_probs = self.hmm_model.predict(returns, volatility)
        
        # Add HMM predictions to features
        enhanced_features = features.copy()
        enhanced_features['hmm_state'] = hmm_states
        for i in range(self.hmm_model.n_states):
            enhanced_features[f'hmm_prob_state_{i}'] = hmm_probs[:, i]
        
        # Create labels for XGBoost
        labels = self.xgb_model.prepare_labels(returns)
        
        # Fit XGBoost with enhanced features
        self.xgb_model.fit(enhanced_features, labels)
        
        self.fitted = True
        
    def predict(self, df: pd.DataFrame, features: pd.DataFrame) -> Dict:
        """
        Get ensemble predictions
        
        Returns:
            Dict with predictions and probabilities
        """
        if not self.fitted:
            raise ValueError("Model must be fitted before prediction")
        
        # Get HMM predictions
        returns = df['close'].pct_change()
        volatility = returns.rolling(window=20).std()
        hmm_states, hmm_probs = self.hmm_model.predict(returns, volatility)
        
        # Enhance features with HMM predictions
        enhanced_features = features.copy()
        enhanced_features['hmm_state'] = hmm_states
        for i in range(self.hmm_model.n_states):
            enhanced_features[f'hmm_prob_state_{i}'] = hmm_probs[:, i]
        
        # Get XGBoost predictions
        xgb_predictions, xgb_probs = self.xgb_model.predict(enhanced_features)
        
        # Combine predictions
        regime_names = ['Bear', 'Neutral', 'Bull']
        
        return {
            'hmm_states': hmm_states,
            'hmm_probabilities': hmm_probs,
            'xgb_predictions': xgb_predictions,
            'xgb_probabilities': xgb_probs,
            'regime_names': [regime_names[i] for i in xgb_predictions],
            'bull_probability': xgb_probs[:, 2],
            'bear_probability': xgb_probs[:, 0],
            'neutral_probability': xgb_probs[:, 1]
        }