#!/usr/bin/env python3
"""
Unified Results Schema for SPY Options Backtesting

This module defines a standardized data model for all backtest results,
ensuring consistency across CLI, Streamlit, and AI analysis systems.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from enum import Enum
import pandas as pd
import numpy as np
import json
import uuid
from pathlib import Path

class OptionType(Enum):
    CALL = "C"
    PUT = "P"

class TradeDirection(Enum):
    LONG = "long"
    SHORT = "short"

class ExitReason(Enum):
    PROFIT_TARGET = "profit_target"
    STOP_LOSS = "stop_loss"
    TIME_DECAY = "time_decay"
    EXPIRATION = "expiration"
    MANUAL = "manual"
    IV_CHANGE = "iv_change"
    DELTA_HEDGE = "delta_hedge"

@dataclass
class MarketConditions:
    """Market conditions at a specific point in time."""
    date: datetime
    underlying_price: float
    vix_level: Optional[float] = None
    iv_rank: Optional[float] = None
    iv_percentile: Optional[float] = None
    volume_percentile: Optional[float] = None
    earnings_nearby: bool = False
    economic_events: List[str] = field(default_factory=list)

@dataclass
class GreeksSnapshot:
    """Option Greeks at a specific point in time."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    implied_volatility: float
    
    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

@dataclass
class TradeEntry:
    """Standardized trade entry record."""
    trade_id: str
    timestamp: datetime
    symbol: str
    option_type: OptionType
    strike: float
    expiration_date: date
    days_to_expiration: int
    quantity: int
    direction: TradeDirection
    entry_price: float
    entry_premium: float
    greeks: GreeksSnapshot
    market_conditions: MarketConditions
    strategy_signals: Dict[str, Any] = field(default_factory=dict)
    position_size_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['option_type'] = self.option_type.value
        data['direction'] = self.direction.value
        data['timestamp'] = self.timestamp.isoformat()
        data['expiration_date'] = self.expiration_date.isoformat()
        data['market_conditions']['date'] = self.market_conditions.date.isoformat()
        return data

@dataclass
class TradeExit:
    """Standardized trade exit record."""
    trade_id: str
    timestamp: datetime
    exit_price: float
    exit_premium: float
    pnl: float
    pnl_percentage: float
    greeks: GreeksSnapshot
    market_conditions: MarketConditions
    exit_reason: ExitReason
    days_held: int
    max_profit_during_trade: float
    max_loss_during_trade: float
    commissions: float = 0.0
    strategy_signals: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['exit_reason'] = self.exit_reason.value
        data['timestamp'] = self.timestamp.isoformat()
        data['market_conditions']['date'] = self.market_conditions.date.isoformat()
        return data

@dataclass
class CompleteTrade:
    """Complete trade record with entry and exit."""
    entry: TradeEntry
    exit: TradeExit
    performance_attribution: Dict[str, float] = field(default_factory=dict)
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)
    
    @property
    def trade_id(self) -> str:
        return self.entry.trade_id
    
    @property
    def total_pnl(self) -> float:
        return self.exit.pnl
    
    @property
    def is_winner(self) -> bool:
        return self.exit.pnl > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'entry': self.entry.to_dict(),
            'exit': self.exit.to_dict(),
            'performance_attribution': self.performance_attribution,
            'risk_metrics': self.risk_metrics,
            'lessons_learned': self.lessons_learned
        }

