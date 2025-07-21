#!/usr/bin/env python3
"""
AI Assistant module for OptionsLab
Provides intelligent analysis of trades and strategies using Google Gemini
"""

import os
import json
import google.generativeai as genai
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image
import io


class AIAssistant:
    """AI Assistant for options trading analysis"""
    
    def __init__(self):
        """Initialize AI Assistant"""
        self.api_key = None
        self.model = None
        self.chat_session = None
        self.context_loaded = False
        self.trade_logs_dir = Path(__file__).parent / "trade_logs"
        self.debug_logs_dir = Path(__file__).parent.parent / "debug_logs"
        
        # Load API key from .env file
        self._load_api_key_from_env()
    
    def _load_api_key_from_env(self):
        """Load API key from .env file"""
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            self.api_key = os.getenv("GEMINI_API_KEY")
            if self.api_key:
                self._initialize_model()
    
    def set_api_key(self, api_key: str) -> bool:
        """Set or update the API key"""
        if not api_key:
            return False
        
        self.api_key = api_key
        return self._initialize_model()
    
    def _initialize_model(self) -> bool:
        """Initialize the Gemini model"""
        try:
            genai.configure(api_key=self.api_key)
            # Try newer model first, fallback to older
            try:
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except:
                try:
                    self.model = genai.GenerativeModel('gemini-1.5-pro')
                except:
                    self.model = genai.GenerativeModel('gemini-pro')
            
            self.chat_session = self.model.start_chat(history=[])
            return True
        except Exception as e:
            print(f"Failed to initialize model: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if AI is properly configured"""
        return self.api_key is not None and self.model is not None
    
    def load_context(self, context_type: str = "all", backtest_path: str = None) -> str:
        """Load context data for the AI"""
        context_parts = []
        
        # Always load code and strategies for comprehensive context
        if context_type in ["all", "code"]:
            # Load relevant source code
            code_context = self._load_source_code()
            if code_context:
                context_parts.append(f"=== SOURCE CODE CONTEXT ===\n{code_context}")
        
        if context_type in ["all", "strategies"]:
            # Load strategy configurations
            strategy_context = self._load_strategies()
            if strategy_context:
                context_parts.append(f"=== STRATEGY CONFIGURATIONS ===\n{strategy_context}")
        
        # Load specific backtest if provided, otherwise load recent logs
        if backtest_path and context_type in ["all", "trades"]:
            # Load specific backtest
            backtest_context = self._load_specific_backtest(backtest_path)
            if backtest_context:
                context_parts.append(f"=== SELECTED BACKTEST DATA ===\n{backtest_context}")
        elif context_type in ["all", "trades"]:
            # Load recent trade logs
            trade_context = self._load_trade_logs()
            if trade_context:
                context_parts.append(f"=== RECENT TRADE LOGS ===\n{trade_context}")
        
        if context_type in ["all", "debug"]:
            # Load debug logs
            debug_context = self._load_debug_logs()
            if debug_context:
                context_parts.append(f"=== DEBUG LOGS ===\n{debug_context}")
        
        full_context = "\n\n".join(context_parts)
        
        if full_context and self.chat_session:
            # Send context to AI
            try:
                response = self.chat_session.send_message(
                    f"You are a professional financial trader and quantitative developer with deep expertise in options trading. "
                    f"I'm providing you with comprehensive data about an options trading system. "
                    f"Analyze this data as an experienced practitioner who can evaluate both the trading performance "
                    f"and the quality of the implementation:\n\n{full_context}"
                )
                self.context_loaded = True
                
                # Provide a summary of what was loaded
                summary_parts = []
                if context_type in ["all", "trades"]:
                    summary_parts.append("✅ Trade logs loaded")
                if context_type in ["all", "strategies"]:
                    summary_parts.append("✅ Strategy configurations loaded")
                if context_type in ["all", "code"]:
                    summary_parts.append("✅ Source code context loaded")
                
                summary = " | ".join(summary_parts)
                return f"**Context loaded successfully!**\n\n{summary}\n\nI've analyzed the {context_type} data and I'm ready to help you with:\n- Trade performance analysis\n- Strategy optimization suggestions\n- Risk management recommendations\n- Pattern identification in your trading results\n\nWhat would you like to explore?"
            except Exception as e:
                self.context_loaded = False
                return f"Error loading context: {str(e)}"
        
        return "No context available or AI not configured"
    
    def _load_trade_logs(self, limit: int = 5) -> str:
        """Load recent trade logs"""
        if not self.trade_logs_dir.exists():
            return ""
        
        # Load index
        index_path = self.trade_logs_dir / "index.json"
        if not index_path.exists():
            return ""
        
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        logs = index.get('logs', [])
        # Sort by date and get most recent
        logs = sorted(logs, key=lambda x: x.get('backtest_date', ''), reverse=True)[:limit]
        
        summaries = []
        for log in logs:
            summary = f"""
Strategy: {log.get('strategy')}
Date Range: {log.get('start_date')} to {log.get('end_date')}
Total Trades: {log.get('total_trades')}
Final Return: {log.get('total_return', 0):.2%}
Win Rate: {log.get('win_rate', 0):.1%}
"""
            summaries.append(summary)
        
        return "\n---\n".join(summaries)
    
    def _load_strategies(self) -> str:
        """Load strategy configurations"""
        strategies_dir = Path(__file__).parent.parent / "config" / "strategies"
        if not strategies_dir.exists():
            return ""
        
        summaries = []
        for yaml_file in strategies_dir.glob("*.yaml"):
            try:
                import yaml
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                summary = f"""
Strategy: {config.get('name', yaml_file.stem)}
Type: {config.get('type')}
Description: {config.get('description', 'N/A')}
Parameters: {json.dumps(config.get('parameters', {}), indent=2)}
"""
                summaries.append(summary)
            except:
                continue
        
        return "\n---\n".join(summaries)
    
    def _load_source_code(self) -> str:
        """Load comprehensive source code context"""
        # Load key files with important functions
        key_files = [
            ("auditable_backtest.py", ["find_suitable_options_advanced", "run_auditable_backtest", "create_implementation_metrics"]),
            ("auditable_gradio_app.py", ["save_trade_log", "analyze_current_backtest"]),
            ("ai_assistant.py", ["analyze_trades", "load_context"])
        ]
        
        code_summaries = []
        for filename, important_functions in key_files:
            file_path = Path(__file__).parent / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Extract important functions with their full implementation
                file_summary = f"=== File: {filename} ===\nPath: {file_path}\n\n"
                
                for func_name in important_functions:
                    # Find function definition
                    import re
                    pattern = rf'def {func_name}\(.*?\):\s*\n(.*?)(?=\ndef|\nclass|\Z)'
                    match = re.search(pattern, content, re.DOTALL)
                    if match:
                        # Get first 50 lines of the function
                        func_lines = match.group(0).split('\n')[:50]
                        file_summary += f"Function: {func_name}\n"
                        file_summary += '\n'.join(func_lines[:20]) + "\n...\n\n"
                
                code_summaries.append(file_summary)
        
        return "\n---\n".join(code_summaries)
    
    def _load_debug_logs(self, limit: int = 1) -> str:
        """Load recent debug logs"""
        if not self.debug_logs_dir.exists():
            return ""
        
        # Get most recent debug log
        debug_files = sorted(self.debug_logs_dir.glob("backtest_debug_*.log"), reverse=True)
        if not debug_files:
            return ""
        
        summaries = []
        for debug_file in debug_files[:limit]:
            try:
                with open(debug_file, 'r') as f:
                    lines = f.readlines()
                
                # Extract key sections
                summary = f"Debug Log: {debug_file.name}\n"
                summary += f"Size: {len(lines)} lines\n"
                
                # Get first 100 lines and last 100 lines
                if len(lines) > 200:
                    summary += "First 50 lines:\n" + ''.join(lines[:50])
                    summary += "\n... [middle section omitted] ...\n\n"
                    summary += "Last 50 lines:\n" + ''.join(lines[-50:])
                else:
                    summary += ''.join(lines)
                
                summaries.append(summary)
            except:
                continue
        
        return "\n---\n".join(summaries)
    
    def _load_specific_backtest(self, backtest_path: str) -> str:
        """Load a specific backtest's complete data"""
        path = Path(backtest_path)
        if not path.exists():
            return f"Backtest file not found: {backtest_path}"
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            trades = data.get('trades', [])
            
            summary = f"""
Backtest: {metadata.get('memorable_name', 'Unknown')}
Display Name: {metadata.get('display_name', 'N/A')}
Strategy: {metadata.get('strategy', 'Unknown')}
Date Range: {metadata.get('start_date')} to {metadata.get('end_date')}
Initial Capital: ${metadata.get('initial_capital', 0):,.2f}
Final Value: ${metadata.get('final_value', 0):,.2f}
Total Return: {metadata.get('total_return', 0):.2%}
Win Rate: {metadata.get('win_rate', 0):.1%}
Total Trades: {metadata.get('total_trades', 0)}

Implementation Metrics:
{json.dumps(metadata.get('implementation_metrics', {}), indent=2)}

Strategy Configuration:
{json.dumps(metadata.get('strategy_config', {}), indent=2)}

Trade Details ({len(trades)} trades):
"""
            # Add detailed trade information
            for i, trade in enumerate(trades[:20]):  # Show first 20 trades
                summary += f"\n==== Trade {i+1} ====\n"
                summary += f"Entry Date: {trade.get('entry_date')} | Exit Date: {trade.get('exit_date', 'Open')}\n"
                summary += f"Option Type: {trade.get('option_type')} | Strike: ${trade.get('strike', 0):.2f}\n"
                summary += f"Entry Price: ${trade.get('option_price', 0):.2f} | Exit Price: ${trade.get('exit_price', 0):.2f}\n"
                summary += f"Entry Delta: {trade.get('entry_delta', 'N/A')} | DTE: {trade.get('dte_at_entry', 'N/A')}\n"
                summary += f"P&L: ${trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):.1f}%)\n"
                summary += f"Exit Reason: {trade.get('exit_reason', 'N/A')}\n"
                
                # Include selection process if available
                if trade.get('selection_process'):
                    summary += f"Selection Process: {json.dumps(trade['selection_process'], indent=2)}\n"
            
            if len(trades) > 20:
                summary += f"\n... and {len(trades) - 20} more trades\n"
            
            # Include file paths for reference
            summary += f"\n\nFile Locations:\n"
            summary += f"JSON: {backtest_path}\n"
            csv_path = path.with_suffix('.csv')
            if csv_path.exists():
                summary += f"CSV: {csv_path}\n"
            
            return summary
        except Exception as e:
            return f"Error loading backtest: {str(e)}"
    
    def analyze_trades(self, trades: List[Dict], strategy_config: Dict = None, implementation_metrics: Dict = None, 
                       backtest_info: Dict = None, strategy_yaml: str = None) -> str:
        """Analyze a list of trades with two-phase approach"""
        if not self.is_configured():
            return "AI not configured. Please set API key."
        
        if not self.chat_session:
            return "Chat session not initialized. Please reload the AI assistant."
        
        if not trades:
            return "No trades to analyze."
        
        # Prepare trade summary
        df = pd.DataFrame(trades)
        completed = df[df['exit_date'].notna()]
        
        if completed.empty:
            return "No completed trades to analyze."
        
        # Extract strategy details if available
        strategy_details = ""
        if strategy_config:
            entry_rules = strategy_config.get('entry_rules', {})
            exit_rules = strategy_config.get('exit_rules', [])
            strategy_details = f"""
Strategy Configuration:
- Name: {strategy_config.get('name', 'Unknown')}
- Entry Delta Target: {entry_rules.get('delta_target', 'N/A')}
- Entry DTE: {entry_rules.get('dte', 'N/A')}
- Exit Rules: {[rule.get('condition', '') for rule in exit_rules]}
"""
        
        # Add implementation metrics if available
        implementation_summary = ""
        if implementation_metrics:
            implementation_summary = f"""
Implementation Metrics Summary:
- Status: {implementation_metrics.get('status', 'UNKNOWN')}
- Delta Analysis: Mean={implementation_metrics.get('delta_analysis', {}).get('mean', 0):.3f}, Target={implementation_metrics.get('target_delta', 0.40):.2f}
- DTE Analysis: Mean={implementation_metrics.get('dte_analysis', {}).get('mean', 0):.1f}, Target={implementation_metrics.get('target_dte', 30)}
- Issues: {implementation_metrics.get('issues', [])}
- Warnings: {implementation_metrics.get('warnings', [])}

Selection Process Summary:
{implementation_metrics.get('selection_process_summary', {})}
"""
        
        # Add backtest identification
        backtest_identification = ""
        if backtest_info:
            backtest_identification = f"""
=== BACKTEST IDENTIFICATION ===
Analyzing: {backtest_info.get('memorable_name', 'Unknown Backtest')}
Display Name: {backtest_info.get('display_name', 'N/A')}
Strategy: {backtest_info.get('strategy_name', 'Unknown')}
Date Range: {backtest_info.get('start_date', 'N/A')} to {backtest_info.get('end_date', 'N/A')}
Trade Count: {len(trades)} trades executed

Log Files:
- CSV: {backtest_info.get('csv_path', 'Not available')}
- JSON: {backtest_info.get('json_path', 'Not available')}

=== DATA VERIFICATION ===
✓ Trade details received: {len(trades)} trades with {'selection process data' if any(t.get('selection_process') for t in trades) else 'basic data only'}
✓ Implementation metrics: {'Available - Status: ' + implementation_metrics.get('status', 'Unknown') if implementation_metrics else 'Not available'}
✓ Strategy config: {'Loaded - ' + str(strategy_config.get('name', 'Unknown')) if strategy_config else 'Not loaded'}
"""
        
        # Calculate performance emoji
        total_return = backtest_info.get('total_return', 0) if backtest_info else 0
        if total_return > 0.1:
            perf_emoji = "🚀"
        elif total_return > 0:
            perf_emoji = "📈"
        elif total_return > -0.1:
            perf_emoji = "📉"
        else:
            perf_emoji = "💥"
            
        prompt = f"""
You are an expert options trading strategy analyst with full access to the backtesting system's source code, logs, and configuration. 

PROVIDE YOUR ANALYSIS IN THIS EXACT STRUCTURE:

═══════════════════════════════════════════════════
🎯 BACKTEST ANALYSIS: {backtest_info.get('memorable_name', 'Unknown') if backtest_info else 'Unknown'}
═══════════════════════════════════════════════════

📅 Date Range: {backtest_info.get('start_date', 'N/A') if backtest_info else 'N/A'} to {backtest_info.get('end_date', 'N/A') if backtest_info else 'N/A'}
🏆 Performance: {total_return:.2%} ({perf_emoji})
📁 Files: {backtest_info.get('json_path', 'N/A') if backtest_info else 'N/A'}

═══════════════════════════════════════════════════
📋 STRATEGY CONFIGURATION ({strategy_config.get('name', 'Unknown').lower().replace(' ', '_')}.yaml)
═══════════════════════════════════════════════════
```yaml
{strategy_yaml if strategy_yaml else 'Configuration not available'}
```

═══════════════════════════════════════════════════
📊 PERFORMANCE METRICS
═══════════════════════════════════════════════════

📊 PERFORMANCE RESULTS:
• Total Trades Executed: {len(completed)}
• Win Rate: {(completed['pnl'] > 0).mean():.1%} ({len(completed[completed['pnl'] > 0])} wins / {len(completed)} trades)
• Total P&L: ${completed['pnl'].sum():.2f}
• Average P&L per Trade: ${completed['pnl'].mean():.2f}
• Best Trade: ${completed['pnl'].max():.2f}
• Worst Trade: ${completed['pnl'].min():.2f}
• Average Win: ${completed[completed['pnl'] > 0]['pnl'].mean():.2f if len(completed[completed['pnl'] > 0]) > 0 else 0:.2f}
• Average Loss: ${completed[completed['pnl'] <= 0]['pnl'].mean():.2f if len(completed[completed['pnl'] <= 0]) > 0 else 0:.2f}

📈 EXIT REASONS BREAKDOWN:
{completed['exit_reason'].value_counts().to_string()}

═══════════════════════════════════════════════════
✅ DATA AVAILABILITY
═══════════════════════════════════════════════════
✓ {len(trades)} complete trade records with Greeks
✓ Selection process data: {'Available' if any(t.get('selection_process') for t in trades) else 'Not available'}
✓ Entry/exit prices and reasons for all trades
✓ Source code: auditable_backtest.py ({sum(1 for line in open(Path(__file__).parent / 'auditable_backtest.py', 'r')) if (Path(__file__).parent / 'auditable_backtest.py').exists() else 'N/A'} lines)
✓ Implementation metrics: {implementation_metrics.get('status', 'Not available') if implementation_metrics else 'Not available'}

═══════════════════════════════════════════════════
🔧 TECHNICAL ROBUSTNESS ASSESSMENT
═══════════════════════════════════════════════════

Analyze the implementation and identify any critical issues:

Based on implementation metrics, identify any critical issues:

⚠️ CRITICAL ISSUES FOUND:
[List specific implementation problems, e.g.:]
- Delta targeting failure (if applicable)
- DTE selection errors
- Exit rule misconfiguration
- Data quality issues

OR if no issues:
✅ No critical implementation issues found

═══════════════════════════════════════════════════
💡 IMMEDIATE RECOMMENDATIONS
═══════════════════════════════════════════════════

1. **Implementation Fixes** (if needed):
   - [Specific code fixes with line numbers]
   
2. **Strategy Improvements**:
   - [Based on performance data]
   
3. **Risk Management**:
   - [Specific suggestions]

THEN proceed with detailed analysis as requested:

✅ Implementation Status: [Clearly state PASS or FAIL]

📌 Option Selection Accuracy:
   • Delta Targeting:
     - Target: {entry_rules.get('delta_target', '0.40')} ± {implementation_metrics.get('delta_tolerance', 0.05)}
     - Actual Average: [Calculate from data]
     - Accuracy: [X%] of trades within tolerance
     - Issues: [Any systematic bias?]
   
   • DTE Selection:
     - Target: {entry_rules.get('dte', '30')} days (range: {implementation_metrics.get('dte_range', [25, 35])})
     - Actual Average: [Calculate from data]
     - Accuracy: [X%] of trades within range
     - Issues: [Any systematic bias?]

📌 Trade Execution Mechanics:
   • Entry Frequency: Are trades being entered as configured?
   • Position Sizing: Is the position size consistent with configuration?
   • Exit Rules Compliance:
     - Profit Target ({[rule.get('target_percent') for rule in strategy_config.get('exit_rules', []) if rule.get('condition') == 'profit_target']}%): [Working correctly?]
     - Stop Loss ({[rule.get('stop_percent') for rule in strategy_config.get('exit_rules', []) if rule.get('condition') == 'stop_loss']}%): [Working correctly?]
     - Time Stop ({[rule.get('max_days') for rule in strategy_config.get('exit_rules', []) if rule.get('condition') == 'time_stop']} days): [Working correctly?]

📌 Selection Process Efficiency:
   • Average options available: {implementation_metrics.get('selection_process_summary', {}).get('avg_total_options', 'N/A')}
   • After all filters: {implementation_metrics.get('selection_process_summary', {}).get('avg_after_liquidity', 'N/A')}
   • Criteria relaxation rate: {implementation_metrics.get('selection_process_summary', {}).get('trades_with_relaxed_criteria', 0)} trades

📌 Data Quality Check:
   • Greeks data: [Available/Missing for X% of trades]
   • Price spreads: [Reasonable/Suspicious]
   • Any anomalies: [List any data issues]

⚠️ Implementation Issues Found:
{chr(10).join(f'   • {issue}' for issue in implementation_metrics.get('issues', [])) if implementation_metrics.get('issues') else '   • None - Implementation appears correct'}

🔧 Required Implementation Fixes:
[If issues found, provide specific fixes needed in the code/configuration]

═══════════════════════════════════════════════════
💡 FINANCIAL STRATEGY OPTIMIZATION
═══════════════════════════════════════════════════

{"⚠️ IMPORTANT: Implementation issues must be fixed before strategy optimization is meaningful." if implementation_metrics.get('status') == 'FAIL' else "Implementation verified ✅ - Proceeding with strategy analysis:"}

📈 Performance Analysis:
   • Win Rate: {(completed['pnl'] > 0).mean():.1%} ({len(completed[completed['pnl'] > 0])} wins / {len(completed)} trades)
   • Average Win: ${completed[completed['pnl'] > 0]['pnl'].mean():.2f} if any
   • Average Loss: ${completed[completed['pnl'] <= 0]['pnl'].mean():.2f} if any
   • Risk/Reward Ratio: [Calculate ratio]
   • Maximum Drawdown: [Calculate if possible]

🎯 Trade Pattern Analysis:
   • Winning trades characteristics:
     - Entry delta range: [Analyze winning trade deltas]
     - Hold duration: [Average days for winners]
     - Exit reasons: [What caused profitable exits?]
   
   • Losing trades characteristics:
     - Entry delta range: [Analyze losing trade deltas]
     - Hold duration: [Average days for losers]
     - Exit reasons: [What caused losses?]

📊 Strategy Optimization Recommendations:

1. **Delta Selection Optimization**
   - Current: {entry_rules.get('delta_target', '0.40')}
   - Suggested: [Based on win/loss analysis]
   - Rationale: [Explain why]

2. **Exit Rule Refinements**
   - Profit Target: [Current vs suggested]
   - Stop Loss: [Current vs suggested]
   - Time-based exits: [Analysis and suggestions]

3. **Entry Timing Improvements**
   - Add volatility filter: [If applicable]
   - Market condition awareness: [Suggestions]
   - Entry frequency optimization: [Analysis]

4. **Risk Management Enhancements**
   - Position sizing: [Current approach and improvements]
   - Portfolio heat: [Max concurrent positions analysis]
   - Capital preservation: [Suggestions]

═══════════════════════════════════════════════════

💬 **Ready for Further Discussion**

Based on this analysis, I can help you explore:

**Technical Topics:**
- Specific code implementation details
- Bug fixes or calculation corrections
- How specific functions work (e.g., option selection algorithm)
- Debug log analysis for specific trades
- Custom modifications to the backtesting logic

**Strategy Topics:**
- Detailed parameter optimization
- Alternative strategy approaches
- Market regime adaptation
- Risk management frameworks
- Performance improvement ideas

What aspect would you like to dive deeper into?
"""
        
        try:
            response = self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            return f"Error analyzing trades: {str(e)}"
    
    def chat(self, message: str, current_data: Optional[Dict] = None) -> str:
        """Chat with the AI assistant"""
        if not self.is_configured():
            return "AI not configured. Please set API key."
        
        if not self.chat_session:
            return "Chat session not initialized. Please reload the AI assistant."
        
        # Build context with file paths instead of structured data
        full_message = message
        if current_data:
            metadata = current_data.get('metadata', {})
            memorable_name = metadata.get('memorable_name', 'Unknown')
            strategy_name = metadata.get('strategy', 'Unknown')
            backtest_date = metadata.get('backtest_date', '')[:10]  # Just the date part
            
            # Find the CSV file path
            csv_filename = f"trades_{strategy_name}_{metadata.get('start_date')}_to_{metadata.get('end_date')}_{backtest_date.replace('-', '')}_*.csv"
            json_path = metadata.get('json_path', '')
            csv_path = json_path.replace('.json', '.csv') if json_path else None
            
            # Get plot path from metadata or construct it
            plot_path = metadata.get('plot_path')
            if not plot_path and json_path:
                # Try to find plot file for older backtests
                plot_path = json_path.replace('.json', '_dashboard.png')
                if not Path(plot_path).exists():
                    plot_path = None
            
            # Find strategy YAML path
            yaml_paths = [
                Path(__file__).parent.parent / f"{strategy_name}.yaml",
                Path(__file__).parent.parent / "config" / "strategies" / f"{strategy_name}.yaml",
                Path(__file__).parent.parent / "simple_test_strategy.yaml"  # fallback
            ]
            yaml_path = None
            for path in yaml_paths:
                if path.exists():
                    yaml_path = str(path)
                    break
            
            context = f"""
You are a professional financial trader and experienced software engineer specializing in options trading strategies. You have deep expertise in quantitative analysis, risk management, and algorithmic trading systems.

CURRENT BACKTEST: {memorable_name}
- Strategy: {strategy_name}
- Performance: {metadata.get('total_return', 0):.2%}
- Total Trades: {metadata.get('total_trades', 0)}

RESOURCES YOU HAVE ACCESS TO:
1. Trade Data CSV: {csv_path or 'Not found'}
   - Complete trade execution logs with entry/exit timestamps
   - All option Greeks (delta, gamma, theta, vega, rho) at entry and exit
   - Underlying price movements and P&L calculations
   - Exit reasons and trade selection details

2. Strategy Configuration: {yaml_path or 'Not found'}
   - Strategy rules and parameters
   - Entry/exit conditions
   - Risk management settings
   - Option selection criteria

3. Performance Dashboard Plot: {plot_path or 'Not found'}
   - Visual representation of P&L curve
   - Trade markers and performance metrics
   - Drawdown visualization
   - Summary statistics
   {f"(I can see this plot image and analyze it visually)" if plot_path and Path(plot_path).exists() else "(Plot not available for this backtest)"}

4. Backtesting Engine Source Code: {Path(__file__).parent}
   - Implementation of the trading logic
   - Data processing algorithms
   - Risk management systems
   - Performance calculation methods

As an experienced trader and coder, you can:
- Analyze trading performance and identify patterns
- Verify implementation quality against strategy specifications
- Suggest parameter optimizations based on market conditions
- Provide insights on risk-adjusted returns
- Debug strategy logic and execution issues
- Recommend improvements to the trading system
- Analyze visual performance charts when available

User Query: {message}"""
            
            full_message = context
        
        try:
            # Check if we have a plot image to include
            if current_data and plot_path and Path(plot_path).exists():
                try:
                    # Load the plot image using PIL
                    img = Image.open(plot_path)
                    
                    # Send multimodal content (text + image)
                    response = self.chat_session.send_message([full_message, img])
                    return response.text
                except Exception as img_error:
                    print(f"Warning: Could not load plot image: {img_error}")
                    # Fall back to text-only
            
            # Text-only message (no plot or error loading plot)
            response = self.chat_session.send_message(full_message)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_suggestions(self, strategy_type: str, market_conditions: str) -> str:
        """Get strategy suggestions based on market conditions"""
        if not self.is_configured():
            return "AI not configured. Please set API key."
        
        prompt = f"""
Given the following:
- Strategy Type: {strategy_type}
- Market Conditions: {market_conditions}
- System: Options trading backtesting system

Please provide:
1. Optimal parameter suggestions for this strategy
2. Risk management rules to implement
3. Market conditions where this strategy works best
4. Common pitfalls to avoid
"""
        
        try:
            response = self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            return f"Error getting suggestions: {str(e)}"
    
    def calculate_implementation_metrics(self, backtest_data: Dict, strategy_yaml: Dict) -> Dict:
        """Calculate implementation metrics from trades"""
        trades = backtest_data.get('trades', [])
        completed_trades = [t for t in trades if t.get('exit_date')]
        
        if not completed_trades:
            return {'status': 'NO_TRADES'}
        
        # Get target values from YAML
        entry_rules = strategy_yaml.get('entry_rules', {})
        option_selection = strategy_yaml.get('option_selection', {})
        
        target_delta = option_selection.get('delta_criteria', {}).get('target', 
                                          entry_rules.get('delta_target', 0.40))
        delta_tolerance = option_selection.get('delta_criteria', {}).get('tolerance', 0.05)
        
        target_dte = option_selection.get('dte_criteria', {}).get('target',
                                        entry_rules.get('dte', 30))
        dte_min = option_selection.get('dte_criteria', {}).get('minimum', 25)
        dte_max = option_selection.get('dte_criteria', {}).get('maximum', 35)
        
        # Analyze deltas
        deltas = [abs(t.get('entry_delta', 0)) for t in completed_trades if t.get('entry_delta')]
        delta_in_range = sum(1 for d in deltas if abs(d - target_delta) <= delta_tolerance)
        
        # Analyze DTEs
        dtes = [t.get('dte_at_entry', 0) for t in completed_trades if t.get('dte_at_entry')]
        dte_in_range = sum(1 for d in dtes if dte_min <= d <= dte_max)
        
        metrics = {
            'target_delta': target_delta,
            'delta_tolerance': delta_tolerance,
            'actual_deltas': deltas,
            'delta_compliance_rate': delta_in_range / len(deltas) if deltas else 0,
            'target_dte': target_dte,
            'dte_range': [dte_min, dte_max],
            'actual_dtes': dtes,
            'dte_compliance_rate': dte_in_range / len(dtes) if dtes else 0,
            'status': 'CALCULATED'
        }
        
        return metrics
    
    def analyze_implementation_adequacy(self, backtest_data: Dict) -> str:
        """Analyze how well a backtest implements its strategy specification"""
        if not self.is_configured():
            return "AI not configured. Please set API key."
        
        metadata = backtest_data.get('metadata', {})
        trades = backtest_data.get('trades', [])
        
        # Find file paths
        memorable_name = metadata.get('memorable_name', 'Unknown')
        strategy_name = metadata.get('strategy', 'Unknown')
        json_path = metadata.get('json_path', '')
        csv_path = json_path.replace('.json', '.csv') if json_path else None
        
        # Find strategy YAML path
        yaml_paths = [
            Path(__file__).parent.parent / f"{strategy_name}.yaml",
            Path(__file__).parent.parent / "config" / "strategies" / f"{strategy_name}.yaml",
            Path(__file__).parent.parent / "simple_test_strategy.yaml"
        ]
        yaml_path = None
        for path in yaml_paths:
            if path.exists():
                yaml_path = str(path)
                break
        
        prompt = f"""
You are an expert financial programmer and options trader analyzing a backtest implementation.
Your task is to assess how well the code implements the strategy specified in the YAML file.

BACKTEST: {memorable_name}
- Strategy: {strategy_name}
- Performance: {metadata.get('total_return', 0):.2%}
- Total Trades: {metadata.get('total_trades', 0)}
- Date Range: {metadata.get('start_date')} to {metadata.get('end_date')}

FILE LOCATIONS:
- Trade Data CSV: {csv_path}
  (Contains complete trade details with all entry/exit data, greeks, and P&L)
- Strategy YAML: {yaml_path}
  (Contains the strategy specification that should have been implemented)
- Source Code: {Path(__file__).parent}

Please analyze these files to provide a comprehensive IMPLEMENTATION ADEQUACY ASSESSMENT:
"""
        # Continue with adequacy assessment format

        prompt += f"""

=== STRATEGY IMPLEMENTATION ADEQUACY REPORT ===

📋 YAML SPECIFICATION vs ACTUAL IMPLEMENTATION:

1. DELTA TARGETING ADEQUACY: [Rate and explain]
   - Compare YAML delta target with actual entry deltas in CSV
   - Calculate compliance rate

2. DTE TARGETING ADEQUACY: [Rate and explain]
   - Compare YAML DTE target with actual DTEs in CSV
   - Calculate compliance rate

3. EXIT RULES ADEQUACY: [Rate and explain]
   - Check if exit_reason in CSV matches YAML exit rules
   - Verify stop losses and profit targets

4. POSITION SIZING ADEQUACY: [Rate and explain]
   - Check if position sizes follow YAML specifications

5. OPTION SELECTION ADEQUACY: [Rate and explain]
   - Verify liquidity filters and other selection criteria

=== IMPLEMENTATION SCORE: [X]/100 ===

CRITICAL ISSUES:
[List any major deviations from the YAML specification]

RECOMMENDATIONS:
[Specific fixes to improve implementation]

VERDICT: [VALID/INVALID] - Explain if this backtest truly tests the intended strategy.
"""
        
        try:
            response = self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            return f"Error generating implementation analysis: {str(e)}"