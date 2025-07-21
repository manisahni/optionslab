#!/usr/bin/env python3
"""
Simplified Auditable Gradio App for OptionsLab
Features unified backtest management across all tabs
"""

import gradio as gr
import pandas as pd
import numpy as np
import yaml
import json
from pathlib import Path
from datetime import datetime, timedelta, date
import subprocess
import sys
import os
import shutil
import random
from typing import List, Dict, Optional, Tuple

# Import our auditable backtest functions
from optionslab.auditable_backtest import (
    load_and_audit_data,
    audit_strategy_config,
    find_suitable_options,
    calculate_position_size,
    run_auditable_backtest
)

# Import visualization and AI modules
from optionslab.visualization import (
    plot_pnl_curve,
    plot_trade_markers,
    plot_greeks_evolution,
    plot_win_loss_distribution,
    plot_strategy_heatmap,
    create_summary_dashboard
)
from optionslab.ai_assistant import AIAssistant

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_trade_logs_dir() -> Path:
    """Get the trade logs directory"""
    return Path(__file__).parent / "trade_logs"

def get_available_data_files():
    """Get available parquet files for backtesting"""
    # Use local data directory
    data_dir = Path(__file__).parent / "data"
    
    files = []
    
    if data_dir.exists():
        # Check for master file first
        master_file = data_dir / "SPY_OPTIONS_MASTER_20200715_20250711.parquet"
        if master_file.exists():
            files.append(("📊 SPY Options Master (2020-07 to 2025-07) - 5 Years", str(master_file)))
        
        # Check for yearly files
        for year in range(2020, 2026):
            year_file = data_dir / f"SPY_OPTIONS_{year}_COMPLETE.parquet"
            if year_file.exists():
                files.append((f"📅 SPY Options {year} - Full Year", str(year_file)))
    
    return files if files else [("❌ No data files found", None)]

def get_available_strategies():
    """Get available strategy configurations"""
    strategies = []
    
    # Check parent directory for simple strategies
    simple_strategy = Path(__file__).parent.parent / "simple_test_strategy.yaml"
    if simple_strategy.exists():
        strategies.append(("🎯 Simple Long Call Test", str(simple_strategy)))
    
    # Check for advanced strategy
    advanced_strategy = Path(__file__).parent.parent / "advanced_test_strategy.yaml"
    if advanced_strategy.exists():
        strategies.append(("🚀 Advanced Long Call (Delta/DTE/Liquidity)", str(advanced_strategy)))
    
    # Check config/strategies directory
    strategies_dir = Path(__file__).parent.parent / "config" / "strategies"
    if strategies_dir.exists():
        for yaml_file in strategies_dir.glob("*.yaml"):
            name = yaml_file.stem.replace('_', ' ').title()
            strategies.append((f"📋 {name}", str(yaml_file)))
    
    return strategies if strategies else [("❌ No strategies found", None)]

def generate_memorable_name() -> str:
    """Generate a unique memorable name for the backtest"""
    adjectives = [
        "Swift", "Golden", "Silver", "Bold", "Wise", "Lucky", "Sharp", "Clever",
        "Mighty", "Noble", "Brave", "Fierce", "Calm", "Bright", "Steady", "Agile",
        "Iron", "Crystal", "Thunder", "Storm", "Fire", "Ice", "Shadow", "Light",
        "Dynamic", "Quantum", "Stellar", "Cosmic", "Mystic", "Ancient", "Modern", "Prime"
    ]
    
    animals = [
        "Eagle", "Tiger", "Fox", "Wolf", "Hawk", "Bear", "Lion", "Falcon",
        "Dragon", "Phoenix", "Panther", "Shark", "Cobra", "Raven", "Bull", "Owl",
        "Stallion", "Jaguar", "Viper", "Condor", "Lynx", "Rhino", "Cheetah", "Orca"
    ]
    
    adjective = random.choice(adjectives)
    animal = random.choice(animals)
    unique_id = datetime.now().strftime("%H%M")
    
    return f"{adjective} {animal}-{unique_id}"

