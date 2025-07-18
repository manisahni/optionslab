#!/usr/bin/env python3
"""
Pure Gradio OptionsLab App
Eliminates FastAPI backend for simplicity and reliability
"""

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yaml
import json
import os
from pathlib import Path
import subprocess
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
STRATEGIES_DIR = "config/strategies"
TEMPLATES_DIR = "strategy_templates"

def get_available_strategies():
    """Get all available strategies from both directories"""
    strategies = []
    
    # Built-in strategies
    built_in = ["long_call", "long_put", "covered_call", "cash_secured_put"]
    for strategy in built_in:
        strategies.append(f"Built-in: {strategy}")
    
    # YAML strategies from config/strategies
    if os.path.exists(STRATEGIES_DIR):
        for file in os.listdir(STRATEGIES_DIR):
            if file.endswith('.yaml'):
                try:
                    with open(os.path.join(STRATEGIES_DIR, file), 'r') as f:
                        config = yaml.safe_load(f)
                        name = config.get('strategy_name', file.replace('.yaml', ''))
                        category = config.get('category', 'Custom')
                        strategies.append(f"[AI] {name} ({category})")
                except Exception as e:
                    logger.warning(f"Error loading {file}: {e}")
    
    # YAML strategies from strategy_templates
    if os.path.exists(TEMPLATES_DIR):
        for file in os.listdir(TEMPLATES_DIR):
            if file.endswith('.yaml'):
                try:
                    with open(os.path.join(TEMPLATES_DIR, file), 'r') as f:
                        config = yaml.safe_load(f)
                        name = config.get('strategy_name', file.replace('.yaml', ''))
                        category = config.get('category', 'Template')
                        strategies.append(f"[Template] {name} ({category})")
                except Exception as e:
                    logger.warning(f"Error loading {file}: {e}")
    
    return strategies

def run_backtest_direct(strategy, start_date, end_date, initial_capital):
    """Run backtest directly using CLI without FastAPI"""
    try:
        # Parse strategy selection
        if strategy.startswith("Built-in: "):
            strategy_name = strategy.replace("Built-in: ", "")
            yaml_config = None
        elif strategy.startswith("[AI] ") or strategy.startswith("[Template] "):
            # Extract strategy name and find corresponding YAML file
            strategy_name = strategy.split(" (")[0].replace("[AI] ", "").replace("[Template] ", "")
            yaml_config = find_yaml_file(strategy_name)
            if not yaml_config:
                return f"❌ Error: Could not find YAML file for strategy '{strategy_name}'"
        else:
            return f"❌ Error: Invalid strategy selection '{strategy}'"
        
        # Build CLI command
        cmd = [
            "python", "backtest_engine.py",
            "--start-date", start_date,
            "--end-date", end_date,
            "--initial-capital", str(initial_capital)
        ]
        
        if yaml_config:
            cmd.extend(["--yaml-config", yaml_config])
        else:
            cmd.extend(["--strategy", strategy_name])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Execute backtest
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # Parse the output
            try:
                # The backtest engine should output JSON to stdout
                data = json.loads(result.stdout)
                return format_results(data, {})
            except json.JSONDecodeError:
                # Fallback: try to parse as text
                return f"✅ Backtest completed successfully!\n\n{result.stdout}"
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            return f"❌ Backtest failed:\n{error_msg}"
            
    except subprocess.TimeoutExpired:
        return "❌ Backtest timed out after 60 seconds"
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return f"❌ Error running backtest: {str(e)}"

def find_yaml_file(strategy_name):
    """Find YAML file for a given strategy name"""
    # Search in both directories
    for directory in [STRATEGIES_DIR, TEMPLATES_DIR]:
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.endswith('.yaml'):
                    try:
                        with open(os.path.join(directory, file), 'r') as f:
                            config = yaml.safe_load(f)
                            if config.get('strategy_name') == strategy_name:
                                return os.path.join(directory, file)
                    except Exception:
                        continue
    return None

