#!/usr/bin/env python3
"""
Comprehensive Verification Suite for Backtest Results

This test suite verifies the complete integrity and consistency of:
- Performance review functionality
- Trade logging accuracy  
- AI analysis integration
- Single source of truth implementation
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime, date, timedelta
import unittest
import logging
import tempfile
import shutil
from contextlib import contextmanager
import warnings

# Import our unified components
from unified_results_schema import (
    UnifiedBacktestResult, BacktestMetadata, StrategyConfiguration,
    PerformanceMetrics, CompleteTrade, PortfolioSnapshot, TradeEntry, TradeExit,
    OptionType, TradeDirection, ExitReason, GreeksSnapshot, MarketConditions,
    ResultValidator, create_backtest_id
)
from unified_results_manager import UnifiedResultsManager

# Suppress warnings for cleaner test output
warnings.filterwarnings('ignore', category=FutureWarning)

class BacktestResultGenerator:
    """Generates realistic test backtest results for verification."""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.seed = seed
    
    def generate_sample_result(self, 
                             num_trades: int = 25,
                             start_date: date = date(2023, 1, 1),
                             end_date: date = date(2023, 12, 31),
                             initial_capital: float = 100000.0,
                             strategy_name: str = "Test Strategy") -> UnifiedBacktestResult:
        """Generate a realistic sample backtest result."""
        
        # Create metadata
        metadata = BacktestMetadata(
            backtest_id=create_backtest_id(),
            run_timestamp=datetime.now(),
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            data_source="test_data",
            version="1.0",
            system_info={'test_generator': True, 'seed': self.seed}
        )
        
        # Create strategy config
        strategy_config = StrategyConfiguration(
            strategy_name=strategy_name,
            strategy_type="options",
            parameters={
                'delta_target': 0.30,
                'dte_range': [10, 45],
                'profit_target': 0.25,
                'stop_loss': 0.50
            },
            entry_criteria={'iv_rank_min': 50},
            exit_criteria={'profit_target': 0.25, 'stop_loss': 0.50},
            risk_management={'max_position_size': 0.05},
            position_sizing={'method': 'fixed_percentage'}
        )
        
        # Generate trades
        trades = self._generate_trades(num_trades, start_date, end_date)
        
        # Generate portfolio snapshots
        portfolio_snapshots = self._generate_portfolio_snapshots(
            trades, initial_capital, start_date, end_date
        )
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(
            trades, portfolio_snapshots, initial_capital
        )
        
        return UnifiedBacktestResult(
            metadata=metadata,
            strategy_config=strategy_config,
            trades=trades,
            portfolio_snapshots=portfolio_snapshots,
            performance_metrics=performance_metrics,
            market_summary={'generated': True, 'seed': self.seed},
            ai_analysis={'test_mode': True}
        )
    
    def _generate_trades(self, num_trades: int, start_date: date, end_date: date) -> List[CompleteTrade]:
        """Generate realistic trade data."""
        trades = []
        
        # Calculate date range
        date_range = (end_date - start_date).days
        underlying_prices = np.random.normal(400, 20, num_trades)  # SPY around $400
        
        for i in range(num_trades):
            # Random trade timing
            days_offset = np.random.randint(0, date_range)
            entry_date = start_date + timedelta(days=days_offset)
            
            # Trade parameters
            strike = np.random.choice([0.95, 0.97, 1.00, 1.03, 1.05]) * underlying_prices[i]
            option_type = np.random.choice([OptionType.PUT, OptionType.CALL])
            dte = np.random.randint(10, 45)
            
            # Entry Greeks
            entry_delta = np.random.uniform(-0.5, 0.5) if option_type == OptionType.PUT else np.random.uniform(0.1, 0.8)
            entry_greeks = GreeksSnapshot(
                delta=entry_delta,
                gamma=np.random.uniform(0.01, 0.10),
                theta=np.random.uniform(-0.20, -0.05),
                vega=np.random.uniform(0.05, 0.25),
                rho=np.random.uniform(-0.05, 0.05),
                implied_volatility=np.random.uniform(0.15, 0.35)
            )
            
            # Market conditions
            entry_market = MarketConditions(
                date=datetime.combine(entry_date, datetime.min.time().replace(hour=10)),
                underlying_price=underlying_prices[i],
                vix_level=np.random.uniform(15, 30),
                iv_rank=np.random.uniform(20, 80)
            )
            
            # Entry premium
            entry_premium = np.random.uniform(50, 500)
            
            # Trade entry
            trade_entry = TradeEntry(
                trade_id=f"trade_{i+1:03d}",
                timestamp=datetime.combine(entry_date, datetime.min.time().replace(hour=10)),
                symbol="SPY",
                option_type=option_type,
                strike=round(strike, 0),
                expiration_date=entry_date + timedelta(days=dte),
                days_to_expiration=dte,
                quantity=1,
                direction=TradeDirection.LONG,
                entry_price=entry_premium / 100,
                entry_premium=entry_premium,
                greeks=entry_greeks,
                market_conditions=entry_market
            )
            
            # Exit timing and conditions
            days_held = np.random.randint(1, min(dte, 21))
            exit_date = entry_date + timedelta(days=days_held)
            
            # Exit outcome (60% win rate)
            is_winner = np.random.random() < 0.60
            
            if is_winner:
                exit_premium = entry_premium * np.random.uniform(1.1, 2.5)  # 10% to 150% gain
                exit_reason = ExitReason.PROFIT_TARGET
            else:
                exit_premium = entry_premium * np.random.uniform(0.3, 0.9)  # 10% to 70% loss
                exit_reason = np.random.choice([ExitReason.STOP_LOSS, ExitReason.TIME_DECAY])
            
            # Exit Greeks
            underlying_change = np.random.uniform(-0.05, 0.05)
            new_underlying = underlying_prices[i] * (1 + underlying_change)
            
            exit_greeks = GreeksSnapshot(
                delta=entry_delta * (1 + np.random.uniform(-0.3, 0.3)),
                gamma=entry_greeks.gamma * (1 + np.random.uniform(-0.2, 0.2)),
                theta=entry_greeks.theta * (1 + np.random.uniform(-0.5, 0.2)),
                vega=entry_greeks.vega * (1 + np.random.uniform(-0.3, 0.3)),
                rho=entry_greeks.rho,
                implied_volatility=entry_greeks.implied_volatility * (1 + np.random.uniform(-0.3, 0.3))
            )
            
            exit_market = MarketConditions(
                date=datetime.combine(exit_date, datetime.min.time().replace(hour=15)),
                underlying_price=new_underlying,
                vix_level=entry_market.vix_level * (1 + np.random.uniform(-0.2, 0.2)),
                iv_rank=entry_market.iv_rank * (1 + np.random.uniform(-0.3, 0.3))
            )
            
            # Trade exit
            trade_exit = TradeExit(
                trade_id=trade_entry.trade_id,
                timestamp=datetime.combine(exit_date, datetime.min.time().replace(hour=15)),
                exit_price=exit_premium / 100,
                exit_premium=exit_premium,
                pnl=exit_premium - entry_premium,
                pnl_percentage=((exit_premium - entry_premium) / entry_premium) * 100,
                greeks=exit_greeks,
                market_conditions=exit_market,
                exit_reason=exit_reason,
                days_held=days_held,
                max_profit_during_trade=max(exit_premium, entry_premium * 1.1),
                max_loss_during_trade=min(exit_premium, entry_premium * 0.8),
                commissions=2.0
            )
            
            # Complete trade
            complete_trade = CompleteTrade(
                entry=trade_entry,
                exit=trade_exit,
                performance_attribution={
                    'delta_pnl': underlying_change * entry_delta * 100,
                    'theta_pnl': entry_greeks.theta * days_held,
                    'vega_pnl': (exit_greeks.implied_volatility - entry_greeks.implied_volatility) * entry_greeks.vega * 100
                },
                risk_metrics={
                    'max_risk': entry_premium,
                    'probability_profit': 0.6 if is_winner else 0.4
                }
            )
            
            trades.append(complete_trade)
        
        return trades
    
    def _generate_portfolio_snapshots(self, trades: List[CompleteTrade], 
                                    initial_capital: float,
                                    start_date: date, end_date: date) -> List[PortfolioSnapshot]:
        """Generate portfolio snapshots based on trade data."""
        snapshots = []
        
        # Create daily snapshots
        current_date = start_date
        current_value = initial_capital
        realized_pnl = 0
        
        while current_date <= end_date:
            # Check for trades that closed on this date
            daily_pnl = 0
            closed_trades = [t for t in trades if t.exit.timestamp.date() == current_date]
            
            for trade in closed_trades:
                daily_pnl += trade.exit.pnl
                realized_pnl += trade.exit.pnl
            
            current_value = initial_capital + realized_pnl
            
            # Count active positions
            active_positions = len([
                t for t in trades 
                if t.entry.timestamp.date() <= current_date and t.exit.timestamp.date() > current_date
            ])
            
            snapshot = PortfolioSnapshot(
                date=datetime.combine(current_date, datetime.min.time().replace(hour=16)),
                total_value=current_value,
                cash=current_value - (active_positions * 250),  # Rough estimate
                options_value=active_positions * 250,
                pnl_unrealized=0,  # Simplified
                pnl_realized=realized_pnl,
                daily_pnl=daily_pnl,
                active_positions=active_positions
            )
            
            snapshots.append(snapshot)
            current_date += timedelta(days=1)
        
        return snapshots
    
    def _calculate_performance_metrics(self, trades: List[CompleteTrade],
                                     portfolio_snapshots: List[PortfolioSnapshot],
                                     initial_capital: float) -> PerformanceMetrics:
        """Calculate performance metrics from trade and portfolio data."""
        
        # Trade metrics
        winning_trades = [t for t in trades if t.exit.pnl > 0]
        losing_trades = [t for t in trades if t.exit.pnl <= 0]
        
        total_pnl = sum(t.exit.pnl for t in trades)
        total_return_pct = (total_pnl / initial_capital) * 100
        
        # Risk metrics
        portfolio_values = [s.total_value for s in portfolio_snapshots]
        if portfolio_values:
            peak_values = pd.Series(portfolio_values).expanding().max()
            drawdowns = (pd.Series(portfolio_values) - peak_values) / peak_values
            max_drawdown_pct = abs(drawdowns.min()) * 100
        else:
            max_drawdown_pct = 0
        
        # Daily returns for Sharpe ratio
        daily_returns = pd.Series([s.daily_pnl for s in portfolio_snapshots]) / initial_capital
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        # Win rate and profit factor
        win_rate_pct = (len(winning_trades) / len(trades)) * 100 if trades else 0
        gross_profit = sum(t.exit.pnl for t in winning_trades)
        gross_loss = abs(sum(t.exit.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return PerformanceMetrics(
            total_return_pct=total_return_pct,
            annualized_return_pct=total_return_pct * (365 / ((portfolio_snapshots[-1].date - portfolio_snapshots[0].date).days)) if portfolio_snapshots else 0,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sharpe_ratio * 1.2,  # Approximation
            max_drawdown_pct=max_drawdown_pct,
            max_drawdown_duration_days=0,  # Simplified
            volatility_annualized=daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate_pct=win_rate_pct,
            profit_factor=profit_factor,
            average_win=gross_profit / len(winning_trades) if winning_trades else 0,
            average_loss=gross_loss / len(losing_trades) if losing_trades else 0,
            largest_win=max((t.exit.pnl for t in winning_trades), default=0),
            largest_loss=min((t.exit.pnl for t in losing_trades), default=0),
            average_days_in_trade=np.mean([t.exit.days_held for t in trades]) if trades else 0
        )


class ComprehensiveVerificationSuite(unittest.TestCase):
    """Comprehensive test suite for backtest result integrity."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="verification_test_"))
        cls.results_manager = UnifiedResultsManager(cls.temp_dir / "results")
        cls.generator = BacktestResultGenerator(seed=42)
        cls.validator = ResultValidator()
        
        # Generate test results
        cls.sample_results = [
            cls.generator.generate_sample_result(num_trades=25, strategy_name="Long Put"),
            cls.generator.generate_sample_result(num_trades=15, strategy_name="Short Call"),
            cls.generator.generate_sample_result(num_trades=0, strategy_name="No Trades"),
        ]
        
        # Save test results
        for result in cls.sample_results:
            cls.results_manager.save_backtest(result, validate=False)  # Skip validation for test setup
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)
    
    def test_unified_schema_validation(self):
        """Test unified schema validation."""
        print("\n🧪 Testing Unified Schema Validation...")
        
        for result in self.sample_results:
            with self.subTest(strategy=result.strategy_config.strategy_name):
                validation = self.validator.validate_result(result)
                
                # Basic validation checks
                self.assertIsInstance(validation, dict)
                self.assertIn('is_valid', validation)
                self.assertIn('issues', validation)
                self.assertIn('warnings', validation)
                
                # Results with trades should be valid
                if result.trade_count > 0:
                    self.assertTrue(validation['is_valid'], 
                                  f"Validation failed for {result.strategy_config.strategy_name}: {validation['issues']}")
                
                print(f"   ✅ {result.strategy_config.strategy_name}: {validation['total_trades']} trades validated")
    
    def test_results_manager_operations(self):
        """Test results manager CRUD operations."""
        print("\n🧪 Testing Results Manager Operations...")
        
        # Test save and load
        test_result = self.generator.generate_sample_result(num_trades=10, strategy_name="CRUD Test")
        
        # Save
        saved_path = self.results_manager.save_backtest(test_result, validate=False)
        self.assertTrue(Path(saved_path).exists())
        print(f"   ✅ Save: {Path(saved_path).name}")
        
        # Load
        loaded_result = self.results_manager.load_backtest(test_result.backtest_id)
        self.assertEqual(loaded_result.backtest_id, test_result.backtest_id)
        self.assertEqual(loaded_result.trade_count, test_result.trade_count)
        print(f"   ✅ Load: {loaded_result.backtest_id}")
        
        # List
        summaries = self.results_manager.list_backtests()
        self.assertGreaterEqual(len(summaries), 1)
        print(f"   ✅ List: {len(summaries)} results found")
        
        # Delete
        success = self.results_manager.delete_backtest(test_result.backtest_id)
        self.assertTrue(success)
        print(f"   ✅ Delete: {test_result.backtest_id}")
    
    def test_data_consistency_across_formats(self):
        """Test data consistency across different access methods."""
        print("\n🧪 Testing Data Consistency Across Formats...")
        
        for result in self.sample_results[:2]:  # Skip empty result
            with self.subTest(strategy=result.strategy_config.strategy_name):
                # Get data in different formats
                trades_df = result.get_trades_dataframe()
                portfolio_df = result.get_portfolio_dataframe()
                
                # Test trade data consistency
                if not trades_df.empty:
                    self.assertEqual(len(trades_df), result.trade_count)
                    
                    # Check that P&L sums correctly
                    df_total_pnl = trades_df['pnl'].sum()
                    result_total_pnl = result.performance_metrics.total_pnl
                    self.assertAlmostEqual(df_total_pnl, result_total_pnl, places=2)
                    
                    # Check win rate calculation
                    df_win_rate = (trades_df['pnl'] > 0).mean() * 100
                    result_win_rate = result.performance_metrics.win_rate_pct
                    self.assertAlmostEqual(df_win_rate, result_win_rate, places=1)
                
                # Test portfolio data consistency
                if not portfolio_df.empty:
                    final_value = portfolio_df['total_value'].iloc[-1]
                    self.assertAlmostEqual(final_value, result.final_portfolio_value, places=2)
                
                print(f"   ✅ {result.strategy_config.strategy_name}: Trade & Portfolio consistency verified")
    
    def test_performance_metrics_accuracy(self):
        """Test accuracy of performance metrics calculations."""
        print("\n🧪 Testing Performance Metrics Accuracy...")
        
        for result in self.sample_results:
            if result.trade_count == 0:
                continue
                
            with self.subTest(strategy=result.strategy_config.strategy_name):
                metrics = result.performance_metrics
                trades = result.trades
                
                # Test trade count consistency
                self.assertEqual(metrics.total_trades, len(trades))
                
                # Test P&L calculation
                actual_pnl = sum(t.exit.pnl for t in trades)
                self.assertAlmostEqual(metrics.total_pnl, actual_pnl, places=2)
                
                # Test win/loss counts
                winning_trades = [t for t in trades if t.exit.pnl > 0]
                losing_trades = [t for t in trades if t.exit.pnl <= 0]
                
                self.assertEqual(metrics.winning_trades, len(winning_trades))
                self.assertEqual(metrics.losing_trades, len(losing_trades))
                
                # Test win rate
                expected_win_rate = (len(winning_trades) / len(trades)) * 100
                self.assertAlmostEqual(metrics.win_rate_pct, expected_win_rate, places=1)
                
                # Test average calculations
                if winning_trades:
                    expected_avg_win = sum(t.exit.pnl for t in winning_trades) / len(winning_trades)
                    self.assertAlmostEqual(metrics.average_win, expected_avg_win, places=2)
                
                print(f"   ✅ {result.strategy_config.strategy_name}: Metrics accuracy verified")
    
    def test_ai_analysis_integration(self):
        """Test AI analysis integration points."""
        print("\n🧪 Testing AI Analysis Integration...")
        
        # Test that results contain AI analysis structure
        for result in self.sample_results:
            with self.subTest(strategy=result.strategy_config.strategy_name):
                self.assertIsInstance(result.ai_analysis, dict)
                
                # Test data access for AI
                result_dict = result.to_dict()
                self.assertIn('trades', result_dict)
                self.assertIn('performance_metrics', result_dict)
                self.assertIn('strategy_config', result_dict)
                
                # Test that all required data is serializable
                try:
                    json.dumps(result_dict, default=str)
                    json_serializable = True
                except Exception:
                    json_serializable = False
                
                self.assertTrue(json_serializable, "Result must be JSON serializable for AI analysis")
                
                print(f"   ✅ {result.strategy_config.strategy_name}: AI integration ready")
    
    def test_trade_log_completeness(self):
        """Test trade log completeness and accuracy."""
        print("\n🧪 Testing Trade Log Completeness...")
        
        for result in self.sample_results:
            if result.trade_count == 0:
                continue
                
            with self.subTest(strategy=result.strategy_config.strategy_name):
                trades_df = result.get_trades_dataframe()
                
                # Check required columns exist
                required_columns = [
                    'trade_id', 'entry_date', 'exit_date', 'symbol', 'option_type',
                    'strike', 'quantity', 'entry_price', 'exit_price', 'pnl',
                    'days_held', 'exit_reason'
                ]
                
                for col in required_columns:
                    self.assertIn(col, trades_df.columns, f"Missing required column: {col}")
                
                # Check data integrity
                self.assertFalse(trades_df['trade_id'].duplicated().any(), "Duplicate trade IDs found")
                self.assertTrue((trades_df['exit_date'] >= trades_df['entry_date']).all(), 
                              "Exit dates before entry dates")
                self.assertTrue((trades_df['days_held'] >= 0).all(), "Negative days held")
                
                # Check P&L calculation
                calculated_pnl = (trades_df['exit_price'] - trades_df['entry_price']) * trades_df['quantity'] * 100
                self.assertTrue(np.allclose(calculated_pnl, trades_df['pnl'], rtol=0.01), 
                              "P&L calculation mismatch")
                
                print(f"   ✅ {result.strategy_config.strategy_name}: Trade log completeness verified")
    
    def test_portfolio_value_reconciliation(self):
        """Test portfolio value reconciliation."""
        print("\n🧪 Testing Portfolio Value Reconciliation...")
        
        for result in self.sample_results:
            if result.trade_count == 0:
                continue
                
            with self.subTest(strategy=result.strategy_config.strategy_name):
                portfolio_df = result.get_portfolio_dataframe()
                
                if portfolio_df.empty:
                    continue
                
                # Check that portfolio values are reasonable
                initial_capital = result.metadata.initial_capital
                final_value = portfolio_df['total_value'].iloc[-1]
                total_pnl = result.performance_metrics.total_pnl
                
                # Final value should equal initial capital + total P&L
                expected_final = initial_capital + total_pnl
                # Allow for small rounding differences (within $200 on $100k+ portfolio)
                tolerance = max(200, abs(expected_final) * 0.002)  # 0.2% tolerance
                self.assertAlmostEqual(final_value, expected_final, delta=tolerance,
                                     msg=f"Portfolio reconciliation failed: {final_value} != {expected_final} (difference: {abs(final_value - expected_final):.2f})")
                
                # Check that daily P&L sums to total P&L (allow for same tolerance)
                total_daily_pnl = portfolio_df['daily_pnl'].sum()
                self.assertAlmostEqual(total_daily_pnl, total_pnl, delta=tolerance,
                                     msg=f"Daily P&L sum mismatch: {total_daily_pnl} != {total_pnl} (difference: {abs(total_daily_pnl - total_pnl):.2f})")
                
                print(f"   ✅ {result.strategy_config.strategy_name}: Portfolio reconciliation verified")
    
    def test_serialization_integrity(self):
        """Test serialization and deserialization integrity."""
        print("\n🧪 Testing Serialization Integrity...")
        
        for result in self.sample_results:
            with self.subTest(strategy=result.strategy_config.strategy_name):
                # Test JSON serialization
                result_dict = result.to_dict()
                reconstructed = UnifiedBacktestResult.from_dict(result_dict)
                
                # Check key attributes match
                self.assertEqual(result.backtest_id, reconstructed.backtest_id)
                self.assertEqual(result.trade_count, reconstructed.trade_count)
                self.assertEqual(result.strategy_config.strategy_name, 
                               reconstructed.strategy_config.strategy_name)
                
                # Check trade data integrity
                if result.trades:
                    original_trade_ids = {t.trade_id for t in result.trades}
                    reconstructed_trade_ids = {t.trade_id for t in reconstructed.trades}
                    self.assertEqual(original_trade_ids, reconstructed_trade_ids)
                
                # Check performance metrics
                self.assertAlmostEqual(result.performance_metrics.total_pnl,
                                     reconstructed.performance_metrics.total_pnl, places=2)
                
                print(f"   ✅ {result.strategy_config.strategy_name}: Serialization integrity verified")
    
    def test_single_source_of_truth(self):
        """Test that all data comes from single source of truth."""
        print("\n🧪 Testing Single Source of Truth...")
        
        # Create a result with known data
        test_result = self.generator.generate_sample_result(num_trades=5, strategy_name="SSOT Test")
        
        # Save to unified storage
        self.results_manager.save_backtest(test_result, validate=False)
        
        # Load and verify all access methods return consistent data
        loaded_result = self.results_manager.load_backtest(test_result.backtest_id)
        trades_df = self.results_manager.get_trade_log(test_result.backtest_id)
        portfolio_df = self.results_manager.get_portfolio_snapshots(test_result.backtest_id)
        
        # All methods should return the same underlying data
        self.assertEqual(len(trades_df), loaded_result.trade_count)
        self.assertEqual(len(portfolio_df), len(loaded_result.portfolio_snapshots))
        
        # Trade data should be identical
        if not trades_df.empty:
            trade_ids_df = set(trades_df['trade_id'])
            trade_ids_result = {t.trade_id for t in loaded_result.trades}
            self.assertEqual(trade_ids_df, trade_ids_result)
        
        # Cleanup
        self.results_manager.delete_backtest(test_result.backtest_id)
        
        print(f"   ✅ Single source of truth verified for {test_result.backtest_id}")
    
    def test_performance_review_generation(self):
        """Test performance review and reporting functionality."""
        print("\n🧪 Testing Performance Review Generation...")
        
        for result in self.sample_results:
            if result.trade_count == 0:
                continue
                
            with self.subTest(strategy=result.strategy_config.strategy_name):
                # Test that we can generate reports
                try:
                    # Save result first
                    self.results_manager.save_backtest(result, overwrite=True, validate=False)
                    
                    # Generate JSON report (simpler than HTML for testing)
                    report_path = self.results_manager.generate_report(
                        result.backtest_id, 
                        report_type='json',
                        output_dir=self.temp_dir / "reports"
                    )
                    
                    self.assertTrue(Path(report_path).exists())
                    
                    # Verify report content
                    with open(report_path, 'r') as f:
                        report_data = json.load(f)
                    
                    self.assertIn('metadata', report_data)
                    self.assertIn('performance_metrics', report_data)
                    self.assertIn('trades', report_data)
                    
                    print(f"   ✅ {result.strategy_config.strategy_name}: Report generated at {Path(report_path).name}")
                    
                except Exception as e:
                    self.fail(f"Report generation failed for {result.strategy_config.strategy_name}: {e}")


def run_comprehensive_verification():
    """Run the comprehensive verification suite."""
    print("🚀 Starting Comprehensive Verification Suite")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(ComprehensiveVerificationSuite)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    tests_run = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    successes = tests_run - failures - errors
    
    print(f"✅ Tests Passed: {successes}/{tests_run}")
    print(f"❌ Tests Failed: {failures}")
    print(f"💥 Tests Errored: {errors}")
    
    if result.failures:
        print("\n🔍 FAILURES:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Overall result
    if failures == 0 and errors == 0:
        print("\n🎉 ALL VERIFICATION TESTS PASSED!")
        print("✅ Performance Review, Trade Log, and AI functionality are working correctly")
        print("✅ Single source of truth implementation is verified")
        return True
    else:
        print(f"\n⚠️  VERIFICATION ISSUES FOUND: {failures + errors} problems detected")
        return False


if __name__ == "__main__":
    # Run verification suite
    success = run_comprehensive_verification()
    
    if success:
        print("\n🚀 SYSTEM READY FOR PRODUCTION")
        print("All components verified for consistency and accuracy")
    else:
        print("\n🛠️  SYSTEM NEEDS ATTENTION")
        print("Please address the issues found before proceeding")
    
    exit(0 if success else 1)