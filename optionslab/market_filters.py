"""
Market filters for options backtesting
Handles IV regime, VIX timing, trend, RSI, and Bollinger Band filters
"""

import numpy as np
from typing import Tuple, List, Dict, Optional


class MarketFilters:
    """Encapsulates all market filter logic for cleaner backtesting"""
    
    def __init__(self, config: Dict, data, unique_dates: List):
        self.config = config
        self.data = data
        self.unique_dates = unique_dates
        self.market_filters = config.get('market_filters', {})
        
    def check_all_filters(self, current_date, current_price: float, date_idx: int) -> Tuple[bool, List[str]]:
        """Check all configured market filters
        
        Returns:
            Tuple of (all_passed: bool, messages: List[str])
        """
        results = []
        messages = []
        
        # Check each filter if configured
        if 'iv_regime' in self.market_filters:
            passed, msg = self.check_iv_filter(current_date, current_price)
            results.append(passed)
            if msg:
                messages.append(msg)
                
        if 'vix_timing' in self.market_filters:
            passed, msg = self.check_vix_timing_filter(current_price, date_idx)
            results.append(passed)
            if msg:
                messages.append(msg)
                
        if 'trend_filter' in self.market_filters:
            passed, msg = self.check_ma_filter(current_price, date_idx)
            results.append(passed)
            if msg:
                messages.append(msg)
                
        if 'rsi_filter' in self.market_filters:
            passed, msg = self.check_rsi_filter(current_price, date_idx)
            results.append(passed)
            if msg:
                messages.append(msg)
                
        if 'bollinger_bands' in self.market_filters:
            passed, msg = self.check_bollinger_filter(current_price, date_idx)
            results.append(passed)
            if msg:
                messages.append(msg)
        
        # All filters must pass
        all_passed = all(results) if results else True
        return all_passed, messages
    
    def check_iv_filter(self, current_date, current_price: float) -> Tuple[bool, Optional[str]]:
        """Check IV regime filter"""
        iv_filter = self.market_filters['iv_regime']
        date_data = self.data[self.data['date'] == current_date]
        
        # Calculate average IV for at-the-money options
        atm_options = date_data[
            (abs(date_data['strike_dollars'] - current_price) <= current_price * 0.02) &
            (date_data['implied_vol'] > 0)
        ]
        
        if atm_options.empty:
            return True, None
            
        avg_iv = atm_options['implied_vol'].mean()
        min_iv = iv_filter.get('min_iv', 0.10)
        max_iv = iv_filter.get('max_iv', 0.50)
        
        if avg_iv < min_iv or avg_iv > max_iv:
            return False, f"IV regime filter blocked - Avg IV: {avg_iv:.3f} (allowed: {min_iv:.3f}-{max_iv:.3f})"
        
        return True, f"IV regime filter passed - Avg IV: {avg_iv:.3f}"
    
    def check_vix_timing_filter(self, current_price: float, date_idx: int) -> Tuple[bool, Optional[str]]:
        """Check VIX-based entry timing filter"""
        vix_filter = self.market_filters['vix_timing']
        vix_lookback = vix_filter.get('lookback_days', 10)
        vix_percentile_threshold = vix_filter.get('percentile_threshold', 75)
        vix_absolute_threshold = vix_filter.get('absolute_threshold', None)
        
        # Need enough history for VIX calculation
        if date_idx < vix_lookback - 1:
            return True, "Not enough data for VIX timing calculation"
        
        # Calculate VIX proxy using ATM option implied volatility
        current_date = self.unique_dates[date_idx]
        date_data = self.data[self.data['date'] == current_date]
        
        # Get ATM options for VIX proxy
        strike_col = 'strike_dollars' if 'strike_dollars' in date_data.columns else 'strike'
        atm_options = date_data[
            (abs(date_data[strike_col] - current_price) <= current_price * 0.02) &
            (date_data['dte'] >= 25) &  # Use ~30 DTE options for VIX proxy
            (date_data['dte'] <= 35) &
            (date_data['implied_vol'] > 0)
        ]
        
        if atm_options.empty:
            return True, None
        
        current_vix_proxy = atm_options['implied_vol'].mean() * 100  # Convert to VIX-like percentage
        
        # Calculate VIX proxy history for lookback period
        vix_history = []
        for i in range(vix_lookback):
            hist_idx = date_idx - i
            if hist_idx >= 0:
                hist_date = self.unique_dates[hist_idx]
                hist_data = self.data[self.data['date'] == hist_date]
                strike_col = 'strike_dollars' if 'strike_dollars' in hist_data.columns else 'strike'
                hist_atm = hist_data[
                    (abs(hist_data[strike_col] - hist_data['underlying_price'].iloc[0]) <= 
                     hist_data['underlying_price'].iloc[0] * 0.02) &
                    (hist_data['dte'] >= 25) &
                    (hist_data['dte'] <= 35) &
                    (hist_data['implied_vol'] > 0)
                ]
                if not hist_atm.empty:
                    vix_history.append(hist_atm['implied_vol'].mean() * 100)
        
        if len(vix_history) < vix_lookback:
            return True, None
            
        # Check absolute threshold if specified
        if vix_absolute_threshold is not None:
            strategy_type = self.config.get('strategy_type', 'long_premium')
            if strategy_type in ['short_strangle', 'iron_condor', 'short_premium']:
                # For premium selling strategies, enter when VIX is HIGH
                if current_vix_proxy < vix_absolute_threshold:
                    return False, f"VIX timing blocked - VIX proxy {current_vix_proxy:.1f} < {vix_absolute_threshold} (need high vol for premium selling)"
                return True, f"VIX timing passed - VIX proxy {current_vix_proxy:.1f} >= {vix_absolute_threshold} (good for premium selling)"
            else:
                # For premium buying strategies, enter when VIX is LOW
                if current_vix_proxy > vix_absolute_threshold:
                    return False, f"VIX timing blocked - VIX proxy {current_vix_proxy:.1f} > {vix_absolute_threshold} (need low vol for premium buying)"
                return True, f"VIX timing passed - VIX proxy {current_vix_proxy:.1f} <= {vix_absolute_threshold} (good for premium buying)"
        
        # Check percentile threshold
        vix_percentile = np.percentile(vix_history, vix_percentile_threshold)
        strategy_type = self.config.get('strategy_type', 'long_premium')
        
        if strategy_type in ['short_strangle', 'iron_condor', 'short_premium']:
            # For premium selling, enter when VIX is in upper percentile (high volatility)
            if current_vix_proxy < vix_percentile:
                return False, (f"VIX timing blocked - VIX proxy {current_vix_proxy:.1f} below "
                             f"{vix_percentile_threshold}th percentile ({vix_percentile:.1f}) - need high vol for premium selling")
            return True, (f"VIX timing passed - VIX proxy {current_vix_proxy:.1f} above "
                         f"{vix_percentile_threshold}th percentile ({vix_percentile:.1f}) - good for premium selling")
        else:
            # For premium buying, enter when VIX is in lower percentile (low volatility)
            low_percentile = 100 - vix_percentile_threshold
            vix_low_threshold = np.percentile(vix_history, low_percentile)
            if current_vix_proxy > vix_low_threshold:
                return False, (f"VIX timing blocked - VIX proxy {current_vix_proxy:.1f} above "
                             f"{low_percentile}th percentile ({vix_low_threshold:.1f}) - need low vol for premium buying")
            return True, (f"VIX timing passed - VIX proxy {current_vix_proxy:.1f} below "
                         f"{low_percentile}th percentile ({vix_low_threshold:.1f}) - good for premium buying")
    
    def check_ma_filter(self, current_price: float, date_idx: int) -> Tuple[bool, Optional[str]]:
        """Check moving average trend filter"""
        trend_filter = self.market_filters['trend_filter']
        ma_period = trend_filter.get('ma_period', 20)
        require_above_ma = trend_filter.get('require_above_ma', True)
        
        # Need enough history
        if date_idx < ma_period - 1:
            return True, "Not enough data for MA calculation"
            
        # Calculate MA
        ma_prices = []
        for j in range(ma_period):
            hist_idx = date_idx - j
            if hist_idx >= 0:
                hist_date = self.unique_dates[hist_idx]
                hist_data = self.data[self.data['date'] == hist_date]
                if not hist_data.empty:
                    ma_prices.append(hist_data['underlying_price'].iloc[0])
        
        if len(ma_prices) != ma_period:
            return True, None
            
        ma_value = sum(ma_prices) / len(ma_prices)
        
        if require_above_ma and current_price < ma_value:
            return False, f"MA trend filter blocked - Price ${current_price:.2f} < MA({ma_period}) ${ma_value:.2f}"
        elif not require_above_ma and current_price > ma_value:
            return False, f"MA trend filter blocked - Price ${current_price:.2f} > MA({ma_period}) ${ma_value:.2f}"
        
        return True, f"MA trend filter passed - Price ${current_price:.2f} vs MA({ma_period}) ${ma_value:.2f}"
    
    def check_rsi_filter(self, current_price: float, date_idx: int) -> Tuple[bool, Optional[str]]:
        """Check RSI filter"""
        rsi_filter = self.market_filters['rsi_filter']
        rsi_period = rsi_filter.get('period', 14)
        rsi_oversold = rsi_filter.get('oversold', 30)
        rsi_overbought = rsi_filter.get('overbought', 70)
        
        # Need enough history
        if date_idx < rsi_period:
            return True, "Not enough data for RSI calculation"
        
        # Calculate RSI
        rsi = self._calculate_rsi(date_idx, rsi_period)
        if rsi is None:
            return True, None
            
        # Apply RSI entry rules based on strategy type
        strategy_type = self.config['strategy_type']
        if strategy_type in ['long_call', 'short_put']:
            # Bullish strategies - enter on oversold
            if rsi > rsi_oversold:
                return False, f"RSI filter blocked - RSI {rsi:.1f} > {rsi_oversold} (not oversold)"
            return True, f"RSI filter passed - RSI {rsi:.1f} <= {rsi_oversold} (oversold)"
        else:
            # Bearish strategies - enter on overbought
            if rsi < rsi_overbought:
                return False, f"RSI filter blocked - RSI {rsi:.1f} < {rsi_overbought} (not overbought)"
            return True, f"RSI filter passed - RSI {rsi:.1f} >= {rsi_overbought} (overbought)"
    
    def check_bollinger_filter(self, current_price: float, date_idx: int) -> Tuple[bool, Optional[str]]:
        """Check Bollinger Bands filter"""
        bb_filter = self.market_filters['bollinger_bands']
        bb_period = bb_filter.get('period', 20)
        bb_std_dev = bb_filter.get('std_dev', 2.0)
        
        # Need enough history
        if date_idx < bb_period - 1:
            return True, "Not enough data for Bollinger Bands calculation"
            
        # Calculate Bollinger Bands
        bands = self._calculate_bollinger_bands(date_idx, bb_period, bb_std_dev)
        if bands is None:
            return True, None
            
        middle_band, upper_band, lower_band = bands
        band_position = (current_price - lower_band) / (upper_band - lower_band) if upper_band > lower_band else 0.5
        
        # Apply entry rules
        if bb_filter.get('entry_at_bands', True):
            strategy_type = self.config['strategy_type']
            if strategy_type in ['long_call', 'short_put']:
                # Bullish - enter near lower band
                lower_threshold = bb_filter.get('lower_band_threshold', 0.2)
                if band_position > lower_threshold:
                    return False, f"BB filter blocked - Price at {band_position:.1%} of bands (need < {lower_threshold:.0%})"
                return True, (f"BB filter passed - Price near lower band ({band_position:.1%})\n"
                            f"   Lower: ${lower_band:.2f}, Price: ${current_price:.2f}, Upper: ${upper_band:.2f}")
            else:
                # Bearish - enter near upper band
                upper_threshold = bb_filter.get('upper_band_threshold', 0.8)
                if band_position < upper_threshold:
                    return False, f"BB filter blocked - Price at {band_position:.1%} of bands (need > {upper_threshold:.0%})"
                return True, (f"BB filter passed - Price near upper band ({band_position:.1%})\n"
                            f"   Lower: ${lower_band:.2f}, Price: ${current_price:.2f}, Upper: ${upper_band:.2f}")
        
        return True, None
    
    def _calculate_rsi(self, date_idx: int, period: int = 14) -> Optional[float]:
        """Calculate RSI for given date index"""
        price_changes = []
        for j in range(period + 1):
            hist_idx = date_idx - j
            if hist_idx >= 0 and hist_idx > 0:
                curr_date = self.unique_dates[hist_idx]
                prev_date = self.unique_dates[hist_idx - 1]
                curr_data = self.data[self.data['date'] == curr_date]
                prev_data = self.data[self.data['date'] == prev_date]
                if not curr_data.empty and not prev_data.empty:
                    change = curr_data['underlying_price'].iloc[0] - prev_data['underlying_price'].iloc[0]
                    price_changes.append(change)
        
        if len(price_changes) < period:
            return None
            
        # Calculate average gains and losses
        gains = [c for c in price_changes[:period] if c > 0]
        losses = [-c for c in price_changes[:period] if c < 0]
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100 if avg_gain > 0 else 50
            
        return rsi
    
    def _calculate_bollinger_bands(self, date_idx: int, period: int, std_dev: float) -> Optional[Tuple[float, float, float]]:
        """Calculate Bollinger Bands for given date index"""
        bb_prices = []
        for j in range(period):
            hist_idx = date_idx - j
            if hist_idx >= 0:
                hist_date = self.unique_dates[hist_idx]
                hist_data = self.data[self.data['date'] == hist_date]
                if not hist_data.empty:
                    bb_prices.append(hist_data['underlying_price'].iloc[0])
        
        if len(bb_prices) != period:
            return None
            
        # Calculate bands
        middle_band = sum(bb_prices) / len(bb_prices)
        variance = sum((p - middle_band) ** 2 for p in bb_prices) / len(bb_prices)
        std = variance ** 0.5
        
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)
        
        return middle_band, upper_band, lower_band
    
    def calculate_current_rsi(self, date_idx: int) -> Optional[float]:
        """Public method to get current RSI (for exit conditions)"""
        return self._calculate_rsi(date_idx)
        
    def calculate_current_bollinger_bands(self, date_idx: int) -> Optional[Tuple[float, float, float]]:
        """Public method to get current Bollinger Bands (for exit conditions)"""
        bb_filter = self.market_filters.get('bollinger_bands', {})
        period = bb_filter.get('period', 20)
        std_dev = bb_filter.get('std_dev', 2.0)
        return self._calculate_bollinger_bands(date_idx, period, std_dev)