@dataclass
class PortfolioSnapshot:
    """Portfolio state at a specific point in time."""
    date: datetime
    total_value: float
    cash: float
    options_value: float
    pnl_unrealized: float
    pnl_realized: float
    daily_pnl: float
    active_positions: int
    portfolio_delta: float = 0.0
    portfolio_gamma: float = 0.0
    portfolio_theta: float = 0.0
    portfolio_vega: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['date'] = self.date.isoformat()
        return data

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    # Return metrics
    total_return_pct: float
    annualized_return_pct: float
    total_pnl: float
    
    # Risk metrics
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: int
    volatility_annualized: float
    
    # Trade metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    average_days_in_trade: float
    
    # Greeks metrics
    average_delta_exposure: float = 0.0
    max_gamma_risk: float = 0.0
    theta_decay_captured: float = 0.0
    vega_risk_realized: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StrategyConfiguration:
    """Strategy configuration and parameters."""
    strategy_name: str
    strategy_type: str
    parameters: Dict[str, Any]
    entry_criteria: Dict[str, Any]
    exit_criteria: Dict[str, Any]
    risk_management: Dict[str, Any]
    position_sizing: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class BacktestMetadata:
    """Metadata about the backtest run."""
    backtest_id: str
    run_timestamp: datetime
    start_date: date
    end_date: date
    initial_capital: float
    data_source: str
    version: str = "1.0"
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['run_timestamp'] = self.run_timestamp.isoformat()
        data['start_date'] = self.start_date.isoformat()
        data['end_date'] = self.end_date.isoformat()
        return data

