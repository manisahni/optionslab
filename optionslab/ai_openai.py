#!/usr/bin/env python3
"""
OpenAI AI Assistant for OptionsLab
Direct OpenAI API integration for options trading analysis
"""

import os
import json
import yaml
import pandas as pd
import numpy as np
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


class OpenAIAssistant:
    """OpenAI Assistant with comprehensive context for options trading"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = None
        self.model = model  # Default to fast and cost-effective model
        self._initialized = False
        self.api_key = None
        self.key_file = Path(__file__).parent / ".openai_key"  # Hidden file for key storage
        
        # Available models for selection
        self.available_models = {
            "gpt-4o-mini": "Fast and cost-effective (recommended)",
            "gpt-4o": "Most capable model, higher cost",
            "gpt-4-turbo": "Balanced performance and cost",
            "gpt-3.5-turbo": "Fastest and most economical"
        }
        
    def initialize(self) -> bool:
        """Initialize connection to OpenAI"""
        if self._initialized:
            return True
            
        if not OpenAI:
            print("OpenAI library not available")
            return False
            
        # Try to get API key from various sources
        self.api_key = self._load_api_key()
        if not self.api_key:
            print("❌ No OpenAI API key found")
            return False
            
        try:
            self.client = OpenAI(api_key=self.api_key)
            
            # Test the connection
            test_response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            print(f"✅ Connected to OpenAI. Using model: {self.model}")
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to OpenAI: {e}")
            return False
    
    def chat(self, message: str, backtest_data: Optional[Dict] = None) -> str:
        """Chat with OpenAI"""
        if not self._initialized:
            if not self.initialize():
                return "❌ OpenAI not configured. Please set OPENAI_API_KEY environment variable."
        
        try:
            # Build comprehensive context
            context = self._build_context(backtest_data)
            
            # System prompt
            system_prompt = """You are an expert options trading analyst specializing in strategy compliance and optimization.

You have access to comprehensive backtest data including:
- Trade-by-trade data with compliance tracking (delta_compliant, dte_compliant, compliance_score)
- Strategy configuration with mandatory delta bands and DTE ranges
- Compliance scorecard with category breakdowns
- Full trade logs with entry/exit prices, dates, reasons, Greeks

**COMPLIANCE-FIRST ANALYSIS APPROACH:**

1. **📊 COMPLIANCE SCORECARD** (Always start with this):
   ```
   Overall Compliance: X%
   ✅ Delta: X% (Target: X ± X)
   ✅ DTE: X% (Target: X, Range: X-X)
   ✅ Entry: X% (Timing, Size)
   ✅ Exit: X% (Rules followed)
   ```

2. **🎯 COMPLIANCE VIOLATIONS**:
   - List specific violations with trade IDs
   - Show impact on performance (compliant vs non-compliant)
   - Example: "Trade #5: Delta 0.45 (target 0.30±0.05) → Loss -$234"

3. **📈 PERFORMANCE-COMPLIANCE CORRELATION**:
   ```
   Compliant Trades: X% win rate, $X avg P&L
   Non-compliant: X% win rate, $X avg P&L
   Impact: X% better performance when compliant
   ```

4. **🔧 ACTIONABLE FIXES**:
   - Specific parameter adjustments
   - Implementation improvements
   - Risk management enhancements

