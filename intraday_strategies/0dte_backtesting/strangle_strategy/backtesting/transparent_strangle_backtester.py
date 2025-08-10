#!/usr/bin/env python3
"""
Transparent 0DTE Strangle Backtester with Educational Explanations
Designed for complete transparency and auditability of every trade
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass, asdict

# Add the parent directory to Python path to import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase

# Configure logging for transparency
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('strangle_backtest_audit.log')
    ]
)
logger = logging.getLogger('TransparentBacktester')


@dataclass
class OptionLeg:
    """Represents one leg of the strangle with full transparency"""
    strike: float
    option_type: str  # 'CALL' or 'PUT'
    bid: float
    ask: float
    mid: float
    delta: float
    gamma: float
    theta: float
    vega: float
    volume: int
    open_interest: int
    implied_volatility: float
    
    def get_explanation(self) -> str:
        """Explain this option leg in plain English"""
        return f"""
        {self.option_type} Option at ${self.strike} strike:
        - Bid: ${self.bid:.2f} (price we can sell at)
        - Ask: ${self.ask:.2f} (price we would pay to buy)
        - Mid: ${self.mid:.2f} (average of bid and ask)
        - Delta: {self.delta:.3f} ({abs(self.delta)*100:.1f}% chance of expiring in-the-money)
        - Volume: {self.volume:,} contracts traded today
        - Open Interest: {self.open_interest:,} contracts outstanding
        """


@dataclass
class StrangleTrade:
    """Complete record of a strangle trade for full auditability"""
    trade_id: int
    date: str
    entry_time: str
    exit_time: str
    
    # Market conditions
    spy_price_entry: float
    spy_price_exit: float
    vix_level: Optional[float]
    
    # Entry details
    call_leg_entry: OptionLeg
    put_leg_entry: OptionLeg
    total_credit: float
    
    # Exit details
    call_leg_exit: OptionLeg
    put_leg_exit: OptionLeg
    total_debit: float
    
    # Results
    net_pnl: float
    return_pct: float
    max_profit: float
    commission: float
    
    # Validity checks
    bid_ask_spread_ok: bool
    liquidity_ok: bool
    data_quality_score: int
    warnings: List[str]
    
    def get_entry_explanation(self) -> str:
        """Explain the entry in plain English"""
        return f"""
=== TRADE #{self.trade_id} ENTRY EXPLANATION ===
Date: {self.date}
Entry Time: {self.entry_time}

📚 WHAT IS A STRANGLE?
A strangle involves selling both a call and put option with different strikes.
We collect premium upfront and profit if SPY stays between the strikes.

MARKET CONTEXT:
- SPY Price: ${self.spy_price_entry:.2f}
- We're looking for options with ~0.30 delta (30% chance of expiring in-the-money)

CALL OPTION SELECTED:
{self.call_leg_entry.get_explanation()}
- We SELL at bid price: ${self.call_leg_entry.bid:.2f} × 100 = ${self.call_leg_entry.bid * 100:.0f} collected

PUT OPTION SELECTED:
{self.put_leg_entry.get_explanation()}
- We SELL at bid price: ${self.put_leg_entry.bid:.2f} × 100 = ${self.put_leg_entry.bid * 100:.0f} collected

TOTAL PREMIUM COLLECTED: ${self.total_credit:.2f}

⚠️ MAXIMUM RISK: Unlimited (if SPY moves far beyond strikes)
✅ MAXIMUM PROFIT: ${self.max_profit:.2f} (if SPY stays between ${self.put_leg_entry.strike}-${self.call_leg_entry.strike})
"""
    
    def get_exit_explanation(self) -> str:
        """Explain the exit and P&L calculation"""
        spy_move = self.spy_price_exit - self.spy_price_entry
        spy_move_pct = (spy_move / self.spy_price_entry) * 100
        
        return f"""
=== EXIT CALCULATION ===
Exit Time: {self.exit_time}
SPY Price: ${self.spy_price_exit:.2f} (moved ${spy_move:.2f} or {spy_move_pct:.2f}%)