def format_results(results, plots):
    """Format backtest results for display"""
    try:
        # Extract key metrics
        performance_metrics = results.get("performance_metrics", {})
        total_return = performance_metrics.get("total_return", 0)
        sharpe_ratio = performance_metrics.get("sharpe_ratio", 0)
        max_drawdown = performance_metrics.get("max_drawdown", 0)
        win_rate = performance_metrics.get("win_rate", 0)
        num_trades = performance_metrics.get("total_trades", 0)
        final_value = performance_metrics.get("final_value", 0)
        
        # Format the results
        formatted = f"""
## 📊 Backtest Results

### 📈 Performance Metrics
- **Final Portfolio Value**: ${final_value:,.2f}
- **Total Return**: {total_return:.2%}
- **Sharpe Ratio**: {sharpe_ratio:.2f}
- **Max Drawdown**: {max_drawdown:.2%}
- **Win Rate**: {win_rate:.2%}
- **Total Trades**: {num_trades}

### 📋 Trade Summary
"""
        
        # Add trade summary table
        trade_logs = results.get("trade_logs", [])
        if trade_logs:
            formatted += "| Entry Date | Exit Date | Type | Strike | Entry Price | Exit Price | P&L | Exit Reason |\n"
            formatted += "|------------|-----------|------|--------|-------------|------------|-----|-------------|\n"
            
            for trade in trade_logs[:10]:  # Show first 10 trades
                entry_date = trade.get("entry_date", "N/A")
                exit_date = trade.get("exit_date", "N/A")
                trade_type = trade.get("trade_type", "N/A")
                strike = trade.get("strike", "N/A")
                entry_price = trade.get("entry_price", 0)
                exit_price = trade.get("exit_price", 0)
                pnl = trade.get("pnl", 0)
                exit_reason = trade.get("exit_reason", "N/A")
                
                formatted += f"| {entry_date} | {exit_date} | {trade_type} | ${strike} | ${entry_price:.2f} | ${exit_price:.2f} | ${pnl:.2f} | {exit_reason} |\n"
            
            if len(trade_logs) > 10:
                formatted += f"\n*Showing first 10 of {len(trade_logs)} trades*\n"
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting results: {e}")
        return f"❌ Error formatting results: {str(e)}"

def format_trade_details(results):
    """Format detailed trade information for collapsible section"""
    try:
        trade_logs = results.get("trade_logs", [])
        if not trade_logs:
            return "No trade details available."
        
        details = "## 🔍 Detailed Trade Information\n\n"
        
        for i, trade in enumerate(trade_logs, 1):
            details += f"### Trade #{i}\n\n"
            details += f"**Entry Date**: {trade.get('entry_date', 'N/A')}\n"
            details += f"**Exit Date**: {trade.get('exit_date', 'N/A')}\n"
            details += f"**Trade Type**: {trade.get('trade_type', 'N/A')}\n"
            details += f"**Strike Price**: ${trade.get('strike', 'N/A')}\n"
            details += f"**Entry Price**: ${trade.get('entry_price', 0):.2f}\n"
            details += f"**Exit Price**: ${trade.get('exit_price', 0):.2f}\n"
            details += f"**P&L**: ${trade.get('pnl', 0):.2f}\n"
            details += f"**Exit Reason**: {trade.get('exit_reason', 'N/A')}\n"
            
            # Add Greeks data if available
            if 'entry_greeks' in trade:
                greeks = trade['entry_greeks']
                details += f"**Entry Greeks**: Delta={greeks.get('delta', 'N/A'):.3f}, Gamma={greeks.get('gamma', 'N/A'):.3f}, Theta={greeks.get('theta', 'N/A'):.3f}, Vega={greeks.get('vega', 'N/A'):.3f}\n"
            
            if 'exit_greeks' in trade:
                greeks = trade['exit_greeks']
                details += f"**Exit Greeks**: Delta={greeks.get('delta', 'N/A'):.3f}, Gamma={greeks.get('gamma', 'N/A'):.3f}, Theta={greeks.get('theta', 'N/A'):.3f}, Vega={greeks.get('vega', 'N/A'):.3f}\n"
            
            # Add IV data if available
            if 'entry_iv' in trade:
                details += f"**Entry IV**: {trade['entry_iv']:.2%}\n"
            if 'exit_iv' in trade:
                details += f"**Exit IV**: {trade['exit_iv']:.2%}\n"
            
            # Add DTE data if available
            if 'entry_dte' in trade:
                details += f"**Entry DTE**: {trade['entry_dte']} days\n"
            if 'exit_dte' in trade:
                details += f"**Exit DTE**: {trade['exit_dte']} days\n"
            
            details += "\n---\n\n"
        
        return details
        
    except Exception as e:
        logger.error(f"Error formatting trade details: {e}")
        return f"❌ Error formatting trade details: {str(e)}"