Keep responses concise and focused on compliance metrics. Use the compliance_scorecard data when available."""
            
            print(f"[DEBUG] Sending chat request to OpenAI ({self.model})")
            
            # Prepare messages
            # Handle large context by truncating if necessary
            max_context_length = 30000  # Doubled for comprehensive analysis
            if len(context) > max_context_length:
                context = context[:max_context_length] + "\n\n... [CONTEXT TRUNCATED - TOO LARGE] ..."
                print(f"[DEBUG] Context truncated from {len(context)} to {max_context_length} characters")
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\nUser Query: {message}"}
            ]
            
            print(f"[DEBUG] Message length: system={len(system_prompt)}, user={len(messages[1]['content'])}")
            
            # Make the API call
            start_time = datetime.now()
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.5,
                max_tokens=4000,
                stream=False
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"[DEBUG] OpenAI responded in {elapsed:.1f} seconds")
            
            # Extract response
            if not response or not response.choices:
                return "❌ No response received from OpenAI"
            
            content = response.choices[0].message.content
            if not content:
                return "❌ Empty response from OpenAI"
                
            print(f"[DEBUG] Response length: {len(content)} characters")
            return content
            
        except Exception as e:
            import traceback
            print(f"[ERROR] OpenAI chat error: {str(e)}")
            traceback.print_exc()
            return f"❌ Error communicating with OpenAI: {str(e)}"
    
    def _get_codebase_context(self) -> str:
        """Create a read-only copy of the codebase and provide context"""
        try:
            # Create a temporary code analysis directory
            code_dir = Path(__file__).parent / ".code_analysis"
            code_dir.mkdir(exist_ok=True)
            
            # Copy key Python files for analysis
            source_dir = Path(__file__).parent
            files_to_copy = [
                "app.py",
                "ai_openai.py", 
                "ai_lm_studio.py",
                "auditable_backtest.py",
                "visualization.py"
            ]
            
            code_context = ["=== CODEBASE ANALYSIS ===\n"]
            
            for filename in files_to_copy:
                source_file = source_dir / filename
                if source_file.exists():
                    try:
                        with open(source_file, 'r') as f:
                            content = f.read()
                        
                        # Add file content to context (truncated if too long)
                        if len(content) > 8000:
                            content = content[:8000] + "\n\n... [TRUNCATED - FILE TOO LONG] ..."
                        
                        code_context.append(f"--- {filename} ---\n{content}\n")
                    except Exception as e:
                        code_context.append(f"--- {filename} ---\n[ERROR READING FILE: {e}]\n")
            
            # Also include key configuration files
            config_files = [
                "pyproject.toml",
                "requirements.txt",
                "setup.py"
            ]
            
            for filename in config_files:
                source_file = Path(__file__).parent.parent / filename
                if source_file.exists():
                    try:
                        with open(source_file, 'r') as f:
                            content = f.read()
                        code_context.append(f"--- {filename} ---\n{content}\n")
                    except Exception:
                        pass
            
            return "\n".join(code_context)
            
        except Exception as e:
            return f"Error accessing codebase: {e}"
    
    def _build_context(self, backtest_data: Optional[Dict]) -> str:
        """Build comprehensive context from backtest data using the new CSV format"""
        if not backtest_data:
            return "No backtest data provided."
        
        context_parts = []
        
        # Get CSV path from metadata
        metadata = backtest_data.get('metadata', {})
        csv_path = metadata.get('csv_path', '')
        
        # If we have a CSV path, load everything from there
        if csv_path and Path(csv_path).exists():
            try:
                from .csv_enhanced import load_comprehensive_csv
                csv_data = load_comprehensive_csv(csv_path)
                
                # 1. Strategy Configuration
                if csv_data.get('strategy_config'):
                    context_parts.append("=== STRATEGY CONFIGURATION ===")
                    context_parts.append(yaml.dump(csv_data['strategy_config'], default_flow_style=False))
                
                # 2. Metadata overview
                csv_metadata = csv_data.get('metadata', {})
                context_parts.append(f"""\n=== BACKTEST OVERVIEW ===