def format_backtest_dropdown_choice(log_data: dict) -> Tuple[str, str]:
    """Create unified format for backtest dropdown choices"""
    memorable_name = log_data.get('memorable_name', 'Unknown')
    total_return = log_data.get('total_return', 0)
    backtest_date = log_data.get('backtest_date', 'Unknown')[:10]
    
    # Performance emoji
    if total_return > 0.1:
        perf_emoji = "🚀"
    elif total_return > 0:
        perf_emoji = "📈"
    elif total_return > -0.1:
        perf_emoji = "📉"
    else:
        perf_emoji = "💥"
    
    label = f"🎯 {memorable_name} | {total_return:.1%} {perf_emoji} | {backtest_date}"
    return (label, log_data['path'])

def get_all_trade_logs() -> List[dict]:
    """Get all trade logs from index"""
    logs_dir = get_trade_logs_dir()
    index_file = logs_dir / "index.json"
    
    if not index_file.exists():
        return []
    
    try:
        with open(index_file, 'r') as f:
            index_data = json.load(f)
        
        # Sort by backtest date descending (most recent first)
        logs = sorted(index_data.get('logs', []), 
                     key=lambda x: x.get('backtest_date', ''), 
                     reverse=True)
        
        # Filter out archived logs
        active_logs = []
        for log in logs:
            log_path = Path(log['path'])
            if log_path.exists() and 'archive' not in str(log_path):
                active_logs.append(log)
        
        return active_logs
    except Exception as e:
        print(f"Error reading index: {e}")
        return []

def get_most_recent_backtest() -> Tuple[Optional[str], Optional[dict]]:
    """Get the most recent backtest path and info"""
    logs = get_all_trade_logs()
    if logs:
        return logs[0]['path'], logs[0]
    return None, None

def save_trade_log(trades_df: pd.DataFrame, results: dict, strategy_name: str, 
                   start_date: str, end_date: str, strategy_config: dict = None) -> tuple[str, str, str]:
    """Save trade log to permanent storage"""
    logs_dir = get_trade_logs_dir()
    now = datetime.now()
    year_dir = logs_dir / str(now.year)
    month_dir = year_dir / f"{now.month:02d}"
    month_dir.mkdir(parents=True, exist_ok=True)
    
    memorable_name = generate_memorable_name()
    
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    base_name = f"trades_{strategy_name}_{start_date}_to_{end_date}_{timestamp}"
    csv_path = month_dir / f"{base_name}.csv"
    json_path = month_dir / f"{base_name}.json"
    
    # Save CSV
    if not trades_df.empty:
        trades_df.to_csv(csv_path, index=False)
    
    # Prepare metadata
    total_return = results.get('total_return', 0)
    metadata = {
        'strategy': strategy_name,
        'start_date': start_date,
        'end_date': end_date,
        'backtest_date': now.isoformat(),
        'memorable_name': memorable_name,
        'initial_capital': results.get('initial_capital', 10000),
        'final_value': results.get('final_value', 0),
        'total_return': total_return,
        'total_trades': len(trades_df),
        'win_rate': results.get('win_rate', 0)
    }
    
    # Convert DataFrame to dict and handle timestamps
    trades_list = []
    if not trades_df.empty:
        # Convert to dict first
        trades_dict = trades_df.to_dict('records')
        # Convert any timestamps to strings
        for trade in trades_dict:
            for key, value in trade.items():
                # Handle various data types
                if isinstance(value, pd.Timestamp):
                    trade[key] = str(value) if pd.notna(value) else None
                elif isinstance(value, (datetime, date)):
                    trade[key] = value.isoformat()
                elif isinstance(value, (np.integer, np.int64, int)):
                    trade[key] = int(value)
                elif isinstance(value, (np.floating, np.float64, float)):
                    # Check for NaN without array ambiguity
                    if isinstance(value, float) and np.isnan(value):
                        trade[key] = None
                    elif hasattr(value, 'item'):  # numpy scalar
                        v = value.item()
                        trade[key] = None if np.isnan(v) else float(v)
                    else:
                        trade[key] = float(value)
                elif value is None or (isinstance(value, float) and np.isnan(value)):
                    trade[key] = None
                elif hasattr(value, '__len__') and not isinstance(value, str):
                    # Handle arrays/lists
                    trade[key] = list(value) if len(value) > 0 else None
        trades_list = trades_dict
    
    # Save JSON with trades and metadata
    json_data = {
        'metadata': metadata,
        'trades': trades_list
    }
    
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2, default=str)
    
    # Update index
    update_trade_log_index(str(json_path), metadata)
    
    return str(csv_path), str(json_path), memorable_name