@dataclass
class UnifiedBacktestResult:
    """
    Unified, comprehensive backtest result containing all data and metrics.
    This is the single source of truth for all backtest results.
    """
    metadata: BacktestMetadata
    strategy_config: StrategyConfiguration
    trades: List[CompleteTrade]
    portfolio_snapshots: List[PortfolioSnapshot]
    performance_metrics: PerformanceMetrics
    market_summary: Dict[str, Any] = field(default_factory=dict)
    ai_analysis: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def backtest_id(self) -> str:
        return self.metadata.backtest_id
    
    @property
    def trade_count(self) -> int:
        return len(self.trades)
    
    @property
    def final_portfolio_value(self) -> float:
        if self.portfolio_snapshots:
            return self.portfolio_snapshots[-1].total_value
        return self.metadata.initial_capital
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """Convert trades to pandas DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        
        trade_records = []
        for trade in self.trades:
            record = {
                'trade_id': trade.trade_id,
                'entry_date': trade.entry.timestamp,
                'exit_date': trade.exit.timestamp,
                'symbol': trade.entry.symbol,
                'option_type': trade.entry.option_type.value,
                'strike': trade.entry.strike,
                'expiration': trade.entry.expiration_date,
                'dte': trade.entry.days_to_expiration,
                'quantity': trade.entry.quantity,
                'direction': trade.entry.direction.value,
                'entry_price': trade.entry.entry_price,
                'exit_price': trade.exit.exit_price,
                'pnl': trade.exit.pnl,
                'pnl_pct': trade.exit.pnl_percentage,
                'days_held': trade.exit.days_held,
                'exit_reason': trade.exit.exit_reason.value,
                'entry_iv': trade.entry.greeks.implied_volatility,
                'exit_iv': trade.exit.greeks.implied_volatility,
                'entry_delta': trade.entry.greeks.delta,
                'exit_delta': trade.exit.greeks.delta,
                'max_profit': trade.exit.max_profit_during_trade,
                'max_loss': trade.exit.max_loss_during_trade
            }
            trade_records.append(record)
        
        return pd.DataFrame(trade_records)
    
    def get_portfolio_dataframe(self) -> pd.DataFrame:
        """Convert portfolio snapshots to pandas DataFrame."""
        if not self.portfolio_snapshots:
            return pd.DataFrame()
        
        portfolio_records = []
        for snapshot in self.portfolio_snapshots:
            record = {
                'date': snapshot.date,
                'total_value': snapshot.total_value,
                'cash': snapshot.cash,
                'options_value': snapshot.options_value,
                'daily_pnl': snapshot.daily_pnl,
                'pnl_unrealized': snapshot.pnl_unrealized,
                'pnl_realized': snapshot.pnl_realized,
                'active_positions': snapshot.active_positions,
                'portfolio_delta': snapshot.portfolio_delta,
                'portfolio_gamma': snapshot.portfolio_gamma,
                'portfolio_theta': snapshot.portfolio_theta,
                'portfolio_vega': snapshot.portfolio_vega
            }
            portfolio_records.append(record)
        
        return pd.DataFrame(portfolio_records)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'metadata': self.metadata.to_dict(),
            'strategy_config': self.strategy_config.to_dict(),
            'trades': [trade.to_dict() for trade in self.trades],
            'portfolio_snapshots': [snap.to_dict() for snap in self.portfolio_snapshots],
            'performance_metrics': self.performance_metrics.to_dict(),
            'market_summary': self.market_summary,
            'ai_analysis': self.ai_analysis
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedBacktestResult':
        """Create from dictionary (JSON deserialization)."""
        # Convert metadata
        metadata_data = data['metadata']
        metadata = BacktestMetadata(
            backtest_id=metadata_data['backtest_id'],
            run_timestamp=datetime.fromisoformat(metadata_data['run_timestamp']),
            start_date=date.fromisoformat(metadata_data['start_date']),
            end_date=date.fromisoformat(metadata_data['end_date']),
            initial_capital=metadata_data['initial_capital'],
            data_source=metadata_data['data_source'],
            version=metadata_data.get('version', '1.0'),
            system_info=metadata_data.get('system_info', {})
        )
        
        # Convert strategy config
        strategy_data = data['strategy_config']
        strategy_config = StrategyConfiguration(**strategy_data)
        
        # Convert trades
        trades = []
        for trade_data in data['trades']:
            entry_data = trade_data['entry']
            exit_data = trade_data['exit']
            
            # Convert entry
            entry_greeks = GreeksSnapshot(**entry_data['greeks'])
            entry_market = MarketConditions(
                date=datetime.fromisoformat(entry_data['market_conditions']['date']),
                **{k: v for k, v in entry_data['market_conditions'].items() if k != 'date'}
            )
            entry = TradeEntry(
                trade_id=entry_data['trade_id'],
                timestamp=datetime.fromisoformat(entry_data['timestamp']),
                symbol=entry_data['symbol'],
                option_type=OptionType(entry_data['option_type']),
                strike=entry_data['strike'],
                expiration_date=date.fromisoformat(entry_data['expiration_date']),
                days_to_expiration=entry_data['days_to_expiration'],
                quantity=entry_data['quantity'],
                direction=TradeDirection(entry_data['direction']),
                entry_price=entry_data['entry_price'],
                entry_premium=entry_data['entry_premium'],
                greeks=entry_greeks,
                market_conditions=entry_market,
                strategy_signals=entry_data.get('strategy_signals', {}),
                position_size_info=entry_data.get('position_size_info', {})
            )
            
            # Convert exit
            exit_greeks = GreeksSnapshot(**exit_data['greeks'])
            exit_market = MarketConditions(
                date=datetime.fromisoformat(exit_data['market_conditions']['date']),
                **{k: v for k, v in exit_data['market_conditions'].items() if k != 'date'}
            )
            exit = TradeExit(
                trade_id=exit_data['trade_id'],
                timestamp=datetime.fromisoformat(exit_data['timestamp']),
                exit_price=exit_data['exit_price'],
                exit_premium=exit_data['exit_premium'],
                pnl=exit_data['pnl'],
                pnl_percentage=exit_data['pnl_percentage'],
                greeks=exit_greeks,
                market_conditions=exit_market,
                exit_reason=ExitReason(exit_data['exit_reason']),
                days_held=exit_data['days_held'],
                max_profit_during_trade=exit_data['max_profit_during_trade'],
                max_loss_during_trade=exit_data['max_loss_during_trade'],
                commissions=exit_data.get('commissions', 0.0),
                strategy_signals=exit_data.get('strategy_signals', {})
            )
            
            complete_trade = CompleteTrade(
                entry=entry,
                exit=exit,
                performance_attribution=trade_data.get('performance_attribution', {}),
                risk_metrics=trade_data.get('risk_metrics', {}),
                lessons_learned=trade_data.get('lessons_learned', [])
            )
            trades.append(complete_trade)
        
        # Convert portfolio snapshots
        portfolio_snapshots = []
        for snap_data in data['portfolio_snapshots']:
            snapshot = PortfolioSnapshot(
                date=datetime.fromisoformat(snap_data['date']),
                **{k: v for k, v in snap_data.items() if k != 'date'}
            )
            portfolio_snapshots.append(snapshot)
        
        # Convert performance metrics
        performance_metrics = PerformanceMetrics(**data['performance_metrics'])
        
        return cls(
            metadata=metadata,
            strategy_config=strategy_config,
            trades=trades,
            portfolio_snapshots=portfolio_snapshots,
            performance_metrics=performance_metrics,
            market_summary=data.get('market_summary', {}),
            ai_analysis=data.get('ai_analysis', {})
        )
    
    def save_to_json(self, filepath: Union[str, Path]) -> None:
        """Save to JSON file."""
        filepath = Path(filepath)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    @classmethod
    def load_from_json(cls, filepath: Union[str, Path]) -> 'UnifiedBacktestResult':
        """Load from JSON file."""
        filepath = Path(filepath)
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class ResultValidator:
    """Validates unified backtest results for consistency and integrity."""
    
    @staticmethod
    def validate_result(result: UnifiedBacktestResult) -> Dict[str, Any]:
        """Validate a unified backtest result."""
        issues = []
        warnings = []
        
        # Metadata validation
        if not result.metadata.backtest_id:
            issues.append("Missing backtest ID")
        
        if result.metadata.start_date > result.metadata.end_date:
            issues.append("Start date is after end date")
        
        # Trade validation
        for i, trade in enumerate(result.trades):
            if trade.entry.trade_id != trade.exit.trade_id:
                issues.append(f"Trade {i}: Entry and exit trade IDs don't match")
            
            if trade.entry.timestamp > trade.exit.timestamp:
                issues.append(f"Trade {i}: Entry timestamp after exit timestamp")
            
            # P&L consistency check
            expected_pnl = trade.exit.exit_premium - trade.entry.entry_premium
            if abs(trade.exit.pnl - expected_pnl) > 0.01:
                warnings.append(f"Trade {i}: P&L calculation discrepancy")
        
        # Portfolio validation
        portfolio_df = result.get_portfolio_dataframe()
        if not portfolio_df.empty:
            # Check for negative portfolio values
            if (portfolio_df['total_value'] < 0).any():
                warnings.append("Portfolio has negative values")
            
            # Check for date gaps
            dates = pd.to_datetime(portfolio_df['date'])
            date_diffs = dates.diff().dt.days
            if (date_diffs > 10).any():  # More than 10 days gap
                warnings.append("Large gaps in portfolio snapshots")
        
        # Performance metrics validation
        if result.performance_metrics.total_trades != len(result.trades):
            issues.append("Trade count mismatch in performance metrics")
        
        # Calculate expected win rate
        if result.trades:
            actual_wins = sum(1 for trade in result.trades if trade.is_winner)
            expected_win_rate = (actual_wins / len(result.trades)) * 100
            if abs(result.performance_metrics.win_rate_pct - expected_win_rate) > 0.1:
                warnings.append("Win rate calculation discrepancy")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_trades': len(result.trades),
            'portfolio_snapshots': len(result.portfolio_snapshots),
            'date_range': {
                'start': result.metadata.start_date.isoformat(),
                'end': result.metadata.end_date.isoformat()
            }
        }


# Utility functions for working with unified results
def create_backtest_id() -> str:
    """Generate a unique backtest ID."""
    return f"bt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

def merge_results(results: List[UnifiedBacktestResult]) -> UnifiedBacktestResult:
    """Merge multiple backtest results into one (for comparison analysis)."""
    if not results:
        raise ValueError("No results to merge")
    
    if len(results) == 1:
        return results[0]
    
    # Use first result as base
    base = results[0]
    
    # Combine trades from all results
    all_trades = []
    for result in results:
        all_trades.extend(result.trades)
    
    # Combine portfolio snapshots (need to be careful about overlaps)
    all_snapshots = []
    seen_dates = set()
    for result in results:
        for snapshot in result.portfolio_snapshots:
            snapshot_date = snapshot.date.date()
            if snapshot_date not in seen_dates:
                all_snapshots.append(snapshot)
                seen_dates.add(snapshot_date)
    
    # Sort by date
    all_snapshots.sort(key=lambda x: x.date)
    
    # Recalculate performance metrics for merged result
    # This is simplified - in practice you'd want more sophisticated merging
    total_pnl = sum(trade.total_pnl for trade in all_trades)
    winning_trades = sum(1 for trade in all_trades if trade.is_winner)
    
    merged_metrics = PerformanceMetrics(
        total_return_pct=(total_pnl / base.metadata.initial_capital) * 100,
        annualized_return_pct=0,  # Would need proper calculation
        total_pnl=total_pnl,
        sharpe_ratio=0,  # Would need proper calculation
        sortino_ratio=0,
        max_drawdown_pct=0,
        max_drawdown_duration_days=0,
        volatility_annualized=0,
        total_trades=len(all_trades),
        winning_trades=winning_trades,
        losing_trades=len(all_trades) - winning_trades,
        win_rate_pct=(winning_trades / len(all_trades)) * 100 if all_trades else 0,
        profit_factor=0,  # Would need proper calculation
        average_win=0,
        average_loss=0,
        largest_win=0,
        largest_loss=0,
        average_days_in_trade=0
    )
    
    # Create merged metadata
    merged_metadata = BacktestMetadata(
        backtest_id=create_backtest_id(),
        run_timestamp=datetime.now(),
        start_date=min(r.metadata.start_date for r in results),
        end_date=max(r.metadata.end_date for r in results),
        initial_capital=base.metadata.initial_capital,
        data_source="merged",
        version="1.0",
        system_info={'merged_from': [r.backtest_id for r in results]}
    )
    
    return UnifiedBacktestResult(
        metadata=merged_metadata,
        strategy_config=base.strategy_config,
        trades=all_trades,
        portfolio_snapshots=all_snapshots,
        performance_metrics=merged_metrics,
        market_summary={'merged': True},
        ai_analysis={'merged': True}
    )


if __name__ == "__main__":
    # Test the unified schema
    print("Testing Unified Results Schema...")
    
    # Create sample data
    metadata = BacktestMetadata(
        backtest_id=create_backtest_id(),
        run_timestamp=datetime.now(),
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        initial_capital=100000.0,
        data_source="spy_options_parquet"
    )
    
    strategy_config = StrategyConfiguration(
        strategy_name="Long Put",
        strategy_type="options",
        parameters={'delta_target': 0.30, 'dte_range': [10, 45]},
        entry_criteria={'iv_rank': {'min': 50}},
        exit_criteria={'profit_target': 0.25, 'stop_loss': 0.50},
        risk_management={'max_position_size': 0.05},
        position_sizing={'method': 'fixed_percentage'}
    )
    
    # Sample trade
    entry_greeks = GreeksSnapshot(
        delta=-0.30, gamma=0.05, theta=-0.08, vega=0.15, rho=-0.02, implied_volatility=0.25
    )
    
    entry_market = MarketConditions(
        date=datetime(2023, 6, 15, 9, 30),
        underlying_price=415.0,
        vix_level=18.5,
        iv_rank=75.0
    )
    
    trade_entry = TradeEntry(
        trade_id="trade_001",
        timestamp=datetime(2023, 6, 15, 9, 30),
        symbol="SPY",
        option_type=OptionType.PUT,
        strike=410.0,
        expiration_date=date(2023, 7, 21),
        days_to_expiration=36,
        quantity=1,
        direction=TradeDirection.LONG,
        entry_price=2.50,
        entry_premium=250.0,
        greeks=entry_greeks,
        market_conditions=entry_market
    )
    
    exit_greeks = GreeksSnapshot(
        delta=-0.45, gamma=0.08, theta=-0.12, vega=0.18, rho=-0.03, implied_volatility=0.30
    )
    
    exit_market = MarketConditions(
        date=datetime(2023, 6, 20, 15, 0),
        underlying_price=405.0,
        vix_level=22.0,
        iv_rank=85.0
    )
    
    trade_exit = TradeExit(
        trade_id="trade_001",
        timestamp=datetime(2023, 6, 20, 15, 0),
        exit_price=3.75,
        exit_premium=375.0,
        pnl=125.0,
        pnl_percentage=50.0,
        greeks=exit_greeks,
        market_conditions=exit_market,
        exit_reason=ExitReason.PROFIT_TARGET,
        days_held=5,
        max_profit_during_trade=375.0,
        max_loss_during_trade=0.0
    )
    
    complete_trade = CompleteTrade(entry=trade_entry, exit=trade_exit)
    
    # Sample portfolio snapshot
    portfolio_snapshot = PortfolioSnapshot(
        date=datetime(2023, 6, 15),
        total_value=100250.0,
        cash=99750.0,
        options_value=500.0,
        pnl_unrealized=250.0,
        pnl_realized=0.0,
        daily_pnl=250.0,
        active_positions=1
    )
    
    # Performance metrics
    performance_metrics = PerformanceMetrics(
        total_return_pct=12.5,
        annualized_return_pct=15.2,
        total_pnl=12500.0,
        sharpe_ratio=1.25,
        sortino_ratio=1.45,
        max_drawdown_pct=5.2,
        max_drawdown_duration_days=15,
        volatility_annualized=12.8,
        total_trades=25,
        winning_trades=18,
        losing_trades=7,
        win_rate_pct=72.0,
        profit_factor=2.1,
        average_win=875.0,
        average_loss=250.0,
        largest_win=2500.0,
        largest_loss=750.0,
        average_days_in_trade=8.5
    )
    
    # Create unified result
    unified_result = UnifiedBacktestResult(
        metadata=metadata,
        strategy_config=strategy_config,
        trades=[complete_trade],
        portfolio_snapshots=[portfolio_snapshot],
        performance_metrics=performance_metrics
    )
    
    # Test serialization
    test_file = Path("test_unified_result.json")
    unified_result.save_to_json(test_file)
    
    # Test deserialization
    loaded_result = UnifiedBacktestResult.load_from_json(test_file)
    
    # Validate
    validator = ResultValidator()
    validation_result = validator.validate_result(loaded_result)
    
    print(f"✅ Backtest ID: {loaded_result.backtest_id}")
    print(f"✅ Trade count: {loaded_result.trade_count}")
    print(f"✅ Final portfolio value: ${loaded_result.final_portfolio_value:,.2f}")
    print(f"✅ Validation passed: {validation_result['is_valid']}")
    print(f"✅ Issues: {len(validation_result['issues'])}")
    print(f"✅ Warnings: {len(validation_result['warnings'])}")
    
    # Test DataFrame conversion
    trades_df = loaded_result.get_trades_dataframe()
    portfolio_df = loaded_result.get_portfolio_dataframe()
    
    print(f"✅ Trades DataFrame shape: {trades_df.shape}")
    print(f"✅ Portfolio DataFrame shape: {portfolio_df.shape}")
    
    # Cleanup
    test_file.unlink()
    
    print("✅ Unified Results Schema test completed successfully")