Backtest ID: {csv_metadata.get('backtest_id', 'Unknown')}
Name: {csv_metadata.get('memorable_name', 'Unknown')}
Strategy: {csv_metadata.get('strategy', 'Unknown')}
Total Return: {csv_metadata.get('total_return', 0):.2%}
Sharpe Ratio: {csv_metadata.get('sharpe_ratio', 'N/A')}
Max Drawdown: {csv_metadata.get('max_drawdown', 'N/A')}
Total Trades: {csv_metadata.get('total_trades', 0)}
Date Range: {csv_metadata.get('start_date')} to {csv_metadata.get('end_date')}
Initial Capital: ${csv_metadata.get('initial_capital', 10000):,}
Final Value: ${csv_metadata.get('final_value', 0):,}""")
                
                # 3. Load trade data
                trades_df = csv_data.get('trades')
                if trades_df is not None and not trades_df.empty:
                    full_trade_data = self._format_trades_for_context(trades_df)
                    context_parts.append(f"\n{full_trade_data}")
                
                # 4. Add audit log if available
                if csv_data.get('audit_log'):
                    context_parts.append("\n=== AUDIT LOG (Last 50 lines) ===")
                    audit_lines = csv_data['audit_log'].strip().split('\n')[-50:]
                    context_parts.append('\n'.join(audit_lines))
                
                return '\n'.join(context_parts)
                
            except Exception as e:
                print(f"Error loading comprehensive CSV: {e}")
                # Fall back to old method
        
        # If CSV not available, build minimal context
        context_parts.append("=== LIMITED DATA AVAILABLE ===")
        context_parts.append("No comprehensive CSV file found. Limited analysis available.")
        
        # Add basic metadata if available
        if metadata:
            context_parts.append(f"\n=== BACKTEST OVERVIEW ===")
            context_parts.append(f"Name: {metadata.get('memorable_name', 'Unknown')}")
            context_parts.append(f"Total Return: {metadata.get('total_return', 0):.2%}")
            context_parts.append(f"Total Trades: {metadata.get('total_trades', 0)}")
        
        # If trades are directly available in backtest_data
        if 'trades' in backtest_data and backtest_data['trades']:
            trades_df = pd.DataFrame(backtest_data['trades'])
            if not trades_df.empty:
                trade_data = self._format_trades_for_context(trades_df)
                context_parts.append(f"\n{trade_data}")
        
        # 3. Add Compliance Scorecard (Priority)
        # Get compliance scorecard from results or calculate it
        scorecard = None
        
        # First check if scorecard is in metadata (saved from backtest results)
        if 'compliance_scorecard' in metadata:
            scorecard = metadata['compliance_scorecard']
        # Then check if it's in the main backtest_data
        elif 'compliance_scorecard' in backtest_data:
            scorecard = backtest_data['compliance_scorecard']
        # Otherwise calculate it from trades
        elif 'trades' in backtest_data:
            from .backtest_metrics import calculate_compliance_scorecard
            scorecard = calculate_compliance_scorecard(backtest_data['trades'])
        
        if scorecard:
            context_parts.append("\n=== COMPLIANCE SCORECARD ===")
            context_parts.append(f"Overall Compliance: {scorecard.get('overall_score', 0):.1f}%")
            context_parts.append(f"Delta Compliance: {scorecard.get('delta_compliance', 0):.1f}%")
            context_parts.append(f"DTE Compliance: {scorecard.get('dte_compliance', 0):.1f}%")
            context_parts.append(f"Entry Compliance: {scorecard.get('entry_compliance', 0):.1f}%")
            context_parts.append(f"Exit Compliance: {scorecard.get('exit_compliance', 0):.1f}%")
            context_parts.append(f"Fully Compliant Trades: {scorecard.get('compliant_trades', 0)}/{scorecard.get('total_trades', 0)}")
        
        # Compliance analysis is already included in the comprehensive CSV data
        # No need for additional processing here
        
        # 5. Add metadata overview
        if metadata:
            context_parts.append(f"""\n=== BACKTEST OVERVIEW ===
