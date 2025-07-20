#!/usr/bin/env python3
"""
OptionsLab - Auditable Backtesting System
Clean, organized Gradio interface for options backtesting with full trade auditing
"""

# Standard library imports
import json
import os
import random
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Third-party imports
import gradio as gr
import numpy as np
import pandas as pd
import yaml

# Local imports
from ai_assistant import AIAssistant
from auditable_backtest import (
    create_implementation_metrics,
    run_auditable_backtest
)

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

TRADE_LOGS_DIR = Path(__file__).parent / "trade_logs"
ARCHIVE_DIR = TRADE_LOGS_DIR / "archive"

# Memorable name generation
ADJECTIVES = ["Swift", "Golden", "Silver", "Bold", "Wise", "Dynamic", "Steady", 
              "Sharp", "Bright", "Solid", "Prime", "Smart", "Quick", "Alert", 
              "Keen", "Nimble", "Rapid", "Agile", "Clever", "Astute"]
ANIMALS = ["Eagle", "Tiger", "Fox", "Wolf", "Hawk", "Falcon", "Lion", "Bear", 
           "Bull", "Shark", "Dolphin", "Panther", "Cheetah", "Jaguar", "Lynx", 
           "Raven", "Phoenix", "Dragon", "Serpent", "Stallion"]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def ensure_directories():
    """Ensure required directories exist"""
    TRADE_LOGS_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

def generate_memorable_name() -> str:
    """Generate a unique memorable name for the backtest"""
    adjective = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    unique_id = datetime.now().strftime("%H%M")
    return f"{adjective} {animal}-{unique_id}"

def safe_percentage(value: float, decimals: int = 1) -> str:
    """Safely format percentage values"""
    try:
        return f"{value:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"

def safe_currency(value: float, decimals: int = 2) -> str:
    """Safely format currency values"""
    try:
        return f"${value:,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"

# ============================================================================
# FILE AND DATA MANAGEMENT
# ============================================================================

def get_available_data_files() -> List[Tuple[str, str]]:
    """Get available SPY options parquet files"""
    data_dirs = [
        Path("../spy_options_downloader/spy_options_parquet/repaired"),
        Path("../spy_options_downloader/spy_options_parquet"),
        Path("spy_options_downloader/spy_options_parquet/repaired"),
        Path("spy_options_downloader/spy_options_parquet")
    ]
    
    files = []
    for data_dir in data_dirs:
        if data_dir.exists():
            parquet_files = list(data_dir.glob("*.parquet"))
            files.extend([
                (f.stem.replace('_', ' ').title(), str(f))
                for f in sorted(parquet_files)[:10]  # Limit to 10 most recent
            ])
            if files:
                break
    
    return files if files else [("No data files found", "")]

def get_available_strategies() -> List[Tuple[str, str]]:
    """Get available strategy YAML files"""
    strategy_dirs = [
        Path(__file__).parent.parent / "config" / "strategies",
        Path("config/strategies"),
        Path("../config/strategies")
    ]
    
    strategies = []
    for strategy_dir in strategy_dirs:
        if strategy_dir.exists():
            yaml_files = list(strategy_dir.glob("*.yaml"))
            
            # Add advanced test strategy if it exists
            advanced_path = Path("../advanced_test_strategy.yaml")
            if advanced_path.exists():
                yaml_files.insert(0, advanced_path)
            
            strategies = [
                (f.stem.replace('_', ' ').title(), str(f))
                for f in yaml_files
            ]
            break
    
    return strategies if strategies else [("No strategies found", "")]

def get_available_backtests() -> List[Tuple[str, str]]:
    """Get available backtest results"""
    ensure_directories()
    index_path = TRADE_LOGS_DIR / "index.json"
    
    if not index_path.exists():
        return []
    
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        logs = index.get('logs', [])
        # Sort by date, most recent first
        logs = sorted(logs, key=lambda x: x.get('backtest_date', ''), reverse=True)
        
        return [
            (
                f"{log.get('memorable_name', 'Unknown')} - {log.get('strategy', 'N/A')} ({log.get('backtest_date', 'N/A')[:10]})",
                log.get('json_path', '')
            )
            for log in logs[:20]  # Limit to 20 most recent
        ]
    except Exception:
        return []