CLOSING THE POSITION:
To exit, we must BUY BACK both options

CALL OPTION (${self.call_leg_entry.strike} strike):
- Current Ask: ${self.call_leg_exit.ask:.2f}
- Cost to buy back: ${self.call_leg_exit.ask:.2f} × 100 = ${self.call_leg_exit.ask * 100:.0f}

PUT OPTION (${self.put_leg_entry.strike} strike):
- Current Ask: ${self.put_leg_exit.ask:.2f}
- Cost to buy back: ${self.put_leg_exit.ask:.2f} × 100 = ${self.put_leg_exit.ask * 100:.0f}

TOTAL EXIT COST: ${self.total_debit:.2f}

PROFIT CALCULATION:
- Premium Collected: ${self.total_credit:.2f}
- Cost to Exit: -${self.total_debit:.2f}
- Commission: -${self.commission:.2f}
- Net Profit: ${self.net_pnl:.2f}
- Return: {self.return_pct:.1f}%

{'✅ This trade was successful!' if self.net_pnl > 0 else '❌ This trade resulted in a loss.'}
SPY {'stayed between' if self.put_leg_entry.strike < self.spy_price_exit < self.call_leg_entry.strike else 'moved beyond'} our strikes.
"""
    
    def get_validity_report(self) -> str:
        """Report on the validity of this backtest data"""
        return f"""
🔍 BACKTEST VALIDITY CHECKS:

{'✅' if self.bid_ask_spread_ok else '⚠️'} Bid/Ask Spreads: {'Realistic' if self.bid_ask_spread_ok else 'Wide'} (call: ${self.call_leg_entry.ask - self.call_leg_entry.bid:.2f}, put: ${self.put_leg_entry.ask - self.put_leg_entry.bid:.2f})
{'✅' if self.liquidity_ok else '⚠️'} Liquidity: {'Sufficient' if self.liquidity_ok else 'Low'} volume (call: {self.call_leg_entry.volume:,}, put: {self.put_leg_entry.volume:,})
✅ Execution: Used conservative bid/ask prices
✅ Timing: Entry at {self.entry_time}, Exit at {self.exit_time}

DATA QUALITY SCORE: {self.data_quality_score}/100