Name: {metadata.get('memorable_name', 'Unknown')}
Strategy: {metadata.get('strategy', 'Unknown')}
Total Return: {metadata.get('total_return', 0):.2%}
Sharpe Ratio: {metadata.get('sharpe_ratio', 'N/A')}
Max Drawdown: {metadata.get('max_drawdown', 'N/A')}
Total Trades: {metadata.get('total_trades', 0)}
Date Range: {metadata.get('start_date')} to {metadata.get('end_date')}
Initial Capital: ${metadata.get('initial_capital', 10000):,}""")
        
        # 6. Add codebase context for code analysis
        code_context = self._get_codebase_context()
        if code_context:
            context_parts.append(f"\n{code_context}")
        
        # 7. Add available data sources info
        context_parts.append("\n=== AVAILABLE DATA SOURCES ===")
        
        # Historical data
        data_dir = Path(__file__).parent / "data"
        if data_dir.exists():
            parquet_files = list(data_dir.glob("*.parquet"))
            if parquet_files:
                context_parts.append(f"Historical SPY options data: {len(parquet_files)} files available")
        
        # Documentation
        docs_dir = Path(__file__).parent.parent / "docs"
        if docs_dir.exists():
            guide_files = list(docs_dir.glob("*.md"))
            if guide_files:
                context_parts.append(f"Documentation: {len(guide_files)} files available")
        
        # Previous backtests
        results_dir = Path(__file__).parent.parent / "results" / "backtests"
        if results_dir.exists():
            backtest_files = list(results_dir.glob("*.json"))
            if backtest_files:
                context_parts.append(f"Previous backtest results: {len(backtest_files)} available")
        
        return "\n".join(context_parts)
    
    def is_configured(self) -> bool:
        """Check if OpenAI is configured and ready"""
        return self._initialized
    
    def get_available_models(self) -> Dict[str, str]:
        """Get list of available models with descriptions"""
        return self.available_models.copy()
    
    def get_current_model(self) -> str:
        """Get the currently selected model"""
        return self.model
    
    def change_model(self, model: str) -> bool:
        """Change the model being used"""
        if model not in self.available_models:
            print(f"❌ Model '{model}' not available. Available models: {list(self.available_models.keys())}")
            return False
        
        self.model = model
        print(f"✅ Model changed to: {model} - {self.available_models[model]}")
        return True
    
    def _load_api_key(self) -> Optional[str]:
        """Load API key from file or environment"""
        # First try the stored key file
        if self.key_file.exists():
            try:
                with open(self.key_file, 'r') as f:
                    key = f.read().strip()
                    if key:
                        return key
            except Exception as e:
                print(f"Error reading key file: {e}")
        
        # Fall back to environment variable
        return os.getenv("OPENAI_API_KEY")
    
    def save_api_key(self, api_key: str) -> bool:
        """Save API key to secure storage"""
        try:
            # Write key to hidden file with restricted permissions
            with open(self.key_file, 'w') as f:
                f.write(api_key.strip())
            
            # Set file permissions to user-only read/write
            os.chmod(self.key_file, 0o600)
            
            # Update current key and reinitialize
            self.api_key = api_key
            self._initialized = False
            return self.initialize()
        except Exception as e:
            print(f"Error saving API key: {e}")
            return False
    
    def delete_api_key(self) -> bool:
        """Delete stored API key"""
        try:
            if self.key_file.exists():
                os.remove(self.key_file)
            self.api_key = None
            self._initialized = False
            return True
        except Exception as e:
            print(f"Error deleting API key: {e}")
            return False
    
    def test_api_key(self, api_key: str) -> bool:
        """Test if an API key is valid"""
        try:
            test_client = OpenAI(api_key=api_key)
            test_response = test_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            print(f"API key test failed: {e}")
            return False
    
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

    def analyze_strategy_adherence(self, backtest_data: Dict) -> str:
        """Analyze strategy adherence with compliance focus"""
        return self.chat(
            "Analyze the strategy adherence. Start with a comprehensive compliance review of the configured parameters. Check if contract selection, entry criteria, and exit criteria are being followed correctly. Provide formal compliance percentages and cite specific reasons for any non-compliance. Then analyze the overall strategy performance.",
            backtest_data
        )
    
    def analyze_performance(self, backtest_data: Dict) -> str:
        """Analyze performance with compliance context"""
        return self.chat(
            "Analyze the trading performance. Start with compliance analysis - check if the strategy is following its configured parameters correctly. Then provide a comprehensive performance analysis including win rate, risk metrics, and identify areas for improvement.",
            backtest_data
        )
    
    def analyze_trade_patterns(self, backtest_data: Dict) -> str:
        """Analyze trade patterns with compliance focus"""
        return self.chat(
            "Analyze the trade patterns. Start by checking compliance with strategy parameters, then identify patterns in entry/exit timing, market conditions, and performance. Look for correlations between compliance and performance.",
            backtest_data
        )
    
    def suggest_optimizations(self, backtest_data: Dict) -> str:
        """Suggest optimizations based on compliance analysis"""
        return self.chat(
            "Suggest strategy optimizations. Start with compliance analysis to identify parameter violations, then suggest specific improvements to the strategy configuration, entry/exit rules, and risk management parameters.",
            backtest_data
        )
    
    def _load_strategy_config(self, strategy_name: str) -> Optional[Dict]:
        """Load strategy configuration as string"""
        if not strategy_name:
            return None
        
        # Handle naming variations (hyphens vs underscores)
        strategy_variations = [strategy_name]
        if '-' in strategy_name:
            strategy_variations.append(strategy_name.replace('-', '_'))
        if '_' in strategy_name:
            strategy_variations.append(strategy_name.replace('_', '-'))
        
        yaml_paths = []
        for variation in strategy_variations:
            yaml_paths.extend([
                Path(__file__).parent.parent / f"{variation}.yaml",
                Path(__file__).parent.parent / "config" / "strategies" / f"{variation}.yaml",
                Path(__file__).parent.parent / "config" / "strategies" / "test" / f"{variation}.yaml",
            ])
        
        for path in yaml_paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        return yaml.safe_load(f)
                except Exception:
                    continue
        
        return None
    
    def _format_trades_for_context(self, trades_df: pd.DataFrame) -> str:
        """Format trades DataFrame for AI context"""
        if trades_df.empty:
            return "No trades found in data."
        
        # Calculate key statistics
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        # Build comprehensive trade data context
        trade_data = f"""=== COMPLETE TRADE DATA FOR ANALYSIS ===

