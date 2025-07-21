#!/usr/bin/env python3
"""
LM Studio AI Assistant for OptionsLab
Simple, focused implementation for local LLM integration
"""

import os
import json
import yaml
import pandas as pd
from typing import Dict, Optional, List
from pathlib import Path
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI library not installed. Please run: pip install openai")
    OpenAI = None

try:
    import pyarrow.parquet as pq
except ImportError:
    pq = None


# Global singleton instance
_assistant_instance = None


class LMStudioAssistant:
    """LM Studio AI Assistant with comprehensive context"""
    
    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        self.base_url = base_url
        self.client = None
        self.model = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize connection to LM Studio"""
        if self._initialized:
            return True
            
        if not OpenAI:
            print("OpenAI library not available")
            return False
            
        try:
            self.client = OpenAI(
                base_url=self.base_url,
                api_key="not-needed"  # LM Studio doesn't require API key
            )
            
            # Test connection and get model
            try:
                models = self.client.models.list()
                if models.data:
                    self.model = models.data[0].id
                    print(f"Connected to LM Studio. Using model: {self.model}")
                else:
                    self.model = "local-model"  # Fallback
                    print("Connected to LM Studio")
            except:
                # Some LM Studio versions don't support model listing
                self.model = "local-model"
                print("Connected to LM Studio")
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Failed to connect to LM Studio at {self.base_url}: {e}")
            print("Make sure LM Studio is running with a model loaded")
            return False
    
    def chat(self, message: str, backtest_data: Optional[Dict] = None) -> str:
        """Chat with LM Studio"""
        if not self._initialized:
            if not self.initialize():
                return "❌ LM Studio not running. Please start LM Studio and load a model."
        
        try:
            # Build comprehensive context
            context = self._build_context(backtest_data)
            
            # System prompt
            system_prompt = """You are an expert options trader, quantitative analyst, and code troubleshooting specialist for OptionsLab.
            
            Your expertise includes:
            1. OPTIONS TRADING: Deep understanding of Greeks, strategies (spreads, straddles, condors), and market mechanics
            2. BACKTESTING ANALYSIS: Evaluating strategy performance, risk metrics (Sharpe, Sortino, max drawdown), and trade patterns
            3. CODE TROUBLESHOOTING: Debugging Python trading systems, understanding ThetaData API, and fixing implementation issues
            4. STRATEGY VALIDATION: Ensuring trades match strategy rules (delta targets, DTE, exit conditions)
            5. PERFORMANCE OPTIMIZATION: Identifying parameter improvements and market regime adaptations
            
            When analyzing:
            - Provide specific numbers and percentages
            - Identify patterns in winning vs losing trades
            - Suggest concrete parameter adjustments
            - Explain any code errors or implementation issues
            - Recommend actionable improvements
            
            You have access to comprehensive trade data and strategy configurations."""
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context + "\n\nUser Query: " + message}
                ],
                temperature=0.5,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error communicating with LM Studio: {str(e)}"
    
    def _build_context(self, backtest_data: Optional[Dict]) -> str:
        """Build comprehensive context from backtest data"""
        if not backtest_data:
            return "No backtest data provided."
        
        context_parts = []
        data_availability = []
        
        # Add metadata overview
        metadata = backtest_data.get('metadata', {})
        if metadata:
            context_parts.append(f"""=== BACKTEST OVERVIEW ===
Name: {metadata.get('memorable_name', 'Unknown')}
Strategy: {metadata.get('strategy', 'Unknown')}
Total Return: {metadata.get('total_return', 0):.2%}
Sharpe Ratio: {metadata.get('sharpe_ratio', 'N/A')}
Max Drawdown: {metadata.get('max_drawdown', 'N/A')}
Total Trades: {metadata.get('total_trades', 0)}
Date Range: {metadata.get('start_date')} to {metadata.get('end_date')}
Initial Capital: ${metadata.get('initial_capital', 10000):,}""")
            data_availability.append("✅ Backtest metadata")
        
        # Try to load CSV for detailed statistics
        json_path = metadata.get('json_path', '')
        if json_path:
            csv_path = json_path.replace('.json', '.csv')
            if Path(csv_path).exists():
                try:
                    trades_df = pd.read_csv(csv_path)
                    if not trades_df.empty:
                        # Calculate statistics
                        winning_trades = trades_df[trades_df['pnl'] > 0]
                        losing_trades = trades_df[trades_df['pnl'] < 0]
                        
                        context_parts.append(f"""\n=== TRADE STATISTICS ===
