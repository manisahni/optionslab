"""
Cache Manager for 0DTE Trading Analysis
Improves performance by caching expensive computations
"""

import pickle
import hashlib
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Callable
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages caching for expensive operations like backtests and calculations
    """
    
    def __init__(self, cache_dir: str = ".cache"):
        """Initialize cache manager with specified directory"""
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0
        }
    
    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"Created cache directory: {self.cache_dir}")
    
    def _generate_cache_key(self, *args, **kwargs) -> str:
        """Generate unique cache key from function arguments"""
        # Convert arguments to string representation
        key_data = {
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        
        # Create hash of the key data
        key_str = json.dumps(key_data, sort_keys=True)
        cache_key = hashlib.md5(key_str.encode()).hexdigest()
        
        return cache_key
    
    def _get_cache_filepath(self, cache_key: str, prefix: str = "") -> str:
        """Get full file path for cache entry"""
        filename = f"{prefix}_{cache_key}.pkl" if prefix else f"{cache_key}.pkl"
        return os.path.join(self.cache_dir, filename)
    
    def get(self, cache_key: str, prefix: str = "") -> Optional[Any]:
        """Retrieve item from cache"""
        filepath = self._get_cache_filepath(cache_key, prefix)
        
        if os.path.exists(filepath):
            try:
                # Check if cache is expired (older than 24 hours)
                file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_age > timedelta(hours=24):
                    logger.info(f"Cache expired for key: {cache_key}")
                    self.cache_stats['misses'] += 1
                    return None
                
                with open(filepath, 'rb') as f:
                    data = pickle.load(f)
                    self.cache_stats['hits'] += 1
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return data
            except Exception as e:
                logger.error(f"Error loading cache for key {cache_key}: {e}")
                self.cache_stats['misses'] += 1
                return None
        
        self.cache_stats['misses'] += 1
        return None
    
    def set(self, cache_key: str, data: Any, prefix: str = "") -> bool:
        """Store item in cache"""
        filepath = self._get_cache_filepath(cache_key, prefix)
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
                self.cache_stats['saves'] += 1
                logger.debug(f"Cached data for key: {cache_key}")
                return True
        except Exception as e:
            logger.error(f"Error saving cache for key {cache_key}: {e}")
            return False
    
    def clear_cache(self, older_than_hours: Optional[int] = None):
        """Clear cache entries, optionally only those older than specified hours"""
        cleared = 0
        
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.pkl'):
                filepath = os.path.join(self.cache_dir, filename)
                
                if older_than_hours:
                    file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_age < timedelta(hours=older_than_hours):
                        continue
                
                try:
                    os.remove(filepath)
                    cleared += 1
                except Exception as e:
                    logger.error(f"Error removing cache file {filename}: {e}")
        
        logger.info(f"Cleared {cleared} cache entries")
        return cleared
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'saves': self.cache_stats['saves'],
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_files': len([f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')])
        }


# Global cache instance
_cache_manager = CacheManager()


def cached_strategy_backtest(strategy_name: str):
    """
    Decorator for caching strategy backtest results
    
    Usage:
        @cached_strategy_backtest("orb")
        def backtest_orb(df, timeframe, ...):
            # expensive backtest code
            return results
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            cache_key = _cache_manager._generate_cache_key(
                strategy_name,
                *args[1:],  # Skip 'self' if it's a method
                **kwargs
            )
            
            # Try to get from cache
            cached_result = _cache_manager.get(cache_key, prefix=f"strategy_{strategy_name}")
            if cached_result is not None:
                logger.info(f"Using cached results for {strategy_name} strategy")
                return cached_result
            
            # Run the actual function
            logger.info(f"Computing {strategy_name} strategy (not in cache)")
            result = func(*args, **kwargs)
            
            # Cache the result
            _cache_manager.set(cache_key, result, prefix=f"strategy_{strategy_name}")
            
            return result
        
        return wrapper
    return decorator


def cached_indicator(indicator_name: str):
    """
    Decorator for caching technical indicator calculations
    
    Usage:
        @cached_indicator("vwap")
        def calculate_vwap(df):
            # expensive calculation
            return vwap_series
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # For DataFrames, use shape and date range as part of key
            key_args = []
            for arg in args:
                if isinstance(arg, pd.DataFrame):
                    key_args.append(f"df_shape_{arg.shape}_dates_{arg.index[0]}_{arg.index[-1]}")
                elif isinstance(arg, pd.Series):
                    key_args.append(f"series_len_{len(arg)}")
                else:
                    key_args.append(str(arg))
            
            cache_key = _cache_manager._generate_cache_key(
                indicator_name,
                *key_args,
                **kwargs
            )
            
            # Try to get from cache
            cached_result = _cache_manager.get(cache_key, prefix=f"indicator_{indicator_name}")
            if cached_result is not None:
                logger.debug(f"Using cached {indicator_name} calculation")
                return cached_result
            
            # Run the actual function
            result = func(*args, **kwargs)
            
            # Cache the result
            _cache_manager.set(cache_key, result, prefix=f"indicator_{indicator_name}")
            
            return result
        
        return wrapper
    return decorator


def cached_data_loader(data_name: str):
    """
    Decorator for caching data loading operations
    
    Usage:
        @cached_data_loader("spy_data")
        def load_spy_data(start_date, end_date):
            # expensive data loading
            return df
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = _cache_manager._generate_cache_key(
                data_name,
                *args,
                **kwargs
            )
            
            # Try to get from cache
            cached_result = _cache_manager.get(cache_key, prefix=f"data_{data_name}")
            if cached_result is not None:
                logger.info(f"Using cached {data_name} data")
                return cached_result
            
            # Load the data
            logger.info(f"Loading {data_name} data (not in cache)")
            result = func(*args, **kwargs)
            
            # Cache the result
            _cache_manager.set(cache_key, result, prefix=f"data_{data_name}")
            
            return result
        
        return wrapper
    return decorator


# Convenience functions
def clear_all_cache():
    """Clear all cached data"""
    return _cache_manager.clear_cache()


def clear_old_cache(hours: int = 24):
    """Clear cache entries older than specified hours"""
    return _cache_manager.clear_cache(older_than_hours=hours)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    stats = _cache_manager.get_stats()
    stats['cache_directory'] = _cache_manager.cache_dir
    stats['cache_size_mb'] = sum(
        os.path.getsize(os.path.join(_cache_manager.cache_dir, f))
        for f in os.listdir(_cache_manager.cache_dir)
        if f.endswith('.pkl')
    ) / (1024 * 1024)  # Convert to MB
    
    return stats


# Example usage in strategies
def apply_caching_to_strategy(strategy_class):
    """
    Apply caching to a strategy class's backtest method
    
    Usage:
        ORBStrategy = apply_caching_to_strategy(ORBStrategy)
    """
    original_backtest = strategy_class.backtest
    
    @cached_strategy_backtest(strategy_class.__name__)
    def cached_backtest(self, *args, **kwargs):
        return original_backtest(self, *args, **kwargs)
    
    strategy_class.backtest = cached_backtest
    return strategy_class