OVERVIEW STATISTICS:
Total Trades: {len(trades_df)}
Winning Trades: {len(winning_trades)} ({len(winning_trades)/len(trades_df)*100:.1f}%)
Losing Trades: {len(losing_trades)} ({len(losing_trades)/len(trades_df)*100:.1f}%)
Average P&L: ${trades_df['pnl'].mean():.2f}
Best Trade: ${trades_df['pnl'].max():.2f}
Worst Trade: ${trades_df['pnl'].min():.2f}
Average Days Held: {trades_df['days_held'].mean():.1f}

DATA COLUMNS AVAILABLE: {list(trades_df.columns)}

COMPLETE TRADE LOG:
"""
        
        # Add ALL trades with full details
        max_trades_for_full_data = 50  # Limit for full data display
        if len(trades_df) > max_trades_for_full_data:
            trade_data += f"\nNOTE: Dataset has {len(trades_df)} trades. Showing first {max_trades_for_full_data} trades with full details, then summary.\n"
            trades_to_show = trades_df.head(max_trades_for_full_data)
            remaining_trades = trades_df.iloc[max_trades_for_full_data:]
        else:
            trades_to_show = trades_df
            remaining_trades = pd.DataFrame()
        
        # Show full details for selected trades
        for idx, trade in trades_to_show.iterrows():
            trade_data += f"\n--- Trade {trade.get('trade_id', idx)} ---\n"
            for col, val in trade.items():
                if pd.notna(val) and col != 'greeks_history':  # Skip large columns
                    trade_data += f"{col}: {val}\n"
        
        # Summary for remaining trades
        if not remaining_trades.empty:
            trade_data += f"\n=== SUMMARY OF REMAINING {len(remaining_trades)} TRADES ===\n"
            trade_data += f"Total P&L: ${remaining_trades['pnl'].sum():.2f}\n"
            trade_data += f"Average P&L: ${remaining_trades['pnl'].mean():.2f}\n"
            trade_data += f"Win Rate: {(remaining_trades['pnl'] > 0).sum() / len(remaining_trades) * 100:.1f}%\n"
        
        return trade_data
    
    def _load_full_trade_data(self, backtest_data: Dict) -> str:
        """Load FULL, unabridged trade data for agentic analysis"""
        metadata = backtest_data.get('metadata', {})
        csv_path = metadata.get('csv_path', '')
        
        if not csv_path:
            return "No trade data available."
        
        if not Path(csv_path).exists():
            return "Trade CSV file not found."
        
        try:
            trades_df = pd.read_csv(csv_path)
            if trades_df.empty:
                return "No trades found in data."
            
            # Calculate key statistics for context
            winning_trades = trades_df[trades_df['pnl'] > 0]
            losing_trades = trades_df[trades_df['pnl'] < 0]
            
            # Build comprehensive trade data context
            trade_data = f"""=== COMPLETE TRADE DATA FOR AGENTIC ANALYSIS ===

OVERVIEW STATISTICS:
Total Trades: {len(trades_df)}
Winning Trades: {len(winning_trades)} ({len(winning_trades)/len(trades_df)*100:.1f}%)
Losing Trades: {len(losing_trades)} ({len(losing_trades)/len(trades_df)*100:.1f}%)
Average P&L: ${trades_df['pnl'].mean():.2f}
Best Trade: ${trades_df['pnl'].max():.2f}
Worst Trade: ${trades_df['pnl'].min():.2f}
Average Days Held: {trades_df['days_held'].mean():.1f}
Total Return: {metadata.get('total_return', 0):.2%}
Sharpe Ratio: {metadata.get('sharpe_ratio', 'N/A')}
Max Drawdown: {metadata.get('max_drawdown', 'N/A')}