def get_most_recent_backtest() -> Tuple[Optional[str], Optional[Dict]]:
    """Get the most recent backtest path and info"""
    backtests = get_available_backtests()
    if not backtests:
        return None, None
    
    # Get the path from the first (most recent) backtest
    most_recent_path = backtests[0][1]
    
    try:
        with open(most_recent_path, 'r') as f:
            data = json.load(f)
        return most_recent_path, data.get('metadata', {})
    except Exception:
        return None, None

# ============================================================================
# TRADE LOG MANAGEMENT
# ============================================================================

def save_trade_log(trades_df: pd.DataFrame, results: dict, strategy_name: str, 
                  start_date: str, end_date: str, strategy_config: dict = None) -> Tuple[str, str, str]:
    """Save trade log with comprehensive metadata"""
    ensure_directories()
    
    # Generate memorable name
    memorable_name = generate_memorable_name()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create filenames
    safe_strategy = strategy_name.replace(' ', '_').lower()
    base_name = f"{safe_strategy}_{timestamp}_{memorable_name.replace(' ', '_').replace('-', '_')}"
    csv_path = TRADE_LOGS_DIR / f"{base_name}.csv"
    json_path = TRADE_LOGS_DIR / f"{base_name}.json"
    
    # Save CSV
    trades_df.to_csv(csv_path, index=False)
    
    # Calculate metrics
    completed_trades = [t for t in results['trades'] if t.get('exit_date')]
    win_rate = calculate_win_rate(completed_trades)
    
    # Create implementation metrics
    implementation_metrics = create_implementation_metrics(completed_trades, strategy_config)
    
    # Prepare comprehensive metadata
    metadata = {
        'memorable_name': memorable_name,
        'display_name': f"{memorable_name} - {strategy_name}",
        'strategy': strategy_name,
        'start_date': start_date,
        'end_date': end_date,
        'backtest_date': datetime.now().isoformat(),
        'initial_capital': results.get('initial_capital', 10000),
        'final_value': results['final_value'],
        'total_return': results['total_return'],
        'total_trades': len(completed_trades),
        'win_rate': win_rate,
        'max_drawdown': results.get('max_drawdown', 0),
        'sharpe_ratio': results.get('sharpe_ratio', 0),
        'strategy_config': strategy_config,
        'implementation_metrics': implementation_metrics
    }
    
    # Save JSON with full data
    full_data = {
        'metadata': metadata,
        'trades': results['trades']
    }
    
    with open(json_path, 'w') as f:
        json.dump(full_data, f, indent=2, default=str)
    
    # Update index
    update_trade_log_index(json_path, metadata)
    
    return str(csv_path), str(json_path), memorable_name

def calculate_win_rate(trades: list) -> float:
    """Calculate win rate from completed trades"""
    if not trades:
        return 0.0
    winning_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
    return (winning_trades / len(trades)) * 100

def update_trade_log_index(log_path: Path, metadata: dict):
    """Update the central index of all trade logs"""
    ensure_directories()
    index_path = TRADE_LOGS_DIR / "index.json"
    
    # Load or create index
    if index_path.exists():
        with open(index_path, 'r') as f:
            index = json.load(f)
    else:
        index = {'logs': [], 'last_updated': None}
    
    # Add new entry
    index['logs'].append({
        'json_path': str(log_path),
        'csv_path': str(log_path).replace('.json', '.csv'),
        **metadata
    })
    
    # Keep only last 100 entries
    index['logs'] = index['logs'][-100:]
    index['last_updated'] = datetime.now().isoformat()
    
    # Save updated index
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

# ============================================================================
# BACKTEST EXECUTION
# ============================================================================

def format_trades_dataframe(trades: List[Dict]) -> pd.DataFrame:
    """Format trades list into a display-friendly DataFrame"""
    if not trades:
        return pd.DataFrame()
    
    df_data = []
    for i, trade in enumerate(trades):
        row = {
            'ID': str(i + 1),
            'Type': trade.get('option_type', 'N/A'),
            'Entry Date': trade.get('entry_date', 'N/A'),
            'Exit Date': trade.get('exit_date', 'Open'),
            'Strike': safe_currency(trade.get('strike', 0)),
            'Entry Price': safe_currency(trade.get('option_price', 0)),
            'Exit Price': safe_currency(trade.get('exit_price', 0)) if trade.get('exit_price') else 'Open',
            'P&L $': safe_currency(trade.get('pnl', 0)),
            'P&L %': safe_percentage(trade.get('pnl_pct', 0)),
            'Exit Reason': trade.get('exit_reason', 'Open')
        }
        df_data.append(row)
    
    return pd.DataFrame(df_data)

