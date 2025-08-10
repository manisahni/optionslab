"""
Breakout Detection for ORB Strategy
Detects and validates breakouts from opening range
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, Optional, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BreakoutDetector:
    """
    Detect and validate breakouts from opening range
    Implements filters to avoid false breakouts
    """
    
    def __init__(self, 
                 confirmation_bars: int = 2,
                 min_breakout_distance: float = 0.0001,
                 volume_surge_multiplier: float = 1.5):
        """
        Initialize breakout detector
        
        Args:
            confirmation_bars: Number of bars to confirm breakout
            min_breakout_distance: Minimum distance from range (% of price)
            volume_surge_multiplier: Volume must be X times average
        """
        self.confirmation_bars = confirmation_bars
        self.min_breakout_distance = min_breakout_distance
        self.volume_surge_multiplier = volume_surge_multiplier
        
        # Track breakouts to ensure one per day
        self.daily_breakout_triggered = False
        self.last_breakout_date = None
        
        logger.info("Breakout Detector initialized")
    
    def detect_breakout(self, current_bar: pd.Series, or_levels: Dict, 
                       historical_bars: pd.DataFrame = None) -> Dict:
        """
        Detect if current bar represents a breakout
        
        Args:
            current_bar: Current price bar
            or_levels: Opening range levels from ORBCalculator
            historical_bars: Recent bars for confirmation
            
        Returns:
            Dict with breakout details or None
        """
        if not or_levels or not or_levels.get('valid'):
            return None
        
        # Check if we already had a breakout today
        current_date = current_bar.name.date() if hasattr(current_bar.name, 'date') else current_bar.name
        if self.last_breakout_date == current_date and self.daily_breakout_triggered:
            return None
        
        # Get price levels
        or_high = or_levels['high']
        or_low = or_levels['low']
        current_price = current_bar['close']
        current_high = current_bar['high']
        current_low = current_bar['low']
        
        # Check for breakout
        breakout_type = None
        breakout_level = None
        
        # Bullish breakout (above OR high)
        if current_price > or_high:
            distance = (current_price - or_high) / or_high
            if distance >= self.min_breakout_distance:
                breakout_type = 'bullish'
                breakout_level = or_high
        
        # Bearish breakout (below OR low)
        elif current_price < or_low:
            distance = (or_low - current_price) / or_low
            if distance >= self.min_breakout_distance:
                breakout_type = 'bearish'
                breakout_level = or_low
        
        if not breakout_type:
            return None
        
        # Validate breakout
        is_valid = self.validate_breakout(
            current_bar, 
            breakout_type, 
            breakout_level,
            or_levels,
            historical_bars
        )
        
        if not is_valid:
            return None
        
        # Calculate breakout strength
        strength = self.calculate_breakout_strength(
            current_bar,
            breakout_type,
            breakout_level,
            or_levels
        )
        
        # Mark breakout as triggered for the day
        self.daily_breakout_triggered = True
        self.last_breakout_date = current_date
        
        breakout_info = {
            'timestamp': current_bar.name,
            'type': breakout_type,
            'breakout_level': breakout_level,
            'entry_price': current_price,
            'or_high': or_high,
            'or_low': or_low,
            'or_range': or_levels['range'],
            'strength': strength,
            'volume': current_bar.get('volume', 0),
            'distance_from_range': abs(current_price - breakout_level)
        }
        
        logger.info(f"{breakout_type.upper()} breakout detected at {current_price:.2f}")
        
        return breakout_info
    
    def validate_breakout(self, current_bar: pd.Series, breakout_type: str,
                         breakout_level: float, or_levels: Dict,
                         historical_bars: pd.DataFrame = None) -> bool:
        """
        Validate breakout with multiple filters
        
        Args:
            current_bar: Current price bar
            breakout_type: 'bullish' or 'bearish'
            breakout_level: Price level of breakout
            or_levels: Opening range levels
            historical_bars: Recent bars for analysis
            
        Returns:
            True if breakout is valid
        """
        # Check time - no breakouts in first/last 30 minutes
        current_time = current_bar.name.time() if hasattr(current_bar.name, 'time') else None
        if current_time:
            if current_time < time(10, 0) or current_time > time(15, 30):
                logger.debug(f"Breakout outside valid time window: {current_time}")
                return False
        
        # Volume validation
        current_volume = current_bar.get('volume', 0)
        avg_volume = or_levels.get('avg_bar_volume', 0)
        
        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            if volume_ratio < self.volume_surge_multiplier:
                logger.debug(f"Insufficient volume surge: {volume_ratio:.2f}x")
                return False
        
        # Check for false breakout (price must stay outside range)
        if historical_bars is not None and len(historical_bars) >= self.confirmation_bars:
            recent_bars = historical_bars.tail(self.confirmation_bars)
            
            if breakout_type == 'bullish':
                # All recent closes should be above OR high
                if not all(recent_bars['close'] > or_levels['high']):
                    logger.debug("Failed confirmation: Price fell back below OR high")
                    return False
            else:
                # All recent closes should be below OR low
                if not all(recent_bars['close'] < or_levels['low']):
                    logger.debug("Failed confirmation: Price rose back above OR low")
                    return False
        
        return True
    
    def calculate_breakout_strength(self, current_bar: pd.Series, 
                                   breakout_type: str, breakout_level: float,
                                   or_levels: Dict) -> float:
        """
        Calculate breakout strength score (0-100)
        
        Args:
            current_bar: Current price bar
            breakout_type: 'bullish' or 'bearish'
            breakout_level: Price level of breakout
            or_levels: Opening range levels
            
        Returns:
            Strength score from 0-100
        """
        strength_score = 50  # Base score
        
        # Distance from breakout level (up to 20 points)
        current_price = current_bar['close']
        distance_pct = abs(current_price - breakout_level) / breakout_level
        distance_score = min(20, distance_pct * 1000)
        strength_score += distance_score
        
        # Volume surge (up to 20 points)
        current_volume = current_bar.get('volume', 0)
        avg_volume = or_levels.get('avg_bar_volume', 1)
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        volume_score = min(20, (volume_ratio - 1) * 10)
        strength_score += volume_score
        
        # Speed of breakout (up to 10 points)
        # How quickly after OR did breakout occur
        time_since_or = (current_bar.name - or_levels['end_time']).total_seconds() / 60
        if time_since_or < 30:  # Within 30 minutes
            speed_score = 10
        elif time_since_or < 60:  # Within 1 hour
            speed_score = 5
        else:
            speed_score = 0
        strength_score += speed_score
        
        return min(100, max(0, strength_score))
    
    def scan_for_breakouts(self, data: pd.DataFrame, or_levels: Dict) -> List[Dict]:
        """
        Scan historical data for all breakouts
        
        Args:
            data: DataFrame with price data
            or_levels: Opening range levels
            
        Returns:
            List of breakout events
        """
        if not or_levels or not or_levels.get('valid'):
            return []
        
        # Filter data after opening range
        post_or_data = data[data.index > or_levels['end_time']]
        
        if post_or_data.empty:
            return []
        
        breakouts = []
        
        # Reset daily flag for scanning
        self.daily_breakout_triggered = False
        
        for idx, bar in post_or_data.iterrows():
            # Use last few bars for confirmation
            bar_position = post_or_data.index.get_loc(idx)
            if bar_position >= self.confirmation_bars:
                historical = post_or_data.iloc[bar_position-self.confirmation_bars:bar_position]
            else:
                historical = None
            
            breakout = self.detect_breakout(bar, or_levels, historical)
            
            if breakout:
                breakouts.append(breakout)
                break  # Only first breakout of the day
        
        return breakouts
    
    def reset_daily_flag(self):
        """Reset the daily breakout flag for new trading day"""
        self.daily_breakout_triggered = False
        self.last_breakout_date = None
        logger.info("Daily breakout flag reset")


def main():
    """Test the breakout detector"""
    
    # Create sample data with a breakout
    dates = pd.date_range(start='2024-01-02 09:30', end='2024-01-02 16:00', freq='1min')
    
    # Simulate price data with breakout at 11:00
    prices = []
    base_price = 450
    
    for i, date in enumerate(dates):
        hour = date.hour
        minute = date.minute
        
        # Opening range: 9:30-10:30, price between 449-451
        if hour == 9 or (hour == 10 and minute < 30):
            price = base_price + np.random.uniform(-1, 1)
        # Breakout at 11:00
        elif hour == 11 and minute == 0:
            price = 451.5  # Break above OR high
        elif hour >= 11:
            price = 451.5 + np.random.uniform(0, 0.5)  # Stay above
        else:
            price = base_price + np.random.uniform(-0.5, 0.5)
        
        prices.append(price)
    
    data = pd.DataFrame({
        'open': prices,
        'high': [p + 0.1 for p in prices],
        'low': [p - 0.1 for p in prices],
        'close': prices,
        'volume': np.random.randint(100000, 1000000, len(dates))
    }, index=dates)
    
    # Simulate OR levels
    or_levels = {
        'high': 451,
        'low': 449,
        'range': 2,
        'end_time': pd.Timestamp('2024-01-02 10:30'),
        'avg_bar_volume': 500000,
        'valid': True
    }
    
    print("Testing Breakout Detector\n" + "="*50)
    
    # Initialize detector
    detector = BreakoutDetector()
    
    # Scan for breakouts
    breakouts = detector.scan_for_breakouts(data, or_levels)
    
    if breakouts:
        for breakout in breakouts:
            print(f"\nBreakout Detected:")
            print(f"Type: {breakout['type']}")
            print(f"Time: {breakout['timestamp']}")
            print(f"Entry Price: ${breakout['entry_price']:.2f}")
            print(f"Strength: {breakout['strength']:.1f}/100")
    else:
        print("No breakouts detected")


if __name__ == "__main__":
    main()