DATA COLUMNS AVAILABLE: {list(trades_df.columns)}

COMPLETE TRADE LOG (ALL {len(trades_df)} TRADES):
"""
            
            # Add ALL trades with full details
            # Check if dataset is too large and provide summary if needed
            max_trades_for_full_data = 50  # Limit for full data display
            if len(trades_df) > max_trades_for_full_data:
                trade_data += f"\nNOTE: Dataset has {len(trades_df)} trades. Showing first {max_trades_for_full_data} trades with full details, then summary.\n"
                trades_to_show = trades_df.head(max_trades_for_full_data)
                remaining_trades = trades_df.iloc[max_trades_for_full_data:]
            else:
                trades_to_show = trades_df
                remaining_trades = None
            
            for i, trade in trades_to_show.iterrows():
                trade_data += f"""
TRADE #{i+1}:
"""
                # Add all available columns for this trade
                for col in trades_df.columns:
                    value = trade.get(col, 'N/A')
                    # Format numeric values appropriately
                    if isinstance(value, (int, float)):
                        if 'price' in col.lower() or 'pnl' in col.lower() or 'cost' in col.lower():
                            trade_data += f"  {col}: ${value:.2f}\n"
                        elif 'pct' in col.lower() or 'ratio' in col.lower():
                            trade_data += f"  {col}: {value:.2f}%\n"
                        else:
                            trade_data += f"  {col}: {value}\n"
                    else:
                        trade_data += f"  {col}: {value}\n"
            
            # Add summary of remaining trades if dataset was truncated
            if remaining_trades is not None:
                trade_data += f"""