def update_trade_log_index(json_path: str, metadata: dict):
    """Update the central index of trade logs"""
    logs_dir = get_trade_logs_dir()
    index_file = logs_dir / "index.json"
    
    # Load existing index or create new
    if index_file.exists():
        with open(index_file, 'r') as f:
            index_data = json.load(f)
    else:
        index_data = {'logs': []}
    
    # Add new log entry
    log_entry = {
        'path': json_path,
        'memorable_name': metadata['memorable_name'],
        'strategy': metadata['strategy'],
        'backtest_date': metadata['backtest_date'],
        'total_return': metadata['total_return'],
        'total_trades': metadata['total_trades']
    }
    
    index_data['logs'].append(log_entry)
    
    # Save updated index
    with open(index_file, 'w') as f:
        json.dump(index_data, f, indent=2)

def delete_trade_log(log_path: str) -> bool:
    """Delete a trade log permanently"""
    try:
        json_path = Path(log_path)
        csv_path = json_path.with_suffix('.csv')
        
        # Delete files
        if json_path.exists():
            json_path.unlink()
        if csv_path.exists():
            csv_path.unlink()
        
        # Update index
        logs_dir = get_trade_logs_dir()
        index_file = logs_dir / "index.json"
        
        if index_file.exists():
            with open(index_file, 'r') as f:
                index_data = json.load(f)
            
            # Remove from index
            index_data['logs'] = [log for log in index_data.get('logs', []) 
                                 if log['path'] != str(json_path)]
            
            with open(index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error deleting log: {e}")
        return False

def delete_old_logs(days_to_keep: int) -> int:
    """Delete logs older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    logs = get_all_trade_logs()
    deleted_count = 0
    
    for log in logs:
        try:
            log_date = datetime.fromisoformat(log.get('backtest_date', ''))
            if log_date < cutoff_date:
                if delete_trade_log(log['path']):
                    deleted_count += 1
        except:
            continue
    
    return deleted_count

def format_trades_dataframe(trades):
    """Format trades into a clean DataFrame for display"""
    if not trades:
        return pd.DataFrame()
    
    completed_trades = [t for t in trades if 'exit_date' in t]
    if not completed_trades:
        return pd.DataFrame()
    
    df_data = []
    for trade in completed_trades:
        row = {
            'ID': trade.get('trade_id', ''),
            'Type': trade.get('option_type', ''),
            'Entry Date': trade.get('entry_date', ''),
            'Exit Date': trade.get('exit_date', ''),
            'Strike': f"${trade.get('strike', 0):.2f}",
            'Days Held': trade.get('days_held', 0),
            'Entry Reason': trade.get('entry_reason', ''),
            'Exit Reason': trade.get('exit_reason', ''),
            'P&L $': f"${trade.get('pnl', 0):.2f}",
            'P&L %': f"{trade.get('pnl_pct', 0):.1f}%"
        }
        df_data.append(row)
    
    return pd.DataFrame(df_data)

def run_auditable_backtest_gradio(data_file, strategy_file, start_date, end_date, initial_capital, log_level="summary"):
    """Run auditable backtest and return results for Gradio"""
    import io
    import sys
    import tempfile
    
    old_stdout = sys.stdout
    audit_output = io.StringIO()
    sys.stdout = audit_output
    
    try:
        results = run_auditable_backtest(data_file, strategy_file, start_date, end_date)
        sys.stdout = old_stdout
        
        if results:
            audit_log = audit_output.getvalue()
            trades_df = format_trades_dataframe(results['trades'])
            
            # Calculate statistics
            completed_trades = [t for t in results['trades'] if 'exit_date' in t]
            winning_trades = [t for t in completed_trades if t.get('pnl', 0) > 0]
            win_rate = (len(winning_trades) / len(completed_trades) * 100) if completed_trades else 0
            
            # Create summary
            summary = f"""
## 📊 Backtest Results

### Overall Performance
- **Final Value:** ${results['final_value']:,.2f}
- **Total Return:** {results['total_return']:.2%}
- **Initial Capital:** ${initial_capital:,.2f}
- **Total Trades:** {len(completed_trades)}
- **Win Rate:** {win_rate:.1f}%
"""
            
            # Save results
            if results['trades']:
                full_trades_df = pd.DataFrame(results['trades'])
                results['initial_capital'] = initial_capital
                
                strategy_name = Path(strategy_file).stem.replace('_', '-')
                perm_csv_path, perm_json_path, memorable_name = save_trade_log(
                    full_trades_df, results, strategy_name, start_date, end_date
                )
                
                summary += f"\n### 🎯 Backtest Name: **{memorable_name}**"
            
            return summary, trades_df, audit_log
        else:
            sys.stdout = old_stdout
            return f"❌ Backtest failed!\n\n{audit_output.getvalue()}", pd.DataFrame(), ""
            
    except Exception as e:
        sys.stdout = old_stdout
        import traceback
        error_trace = traceback.format_exc()
        return f"❌ Error: {str(e)}\n\n{error_trace}", pd.DataFrame(), ""

# ============================================================================
# MAIN INTERFACE
# ============================================================================

def create_simple_interface():
    """Create the simplified Gradio interface with unified backtest management"""
    
    with gr.Blocks(title="OptionsLab - Simple", theme=gr.themes.Soft()) as app:
        
        # Header
        gr.Markdown("""
        # 🎯 OptionsLab - Auditable Backtesting System
        
        **Simplified interface with unified backtest management**
        """)
        
        # Unified backtest selector at the top
        with gr.Row():
            with gr.Column(scale=3):
                backtest_selector = gr.Dropdown(
                    label="📊 Active Backtest",
                    choices=[],
                    info="Select a backtest to view across all tabs",
                    scale=3
                )
            with gr.Column(scale=1):
                refresh_btn = gr.Button("🔄 Refresh", size="sm")
                auto_delete_days = gr.Number(
                    label="Auto-delete after (days)",
                    value=30,
                    minimum=7,
                    maximum=365,
                    visible=False  # Hidden for now
                )
        
        selected_backtest_info = gr.Markdown("No backtest selected")
        
        # Shared states
        selected_backtest_data = gr.State(None)
        
        with gr.Tabs() as tabs:
            # Run Backtest Tab
            with gr.TabItem("🚀 Run Backtest", id=0):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 Configuration")
                        
                        data_files = get_available_data_files()
                        data_file_dropdown = gr.Dropdown(
                            choices=data_files,
                            label="📁 Select Data File",
                            value=data_files[0][1] if data_files else None
                        )
                        
                        strategies = get_available_strategies()
                        strategy_dropdown = gr.Dropdown(
                            choices=strategies,
                            label="📋 Select Strategy",
                            value=strategies[0][1] if strategies else None
                        )
                        
                        start_date = gr.Textbox(
                            label="📅 Start Date",
                            value="2022-01-01"
                        )
                        
                        end_date = gr.Textbox(
                            label="📅 End Date",
                            value="2022-12-31"
                        )
                        
                        initial_capital = gr.Number(
                            label="💰 Initial Capital",
                            value=10000,
                            minimum=1000,
                            maximum=1000000,
                            step=1000
                        )
                        
                        run_btn = gr.Button("🚀 Run Backtest", variant="primary", size="lg")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Results")
                        summary_output = gr.Markdown("Results will appear here...")
                        trades_table = gr.DataFrame()
                        audit_log = gr.Textbox(label="Audit Log", lines=10, visible=False)
            
            # Visualizations Tab
            with gr.TabItem("📊 Visualizations", id=1):
                with gr.Row():
                    with gr.Column(scale=1):
                        chart_type = gr.Dropdown(
                            label="Chart Type",
                            choices=[
                                ("P&L Curve", "pnl_curve"),
                                ("Trade Markers", "trade_markers"),
                                ("Win/Loss Distribution", "win_loss"),
                                ("Monthly Heatmap", "heatmap"),
                                ("Summary Dashboard", "dashboard")
                            ],
                            value="pnl_curve"
                        )
                        generate_chart_btn = gr.Button("📊 Generate", variant="primary")
                        
                    with gr.Column(scale=3):
                        main_chart = gr.Plot(label="Visualization")
            
            # AI Assistant Tab
            with gr.TabItem("🤖 AI Assistant", id=2):
                ai_assistant = gr.State(AIAssistant())
                
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 🔧 AI Configuration")
                        api_key_input = gr.Textbox(
                            type="password",
                            label="Gemini API Key",
                            placeholder="Enter or use .env"
                        )
                        save_key_btn = gr.Button("💾 Update Key", size="sm")
                        api_status = gr.Markdown("Checking...")
                        
                        start_chat_btn = gr.Button("🤖 Start AI Assistant", variant="primary", size="lg")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("### 💬 Chat")
                        chatbot = gr.Chatbot(height=500, type="messages")
                        msg_input = gr.Textbox(label="Message", lines=2)
                        send_btn = gr.Button("📤 Send", variant="primary")
            
            # Log Manager Tab
            with gr.TabItem("📁 Log Manager", id=3):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🗑️ Manage Logs")
                        
                        with gr.Row():
                            delete_btn = gr.Button("🗑️ Delete Selected", variant="stop")
                            delete_old_btn = gr.Button("🧹 Delete Old Logs", variant="secondary")
                            keep_days = gr.Number(label="Keep last N days", value=30, minimum=7)
                        
                        action_output = gr.Markdown("")
                        
                        gr.Markdown("### 📊 Selected Log Details")
                        log_info_df = gr.DataFrame()
        
        # ========================================================================
        # EVENT HANDLERS
        # ========================================================================
        
        def refresh_backtest_list():
            """Refresh the unified backtest selector"""
            logs = get_all_trade_logs()
            if not logs:
                return gr.update(choices=[], value=None), "No backtests found"
            
            choices = [format_backtest_dropdown_choice(log) for log in logs]
            most_recent = choices[0][1] if choices else None
            
            return gr.update(choices=choices, value=most_recent), f"Found {len(logs)} backtests"
        
        def load_selected_backtest(selected_path):
            """Load data for the selected backtest"""
            if not selected_path:
                return None, "No backtest selected"
            
            try:
                with open(selected_path, 'r') as f:
                    data = json.load(f)
                
                metadata = data.get('metadata', {})
                memorable_name = metadata.get('memorable_name', 'Unknown')
                total_return = metadata.get('total_return', 0)
                total_trades = metadata.get('total_trades', 0)
                win_rate = metadata.get('win_rate', 0)
                
                info = f"""
### 🎯 {memorable_name}
- **Return:** {total_return:.1%}
- **Trades:** {total_trades}
- **Win Rate:** {win_rate:.1%}
- **Date:** {metadata.get('backtest_date', 'Unknown')[:10]}
"""
                return data, info
            except Exception as e:
                return None, f"Error loading backtest: {str(e)}"
        
        def on_backtest_complete(summary, trades_df, audit_log, results):
            """Handle backtest completion and auto-select new result"""
            if results:
                # Refresh the selector and select the new backtest
                logs = get_all_trade_logs()
                if logs:
                    choices = [format_backtest_dropdown_choice(log) for log in logs]
                    # The most recent will be our new backtest
                    return (
                        summary, 
                        trades_df, 
                        audit_log,
                        gr.update(choices=choices, value=choices[0][1]),  # backtest_selector
                        logs[0],  # selected_backtest_data
                        f"Found {len(logs)} backtests"  # selected_backtest_info
                    )
            return summary, trades_df, audit_log, gr.update(), None, "Backtest failed"
        
        def generate_visualization(chart_type, backtest_data):
            """Generate visualization for selected backtest"""
            if not backtest_data:
                return None
            
            try:
                trades = backtest_data.get('trades', [])
                metadata = backtest_data.get('metadata', {})
                
                if chart_type == "pnl_curve":
                    return plot_pnl_curve(trades, metadata.get('initial_capital', 10000))
                elif chart_type == "trade_markers":
                    return plot_trade_markers(trades)
                elif chart_type == "win_loss":
                    return plot_win_loss_distribution(trades)
                elif chart_type == "heatmap":
                    return plot_strategy_heatmap(trades)
                elif chart_type == "dashboard":
                    return create_summary_dashboard(trades, metadata.get('initial_capital', 10000))
            except Exception as e:
                print(f"Visualization error: {e}")
                return None
        
        def delete_selected_backtest(selected_path, current_selection):
            """Delete the selected backtest"""
            if not selected_path:
                return "No backtest selected", gr.update(), None
            
            if delete_trade_log(selected_path):
                # Refresh list and select most recent
                logs = get_all_trade_logs()
                if logs:
                    choices = [format_backtest_dropdown_choice(log) for log in logs]
                    return (
                        "✅ Backtest deleted successfully",
                        gr.update(choices=choices, value=choices[0][1]),
                        logs[0]
                    )
                else:
                    return (
                        "✅ Backtest deleted successfully",
                        gr.update(choices=[], value=None),
                        None
                    )
            else:
                return "❌ Failed to delete backtest", gr.update(), current_selection
        
        def delete_old_backtests(days):
            """Delete backtests older than specified days"""
            count = delete_old_logs(int(days))
            # Refresh list
            logs = get_all_trade_logs()
            if logs:
                choices = [format_backtest_dropdown_choice(log) for log in logs]
                return f"✅ Deleted {count} old backtests", gr.update(choices=choices, value=choices[0][1])
            else:
                return f"✅ Deleted {count} old backtests", gr.update(choices=[], value=None)
        
        
        # Wire up event handlers
        refresh_btn.click(
            fn=refresh_backtest_list,
            outputs=[backtest_selector, selected_backtest_info]
        )
        
        backtest_selector.change(
            fn=load_selected_backtest,
            inputs=[backtest_selector],
            outputs=[selected_backtest_data, selected_backtest_info]
        )
        
        run_btn.click(
            fn=run_auditable_backtest_gradio,
            inputs=[data_file_dropdown, strategy_dropdown, start_date, end_date, initial_capital],
            outputs=[summary_output, trades_table, audit_log]
        ).then(
            fn=refresh_backtest_list,
            outputs=[backtest_selector, selected_backtest_info]
        )
        
        generate_chart_btn.click(
            fn=generate_visualization,
            inputs=[chart_type, selected_backtest_data],
            outputs=[main_chart]
        )
        
        save_key_btn.click(
            fn=lambda key, ai: ("✅ Key saved", ai.set_api_key(key) or ai),
            inputs=[api_key_input, ai_assistant],
            outputs=[api_status, ai_assistant]
        )
        
        def start_ai_chat(ai_assistant, backtest_data):
            """Start AI conversation with initial greeting and options"""
            if not ai_assistant.is_configured():
                return [{"role": "assistant", "content": "❌ AI not configured. Please set API key."}]
            
            if not backtest_data:
                return [{"role": "assistant", "content": "❌ No backtest selected. Please select a backtest from the dropdown above."}]
            
            metadata = backtest_data.get('metadata', {})
            greeting = f"""👋 I'm a professional financial trader and quantitative developer with expertise in options trading strategies.

I've reviewed the backtest: **{metadata.get('memorable_name', 'Unknown')}**
- Total Return: {metadata.get('total_return', 0):.1%}
- Total Trades: {metadata.get('total_trades', 0)}
- Win Rate: {metadata.get('win_rate', 0):.1%}

I have access to:
- Complete trade execution logs and performance metrics
- Strategy configuration and parameters
- The backtesting engine source code
- Historical Greeks and underlying price data

As an experienced trader and coder, I can help you with:
1. 📊 **Performance Analysis** - Deep dive into trade metrics and risk-adjusted returns
2. 🔍 **Implementation Verification** - Ensure the strategy logic matches specifications
3. 💡 **Strategy Optimization** - Recommend parameter adjustments based on market regime
4. 🛠️ **Code Review** - Analyze the implementation quality and suggest improvements
5. 📈 **Risk Management** - Evaluate position sizing and drawdown control

What aspect would you like to explore?"""
            
            return [{"role": "assistant", "content": greeting}]
        
        def chat_with_ai(message, chat_history, ai_assistant, backtest_data):
            """Handle chat messages and maintain conversation"""
            if not ai_assistant.is_configured():
                chat_history.append({"role": "user", "content": message})
                chat_history.append({"role": "assistant", "content": "❌ AI not configured. Please set API key."})
                return chat_history, ""
            
            if not backtest_data:
                chat_history.append({"role": "user", "content": message})
                chat_history.append({"role": "assistant", "content": "❌ No backtest selected. Please select a backtest first."})
                return chat_history, ""
            
            # Add user message to history
            chat_history.append({"role": "user", "content": message})
            
            # Determine what the user wants
            message_lower = message.lower()
            
            if any(word in message_lower for word in ["analyze", "performance", "trades", "1"]):
                # Analyze backtest performance
                metadata = backtest_data.get('metadata', {})
                trades = backtest_data.get('trades', [])
                
                prompt = f"""Analyze this backtest: {metadata.get('memorable_name')}
Total Return: {metadata.get('total_return', 0):.1%}
Total Trades: {len(trades)}
Provide insights and suggestions."""
                
                response = ai_assistant.chat(prompt, backtest_data)
                
            elif any(word in message_lower for word in ["implementation", "quality", "check", "verify", "2"]):
                # Check implementation adequacy
                response = ai_assistant.analyze_implementation_adequacy(backtest_data)
                
            elif any(word in message_lower for word in ["improve", "optimize", "suggestion", "3"]):
                # Provide improvement suggestions
                response = ai_assistant.chat("Based on this backtest data, what specific improvements would you recommend for better performance?", backtest_data)
                
            else:
                # General chat
                response = ai_assistant.chat(message, backtest_data)
            
            # Add AI response to history
            chat_history.append({"role": "assistant", "content": response})
            
            # Return updated history and clear input
            return chat_history, ""
        
        start_chat_btn.click(
            fn=start_ai_chat,
            inputs=[ai_assistant, selected_backtest_data],
            outputs=[chatbot]
        )
        
        # Connect the send button for continuous conversation
        send_btn.click(
            fn=chat_with_ai,
            inputs=[msg_input, chatbot, ai_assistant, selected_backtest_data],
            outputs=[chatbot, msg_input]
        )
        
        # Also handle Enter key press
        msg_input.submit(
            fn=chat_with_ai,
            inputs=[msg_input, chatbot, ai_assistant, selected_backtest_data],
            outputs=[chatbot, msg_input]
        )
        
        delete_btn.click(
            fn=delete_selected_backtest,
            inputs=[backtest_selector, selected_backtest_data],
            outputs=[action_output, backtest_selector, selected_backtest_data]
        )
        
        delete_old_btn.click(
            fn=delete_old_backtests,
            inputs=[keep_days],
            outputs=[action_output, backtest_selector]
        )
        
        # Load initial data
        app.load(
            fn=refresh_backtest_list,
            outputs=[backtest_selector, selected_backtest_info]
        ).then(
            fn=load_selected_backtest,
            inputs=[backtest_selector],
            outputs=[selected_backtest_data, selected_backtest_info]
        )
    
    return app

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    app = create_simple_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        inbrowser=False
    )