WARNINGS:
{chr(10).join(f'⚠️ {warning}' for warning in self.warnings) if self.warnings else '✅ No warnings - clean data'}
"""


class TransparentStrangleBacktester:
    """
    Transparent backtesting engine with full explanations
    """
    
    def __init__(self, commission_per_contract: float = 0.65):
        """
        Initialize the backtester
        
        Args:
            commission_per_contract: Commission charged per contract (default $0.65)
        """
        self.db = ZeroDTESPYOptionsDatabase()
        self.commission = commission_per_contract
        self.trades: List[StrangleTrade] = []
        self.trade_counter = 0
        
        logger.info("Initialized Transparent Strangle Backtester")
        
    def find_strangle_entry(self, df: pd.DataFrame, timestamp: str, 
                           delta_target: float = 0.30,
                           min_volume: int = 100) -> Optional[Tuple[OptionLeg, OptionLeg]]:
        """
        Find optimal strangle entry with transparency
        
        Args:
            df: Options data
            timestamp: Entry timestamp
            delta_target: Target delta for options
            min_volume: Minimum volume filter
            
        Returns:
            Tuple of (call_leg, put_leg) or None
        """
        # Filter to specific timestamp
        time_df = df[df['timestamp'] == timestamp].copy()
        if time_df.empty:
            logger.warning(f"No data found for timestamp {timestamp}")
            return None
        
        # Get SPY price
        spy_price = time_df.iloc[0]['underlying_price']
        if spy_price > 1000:  # Price is in cents
            spy_price = spy_price / 100
            
        # Separate calls and puts - skip volume filter if column doesn't exist
        if 'volume' in time_df.columns:
            calls = time_df[(time_df['right'] == 'CALL') & (time_df['volume'] >= min_volume)].copy()
            puts = time_df[(time_df['right'] == 'PUT') & (time_df['volume'] >= min_volume)].copy()
        else:
            calls = time_df[time_df['right'] == 'CALL'].copy()
            puts = time_df[time_df['right'] == 'PUT'].copy()
        
        if calls.empty or puts.empty:
            logger.warning(f"Insufficient liquid options at {timestamp}")
            return None
        
        # Find best call (closest to delta target)
        calls['delta_diff'] = abs(calls['delta'] - delta_target)
        best_call_row = calls.nsmallest(1, 'delta_diff').iloc[0]
        
        # Find best put (closest to delta target, remember put deltas are negative)
        puts['delta_diff'] = abs(abs(puts['delta']) - delta_target)
        best_put_row = puts.nsmallest(1, 'delta_diff').iloc[0]
        
        # Validate bid/ask
        if (best_call_row['bid'] <= 0 or best_call_row['ask'] <= 0 or
            best_put_row['bid'] <= 0 or best_put_row['ask'] <= 0):
            logger.warning(f"Invalid bid/ask prices at {timestamp}")
            return None
            
        if (best_call_row['bid'] >= best_call_row['ask'] or 
            best_put_row['bid'] >= best_put_row['ask']):
            logger.warning(f"Crossed bid/ask at {timestamp}")
            return None
        
        # Create option leg objects
        call_leg = OptionLeg(
            strike=best_call_row['strike'],
            option_type='CALL',
            bid=best_call_row['bid'],
            ask=best_call_row['ask'],
            mid=(best_call_row['bid'] + best_call_row['ask']) / 2,
            delta=best_call_row['delta'],
            gamma=best_call_row.get('gamma', 0),
            theta=best_call_row.get('theta', 0),
            vega=best_call_row.get('vega', 0),
            volume=best_call_row.get('volume', 0),
            open_interest=best_call_row.get('open_interest', 0),
            implied_volatility=best_call_row.get('implied_vol', best_call_row.get('implied_volatility', 0))
        )
        
        put_leg = OptionLeg(
            strike=best_put_row['strike'],
            option_type='PUT',
            bid=best_put_row['bid'],
            ask=best_put_row['ask'],
            mid=(best_put_row['bid'] + best_put_row['ask']) / 2,
            delta=best_put_row['delta'],
            gamma=best_put_row.get('gamma', 0),
            theta=best_put_row.get('theta', 0),
            vega=best_put_row.get('vega', 0),
            volume=best_put_row.get('volume', 0),
            open_interest=best_put_row.get('open_interest', 0),
            implied_volatility=best_put_row.get('implied_vol', best_put_row.get('implied_volatility', 0))
        )
        
        logger.info(f"Found strangle: Call ${call_leg.strike} (δ={call_leg.delta:.3f}), "
                   f"Put ${put_leg.strike} (δ={put_leg.delta:.3f})")
        
        return call_leg, put_leg
    
    def find_exit_prices(self, df: pd.DataFrame, timestamp: str,
                        call_strike: float, put_strike: float) -> Optional[Tuple[OptionLeg, OptionLeg]]:
        """Find exit prices for existing position"""
        # Filter to exit time and our strikes
        exit_df = df[(df['timestamp'] == timestamp) & 
                     ((df['strike'] == call_strike) | (df['strike'] == put_strike))]
        
        if len(exit_df) < 2:
            logger.warning(f"Cannot find both legs at exit time {timestamp}")
            return None
        
        # Get call and put exit data
        call_exit = exit_df[exit_df['strike'] == call_strike].iloc[0]
        put_exit = exit_df[exit_df['strike'] == put_strike].iloc[0]
        
        # Create exit leg objects
        call_leg = OptionLeg(
            strike=call_exit['strike'],
            option_type='CALL',
            bid=call_exit['bid'],
            ask=call_exit['ask'],
            mid=(call_exit['bid'] + call_exit['ask']) / 2,
            delta=call_exit['delta'],
            gamma=call_exit.get('gamma', 0),
            theta=call_exit.get('theta', 0),
            vega=call_exit.get('vega', 0),
            volume=call_exit.get('volume', 0),
            open_interest=call_exit.get('open_interest', 0),
            implied_volatility=call_exit.get('implied_vol', call_exit.get('implied_volatility', 0))
        )
        
        put_leg = OptionLeg(
            strike=put_exit['strike'],
            option_type='PUT',
            bid=put_exit['bid'],
            ask=put_exit['ask'],
            mid=(put_exit['bid'] + put_exit['ask']) / 2,
            delta=put_exit['delta'],
            gamma=put_exit.get('gamma', 0),
            theta=put_exit.get('theta', 0),
            vega=put_exit.get('vega', 0),
            volume=put_exit.get('volume', 0),
            open_interest=put_exit.get('open_interest', 0),
            implied_volatility=put_exit.get('implied_vol', put_exit.get('implied_volatility', 0))
        )
        
        return call_leg, put_leg
    
    def validate_trade_data(self, trade: StrangleTrade) -> Tuple[bool, bool, int, List[str]]:
        """
        Validate trade data quality
        
        Returns:
            Tuple of (bid_ask_ok, liquidity_ok, quality_score, warnings)
        """
        warnings = []
        quality_score = 100
        
        # Check bid/ask spreads
        call_spread_pct = (trade.call_leg_entry.ask - trade.call_leg_entry.bid) / trade.call_leg_entry.mid
        put_spread_pct = (trade.put_leg_entry.ask - trade.put_leg_entry.bid) / trade.put_leg_entry.mid
        
        bid_ask_ok = call_spread_pct < 0.10 and put_spread_pct < 0.10  # Less than 10% spread
        if not bid_ask_ok:
            warnings.append(f"Wide bid/ask spreads: Call {call_spread_pct:.1%}, Put {put_spread_pct:.1%}")
            quality_score -= 10
        
        # Check liquidity (if volume data available)
        if trade.call_leg_entry.volume > 0 or trade.put_leg_entry.volume > 0:
            liquidity_ok = trade.call_leg_entry.volume >= 100 and trade.put_leg_entry.volume >= 100
            if not liquidity_ok:
                warnings.append(f"Low volume: Call {trade.call_leg_entry.volume}, Put {trade.put_leg_entry.volume}")
                quality_score -= 15
        else:
            liquidity_ok = True  # Assume OK if no volume data
            warnings.append("Volume data not available - liquidity cannot be verified")
            quality_score -= 5
        
        # Check for reasonable Greeks
        if abs(trade.call_leg_entry.delta) > 0.5 or abs(trade.put_leg_entry.delta) > 0.5:
            warnings.append("High delta options selected - may not be ideal for strangles")
            quality_score -= 5
        
        # Check time of day
        entry_hour = int(trade.entry_time.split(':')[0])
        if entry_hour < 10:
            warnings.append("Entry before 10:00 AM - potentially lower liquidity")
            quality_score -= 5
        
        return bid_ask_ok, liquidity_ok, quality_score, warnings
    
    def execute_single_trade(self, date: str, entry_time: str = "10:00",
                           exit_time: str = "15:50", delta_target: float = 0.30) -> Optional[StrangleTrade]:
        """
        Execute a single day's strangle trade with full transparency
        """
        logger.info(f"Executing trade for {date}")
        
        # Load data
        df = self.db.load_zero_dte_data(date)
        if df.empty:
            logger.warning(f"No data available for {date}")
            return None
        
        # Format timestamps
        date_formatted = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        entry_ts = f"{date_formatted}T{entry_time}:00"
        exit_ts = f"{date_formatted}T{exit_time}:00"
        
        # Find entry
        entry_result = self.find_strangle_entry(df, entry_ts, delta_target)
        if not entry_result:
            return None
            
        call_entry, put_entry = entry_result
        
        # Get SPY prices
        entry_spy = df[df['timestamp'] == entry_ts].iloc[0]['underlying_price']
        if entry_spy > 1000:
            entry_spy = entry_spy / 100
            
        # Find exit
        exit_result = self.find_exit_prices(df, exit_ts, call_entry.strike, put_entry.strike)
        if not exit_result:
            return None
            
        call_exit, put_exit = exit_result
        
        exit_spy = df[df['timestamp'] == exit_ts].iloc[0]['underlying_price']
        if exit_spy > 1000:
            exit_spy = exit_spy / 100
        
        # Calculate P&L (selling strangle)
        total_credit = (call_entry.bid + put_entry.bid) * 100
        total_debit = (call_exit.ask + put_exit.ask) * 100
        commission_total = self.commission * 4  # 2 contracts to open, 2 to close
        
        net_pnl = total_credit - total_debit - commission_total
        return_pct = (net_pnl / total_credit) * 100 if total_credit > 0 else 0
        
        # Create trade object
        self.trade_counter += 1
        trade = StrangleTrade(
            trade_id=self.trade_counter,
            date=date_formatted,
            entry_time=entry_time,
            exit_time=exit_time,
            spy_price_entry=entry_spy,
            spy_price_exit=exit_spy,
            vix_level=None,  # TODO: Add VIX data
            call_leg_entry=call_entry,
            put_leg_entry=put_entry,
            total_credit=total_credit,
            call_leg_exit=call_exit,
            put_leg_exit=put_exit,
            total_debit=total_debit,
            net_pnl=net_pnl,
            return_pct=return_pct,
            max_profit=total_credit,
            commission=commission_total,
            bid_ask_spread_ok=True,
            liquidity_ok=True,
            data_quality_score=100,
            warnings=[]
        )
        
        # Validate trade
        bid_ask_ok, liquidity_ok, quality_score, warnings = self.validate_trade_data(trade)
        trade.bid_ask_spread_ok = bid_ask_ok
        trade.liquidity_ok = liquidity_ok
        trade.data_quality_score = quality_score
        trade.warnings = warnings
        
        # Log the trade
        logger.info(f"Trade #{trade.trade_id}: P&L=${net_pnl:.2f} ({return_pct:.1f}%), Quality={quality_score}/100")
        
        return trade
    
    def backtest_period(self, start_date: str, end_date: str,
                       entry_time: str = "10:00", exit_time: str = "15:50",
                       delta_target: float = 0.30) -> pd.DataFrame:
        """
        Run backtest over a period with full transparency
        """
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Get all available dates
        all_dates = sorted(self.db.metadata.get('downloaded_dates', []))
        test_dates = [d for d in all_dates if start_date <= d <= end_date]
        
        if not test_dates:
            logger.error(f"No data available between {start_date} and {end_date}")
            return pd.DataFrame()
        
        logger.info(f"Found {len(test_dates)} trading days to test")
        
        # Clear previous trades
        self.trades = []
        self.trade_counter = 0
        
        # Execute trades
        for date in test_dates:
            trade = self.execute_single_trade(date, entry_time, exit_time, delta_target)
            if trade:
                self.trades.append(trade)
                
                # Print summary for this trade
                print(f"\nTrade #{trade.trade_id} - {trade.date}")
                print(f"P&L: ${trade.net_pnl:.2f} ({trade.return_pct:.1f}%)")
                print(f"Quality Score: {trade.data_quality_score}/100")
                if trade.warnings:
                    print(f"Warnings: {', '.join(trade.warnings)}")
        
        # Create summary DataFrame
        if self.trades:
            trades_dict = [asdict(t) for t in self.trades]
            df = pd.DataFrame(trades_dict)
            
            # Add summary statistics
            print("\n" + "="*60)
            print("BACKTEST SUMMARY")
            print("="*60)
            print(f"Total Trades: {len(df)}")
            print(f"Winning Trades: {len(df[df['net_pnl'] > 0])}")
            print(f"Losing Trades: {len(df[df['net_pnl'] <= 0])}")
            print(f"Win Rate: {(len(df[df['net_pnl'] > 0]) / len(df) * 100):.1f}%")
            print(f"Average P&L: ${df['net_pnl'].mean():.2f}")
            print(f"Total P&L: ${df['net_pnl'].sum():.2f}")
            print(f"Average Return: {df['return_pct'].mean():.1f}%")
            print(f"Sharpe Ratio: {(df['return_pct'].mean() / df['return_pct'].std() * np.sqrt(252)):.2f}")
            print(f"Max Drawdown: ${df['net_pnl'].cumsum().min():.2f}")
            print(f"Average Data Quality: {df['data_quality_score'].mean():.1f}/100")
            
            return df
        else:
            logger.warning("No trades were executed")
            return pd.DataFrame()
    
    def export_trades_to_csv(self, filename: str = "strangle_trades_audit.csv"):
        """Export all trades to CSV for external analysis"""
        if not self.trades:
            logger.warning("No trades to export")
            return
            
        # Convert to DataFrame with all details
        trades_data = []
        for trade in self.trades:
            trade_dict = asdict(trade)
            # Flatten the option leg data
            for key in ['call_leg_entry', 'put_leg_entry', 'call_leg_exit', 'put_leg_exit']:
                leg_data = trade_dict.pop(key)
                for field, value in leg_data.items():
                    trade_dict[f"{key}_{field}"] = value
            trades_data.append(trade_dict)
        
        df = pd.DataFrame(trades_data)
        df.to_csv(filename, index=False)
        logger.info(f"Exported {len(df)} trades to {filename}")
        
    def generate_trade_report(self, trade_id: int) -> str:
        """Generate a complete educational report for a specific trade"""
        trade = next((t for t in self.trades if t.trade_id == trade_id), None)
        if not trade:
            return f"Trade #{trade_id} not found"
        
        report = f"""
{"="*80}
COMPLETE TRADE REPORT - TRADE #{trade.trade_id}
{"="*80}