def run_backtest_with_details(strategy, start_date, end_date, initial_capital):
    """Run backtest and return both results and trade details"""
    try:
        # Parse strategy selection
        if strategy.startswith("Built-in: "):
            strategy_name = strategy.replace("Built-in: ", "")
            yaml_config = None
        elif strategy.startswith("[AI] ") or strategy.startswith("[Template] "):
            strategy_name = strategy.split(" (")[0].replace("[AI] ", "").replace("[Template] ", "")
            yaml_config = find_yaml_file(strategy_name)
            if not yaml_config:
                return f"❌ Error: Could not find YAML file for strategy '{strategy_name}'", "No trade details available."
        else:
            return f"❌ Error: Invalid strategy selection '{strategy}'", "No trade details available."
        
        # Build CLI command
        cmd = [
            "python", "backtest_engine.py",
            "--start-date", start_date,
            "--end-date", end_date,
            "--initial-capital", str(initial_capital)
        ]
        
        if yaml_config:
            cmd.extend(["--yaml-config", yaml_config])
        else:
            cmd.extend(["--strategy", strategy_name])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        # Execute backtest
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            try:
                # Parse JSON output
                data = json.loads(result.stdout)
                results_text = format_results(data, {})
                trade_details = format_trade_details(data)
                return results_text, trade_details
            except json.JSONDecodeError:
                # Fallback to text output
                return f"✅ Backtest completed successfully!\n\n{result.stdout}", "Trade details not available in text format."
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            return f"❌ Backtest failed:\n{error_msg}", "No trade details available."
            
    except subprocess.TimeoutExpired:
        return "❌ Backtest timed out after 60 seconds", "No trade details available."
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return f"❌ Error running backtest: {str(e)}", "No trade details available."

def create_interface():
    """Create the Gradio interface"""
    with gr.Blocks(title="OptionsLab - Pure Gradio", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🚀 OptionsLab - Pure Gradio Edition")
        gr.Markdown("### Simplified options backtesting without FastAPI backend")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### ⚙️ Configuration")
                
                # Strategy selection
                strategies = get_available_strategies()
                strategy = gr.Dropdown(
                    choices=strategies,
                    value=strategies[0] if strategies else None,
                    label="📈 Strategy",
                    info="Select a trading strategy to backtest"
                )
                
                # Date inputs
                start_date = gr.Textbox(
                    value="2024-01-01",
                    label="📅 Start Date",
                    info="Format: YYYY-MM-DD"
                )
                
                end_date = gr.Textbox(
                    value="2024-01-31",
                    label="📅 End Date", 
                    info="Format: YYYY-MM-DD"
                )
                
                # Capital input
                initial_capital = gr.Number(
                    value=10000,
                    label="💰 Initial Capital",
                    info="Starting portfolio value"
                )
                
                # Run button
                run_btn = gr.Button("🚀 Run Backtest", variant="primary", size="lg")
                
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")
                results_output = gr.Markdown("Ready to run backtest...")
                
                # Trade Details section (collapsible)
                with gr.Accordion("🔍 Detailed Trade Information", open=False):
                    trade_details_output = gr.Markdown("Run a backtest first to see detailed trade information")
        
        # Event handlers
        run_btn.click(
            fn=run_backtest_with_details,
            inputs=[strategy, start_date, end_date, initial_capital],
            outputs=[results_output, trade_details_output]
        )
        
        # Footer
        gr.Markdown("---")
        gr.Markdown("**Pure Gradio Edition** - No FastAPI backend required!")
    
    return app

if __name__ == "__main__":
    # Create and launch the interface
    app = create_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    ) 