def run_auditable_backtest_gradio(data_file: str, strategy_file: str, start_date: str, 
                                 end_date: str, initial_capital: float, log_level: str = "summary") -> Tuple:
    """Run backtest and return formatted results for Gradio"""
    # Redirect stdout to capture audit messages
    import io
    old_stdout = sys.stdout
    audit_output = io.StringIO()
    sys.stdout = audit_output
    
    try:
        # Run the backtest
        results = run_auditable_backtest(data_file, strategy_file, start_date, end_date)
        
        # Restore stdout
        sys.stdout = old_stdout
        
        if not results:
            return "❌ Backtest failed - check configuration", pd.DataFrame(), "", None
        
        # Process results
        audit_log = audit_output.getvalue()
        trades_df = format_trades_dataframe(results['trades'])
        
        # Load strategy config
        try:
            with open(strategy_file, 'r') as f:
                strategy_config = yaml.safe_load(f)
        except:
            strategy_config = None
        
        # Create summary
        summary = create_backtest_summary(results, strategy_config, initial_capital)
        
        # Filter audit log based on level
        if log_level == "summary":
            audit_log = ""  # No audit log for summary
        elif log_level == "standard":
            # Filter for key events only
            audit_log = filter_audit_log(audit_log, key_events_only=True)
        
        # Save results
        strategy_name = Path(strategy_file).stem
        csv_path, json_path, memorable_name = save_trade_log(
            pd.DataFrame(results['trades']), results, strategy_name, 
            start_date, end_date, strategy_config
        )
        
        # Add save info to summary
        summary += f"\n\n### 🎯 Backtest Name: **{memorable_name}**\n"
        summary += f"### 📁 Trade Log Saved\n- CSV: `{Path(csv_path).name}`\n- JSON: `{Path(json_path).name}`"
        
        return summary, trades_df, audit_log, csv_path
        
    except Exception as e:
        sys.stdout = old_stdout
        error_msg = f"❌ Error: {str(e)}\n\n## 🔍 Error Log\n```\n{audit_output.getvalue()}\n```"
        return error_msg, pd.DataFrame(), "", None

def create_backtest_summary(results: dict, strategy_config: dict, initial_capital: float) -> str:
    """Create a clean summary of backtest results"""
    completed_trades = [t for t in results['trades'] if 'exit_date' in t]
    winning_trades = [t for t in completed_trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in completed_trades if t.get('pnl', 0) <= 0]
    
    # Calculate metrics
    win_rate = calculate_win_rate(completed_trades)
    avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    # Strategy details
    strategy_details = ""
    if strategy_config:
        strategy_details = format_strategy_details(strategy_config)
    
    return f"""## 📊 Backtest Results

{strategy_details}

### Overall Performance
- **Final Value:** {safe_currency(results['final_value'])}
- **Total Return:** {safe_percentage(results['total_return'] * 100, 2)}
- **Initial Capital:** {safe_currency(initial_capital)}
- **Total Trades:** {len(completed_trades)}

### Trade Statistics
- **Win Rate:** {safe_percentage(win_rate)}
- **Average Win:** {safe_currency(avg_win)}
- **Average Loss:** {safe_currency(avg_loss)}
- **Best Trade:** {safe_currency(max(t.get('pnl', 0) for t in completed_trades)) if completed_trades else '$0.00'}
- **Worst Trade:** {safe_currency(min(t.get('pnl', 0) for t in completed_trades)) if completed_trades else '$0.00'}"""

def format_strategy_details(config: dict) -> str:
    """Format strategy configuration details"""
    entry_rules = config.get('entry_rules', {})
    exit_rules = config.get('exit_rules', [])
    
    details = f"""### 📋 Strategy: {config.get('name', 'Unknown')}
**Description:** {config.get('description', 'N/A')}

#### Entry Criteria:
- **Target Delta:** {entry_rules.get('delta_target', 'N/A')}
- **Days to Expiration:** {entry_rules.get('dte', 'N/A')}
- **Min Volume:** {entry_rules.get('volume_min', 'N/A')}
- **Min Open Interest:** {entry_rules.get('open_interest_min', 'N/A')}

#### Exit Rules:"""
    
    for rule in exit_rules:
        if rule.get('condition') == 'profit_target':
            details += f"\n- **Profit Target:** {rule.get('target_percent', 'N/A')}%"
        elif rule.get('condition') == 'stop_loss':
            details += f"\n- **Stop Loss:** {rule.get('stop_percent', 'N/A')}%"
        elif rule.get('condition') == 'time_stop':
            details += f"\n- **Time Stop:** {rule.get('max_days', 'N/A')} days"
    
    return details