{trade.get_entry_explanation()}

{trade.get_exit_explanation()}

{trade.get_validity_report()}

EDUCATIONAL NOTES:
- This trade demonstrates a {'successful' if trade.net_pnl > 0 else 'losing'} strangle strategy
- The key to profitability was {'SPY staying within the expected range' if trade.net_pnl > 0 else 'SPY moving beyond our strikes'}
- Commission impact: ${trade.commission:.2f} ({(trade.commission / trade.total_credit * 100):.1f}% of credit received)
- Time decay worked {'in our favor' if trade.net_pnl > 0 else 'against us'} during this trade

LESSONS LEARNED:
1. Entry timing: {trade.entry_time} {'was' if trade.net_pnl > 0 else 'was not'} optimal for this day
2. Delta selection: {trade.call_leg_entry.delta:.2f} delta calls and {abs(trade.put_leg_entry.delta):.2f} delta puts
3. Risk management: Maximum risk was unlimited, but actual loss was limited by exit time
4. Market conditions: SPY moved {abs(trade.spy_price_exit - trade.spy_price_entry):.2f} points ({abs((trade.spy_price_exit - trade.spy_price_entry) / trade.spy_price_entry * 100):.2f}%)

{"="*80}
"""
        return report


# Example usage
if __name__ == "__main__":
    # Create backtester
    backtester = TransparentStrangleBacktester(commission_per_contract=0.65)
    
    # Run a sample backtest
    print("Running transparent backtest with educational output...")
    results = backtester.backtest_period(
        start_date="20250728",
        end_date="20250801",
        entry_time="10:00",
        exit_time="15:50",
        delta_target=0.30
    )
    
    # Export trades for audit
    if len(results) > 0:
        backtester.export_trades_to_csv("transparent_strangle_audit.csv")
        
        # Generate detailed report for first trade
        print("\n" + "="*80)
        print("DETAILED REPORT FOR FIRST TRADE:")
        print("="*80)
        print(backtester.generate_trade_report(1))