SUMMARY OF REMAINING {len(remaining_trades)} TRADES:
Average P&L: ${remaining_trades['pnl'].mean():.2f}
Win Rate: {len(remaining_trades[remaining_trades['pnl'] > 0])/len(remaining_trades)*100:.1f}%
Date Range: {remaining_trades['entry_date'].min()} to {remaining_trades['entry_date'].max()}
"""
            
            return trade_data
            
        except Exception as e:
            return f"Error loading trade data: {e}"

    def _analyze_strategy_compliance(self, strategy_config: Dict, trades_df: pd.DataFrame) -> str:
        """Analyze compliance with strategy parameters and generate compliance metrics"""
        if trades_df.empty:
            return "No trade data available for compliance analysis."
        
        compliance_analysis = []
        compliance_analysis.append("=== STRATEGY COMPLIANCE ANALYSIS ===")
        
        # 1. Strategy Configuration Review
        compliance_analysis.append("\n--- STRATEGY PARAMETERS ---")
        compliance_analysis.append(f"Strategy Name: {strategy_config.get('name', 'N/A')}")
        compliance_analysis.append(f"Strategy Type: {strategy_config.get('strategy_type', 'N/A')}")
        compliance_analysis.append(f"Description: {strategy_config.get('description', 'N/A')}")
        
        # Entry Rules Analysis
        entry_rules = strategy_config.get('entry_rules', [])
        compliance_analysis.append("\n--- ENTRY RULES ---")
        
        if isinstance(entry_rules, list):
            for rule in entry_rules:
                compliance_analysis.append(f"Condition: {rule.get('condition', 'N/A')}")
                compliance_analysis.append(f"Action: {rule.get('action', 'N/A')}")
                if 'strike_selection' in rule:
                    compliance_analysis.append(f"Strike Selection: {rule['strike_selection']}")
                if 'expiration_selection' in rule:
                    compliance_analysis.append(f"Expiration Selection: {rule['expiration_selection']}")
        elif isinstance(entry_rules, dict):
            for key, value in entry_rules.items():
                compliance_analysis.append(f"{key}: {value}")
        
        # Exit Rules Analysis
        exit_rules = strategy_config.get('exit_rules', [])
        compliance_analysis.append("\n--- EXIT RULES ---")
        
        if isinstance(exit_rules, list):
            for rule in exit_rules:
                compliance_analysis.append(f"Condition: {rule.get('condition', 'N/A')}")
                compliance_analysis.append(f"Action: {rule.get('action', 'N/A')}")
        elif isinstance(exit_rules, dict):
            for key, value in exit_rules.items():
                compliance_analysis.append(f"{key}: {value}")
        
        # Risk Management
        risk_mgmt = strategy_config.get('risk_management', {})
        compliance_analysis.append("\n--- RISK MANAGEMENT ---")
        compliance_analysis.append(f"Max Position Size: {risk_mgmt.get('max_position_size', 'N/A')}")
        compliance_analysis.append(f"Stop Loss: {risk_mgmt.get('stop_loss', 'N/A')}")
        compliance_analysis.append(f"Take Profit: {risk_mgmt.get('take_profit', 'N/A')}")
        
        # 2. Compliance Metrics Calculation
        compliance_analysis.append("\n--- COMPLIANCE METRICS ---")
        
        # DTE Compliance
        if 'dte_at_entry' in trades_df.columns:
            max_dte = 30  # From strategy config
            dte_compliant = trades_df['dte_at_entry'] <= max_dte
            dte_compliance_pct = (dte_compliant.sum() / len(trades_df)) * 100
            compliance_analysis.append(f"DTE Compliance: {dte_compliance_pct:.1f}% ({dte_compliant.sum()}/{len(trades_df)} trades)")
            
            # Non-compliance reasons
            non_compliant_dte = trades_df[~dte_compliant]
            if len(non_compliant_dte) > 0:
                compliance_analysis.append(f"  Non-compliant DTE trades: {len(non_compliant_dte)}")
                for _, trade in non_compliant_dte.iterrows():
                    compliance_analysis.append(f"    Trade {trade['trade_id']}: DTE {trade['dte_at_entry']} > {max_dte}")
        
        # Delta Compliance (if applicable)
        if 'entry_delta' in trades_df.columns:
            # Check if there are any delta constraints in the strategy
            delta_compliance_pct = 100.0  # Default to 100% if no constraints
            compliance_analysis.append(f"Delta Compliance: {delta_compliance_pct:.1f}% (no explicit constraints)")
        
        # Days Held Compliance
        if 'days_held' in trades_df.columns:
            max_hold_days = strategy_config.get('parameters', {}).get('max_hold_days', 5)
            hold_compliant = trades_df['days_held'] <= max_hold_days
            hold_compliance_pct = (hold_compliant.sum() / len(trades_df)) * 100
            compliance_analysis.append(f"Hold Days Compliance: {hold_compliance_pct:.1f}% ({hold_compliant.sum()}/{len(trades_df)} trades)")
            
            # Non-compliance reasons
            non_compliant_hold = trades_df[~hold_compliant]
            if len(non_compliant_hold) > 0:
                compliance_analysis.append(f"  Non-compliant hold days trades: {len(non_compliant_hold)}")
                for _, trade in non_compliant_hold.iterrows():
                    compliance_analysis.append(f"    Trade {trade['trade_id']}: Held {trade['days_held']} days > {max_hold_days}")
        
        # Position Size Compliance
        if 'cost' in trades_df.columns and 'cash_before' in trades_df.columns:
            max_position_size = risk_mgmt.get('max_position_size', 0.1)
            position_size_pct = trades_df['cost'] / trades_df['cash_before']
            size_compliant = position_size_pct <= max_position_size
            size_compliance_pct = (size_compliant.sum() / len(trades_df)) * 100
            compliance_analysis.append(f"Position Size Compliance: {size_compliance_pct:.1f}% ({size_compliant.sum()}/{len(trades_df)} trades)")
            
            # Non-compliance reasons
            non_compliant_size = trades_df[~size_compliant]
            if len(non_compliant_size) > 0:
                compliance_analysis.append(f"  Non-compliant position size trades: {len(non_compliant_size)}")
                for _, trade in non_compliant_size.iterrows():
                    actual_size = (trade['cost'] / trade['cash_before']) * 100
                    compliance_analysis.append(f"    Trade {trade['trade_id']}: {actual_size:.1f}% > {max_position_size * 100}%")
        
        # Exit Reason Compliance
        if 'exit_reason' in trades_df.columns:
            compliance_analysis.append("\n--- EXIT REASON ANALYSIS ---")
            exit_reasons = trades_df['exit_reason'].value_counts()
            for reason, count in exit_reasons.items():
                percentage = (count / len(trades_df)) * 100
                compliance_analysis.append(f"{reason}: {count} trades ({percentage:.1f}%)")
        
        # 3. Overall Compliance Summary
        compliance_analysis.append("\n--- OVERALL COMPLIANCE SUMMARY ---")
        
        # Calculate overall compliance score
        compliance_scores = []
        if 'dte_at_entry' in trades_df.columns:
            compliance_scores.append(dte_compliance_pct)
        if 'days_held' in trades_df.columns:
            compliance_scores.append(hold_compliance_pct)
        if 'cost' in trades_df.columns and 'cash_before' in trades_df.columns:
            compliance_scores.append(size_compliance_pct)
        
        if compliance_scores:
            overall_compliance = sum(compliance_scores) / len(compliance_scores)
            compliance_analysis.append(f"Overall Strategy Compliance: {overall_compliance:.1f}%")
            
            if overall_compliance >= 90:
                compliance_analysis.append("Status: EXCELLENT - High compliance with strategy parameters")
            elif overall_compliance >= 80:
                compliance_analysis.append("Status: GOOD - Good compliance with minor deviations")
            elif overall_compliance >= 70:
                compliance_analysis.append("Status: FAIR - Moderate compliance with some issues")
            else:
                compliance_analysis.append("Status: POOR - Significant compliance issues detected")
        
        return "\n".join(compliance_analysis)

    def _add_compliance_columns(self, trades_df: pd.DataFrame, strategy_config: Dict) -> pd.DataFrame:
        """Add compliance columns to the trade dataframe"""
        if trades_df.empty:
            return trades_df
        
        # Create a copy to avoid modifying original
        df = trades_df.copy()
        
        # DTE Compliance
        if 'dte_at_entry' in df.columns:
            max_dte = 30  # From strategy config
            df['dte_compliant'] = df['dte_at_entry'] <= max_dte
            df['dte_compliance_reason'] = df['dte_compliant'].map({
                True: 'Compliant',
                False: f'DTE {max_dte}+ days'
            })
        
        # Hold Days Compliance
        if 'days_held' in df.columns:
            max_hold_days = strategy_config.get('parameters', {}).get('max_hold_days', 5)
            df['hold_days_compliant'] = df['days_held'] <= max_hold_days
            df['hold_days_compliance_reason'] = df['hold_days_compliant'].map({
                True: 'Compliant',
                False: f'Held {max_hold_days}+ days'
            })
        
        # Position Size Compliance
        if 'cost' in df.columns and 'cash_before' in df.columns:
            max_position_size = strategy_config.get('risk_management', {}).get('max_position_size', 0.1)
            position_size_pct = df['cost'] / df['cash_before']
            df['position_size_compliant'] = position_size_pct <= max_position_size
            df['position_size_compliance_reason'] = df['position_size_compliant'].map({
                True: 'Compliant',
                False: f'Size > {max_position_size * 100}%'
            })
        
        # Overall Compliance
        compliance_columns = [col for col in df.columns if col.endswith('_compliant')]
        if compliance_columns:
            df['overall_compliant'] = df[compliance_columns].all(axis=1)
            df['compliance_score'] = df[compliance_columns].sum(axis=1) / len(compliance_columns) * 100
        
        return df

    def run_risk_analysis(self, backtest_data: Dict) -> str:
        """Run risk analysis with compliance context"""
        return self.chat(
            "Perform a comprehensive risk analysis. Start with compliance analysis to understand if risk management rules are being followed, then analyze drawdowns, volatility, and suggest risk management improvements.",
            backtest_data
        )

    def run_code_analysis(self, backtest_data: Dict) -> str:
        """Run code analysis with compliance focus"""
        return self.chat(
            "Analyze the code implementation. Start with compliance analysis to understand if the code is correctly implementing the strategy parameters, then review the code for any bugs, inefficiencies, or areas for improvement.",
            backtest_data
        )


def get_openai_assistant(model: str = None) -> OpenAIAssistant:
    """Get or create the singleton OpenAI assistant instance"""
    global _assistant_instance
    
    if _assistant_instance is None:
        _assistant_instance = OpenAIAssistant(model or "gpt-4o-mini")
        # Try to initialize immediately
        _assistant_instance.initialize()
    elif model and model != _assistant_instance.model:
        # Change model if requested and different from current
        _assistant_instance.change_model(model)
    
    return _assistant_instance