def filter_audit_log(audit_log: str, key_events_only: bool = True) -> str:
    """Filter audit log to show only key events"""
    if not key_events_only:
        return audit_log
    
    key_patterns = [
        '✅ AUDIT: Executing trade',
        '🔍 AUDIT: Exiting position',
        '💰 AUDIT: Initial Capital',
        '📊 AUDIT: Final Results',
        '✅ AUDIT: Strategy:',
        '🎯 AUDIT: Profit target hit',
        '🛑 AUDIT: Stop loss hit'
    ]
    
    filtered_lines = []
    for line in audit_log.split('\n'):
        if any(pattern in line for pattern in key_patterns):
            filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

# ============================================================================
# GRADIO INTERFACE
# ============================================================================

def create_auditable_interface():
    """Create the main Gradio interface"""
    ai_assistant = AIAssistant()
    
    with gr.Blocks(title="OptionsLab - Auditable Backtesting", theme=gr.themes.Soft()) as app:
        # Header
        gr.Markdown("""
        # 🎯 OptionsLab - Auditable Backtesting System
        
        **Trustworthy, traceable options backtesting with full data flow auditing.**
        """)
        
        # State management
        current_backtest_data = gr.State(None)
        
        with gr.Tabs():
            # Backtest Tab
            create_backtest_tab(current_backtest_data)
            
            # Log Management Tab
            create_log_management_tab()
            
            # AI Assistant Tab
            create_ai_assistant_tab(ai_assistant, current_backtest_data)
    
    return app

