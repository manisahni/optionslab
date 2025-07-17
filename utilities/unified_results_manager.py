#!/usr/bin/env python3
"""
Unified Results Manager - Single Source of Truth for Backtest Results

This module provides centralized management of all backtest results,
ensuring consistency across CLI, Streamlit, and AI analysis systems.
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime, date
import logging
import shutil
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
import pickle
import gzip

from unified_results_schema import (
    UnifiedBacktestResult, BacktestMetadata, StrategyConfiguration,
    PerformanceMetrics, CompleteTrade, PortfolioSnapshot,
    ResultValidator, create_backtest_id
)

logger = logging.getLogger(__name__)

class ResultsStorageError(Exception):
    """Exception raised for results storage errors."""
    pass

class BacktestSummary:
    """Summary information about a backtest for listing purposes."""
    
    def __init__(self, result: UnifiedBacktestResult):
        self.backtest_id = result.backtest_id
        self.strategy_name = result.strategy_config.strategy_name
        self.run_timestamp = result.metadata.run_timestamp
        self.start_date = result.metadata.start_date
        self.end_date = result.metadata.end_date
        self.total_trades = result.trade_count
        self.total_return_pct = result.performance_metrics.total_return_pct
        self.win_rate_pct = result.performance_metrics.win_rate_pct
        self.max_drawdown_pct = result.performance_metrics.max_drawdown_pct
        self.sharpe_ratio = result.performance_metrics.sharpe_ratio
        self.initial_capital = result.metadata.initial_capital
        self.final_value = result.final_portfolio_value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'backtest_id': self.backtest_id,
            'strategy_name': self.strategy_name,
            'run_timestamp': self.run_timestamp.isoformat(),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'total_trades': self.total_trades,
            'total_return_pct': self.total_return_pct,
            'win_rate_pct': self.win_rate_pct,
            'max_drawdown_pct': self.max_drawdown_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'initial_capital': self.initial_capital,
            'final_value': self.final_value
        }

class UnifiedResultsManager:
    """
    Central manager for all backtest results providing single source of truth.
    
    Features:
    - Unified storage format
    - Automatic backup and versioning
    - Concurrent access handling
    - Data integrity validation
    - Legacy format migration
    - Performance optimization
    """
    
    def __init__(self, base_dir: Union[str, Path] = "results", 
                 enable_compression: bool = True,
                 enable_backup: bool = True,
                 max_concurrent_ops: int = 4):
        """
        Initialize the unified results manager.
        
        Args:
            base_dir: Base directory for storing results
            enable_compression: Whether to compress stored results
            enable_backup: Whether to create automatic backups
            max_concurrent_ops: Maximum concurrent operations
        """
        self.base_dir = Path(base_dir)
        self.unified_dir = self.base_dir / "unified"
        self.backup_dir = self.base_dir / "backups"
        self.legacy_dir = self.base_dir / "legacy"
        self.temp_dir = self.base_dir / "temp"
        
        # Configuration
        self.enable_compression = enable_compression
        self.enable_backup = enable_backup
        self.max_concurrent_ops = max_concurrent_ops
        
        # Create directories
        for directory in [self.unified_dir, self.backup_dir, self.legacy_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent_ops)
        
        # Cache for performance
        self._summary_cache: Dict[str, BacktestSummary] = {}
        self._cache_timestamp = datetime.now()
        self._cache_ttl_seconds = 300  # 5 minutes
        
        # Validator
        self.validator = ResultValidator()
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging for results manager."""
        log_file = self.base_dir / "results_manager.log"
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    def _generate_filename(self, result: UnifiedBacktestResult) -> str:
        """Generate standardized filename for a result."""
        strategy_name = result.strategy_config.strategy_name.replace(' ', '_').lower()
        timestamp = result.metadata.run_timestamp.strftime('%Y%m%d_%H%M%S')
        
        # Create a hash of key parameters for uniqueness
        params_str = json.dumps(result.strategy_config.parameters, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        filename = f"backtest_{timestamp}_{strategy_name}_{params_hash}"
        
        if self.enable_compression:
            return f"{filename}.json.gz"
        else:
            return f"{filename}.json"
    
    def _save_compressed(self, data: Dict[str, Any], filepath: Path) -> None:
        """Save data with optional compression."""
        if self.enable_compression and filepath.suffix == '.gz':
            with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
    
    def _load_compressed(self, filepath: Path) -> Dict[str, Any]:
        """Load data with optional compression support."""
        if filepath.suffix == '.gz':
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def _create_backup(self, backtest_id: str) -> None:
        """Create backup of existing result."""
        if not self.enable_backup:
            return
        
        existing_file = self._find_result_file(backtest_id)
        if existing_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{existing_file.stem}_backup_{timestamp}{existing_file.suffix}"
            backup_path = self.backup_dir / backup_name
            shutil.copy2(existing_file, backup_path)
            logger.info(f"Created backup: {backup_path}")
    
    def _find_result_file(self, backtest_id: str) -> Optional[Path]:
        """Find the file containing a specific backtest result."""
        # Search in unified directory
        for file_path in self.unified_dir.glob("*.json*"):
            try:
                data = self._load_compressed(file_path)
                if data.get('metadata', {}).get('backtest_id') == backtest_id:
                    return file_path
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                continue
        
        return None
    
    def _invalidate_cache(self):
        """Invalidate the summary cache."""
        with self._lock:
            self._summary_cache.clear()
            self._cache_timestamp = datetime.now()
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        return (datetime.now() - self._cache_timestamp).seconds < self._cache_ttl_seconds
    
    def save_backtest(self, result: UnifiedBacktestResult, 
                     overwrite: bool = False,
                     validate: bool = True) -> str:
        """
        Save a backtest result to unified storage.
        
        Args:
            result: Unified backtest result to save
            overwrite: Whether to overwrite existing results
            validate: Whether to validate the result before saving
            
        Returns:
            Path to saved file
            
        Raises:
            ResultsStorageError: If save operation fails
        """
        try:
            with self._lock:
                # Validate if requested
                if validate:
                    validation = self.validator.validate_result(result)
                    if not validation['is_valid']:
                        issues = ', '.join(validation['issues'])
                        raise ResultsStorageError(f"Validation failed: {issues}")
                
                # Check if result already exists
                existing_file = self._find_result_file(result.backtest_id)
                if existing_file and not overwrite:
                    raise ResultsStorageError(f"Backtest {result.backtest_id} already exists. Use overwrite=True to replace.")
                
                # Create backup if overwriting
                if existing_file and overwrite:
                    self._create_backup(result.backtest_id)
                
                # Generate filename and save
                filename = self._generate_filename(result)
                filepath = self.unified_dir / filename
                
                # Save to temporary file first, then move (atomic operation)
                temp_filepath = self.temp_dir / f"temp_{filename}"
                self._save_compressed(result.to_dict(), temp_filepath)
                
                # Move to final location
                shutil.move(temp_filepath, filepath)
                
                # Update cache
                self._summary_cache[result.backtest_id] = BacktestSummary(result)
                
                logger.info(f"Saved backtest {result.backtest_id} to {filepath}")
                return str(filepath)
                
        except Exception as e:
            logger.error(f"Failed to save backtest {result.backtest_id}: {e}")
            raise ResultsStorageError(f"Save failed: {e}")
    
    def load_backtest(self, backtest_id: str) -> UnifiedBacktestResult:
        """
        Load a specific backtest result.
        
        Args:
            backtest_id: ID of the backtest to load
            
        Returns:
            Unified backtest result
            
        Raises:
            ResultsStorageError: If load operation fails
        """
        try:
            filepath = self._find_result_file(backtest_id)
            if not filepath:
                raise ResultsStorageError(f"Backtest {backtest_id} not found")
            
            data = self._load_compressed(filepath)
            result = UnifiedBacktestResult.from_dict(data)
            
            logger.debug(f"Loaded backtest {backtest_id} from {filepath}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to load backtest {backtest_id}: {e}")
            raise ResultsStorageError(f"Load failed: {e}")
    
    def list_backtests(self, filters: Optional[Dict[str, Any]] = None,
                      sort_by: str = 'run_timestamp',
                      sort_descending: bool = True,
                      limit: Optional[int] = None) -> List[BacktestSummary]:
        """
        List backtest summaries with optional filtering and sorting.
        
        Args:
            filters: Filter criteria (e.g., {'strategy_name': 'Long Put'})
            sort_by: Field to sort by
            sort_descending: Sort order
            limit: Maximum number of results
            
        Returns:
            List of backtest summaries
        """
        try:
            with self._lock:
                # Refresh cache if needed
                if not self._is_cache_valid() or not self._summary_cache:
                    self._refresh_summary_cache()
                
                summaries = list(self._summary_cache.values())
                
                # Apply filters
                if filters:
                    filtered_summaries = []
                    for summary in summaries:
                        include = True
                        for key, value in filters.items():
                            if hasattr(summary, key):
                                if getattr(summary, key) != value:
                                    include = False
                                    break
                        if include:
                            filtered_summaries.append(summary)
                    summaries = filtered_summaries
                
                # Sort
                if sort_by and hasattr(summaries[0] if summaries else BacktestSummary, sort_by):
                    summaries.sort(key=lambda x: getattr(x, sort_by), reverse=sort_descending)
                
                # Limit
                if limit:
                    summaries = summaries[:limit]
                
                return summaries
                
        except Exception as e:
            logger.error(f"Failed to list backtests: {e}")
            return []
    
    def _refresh_summary_cache(self):
        """Refresh the summary cache by scanning all result files."""
        logger.info("Refreshing summary cache...")
        self._summary_cache.clear()
        
        for file_path in self.unified_dir.glob("*.json*"):
            try:
                data = self._load_compressed(file_path)
                result = UnifiedBacktestResult.from_dict(data)
                summary = BacktestSummary(result)
                self._summary_cache[result.backtest_id] = summary
            except Exception as e:
                logger.warning(f"Could not process {file_path}: {e}")
                continue
        
        self._cache_timestamp = datetime.now()
        logger.info(f"Cache refreshed with {len(self._summary_cache)} results")
    
    def delete_backtest(self, backtest_id: str, create_backup: bool = True) -> bool:
        """
        Delete a backtest result.
        
        Args:
            backtest_id: ID of the backtest to delete
            create_backup: Whether to create backup before deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                filepath = self._find_result_file(backtest_id)
                if not filepath:
                    logger.warning(f"Backtest {backtest_id} not found for deletion")
                    return False
                
                # Create backup if requested
                if create_backup:
                    self._create_backup(backtest_id)
                
                # Delete file
                filepath.unlink()
                
                # Remove from cache
                self._summary_cache.pop(backtest_id, None)
                
                logger.info(f"Deleted backtest {backtest_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete backtest {backtest_id}: {e}")
            return False
    
    def get_trade_log(self, backtest_id: str) -> pd.DataFrame:
        """
        Get trade log as pandas DataFrame.
        
        Args:
            backtest_id: ID of the backtest
            
        Returns:
            DataFrame with trade data
        """
        result = self.load_backtest(backtest_id)
        return result.get_trades_dataframe()
    
    def get_portfolio_snapshots(self, backtest_id: str) -> pd.DataFrame:
        """
        Get portfolio snapshots as pandas DataFrame.
        
        Args:
            backtest_id: ID of the backtest
            
        Returns:
            DataFrame with portfolio data
        """
        result = self.load_backtest(backtest_id)
        return result.get_portfolio_dataframe()
    
    def generate_report(self, backtest_id: str, 
                       report_type: str = 'html',
                       output_dir: Optional[Path] = None) -> str:
        """
        Generate a comprehensive report for a backtest.
        
        Args:
            backtest_id: ID of the backtest
            report_type: Type of report ('html', 'pdf', 'json')
            output_dir: Directory to save report
            
        Returns:
            Path to generated report
        """
        result = self.load_backtest(backtest_id)
        
        if output_dir is None:
            output_dir = self.base_dir / "reports"
        
        # Ensure output directory exists
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if report_type == 'html':
            # Import here to avoid circular dependency
            import sys
            sys.path.append('spy_backtester')
            from reporter import PerformanceReporter
            
            # Convert to format expected by PerformanceReporter
            legacy_results = {
                'trades_df': result.get_trades_dataframe(),
                'snapshots_df': result.get_portfolio_dataframe(),
                'performance': result.performance_metrics.to_dict(),
                'strategy': result.strategy_config.strategy_name,
                'period': f"{result.metadata.start_date} to {result.metadata.end_date}"
            }
            
            reporter = PerformanceReporter(legacy_results, str(output_dir))
            report_path = reporter.generate_full_report()
            return report_path
            
        elif report_type == 'json':
            report_path = output_dir / f"report_{backtest_id}_{timestamp}.json"
            with open(report_path, 'w') as f:
                json.dump(result.to_dict(), f, indent=2, default=str)
            return str(report_path)
        
        else:
            raise ValueError(f"Unsupported report type: {report_type}")
    
    def compare_backtests(self, backtest_ids: List[str]) -> pd.DataFrame:
        """
        Compare multiple backtests side by side.
        
        Args:
            backtest_ids: List of backtest IDs to compare
            
        Returns:
            DataFrame with comparison metrics
        """
        comparison_data = []
        
        for backtest_id in backtest_ids:
            try:
                result = self.load_backtest(backtest_id)
                comparison_data.append({
                    'backtest_id': backtest_id,
                    'strategy': result.strategy_config.strategy_name,
                    'start_date': result.metadata.start_date,
                    'end_date': result.metadata.end_date,
                    'total_trades': result.trade_count,
                    'total_return_pct': result.performance_metrics.total_return_pct,
                    'annualized_return_pct': result.performance_metrics.annualized_return_pct,
                    'win_rate_pct': result.performance_metrics.win_rate_pct,
                    'profit_factor': result.performance_metrics.profit_factor,
                    'max_drawdown_pct': result.performance_metrics.max_drawdown_pct,
                    'sharpe_ratio': result.performance_metrics.sharpe_ratio,
                    'sortino_ratio': result.performance_metrics.sortino_ratio,
                    'volatility': result.performance_metrics.volatility_annualized,
                    'final_value': result.final_portfolio_value
                })
            except Exception as e:
                logger.warning(f"Could not load backtest {backtest_id} for comparison: {e}")
        
        return pd.DataFrame(comparison_data)
    
    def migrate_legacy_results(self, legacy_dirs: List[Union[str, Path]],
                             dry_run: bool = True) -> Dict[str, Any]:
        """
        Migrate results from legacy formats to unified format.
        
        Args:
            legacy_dirs: List of directories containing legacy results
            dry_run: If True, only analyze without migrating
            
        Returns:
            Migration report
        """
        migration_report = {
            'processed_files': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'errors': [],
            'migrated_results': []
        }
        
        for legacy_dir in legacy_dirs:
            legacy_path = Path(legacy_dir)
            if not legacy_path.exists():
                migration_report['errors'].append(f"Legacy directory not found: {legacy_dir}")
                continue
            
            # Look for CSV and JSON files
            for file_pattern in ["*.csv", "*.json"]:
                for file_path in legacy_path.glob(file_pattern):
                    migration_report['processed_files'] += 1
                    
                    try:
                        if dry_run:
                            logger.info(f"Would migrate: {file_path}")
                            migration_report['successful_migrations'] += 1
                        else:
                            # Actual migration logic would go here
                            # This is a placeholder for the conversion logic
                            logger.info(f"Migrating: {file_path}")
                            migration_report['successful_migrations'] += 1
                            migration_report['migrated_results'].append(str(file_path))
                            
                    except Exception as e:
                        migration_report['failed_migrations'] += 1
                        migration_report['errors'].append(f"Failed to migrate {file_path}: {e}")
        
        return migration_report
    
    def validate_all_results(self) -> Dict[str, Any]:
        """
        Validate all stored results for integrity.
        
        Returns:
            Validation report
        """
        validation_report = {
            'total_results': 0,
            'valid_results': 0,
            'invalid_results': 0,
            'results_with_warnings': 0,
            'issues': [],
            'warnings': []
        }
        
        for file_path in self.unified_dir.glob("*.json*"):
            validation_report['total_results'] += 1
            
            try:
                data = self._load_compressed(file_path)
                result = UnifiedBacktestResult.from_dict(data)
                validation = self.validator.validate_result(result)
                
                if validation['is_valid']:
                    validation_report['valid_results'] += 1
                else:
                    validation_report['invalid_results'] += 1
                    validation_report['issues'].extend([
                        f"{result.backtest_id}: {issue}" for issue in validation['issues']
                    ])
                
                if validation['warnings']:
                    validation_report['results_with_warnings'] += 1
                    validation_report['warnings'].extend([
                        f"{result.backtest_id}: {warning}" for warning in validation['warnings']
                    ])
                    
            except Exception as e:
                validation_report['invalid_results'] += 1
                validation_report['issues'].append(f"{file_path.name}: Failed to load - {e}")
        
        return validation_report
    
    def cleanup_storage(self, max_backup_age_days: int = 30,
                       max_temp_age_hours: int = 24) -> Dict[str, int]:
        """
        Clean up old backup and temporary files.
        
        Args:
            max_backup_age_days: Maximum age for backup files
            max_temp_age_hours: Maximum age for temporary files
            
        Returns:
            Cleanup statistics
        """
        cleanup_stats = {'deleted_backups': 0, 'deleted_temp_files': 0}
        
        now = datetime.now()
        
        # Clean old backups
        for backup_file in self.backup_dir.glob("*"):
            file_age = now - datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_age.days > max_backup_age_days:
                backup_file.unlink()
                cleanup_stats['deleted_backups'] += 1
        
        # Clean old temp files
        for temp_file in self.temp_dir.glob("*"):
            file_age = now - datetime.fromtimestamp(temp_file.stat().st_mtime)
            if file_age.total_seconds() > max_temp_age_hours * 3600:
                temp_file.unlink()
                cleanup_stats['deleted_temp_files'] += 1
        
        return cleanup_stats
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        def get_dir_size(directory: Path) -> int:
            return sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
        
        return {
            'unified_results_count': len(list(self.unified_dir.glob("*.json*"))),
            'unified_size_mb': get_dir_size(self.unified_dir) / (1024 * 1024),
            'backup_count': len(list(self.backup_dir.glob("*"))),
            'backup_size_mb': get_dir_size(self.backup_dir) / (1024 * 1024),
            'temp_files_count': len(list(self.temp_dir.glob("*"))),
            'total_size_mb': get_dir_size(self.base_dir) / (1024 * 1024)
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self._executor.shutdown(wait=True)


# Global instance for easy access
_global_manager: Optional[UnifiedResultsManager] = None

def get_results_manager(base_dir: Union[str, Path] = "results") -> UnifiedResultsManager:
    """Get or create global results manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = UnifiedResultsManager(base_dir)
    return _global_manager

def reset_results_manager():
    """Reset global results manager (for testing)."""
    global _global_manager
    if _global_manager:
        _global_manager.__exit__(None, None, None)
    _global_manager = None


if __name__ == "__main__":
    # Test the unified results manager
    print("Testing Unified Results Manager...")
    
    # Create test directory
    test_dir = Path("test_results_manager")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    try:
        # Initialize manager
        manager = UnifiedResultsManager(test_dir)
        
        # Create sample result (reuse from schema test)
        from unified_results_schema import *
        
        metadata = BacktestMetadata(
            backtest_id=create_backtest_id(),
            run_timestamp=datetime.now(),
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            initial_capital=100000.0,
            data_source="test_data"
        )
        
        strategy_config = StrategyConfiguration(
            strategy_name="Test Strategy",
            strategy_type="options",
            parameters={'test_param': 42},
            entry_criteria={},
            exit_criteria={},
            risk_management={},
            position_sizing={}
        )
        
        performance_metrics = PerformanceMetrics(
            total_return_pct=15.5, annualized_return_pct=18.2, total_pnl=15500.0,
            sharpe_ratio=1.35, sortino_ratio=1.55, max_drawdown_pct=8.2,
            max_drawdown_duration_days=25, volatility_annualized=14.5,
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate_pct=0.0, profit_factor=0.0, average_win=0.0,
            average_loss=0.0, largest_win=0.0, largest_loss=0.0,
            average_days_in_trade=0.0
        )
        
        unified_result = UnifiedBacktestResult(
            metadata=metadata,
            strategy_config=strategy_config,
            trades=[],
            portfolio_snapshots=[],
            performance_metrics=performance_metrics
        )
        
        # Test save
        saved_path = manager.save_backtest(unified_result)
        print(f"✅ Saved result to: {saved_path}")
        
        # Test load
        loaded_result = manager.load_backtest(unified_result.backtest_id)
        print(f"✅ Loaded result: {loaded_result.backtest_id}")
        
        # Test list
        summaries = manager.list_backtests()
        print(f"✅ Found {len(summaries)} results")
        
        # Test storage stats
        stats = manager.get_storage_stats()
        print(f"✅ Storage stats: {stats['unified_results_count']} results, {stats['total_size_mb']:.2f} MB")
        
        # Test validation
        validation_report = manager.validate_all_results()
        print(f"✅ Validation: {validation_report['valid_results']}/{validation_report['total_results']} valid")
        
        print("✅ Unified Results Manager test completed successfully")
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)