Total Trades: {len(trades_df)}
Winning Trades: {len(winning_trades)} ({(len(winning_trades) / len(trades_df) * 100):.1f}%)
Losing Trades: {len(losing_trades)} ({(len(losing_trades) / len(trades_df) * 100):.1f}%)

Profit/Loss:
  - Total P&L: ${trades_df['pnl'].sum():.2f}
  - Average Win: ${winning_trades['pnl'].mean():.2f if len(winning_trades) > 0 else 0:.2f}
  - Average Loss: ${losing_trades['pnl'].mean():.2f if len(losing_trades) > 0 else 0:.2f}
  - Max Win: ${trades_df['pnl'].max():.2f}
  - Max Loss: ${trades_df['pnl'].min():.2f}""")
                        
                        # Exit reason analysis
                        if 'exit_reason' in trades_df.columns:
                            exit_counts = trades_df['exit_reason'].value_counts()
                            context_parts.append("\nExit Reasons:")
                            for reason, count in exit_counts.items():
                                context_parts.append(f"  - {reason}: {count} ({count/len(trades_df)*100:.1f}%)")
                        
                        data_availability.append("✅ CSV trade data with full details")
                        
                        # Check what columns we have
                        available_cols = set(trades_df.columns)
                        if 'entry_delta' in available_cols:
                            data_availability.append("✅ Entry Greeks")
                        if 'entry_iv' in available_cols:
                            data_availability.append("✅ Implied volatility data")
                        if 'days_held' in available_cols:
                            data_availability.append("✅ Trade duration data")
                        
                        # Sample trades
                        context_parts.append("\n=== RECENT TRADES (last 5) ===")
                        for i, trade in trades_df.tail(5).iterrows():
                            context_parts.append(f"""\nTrade {i+1}:
  Entry: {trade.get('entry_date')} at ${trade.get('entry_price', 0):.2f}
  Exit: {trade.get('exit_date')} at ${trade.get('exit_price', 0):.2f}
  P&L: ${trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):.1f}%)
  Exit Reason: {trade.get('exit_reason', 'N/A')}""")
                            
                except Exception as e:
                    context_parts.append(f"\nError loading detailed trade data: {e}")
                    data_availability.append("❌ CSV trade data not accessible")
            else:
                data_availability.append("❌ CSV trade data not found")
        
        # Load strategy configuration
        strategy_name = metadata.get('strategy', '')
        if strategy_name:
            yaml_paths = [
                Path(__file__).parent.parent / f"{strategy_name}.yaml",
                Path(__file__).parent.parent / "config" / "strategies" / f"{strategy_name}.yaml",
            ]
            for path in yaml_paths:
                if path.exists():
                    try:
                        with open(path, 'r') as f:
                            strategy_config = yaml.safe_load(f)
                        
                        context_parts.append("\n=== STRATEGY CONFIGURATION ===")
                        if 'entry_rules' in strategy_config:
                            entry = strategy_config['entry_rules']
                            context_parts.append(f"Entry Rules:")
                            context_parts.append(f"  - Delta Target: {entry.get('delta_target', 'N/A')}")
                            context_parts.append(f"  - DTE Range: {entry.get('dte_min', 'N/A')} to {entry.get('dte_max', 'N/A')}")
                        
                        if 'exit_rules' in strategy_config:
                            exit = strategy_config['exit_rules']
                            context_parts.append(f"Exit Rules:")
                            context_parts.append(f"  - Profit Target: {exit.get('profit_target', 'N/A')}")
                            context_parts.append(f"  - Stop Loss: {exit.get('stop_loss', 'N/A')}")
                            
                        data_availability.append("✅ Strategy YAML configuration")
                    except Exception:
                        pass
                    break
            
            if not any(path.exists() for path in yaml_paths):
                data_availability.append("❌ Strategy YAML configuration not found")
        
        # Add data availability summary at the end
        context_parts.append("\n=== DATA AVAILABILITY ===")
        context_parts.extend(data_availability)
        
        # Check for additional data sources
        available_files = self._get_available_data_files()
        
        # Add historical data summary
        parquet_summary = self._get_parquet_summary()
        if parquet_summary:
            context_parts.append(f"\n{parquet_summary}")
            data_availability.append("✅ Historical SPY options data (2020-2025)")
        
        # Add available guides
        if available_files["trade_guides"]:
            context_parts.append(f"\n✅ Documentation available: {', '.join(available_files['trade_guides'])}")
        
        # Add previous backtest results info
        if available_files["backtest_results"]:
            context_parts.append(f"\n✅ Previous backtest results: {len(available_files['backtest_results'])} available for comparison")
        
        # Note missing data that would be helpful
        context_parts.append("\n=== MISSING DATA (would enhance analysis) ===")
        context_parts.append("- Market data (SPY, VIX) during trade periods")
        context_parts.append("- Greeks evolution over time")
        context_parts.append("- Intraday price movements")
        context_parts.append("- Real-time market context")
        
        return "\n".join(context_parts)
    
    def is_configured(self) -> bool:
        """Check if LM Studio is configured and ready"""
        return self._initialized
    
    def _get_available_data_files(self) -> Dict[str, List[str]]:
        """Get list of available data files"""
        available_files = {
            "historical_data": [],
            "backtest_results": [],
            "trade_guides": []
        }
        
        # Check for historical data files
        data_dir = Path(__file__).parent / "data"
        if data_dir.exists():
            for parquet_file in data_dir.glob("*.parquet"):
                available_files["historical_data"].append(parquet_file.name)
        
        # Check for previous backtest results
        results_dir = Path(__file__).parent.parent / "results" / "backtests"
        if results_dir.exists():
            for json_file in results_dir.glob("*.json"):
                available_files["backtest_results"].append(json_file.name)
        
        # Check for documentation
        trade_logs_dir = Path(__file__).parent / "trade_logs"
        if trade_logs_dir.exists():
            for md_file in trade_logs_dir.glob("*.md"):
                available_files["trade_guides"].append(md_file.name)
        
        return available_files
    
    def _read_guide_file(self, filename: str) -> Optional[str]:
        """Read a guide file from trade_logs"""
        try:
            guide_path = Path(__file__).parent / "trade_logs" / filename
            if guide_path.exists() and guide_path.suffix in ['.md', '.txt']:
                with open(guide_path, 'r') as f:
                    return f.read()[:1000]  # First 1000 chars
        except Exception:
            pass
        return None
    
    def _get_parquet_summary(self) -> Optional[str]:
        """Get summary of available parquet data files"""
        if not pq:
            return "PyArrow not installed - cannot read parquet files"
        
        try:
            data_dir = Path(__file__).parent / "data"
            if not data_dir.exists():
                return None
                
            summaries = []
            for parquet_file in sorted(data_dir.glob("SPY_OPTIONS_*.parquet")):
                try:
                    # Read just metadata for efficiency
                    parquet_file_obj = pq.ParquetFile(parquet_file)
                    num_rows = parquet_file_obj.metadata.num_rows
                    year = parquet_file.stem.split('_')[2]
                    summaries.append(f"- {year}: {num_rows:,} option records")
                except Exception:
                    continue
                    
            if summaries:
                return "Historical SPY Options Data Available:\n" + "\n".join(summaries)
        except Exception:
            pass
        return None


def get_lm_studio_assistant() -> LMStudioAssistant:
    """Get or create the singleton LM Studio assistant instance"""
    global _assistant_instance
    
    if _assistant_instance is None:
        _assistant_instance = LMStudioAssistant()
        # Try to initialize immediately
        _assistant_instance.initialize()
    
    return _assistant_instance