def create_backtest_tab(current_backtest_data):
    """Create the backtest configuration and results tab"""
    with gr.TabItem("🚀 Run Backtest"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📊 Configuration")
                
                # Data file selection
                data_files = get_available_data_files()
                data_file_dropdown = gr.Dropdown(
                    choices=data_files,
                    label="📁 Select Data File",
                    value=data_files[0][1] if data_files else None
                )
                
                # Strategy selection
                strategies = get_available_strategies()
                strategy_dropdown = gr.Dropdown(
                    choices=strategies,
                    label="📋 Select Strategy",
                    value=strategies[0][1] if strategies else None
                )
                
                # Date inputs
                start_date = gr.Textbox(
                    label="📅 Start Date",
                    value="2022-01-01",
                    placeholder="YYYY-MM-DD"
                )
                
                end_date = gr.Textbox(
                    label="📅 End Date",
                    value="2022-12-31",
                    placeholder="YYYY-MM-DD"
                )
                
                # Capital input
                initial_capital = gr.Number(
                    label="💰 Initial Capital",
                    value=10000,
                    minimum=1000,
                    maximum=1000000,
                    step=1000
                )
                
                # Log level
                log_level = gr.Dropdown(
                    label="📝 Log Detail Level",
                    choices=[
                        ("Summary - Just results and trades", "summary"),
                        ("Standard - Key events only", "standard"),
                        ("Detailed - Full audit log", "detailed")
                    ],
                    value="summary"
                )
                
                # Run button
                run_btn = gr.Button("🚀 Run Backtest", variant="primary", size="lg")
            
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results")
                
                # Summary
                summary_output = gr.Markdown(
                    value="**Results will appear here after running a backtest.**"
                )
                
                # Trade details
                with gr.Row():
                    gr.Markdown("### 📈 Trade Details")
                    export_btn = gr.Button("📥 Export to CSV", size="sm", variant="secondary")
                
                trades_table = gr.DataFrame(
                    headers=["ID", "Type", "Entry Date", "Exit Date", "Strike", "P&L $", "P&L %", "Exit Reason"],
                    wrap=True
                )
                
                # Hidden CSV path state
                csv_path = gr.State()
                csv_output = gr.File(visible=False, label="Download Trade Log CSV")
                
                # Audit log (collapsible)
                with gr.Accordion("🔍 Audit Log", open=False):
                    audit_log_output = gr.Textbox(
                        label="Detailed Audit Trail",
                        lines=20,
                        max_lines=50,
                        show_copy_button=True
                    )
        
        # Event handlers
        def on_run_backtest(data_file, strategy_file, start_date, end_date, initial_capital, log_level):
            """Handle backtest execution"""
            summary, trades_df, audit_log, csv_path = run_auditable_backtest_gradio(
                data_file, strategy_file, start_date, end_date, initial_capital, log_level
            )
            
            # Extract backtest data for AI
            backtest_data = None
            if csv_path and os.path.exists(csv_path):
                json_path = Path(csv_path).with_suffix('.json')
                if json_path.exists():
                    with open(json_path, 'r') as f:
                        full_data = json.load(f)
                        backtest_data = {
                            'trades': full_data.get('trades', []),
                            'metadata': full_data.get('metadata', {}),
                            'json_path': str(json_path)
                        }
            
            return summary, trades_df, audit_log, csv_path, backtest_data
        
        def export_trades_to_csv(csv_path):
            """Export trades to CSV file"""
            if csv_path and os.path.exists(csv_path):
                return csv_path
            return None
        
        # Connect events
        run_btn.click(
            fn=on_run_backtest,
            inputs=[data_file_dropdown, strategy_dropdown, start_date, end_date, initial_capital, log_level],
            outputs=[summary_output, trades_table, audit_log_output, csv_path, current_backtest_data]
        )
        
        export_btn.click(
            fn=export_trades_to_csv,
            inputs=[csv_path],
            outputs=[csv_output]
        )

def create_log_management_tab():
    """Create the trade log management tab"""
    with gr.TabItem("📁 Log Management"):
        gr.Markdown("### 🗂️ Trade Log Management")
        
        with gr.Row():
            with gr.Column():
                refresh_btn = gr.Button("🔄 Refresh Log List", size="sm")
                
                log_dropdown = gr.Dropdown(
                    label="📋 Select Trade Log",
                    choices=[],
                    info="Choose a log to view or manage"
                )
                
                with gr.Row():
                    view_btn = gr.Button("👁️ View Details", variant="primary")
                    download_btn = gr.Button("📥 Download", variant="secondary")
                    delete_btn = gr.Button("🗑️ Delete", variant="stop")
            
            with gr.Column():
                log_details = gr.Markdown("### 📊 Log Details\nSelect a log to view details...")
                log_trades_table = gr.DataFrame(
                    headers=["Trade #", "Type", "Entry", "Exit", "P&L", "Return"],
                    wrap=True
                )
        
        # Event handlers
        def refresh_logs():
            """Refresh the list of available logs"""
            logs = get_available_backtests()
            return gr.update(choices=logs)
        
        def view_log_details(selected_log):
            """View details of selected log"""
            if not selected_log:
                return "No log selected", pd.DataFrame()
            
            try:
                with open(selected_log, 'r') as f:
                    data = json.load(f)
                
                metadata = data.get('metadata', {})
                trades = data.get('trades', [])
                
                # Create summary
                summary = f"""### 📊 {metadata.get('memorable_name', 'Unknown')}
**Strategy:** {metadata.get('strategy', 'N/A')}
**Date Range:** {metadata.get('start_date', 'N/A')} to {metadata.get('end_date', 'N/A')}
**Total Return:** {safe_percentage(metadata.get('total_return', 0) * 100, 2)}
**Win Rate:** {safe_percentage(metadata.get('win_rate', 0))}
**Total Trades:** {metadata.get('total_trades', 0)}"""
                
                # Create trades table
                trades_df = format_trades_dataframe(trades)
                
                return summary, trades_df
            except Exception as e:
                return f"Error loading log: {str(e)}", pd.DataFrame()
        
        # Connect events
        refresh_btn.click(fn=refresh_logs, outputs=[log_dropdown])
        view_btn.click(
            fn=view_log_details,
            inputs=[log_dropdown],
            outputs=[log_details, log_trades_table]
        )

def create_ai_assistant_tab(ai_assistant, current_backtest_data):
    """Create the AI assistant tab"""
    with gr.TabItem("🤖 AI Assistant"):
        gr.Markdown("### 🧠 AI Trading Assistant")
        
        with gr.Row():
            with gr.Column(scale=1):
                # API Key management
                gr.Markdown("### 🔐 Configuration")
                
                api_key_input = gr.Textbox(
                    label="Gemini API Key",
                    type="password",
                    placeholder="Enter API key or leave blank to use .env"
                )
                
                save_key_btn = gr.Button("💾 Update API Key", size="sm")
                api_status = gr.Markdown("Checking API status...")
                
                # Backtest selection
                gr.Markdown("### 📊 Backtest Analysis")
                
                backtest_dropdown = gr.Dropdown(
                    label="Select Backtest",
                    choices=[],
                    info="Auto-selects most recent if none chosen"
                )
                
                refresh_backtests_btn = gr.Button("🔄", size="sm")
                
                # Analysis button
                analyze_btn = gr.Button("🎯 Analyze Backtest", variant="primary", size="lg")
            
            with gr.Column(scale=2):
                gr.Markdown("### 💬 AI Chat")
                
                chatbot = gr.Chatbot(
                    height=500,
                    label="AI Trading Assistant",
                    type="messages",
                    value=[]
                )
                
                msg_input = gr.Textbox(
                    label="Your Message",
                    placeholder="Ask about trades, strategies, or market analysis...",
                    lines=2
                )
                
                with gr.Row():
                    send_btn = gr.Button("📤 Send", variant="primary")
                    clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
        
        # Event handlers
        def check_api_status():
            """Check if AI is configured"""
            if ai_assistant.is_configured():
                return "✅ API Configured and Ready"
            return "❌ API Not Configured - Enter API key or check .env file"
        
        def update_api_key(api_key):
            """Update API key"""
            if not api_key:
                ai_assistant._load_api_key_from_env()
            else:
                ai_assistant.set_api_key(api_key)
            
            if ai_assistant.is_configured():
                return "✅ API Key Updated Successfully"
            return "❌ Failed to Configure API"
        
        def refresh_backtests():
            """Refresh backtest list"""
            backtests = get_available_backtests()
            return gr.update(choices=backtests)
        
        def analyze_backtest(selected_backtest, history):
            """Analyze selected backtest"""
            if history is None:
                history = []
            
            if not ai_assistant.is_configured():
                history.append({"role": "system", "content": "❌ AI not configured. Please set API key."})
                return history
            
            # Get backtest path
            backtest_path = selected_backtest
            if not backtest_path:
                recent_path, _ = get_most_recent_backtest()
                backtest_path = recent_path
            
            if not backtest_path:
                history.append({"role": "system", "content": "No backtest data available."})
                return history
            
            # Load and analyze
            try:
                with open(backtest_path, 'r') as f:
                    data = json.load(f)
                
                metadata = data.get('metadata', {})
                trades = data.get('trades', [])
                
                history.append({"role": "user", "content": "Generate a comprehensive analysis report"})
                
                analysis = ai_assistant.analyze_trades(
                    trades,
                    metadata.get('strategy_config'),
                    metadata.get('implementation_metrics'),
                    metadata,
                    yaml.dump(metadata.get('strategy_config', {}), default_flow_style=False)
                )
                
                history.append({"role": "assistant", "content": analysis})
                return history
            except Exception as e:
                history.append({"role": "system", "content": f"❌ Error: {str(e)}"})
                return history
        
        def chat_with_ai(message, history):
            """Chat with AI assistant"""
            if history is None:
                history = []
            
            if not message:
                return history
            
            history.append({"role": "user", "content": message})
            response = ai_assistant.chat(message)
            history.append({"role": "assistant", "content": response})
            
            return history, ""
        
        # Connect events
        # Initialize on tab load
        api_status.value = check_api_status()
        backtest_dropdown.choices = get_available_backtests()
        
        save_key_btn.click(
            fn=update_api_key,
            inputs=[api_key_input],
            outputs=[api_status]
        )
        
        refresh_backtests_btn.click(
            fn=refresh_backtests,
            outputs=[backtest_dropdown]
        )
        
        analyze_btn.click(
            fn=analyze_backtest,
            inputs=[backtest_dropdown, chatbot],
            outputs=[chatbot]
        )
        
        msg_input.submit(
            fn=chat_with_ai,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        send_btn.click(
            fn=chat_with_ai,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        clear_btn.click(
            lambda: ([], ""),
            outputs=[chatbot, msg_input]
        )

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = create_auditable_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        debug=False,
        inbrowser=False
    )