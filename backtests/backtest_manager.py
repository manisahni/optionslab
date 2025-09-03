"""
Centralized Backtest Management System
Handles running, storing, and retrieving backtest results for both notebook and Gradio interfaces
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import shutil
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')

from optionslab.backtest_engine import run_auditable_backtest
from optionslab.data_loader import load_strategy_config


class BacktestManager:
    """Manages backtest execution, storage, and retrieval"""
    
    def __init__(self, base_dir: str = "backtests/results"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_dir / "index.json"
        self.load_index()
    
    def load_index(self) -> None:
        """Load the master index of all backtests"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {"backtests": [], "last_updated": None}
    
    def save_index(self) -> None:
        """Save the master index"""
        self.index["last_updated"] = datetime.now().isoformat()
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def run_backtest(self, 
                     config_file: str,
                     start_date: str,
                     end_date: str,
                     data_file: str = "data/spy_options/",
                     description: str = "") -> Dict[str, Any]:
        """
        Run a backtest and store results
        
        Args:
            config_file: Path to strategy YAML config
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            data_file: Path to data directory
            description: Optional description for this run
            
        Returns:
            Dictionary with result_id and summary metrics
        """
        # Load config to get strategy name
        config = load_strategy_config(config_file)
        strategy_name = config.get('name', 'unknown').lower().replace(' ', '_')
        strategy_type = config.get('strategy_type', 'custom')
        
        # Create result directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        year = datetime.now().year
        result_dir = self.base_dir / str(year) / strategy_type / timestamp
        result_dir.mkdir(parents=True, exist_ok=True)
        
        # Create result ID
        result_id = f"{strategy_type}_{timestamp}"
        
        print(f"\n📊 Running backtest: {strategy_name}")
        print(f"   Period: {start_date} to {end_date}")
        print(f"   Result ID: {result_id}")
        
        # Capture stdout for audit log
        import io
        from contextlib import redirect_stdout
        
        audit_log = io.StringIO()
        
        try:
            # Run the backtest with output capture
            with redirect_stdout(audit_log):
                results = run_auditable_backtest(
                    data_file=data_file,
                    config_file=config_file,
                    start_date=start_date,
                    end_date=end_date
                )
            
            # Also print to console
            audit_content = audit_log.getvalue()
            print(audit_content)
            
            # Parse results from audit log
            parsed_results = self._parse_audit_log(audit_content)
            
            # Store all components
            self._store_results(
                result_dir=result_dir,
                config_file=config_file,
                audit_log=audit_content,
                parsed_results=parsed_results,
                start_date=start_date,
                end_date=end_date,
                description=description
            )
            
            # Update index
            index_entry = {
                "result_id": result_id,
                "strategy_name": strategy_name,
                "strategy_type": strategy_type,
                "start_date": start_date,
                "end_date": end_date,
                "timestamp": timestamp,
                "description": description,
                "path": str(result_dir.relative_to(self.base_dir)),
                "metrics": parsed_results.get("metrics", {})
            }
            
            self.index["backtests"].append(index_entry)
            self.save_index()
            
            print(f"\n✅ Backtest completed and saved to: {result_dir}")
            
            return {
                "result_id": result_id,
                "path": str(result_dir),
                "metrics": parsed_results.get("metrics", {}),
                "success": True
            }
            
        except Exception as e:
            print(f"\n❌ Backtest failed: {e}")
            # Clean up failed result directory
            if result_dir.exists():
                shutil.rmtree(result_dir)
            
            return {
                "result_id": None,
                "error": str(e),
                "success": False
            }
    
    def _parse_audit_log(self, audit_log: str) -> Dict[str, Any]:
        """Parse the audit log to extract metrics and trades"""
        results = {
            "metrics": {},
            "trades": [],
            "summary": {}
        }
        
        lines = audit_log.split('\n')
        
        # Extract key metrics
        for line in lines:
            if 'Total Return:' in line:
                try:
                    results["metrics"]["total_return"] = float(line.split(':')[1].strip().replace('%', ''))
                except:
                    pass
            elif 'Sharpe Ratio:' in line:
                try:
                    results["metrics"]["sharpe_ratio"] = float(line.split(':')[1].strip())
                except:
                    pass
            elif 'Max Drawdown:' in line:
                try:
                    results["metrics"]["max_drawdown"] = float(line.split(':')[1].strip().replace('%', ''))
                except:
                    pass
            elif 'Win Rate:' in line:
                try:
                    results["metrics"]["win_rate"] = float(line.split(':')[1].strip().replace('%', ''))
                except:
                    pass
            elif 'Total Trades:' in line or 'trades executed' in line:
                try:
                    # Handle different formats
                    if 'Total Trades:' in line:
                        results["metrics"]["total_trades"] = int(line.split(':')[1].strip())
                    else:
                        # Extract from "X trades executed"
                        import re
                        match = re.search(r'(\d+)\s+trades?\s+executed', line)
                        if match:
                            results["metrics"]["total_trades"] = int(match.group(1))
                except:
                    pass
        
        return results
    
    def _store_results(self, 
                      result_dir: Path,
                      config_file: str,
                      audit_log: str,
                      parsed_results: Dict,
                      start_date: str,
                      end_date: str,
                      description: str) -> None:
        """Store all backtest components"""
        
        # Copy config file
        shutil.copy2(config_file, result_dir / "config.yaml")
        
        # Save audit log
        with open(result_dir / "audit_log.txt", 'w') as f:
            f.write(audit_log)
        
        # Save parsed results as JSON
        results_json = {
            "start_date": start_date,
            "end_date": end_date,
            "description": description,
            "metrics": parsed_results.get("metrics", {}),
            "run_timestamp": datetime.now().isoformat()
        }
        
        with open(result_dir / "results.json", 'w') as f:
            json.dump(results_json, f, indent=2)
        
        # Create placeholder for trades and equity curve (to be enhanced later)
        pd.DataFrame().to_parquet(result_dir / "trades.parquet")
        pd.DataFrame().to_parquet(result_dir / "equity_curve.parquet")
    
    def get_backtest(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific backtest result"""
        for entry in self.index["backtests"]:
            if entry["result_id"] == result_id:
                result_dir = self.base_dir / entry["path"]
                
                # Load all components
                with open(result_dir / "results.json", 'r') as f:
                    results = json.load(f)
                
                with open(result_dir / "audit_log.txt", 'r') as f:
                    audit_log = f.read()
                
                return {
                    "metadata": entry,
                    "results": results,
                    "audit_log": audit_log,
                    "path": str(result_dir)
                }
        
        return None
    
    def list_backtests(self, 
                       strategy_type: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """List backtests with optional filtering"""
        backtests = self.index["backtests"]
        
        if strategy_type:
            backtests = [bt for bt in backtests if bt["strategy_type"] == strategy_type]
        
        if start_date:
            backtests = [bt for bt in backtests if bt["end_date"] >= start_date]
        
        if end_date:
            backtests = [bt for bt in backtests if bt["start_date"] <= end_date]
        
        # Sort by timestamp descending (most recent first)
        backtests.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return backtests
    
    def compare_backtests(self, result_ids: List[str]) -> pd.DataFrame:
        """Compare metrics across multiple backtests"""
        comparison_data = []
        
        for result_id in result_ids:
            backtest = self.get_backtest(result_id)
            if backtest:
                row = {
                    "Result ID": result_id,
                    "Strategy": backtest["metadata"]["strategy_name"],
                    "Period": f"{backtest['metadata']['start_date']} to {backtest['metadata']['end_date']}",
                    **backtest["results"]["metrics"]
                }
                comparison_data.append(row)
        
        return pd.DataFrame(comparison_data)
    
    def create_comparison_chart(self, result_ids: List[str]) -> go.Figure:
        """Create a visual comparison of multiple backtests"""
        df = self.compare_backtests(result_ids)
        
        if df.empty:
            return go.Figure().add_annotation(text="No data available", showarrow=False)
        
        # Create subplots for different metrics
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Total Return (%)", "Sharpe Ratio", "Max Drawdown (%)", "Win Rate (%)"),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Add traces
        metrics = [
            ("total_return", 1, 1),
            ("sharpe_ratio", 1, 2),
            ("max_drawdown", 2, 1),
            ("win_rate", 2, 2)
        ]
        
        for metric, row, col in metrics:
            if metric in df.columns:
                fig.add_trace(
                    go.Bar(
                        x=df["Strategy"],
                        y=df[metric],
                        text=df[metric].round(2),
                        textposition='auto',
                        name=metric.replace('_', ' ').title()
                    ),
                    row=row, col=col
                )
        
        fig.update_layout(
            title="Backtest Comparison",
            showlegend=False,
            height=600
        )
        
        return fig
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics across all backtests"""
        if not self.index["backtests"]:
            return {"total_backtests": 0}
        
        df = pd.DataFrame(self.index["backtests"])
        
        # Calculate summary stats
        summary = {
            "total_backtests": len(df),
            "unique_strategies": df["strategy_type"].nunique(),
            "last_run": df["timestamp"].max() if not df.empty else None,
            "average_return": df["metrics"].apply(lambda x: x.get("total_return", 0)).mean(),
            "best_performing": None,
            "worst_performing": None
        }
        
        # Find best and worst
        if not df.empty and "metrics" in df.columns:
            returns = df["metrics"].apply(lambda x: x.get("total_return", 0))
            if not returns.empty:
                best_idx = returns.idxmax()
                worst_idx = returns.idxmin()
                
                summary["best_performing"] = {
                    "strategy": df.loc[best_idx, "strategy_name"],
                    "return": returns[best_idx],
                    "result_id": df.loc[best_idx, "result_id"]
                }
                
                summary["worst_performing"] = {
                    "strategy": df.loc[worst_idx, "strategy_name"],
                    "return": returns[worst_idx],
                    "result_id": df.loc[worst_idx, "result_id"]
                }
        
        return summary


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backtest Manager CLI")
    parser.add_argument("command", choices=["run", "list", "get", "compare", "summary"])
    parser.add_argument("--config", help="Config file for run command")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--id", help="Result ID for get command")
    parser.add_argument("--ids", help="Comma-separated result IDs for compare command")
    parser.add_argument("--description", help="Description for the backtest run", default="")
    
    args = parser.parse_args()
    
    manager = BacktestManager()
    
    if args.command == "run":
        if not all([args.config, args.start, args.end]):
            print("Error: run command requires --config, --start, and --end")
        else:
            result = manager.run_backtest(
                config_file=args.config,
                start_date=args.start,
                end_date=args.end,
                description=args.description
            )
            print(f"\nResult: {json.dumps(result, indent=2)}")
    
    elif args.command == "list":
        backtests = manager.list_backtests()
        print(f"\nFound {len(backtests)} backtests:")
        for bt in backtests:
            print(f"  - {bt['result_id']}: {bt['strategy_name']} ({bt['start_date']} to {bt['end_date']})")
            if bt.get('metrics', {}).get('total_return'):
                print(f"    Return: {bt['metrics']['total_return']:.2f}%")
    
    elif args.command == "get":
        if not args.id:
            print("Error: get command requires --id")
        else:
            result = manager.get_backtest(args.id)
            if result:
                print(f"\nBacktest {args.id}:")
                print(f"Strategy: {result['metadata']['strategy_name']}")
                print(f"Period: {result['metadata']['start_date']} to {result['metadata']['end_date']}")
                print(f"Metrics: {json.dumps(result['results']['metrics'], indent=2)}")
            else:
                print(f"Backtest {args.id} not found")
    
    elif args.command == "compare":
        if not args.ids:
            print("Error: compare command requires --ids (comma-separated)")
        else:
            ids = args.ids.split(',')
            df = manager.compare_backtests(ids)
            print(f"\nComparison of {len(ids)} backtests:")
            print(df.to_string())
    
    elif args.command == "summary":
        stats = manager.get_summary_stats()
        print(f"\nBacktest Summary Statistics:")
        print(json.dumps(stats, indent=2, default=str))