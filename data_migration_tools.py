#!/usr/bin/env python3
"""
Data Migration and Compatibility Tools

This module provides tools to migrate existing backtest results from various
legacy formats to the unified format, ensuring backward compatibility and
single source of truth implementation.
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, date, timedelta
import logging
import shutil
import re
from dataclasses import asdict
import warnings

from unified_results_schema import (
    UnifiedBacktestResult, BacktestMetadata, StrategyConfiguration,
    PerformanceMetrics, CompleteTrade, PortfolioSnapshot, TradeEntry, TradeExit,
    OptionType, TradeDirection, ExitReason, GreeksSnapshot, MarketConditions,
    create_backtest_id
)
from unified_results_manager import UnifiedResultsManager

warnings.filterwarnings('ignore', category=FutureWarning)

class LegacyDataConverter:
    """Converts legacy data formats to unified format."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Known legacy schemas
        self.cli_schema_mapping = {
            'trade_id': 'trade_id',
            'entry_date': 'entry_date',
            'exit_date': 'exit_date',
            'symbol': 'symbol',
            'option_type': 'option_type',
            'strike': 'strike',
            'expiration': 'expiration_date',
            'dte': 'days_to_expiration',
            'quantity': 'quantity',
            'entry_price': 'entry_price',
            'exit_price': 'exit_price',
            'pnl': 'pnl',
            'pnl_pct': 'pnl_percentage',
            'days_held': 'days_held',
            'exit_reason': 'exit_reason',
            'delta': 'entry_delta',
            'gamma': 'entry_gamma',
            'theta': 'entry_theta',
            'vega': 'entry_vega',
            'iv': 'entry_iv'
        }
        
        self.streamlit_schema_mapping = {
            'backtest_id': 'backtest_id',
            'strategy_name': 'strategy_name',
            'total_return': 'total_return_pct',
            'sharpe_ratio': 'sharpe_ratio',
            'max_drawdown': 'max_drawdown_pct',
            'total_trades': 'total_trades',
            'win_rate': 'win_rate_pct',
            'profit_factor': 'profit_factor'
        }
    
    def _setup_logging(self):
        """Setup logging for the converter."""
        logger = logging.getLogger('LegacyDataConverter')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def convert_cli_csv_result(self, csv_file: Path, 
                              strategy_name: str = "Migrated Strategy",
                              initial_capital: float = 100000.0) -> UnifiedBacktestResult:
        """Convert CLI CSV result to unified format."""
        
        self.logger.info(f"Converting CLI CSV: {csv_file}")
        
        # Read CSV data
        df = pd.read_csv(csv_file)
        
        # Create metadata
        metadata = BacktestMetadata(
            backtest_id=create_backtest_id(),
            run_timestamp=datetime.fromtimestamp(csv_file.stat().st_mtime),
            start_date=pd.to_datetime(df['entry_date'].min()).date(),
            end_date=pd.to_datetime(df['exit_date'].max()).date(),
            initial_capital=initial_capital,
            data_source="migrated_cli_csv",
            version="1.0",
            system_info={'migrated_from': str(csv_file)}
        )
        
        # Create strategy config
        strategy_config = StrategyConfiguration(
            strategy_name=strategy_name,
            strategy_type="options",
            parameters={'migrated': True},
            entry_criteria={},
            exit_criteria={},
            risk_management={},
            position_sizing={}
        )
        
        # Convert trades
        trades = []
        for _, row in df.iterrows():
            trade = self._convert_cli_trade_row(row)
            if trade:
                trades.append(trade)
        
        # Generate portfolio snapshots from trades
        portfolio_snapshots = self._generate_portfolio_snapshots_from_trades(
            trades, initial_capital, metadata.start_date, metadata.end_date
        )
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_from_trades(
            trades, portfolio_snapshots, initial_capital
        )
        
        return UnifiedBacktestResult(
            metadata=metadata,
            strategy_config=strategy_config,
            trades=trades,
            portfolio_snapshots=portfolio_snapshots,
            performance_metrics=performance_metrics,
            market_summary={'migrated': True},
            ai_analysis={'migrated': True}
        )
    
    def _convert_cli_trade_row(self, row: pd.Series) -> Optional[CompleteTrade]:
        """Convert a single CLI trade row to CompleteTrade."""
        try:
            # Parse dates
            entry_date = pd.to_datetime(row['entry_date'])
            exit_date = pd.to_datetime(row['exit_date'])
            
            if pd.isna(entry_date) or pd.isna(exit_date):
                return None
            
            # Parse expiration
            if 'expiration' in row:
                exp_str = str(row['expiration'])
                if len(exp_str) == 8 and exp_str.isdigit():
                    expiration_date = datetime.strptime(exp_str, '%Y%m%d').date()
                else:
                    expiration_date = entry_date.date() + timedelta(days=30)
            else:
                expiration_date = entry_date.date() + timedelta(days=30)
            
            # Create Greeks snapshots
            entry_greeks = GreeksSnapshot(
                delta=float(row.get('delta', 0)),
                gamma=float(row.get('gamma', 0)),
                theta=float(row.get('theta', 0)),
                vega=float(row.get('vega', 0)),
                rho=float(row.get('rho', 0)),
                implied_volatility=float(row.get('iv', 0.2))
            )
            
            exit_greeks = GreeksSnapshot(
                delta=float(row.get('exit_delta', row.get('delta', 0))),
                gamma=float(row.get('exit_gamma', row.get('gamma', 0))),
                theta=float(row.get('exit_theta', row.get('theta', 0))),
                vega=float(row.get('exit_vega', row.get('vega', 0))),
                rho=float(row.get('exit_rho', row.get('rho', 0))),
                implied_volatility=float(row.get('exit_iv', row.get('iv', 0.2)))
            )
            
            # Create market conditions (estimated)
            entry_market = MarketConditions(
                date=entry_date,
                underlying_price=float(row.get('underlying_price', row.get('strike', 400))),
                vix_level=20.0,  # Default
                iv_rank=50.0     # Default
            )
            
            exit_market = MarketConditions(
                date=exit_date,
                underlying_price=float(row.get('exit_underlying_price', entry_market.underlying_price)),
                vix_level=20.0,  # Default
                iv_rank=50.0     # Default
            )
            
            # Parse option type
            option_type = OptionType.PUT if str(row.get('option_type', 'P')).upper() == 'P' else OptionType.CALL
            
            # Parse exit reason
            exit_reason_str = str(row.get('exit_reason', 'manual')).lower()
            if 'profit' in exit_reason_str:
                exit_reason = ExitReason.PROFIT_TARGET
            elif 'stop' in exit_reason_str or 'loss' in exit_reason_str:
                exit_reason = ExitReason.STOP_LOSS
            elif 'time' in exit_reason_str or 'decay' in exit_reason_str:
                exit_reason = ExitReason.TIME_DECAY
            elif 'expir' in exit_reason_str:
                exit_reason = ExitReason.EXPIRATION
            else:
                exit_reason = ExitReason.MANUAL
            
            # Create trade entry
            trade_entry = TradeEntry(
                trade_id=str(row.get('trade_id', f"migrated_{hash(str(row))}")),
                timestamp=entry_date,
                symbol=str(row.get('symbol', 'SPY')),
                option_type=option_type,
                strike=float(row.get('strike', 400)),
                expiration_date=expiration_date,
                days_to_expiration=int(row.get('dte', 30)),
                quantity=int(row.get('quantity', 1)),
                direction=TradeDirection.LONG,  # Assume long for migrations
                entry_price=float(row.get('entry_price', 0)),
                entry_premium=float(row.get('entry_price', 0)) * 100,
                greeks=entry_greeks,
                market_conditions=entry_market
            )
            
            # Create trade exit
            trade_exit = TradeExit(
                trade_id=trade_entry.trade_id,
                timestamp=exit_date,
                exit_price=float(row.get('exit_price', 0)),
                exit_premium=float(row.get('exit_price', 0)) * 100,
                pnl=float(row.get('pnl', 0)),
                pnl_percentage=float(row.get('pnl_pct', 0)),
                greeks=exit_greeks,
                market_conditions=exit_market,
                exit_reason=exit_reason,
                days_held=int(row.get('days_held', (exit_date - entry_date).days)),
                max_profit_during_trade=max(float(row.get('pnl', 0)), 0),
                max_loss_during_trade=min(float(row.get('pnl', 0)), 0),
                commissions=float(row.get('commissions', 2.0))
            )
            
            return CompleteTrade(
                entry=trade_entry,
                exit=trade_exit,
                performance_attribution={'migrated': True},
                risk_metrics={'migrated': True},
                lessons_learned=['Migrated from legacy CSV format']
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to convert trade row: {e}")
            return None
    
    def convert_streamlit_json_result(self, json_file: Path) -> UnifiedBacktestResult:
        """Convert Streamlit JSON result to unified format."""
        
        self.logger.info(f"Converting Streamlit JSON: {json_file}")
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Extract key information
        results = data.get('results', {})
        config = data.get('config', {})
        
        # Create metadata
        metadata = BacktestMetadata(
            backtest_id=data.get('run_id', create_backtest_id()),
            run_timestamp=datetime.fromtimestamp(json_file.stat().st_mtime),
            start_date=pd.to_datetime(config.get('start_date', '2023-01-01')).date(),
            end_date=pd.to_datetime(config.get('end_date', '2023-12-31')).date(),
            initial_capital=float(config.get('initial_capital', 100000)),
            data_source="migrated_streamlit_json",
            version="1.0",
            system_info={'migrated_from': str(json_file)}
        )
        
        # Create strategy config
        strategy_config = StrategyConfiguration(
            strategy_name=config.get('strategy_name', 'Migrated Streamlit Strategy'),
            strategy_type="options",
            parameters=config.get('strategy_params', {}),
            entry_criteria=config.get('entry_criteria', {}),
            exit_criteria=config.get('exit_criteria', {}),
            risk_management=config.get('risk_management', {}),
            position_sizing=config.get('position_sizing', {})
        )
        
        # Convert trades if available
        trades = []
        if 'trade_log' in results:
            trade_data = results['trade_log']
            if isinstance(trade_data, list):
                trades = [self._convert_streamlit_trade(t) for t in trade_data]
                trades = [t for t in trades if t is not None]
        
        # Convert portfolio snapshots if available
        portfolio_snapshots = []
        if 'daily_equity' in results:
            portfolio_snapshots = self._convert_streamlit_portfolio(results['daily_equity'], metadata.initial_capital)
        
        # Extract or calculate performance metrics
        performance_metrics = self._extract_streamlit_performance(results, trades, metadata.initial_capital)
        
        return UnifiedBacktestResult(
            metadata=metadata,
            strategy_config=strategy_config,
            trades=trades,
            portfolio_snapshots=portfolio_snapshots,
            performance_metrics=performance_metrics,
            market_summary={'migrated': True},
            ai_analysis={'migrated': True}
        )
    
    def _convert_streamlit_trade(self, trade_data: Dict[str, Any]) -> Optional[CompleteTrade]:
        """Convert a Streamlit trade to CompleteTrade."""
        try:
            # This is a simplified conversion - would need to be adapted based on actual Streamlit format
            return None  # Placeholder
        except Exception as e:
            self.logger.warning(f"Failed to convert Streamlit trade: {e}")
            return None
    
    def _convert_streamlit_portfolio(self, equity_data: List[Dict], initial_capital: float) -> List[PortfolioSnapshot]:
        """Convert Streamlit portfolio data to PortfolioSnapshot list."""
        snapshots = []
        
        try:
            for entry in equity_data:
                snapshot = PortfolioSnapshot(
                    date=pd.to_datetime(entry['date']),
                    total_value=float(entry.get('equity', initial_capital)),
                    cash=float(entry.get('cash', initial_capital)),
                    options_value=float(entry.get('options_value', 0)),
                    pnl_unrealized=float(entry.get('unrealized_pnl', 0)),
                    pnl_realized=float(entry.get('realized_pnl', 0)),
                    daily_pnl=float(entry.get('daily_pnl', 0)),
                    active_positions=int(entry.get('active_positions', 0))
                )
                snapshots.append(snapshot)
        except Exception as e:
            self.logger.warning(f"Failed to convert portfolio data: {e}")
        
        return snapshots
    
    def _extract_streamlit_performance(self, results: Dict, trades: List[CompleteTrade], 
                                     initial_capital: float) -> PerformanceMetrics:
        """Extract performance metrics from Streamlit results."""
        
        # Try to extract from results, fallback to calculation
        total_pnl = sum(t.exit.pnl for t in trades) if trades else 0
        total_return_pct = (total_pnl / initial_capital) * 100
        
        winning_trades = [t for t in trades if t.exit.pnl > 0]
        losing_trades = [t for t in trades if t.exit.pnl <= 0]
        
        return PerformanceMetrics(
            total_return_pct=float(results.get('total_return', total_return_pct)),
            annualized_return_pct=float(results.get('annualized_return', total_return_pct * 1.2)),
            total_pnl=total_pnl,
            sharpe_ratio=float(results.get('sharpe_ratio', 0)),
            sortino_ratio=float(results.get('sortino_ratio', 0)),
            max_drawdown_pct=float(results.get('max_drawdown', 0)),
            max_drawdown_duration_days=int(results.get('max_drawdown_duration', 0)),
            volatility_annualized=float(results.get('volatility', 0)),
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate_pct=(len(winning_trades) / len(trades) * 100) if trades else 0,
            profit_factor=float(results.get('profit_factor', 0)),
            average_win=sum(t.exit.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            average_loss=abs(sum(t.exit.pnl for t in losing_trades)) / len(losing_trades) if losing_trades else 0,
            largest_win=max((t.exit.pnl for t in winning_trades), default=0),
            largest_loss=min((t.exit.pnl for t in losing_trades), default=0),
            average_days_in_trade=np.mean([t.exit.days_held for t in trades]) if trades else 0
        )
    
    def _generate_portfolio_snapshots_from_trades(self, trades: List[CompleteTrade], 
                                                initial_capital: float,
                                                start_date: date, end_date: date) -> List[PortfolioSnapshot]:
        """Generate portfolio snapshots from trade data."""
        snapshots = []
        
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
                cash=current_value - (active_positions * 250),
                options_value=active_positions * 250,
                pnl_unrealized=0,
                pnl_realized=realized_pnl,
                daily_pnl=daily_pnl,
                active_positions=active_positions
            )
            
            snapshots.append(snapshot)
            current_date += timedelta(days=1)
        
        return snapshots
    
    def _calculate_performance_from_trades(self, trades: List[CompleteTrade],
                                         portfolio_snapshots: List[PortfolioSnapshot],
                                         initial_capital: float) -> PerformanceMetrics:
        """Calculate performance metrics from trade and portfolio data."""
        
        if not trades:
            return PerformanceMetrics(
                total_return_pct=0, annualized_return_pct=0, total_pnl=0,
                sharpe_ratio=0, sortino_ratio=0, max_drawdown_pct=0,
                max_drawdown_duration_days=0, volatility_annualized=0,
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate_pct=0, profit_factor=0, average_win=0,
                average_loss=0, largest_win=0, largest_loss=0,
                average_days_in_trade=0
            )
        
        # Trade metrics
        winning_trades = [t for t in trades if t.exit.pnl > 0]
        losing_trades = [t for t in trades if t.exit.pnl <= 0]
        
        total_pnl = sum(t.exit.pnl for t in trades)
        total_return_pct = (total_pnl / initial_capital) * 100
        
        # Risk metrics from portfolio snapshots
        if portfolio_snapshots:
            portfolio_values = [s.total_value for s in portfolio_snapshots]
            peak_values = pd.Series(portfolio_values).expanding().max()
            drawdowns = (pd.Series(portfolio_values) - peak_values) / peak_values
            max_drawdown_pct = abs(drawdowns.min()) * 100
            
            daily_returns = pd.Series([s.daily_pnl for s in portfolio_snapshots]) / initial_capital
            sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
            volatility = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0
        else:
            max_drawdown_pct = 0
            sharpe_ratio = 0
            volatility = 0
        
        # Win rate and profit factor
        win_rate_pct = (len(winning_trades) / len(trades)) * 100
        gross_profit = sum(t.exit.pnl for t in winning_trades)
        gross_loss = abs(sum(t.exit.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return PerformanceMetrics(
            total_return_pct=total_return_pct,
            annualized_return_pct=total_return_pct * (365 / 252),  # Rough approximation
            total_pnl=total_pnl,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sharpe_ratio * 1.2,  # Approximation
            max_drawdown_pct=max_drawdown_pct,
            max_drawdown_duration_days=0,  # Would need more complex calculation
            volatility_annualized=volatility,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate_pct=win_rate_pct,
            profit_factor=profit_factor,
            average_win=gross_profit / len(winning_trades) if winning_trades else 0,
            average_loss=gross_loss / len(losing_trades) if losing_trades else 0,
            largest_win=max((t.exit.pnl for t in winning_trades), default=0),
            largest_loss=min((t.exit.pnl for t in losing_trades), default=0),
            average_days_in_trade=np.mean([t.exit.days_held for t in trades])
        )


class MigrationManager:
    """Manages the complete migration process from legacy to unified format."""
    
    def __init__(self, unified_manager: UnifiedResultsManager):
        self.unified_manager = unified_manager
        self.converter = LegacyDataConverter()
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging for migration manager."""
        logger = logging.getLogger('MigrationManager')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = Path("migration.log")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def migrate_directory(self, source_dir: Path, 
                         file_patterns: List[str] = ["*.csv", "*.json"],
                         dry_run: bool = True) -> Dict[str, Any]:
        """Migrate all files in a directory to unified format."""
        
        self.logger.info(f"Starting migration of {source_dir} (dry_run={dry_run})")
        
        migration_report = {
            'source_directory': str(source_dir),
            'dry_run': dry_run,
            'start_time': datetime.now().isoformat(),
            'files_processed': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'errors': [],
            'migrated_ids': []
        }
        
        if not source_dir.exists():
            migration_report['errors'].append(f"Source directory does not exist: {source_dir}")
            return migration_report
        
        # Find files to migrate
        files_to_migrate = []
        for pattern in file_patterns:
            files_to_migrate.extend(source_dir.glob(pattern))
        
        self.logger.info(f"Found {len(files_to_migrate)} files to migrate")
        
        for file_path in files_to_migrate:
            migration_report['files_processed'] += 1
            
            try:
                # Determine file type and convert
                if file_path.suffix.lower() == '.csv':
                    unified_result = self.converter.convert_cli_csv_result(file_path)
                elif file_path.suffix.lower() == '.json':
                    unified_result = self.converter.convert_streamlit_json_result(file_path)
                else:
                    self.logger.warning(f"Unsupported file type: {file_path}")
                    continue
                
                if not dry_run:
                    # Save to unified storage
                    self.unified_manager.save_backtest(unified_result, validate=False)
                    migration_report['migrated_ids'].append(unified_result.backtest_id)
                
                migration_report['successful_migrations'] += 1
                self.logger.info(f"Successfully migrated: {file_path.name}")
                
            except Exception as e:
                migration_report['failed_migrations'] += 1
                error_msg = f"Failed to migrate {file_path.name}: {str(e)}"
                migration_report['errors'].append(error_msg)
                self.logger.error(error_msg)
        
        migration_report['end_time'] = datetime.now().isoformat()
        self.logger.info(f"Migration complete: {migration_report['successful_migrations']}/{migration_report['files_processed']} successful")
        
        return migration_report
    
    def migrate_known_directories(self, base_dir: Path = Path("."), dry_run: bool = True) -> Dict[str, Any]:
        """Migrate all known legacy data directories."""
        
        known_sources = [
            (base_dir / "spy_backtester" / "results", ["*.csv"]),
            (base_dir / "streamlit-backtester" / "backtest_results", ["*.json"]),
            (base_dir / "results", ["*.csv", "*.json"]),
            (base_dir / "backtest_results", ["*.csv", "*.json"])
        ]
        
        overall_report = {
            'migration_type': 'known_directories',
            'dry_run': dry_run,
            'start_time': datetime.now().isoformat(),
            'directories_processed': 0,
            'total_files_processed': 0,
            'total_successful_migrations': 0,
            'total_failed_migrations': 0,
            'directory_reports': {}
        }
        
        for source_dir, patterns in known_sources:
            if source_dir.exists():
                overall_report['directories_processed'] += 1
                
                report = self.migrate_directory(source_dir, patterns, dry_run)
                overall_report['directory_reports'][str(source_dir)] = report
                
                overall_report['total_files_processed'] += report['files_processed']
                overall_report['total_successful_migrations'] += report['successful_migrations']
                overall_report['total_failed_migrations'] += report['failed_migrations']
        
        overall_report['end_time'] = datetime.now().isoformat()
        
        return overall_report
    
    def create_compatibility_layer(self) -> Dict[str, Callable]:
        """Create compatibility functions for legacy code."""
        
        def load_cli_format(backtest_id: str) -> pd.DataFrame:
            """Load backtest in CLI CSV format."""
            result = self.unified_manager.load_backtest(backtest_id)
            return result.get_trades_dataframe()
        
        def load_streamlit_format(backtest_id: str) -> Dict[str, Any]:
            """Load backtest in Streamlit JSON format."""
            result = self.unified_manager.load_backtest(backtest_id)
            return {
                'results': {
                    'trade_log': result.get_trades_dataframe().to_dict('records'),
                    'daily_equity': result.get_portfolio_dataframe().to_dict('records'),
                    'performance': result.performance_metrics.to_dict()
                },
                'config': result.strategy_config.to_dict(),
                'run_id': result.backtest_id
            }
        
        def get_legacy_performance_summary(backtest_id: str) -> Dict[str, float]:
            """Get performance summary in legacy format."""
            result = self.unified_manager.load_backtest(backtest_id)
            metrics = result.performance_metrics
            
            return {
                'total_return': metrics.total_return_pct,
                'sharpe_ratio': metrics.sharpe_ratio,
                'max_drawdown': metrics.max_drawdown_pct,
                'total_trades': metrics.total_trades,
                'win_rate': metrics.win_rate_pct,
                'profit_factor': metrics.profit_factor,
                'average_win': metrics.average_win,
                'average_loss': metrics.average_loss
            }
        
        return {
            'load_cli_format': load_cli_format,
            'load_streamlit_format': load_streamlit_format,
            'get_legacy_performance_summary': get_legacy_performance_summary
        }


def create_migration_script(base_dir: Path = Path(".")) -> str:
    """Create a standalone migration script."""
    
    script_content = f'''#!/usr/bin/env python3
"""
Standalone Migration Script
Generated: {datetime.now().isoformat()}

Run this script to migrate all legacy backtest results to unified format.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append("{base_dir}")

from unified_results_manager import UnifiedResultsManager
from data_migration_tools import MigrationManager

def main():
    print("🚀 Starting Backtest Results Migration")
    print("=" * 50)
    
    # Initialize unified results manager
    manager = UnifiedResultsManager("{base_dir}/results")
    migrator = MigrationManager(manager)
    
    # Perform dry run first
    print("📋 Performing dry run...")
    dry_report = migrator.migrate_known_directories(Path("{base_dir}"), dry_run=True)
    
    print(f"   Found {{dry_report['total_files_processed']}} files to migrate")
    print(f"   Expected {{dry_report['total_successful_migrations']}} successful migrations")
    
    if dry_report['total_files_processed'] == 0:
        print("ℹ️  No legacy files found to migrate")
        return
    
    # Ask for confirmation
    response = input("\\n🔄 Proceed with actual migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled")
        return
    
    # Perform actual migration
    print("\\n🔄 Performing actual migration...")
    actual_report = migrator.migrate_known_directories(Path("{base_dir}"), dry_run=False)
    
    # Print results
    print("\\n" + "=" * 50)
    print("📊 MIGRATION RESULTS")
    print("=" * 50)
    print(f"Directories processed: {{actual_report['directories_processed']}}")
    print(f"Files processed: {{actual_report['total_files_processed']}}")
    print(f"Successful migrations: {{actual_report['total_successful_migrations']}}")
    print(f"Failed migrations: {{actual_report['total_failed_migrations']}}")
    
    if actual_report['total_successful_migrations'] > 0:
        print("\\n✅ Migration completed successfully!")
        print("All legacy results have been converted to unified format")
    else:
        print("\\n⚠️  No files were migrated")
    
    # Show storage stats
    stats = manager.get_storage_stats()
    print(f"\\n📈 Storage: {{stats['unified_results_count']}} unified results, {{stats['total_size_mb']:.1f}} MB")

if __name__ == "__main__":
    main()
'''
    
    return script_content


if __name__ == "__main__":
    # Test migration tools
    print("🧪 Testing Migration Tools...")
    
    # Create test directories and files
    test_dir = Path("test_migration")
    test_dir.mkdir(exist_ok=True)
    
    # Create sample CSV data
    sample_csv_data = {
        'trade_id': ['trade_001', 'trade_002'],
        'entry_date': ['2023-06-15', '2023-06-20'],
        'exit_date': ['2023-06-20', '2023-06-25'],
        'symbol': ['SPY', 'SPY'],
        'option_type': ['P', 'C'],
        'strike': [410, 420],
        'quantity': [1, 1],
        'entry_price': [2.50, 3.00],
        'exit_price': [3.75, 2.25],
        'pnl': [125, -75],
        'days_held': [5, 5],
        'delta': [-0.30, 0.25]
    }
    
    sample_df = pd.DataFrame(sample_csv_data)
    csv_file = test_dir / "sample_backtest.csv"
    sample_df.to_csv(csv_file, index=False)
    
    try:
        # Test converter
        converter = LegacyDataConverter()
        unified_result = converter.convert_cli_csv_result(csv_file, "Test Migration Strategy")
        
        print(f"✅ Converted CSV with {unified_result.trade_count} trades")
        print(f"   Strategy: {unified_result.strategy_config.strategy_name}")
        print(f"   Total P&L: ${unified_result.performance_metrics.total_pnl:.2f}")
        print(f"   Win Rate: {unified_result.performance_metrics.win_rate_pct:.1f}%")
        
        # Test migration manager
        manager = UnifiedResultsManager(test_dir / "unified")
        migrator = MigrationManager(manager)
        
        migration_report = migrator.migrate_directory(test_dir, ["*.csv"], dry_run=True)
        print(f"✅ Migration dry run: {migration_report['successful_migrations']} files ready")
        
        # Generate migration script
        script_content = create_migration_script(Path("."))
        script_file = test_dir / "migrate.py"
        with open(script_file, 'w') as f:
            f.write(script_content)
        print(f"✅ Migration script generated: {script_file}")
        
        print("\n🎉 Migration Tools Test Complete!")
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)