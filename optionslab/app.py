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
import uuid
from typing import List, Dict, Optional, Tuple
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Import our backtest engine and modules
from .backtest_engine import run_auditable_backtest
from .option_selector import find_suitable_options, calculate_position_size
from .data_loader import load_strategy_config
from .backtest_metrics import calculate_compliance_scorecard

# Import visualization and AI modules
from .visualization import (
    plot_pnl_curve,
    plot_trade_markers,
    plot_greeks_evolution,
    plot_win_loss_distribution,
    plot_strategy_heatmap,
    create_summary_dashboard,
    plot_delta_histogram,
    plot_dte_histogram,
    plot_compliance_scorecard,
    plot_option_coverage_heatmap,
    plot_delta_coverage_time_series,
    plot_dte_coverage_time_series,
    plot_exit_reason_distribution,
    plot_exit_efficiency_heatmap,
    plot_technical_indicators_dashboard
)
from .ai_openai import get_openai_assistant

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
    
    # Check parent directory for the main strategy
    simple_strategy = Path(__file__).parent.parent / "simple_test_strategy.yaml"
    if simple_strategy.exists():
        strategies.append(("🎯 Simple Long Call Strategy", str(simple_strategy)))
    
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
                   start_date: str, end_date: str, strategy_config: dict = None,
                   strategy_file_path: str = None, audit_log: str = None) -> tuple[str, str, str]:
    """Save trade log to permanent storage using comprehensive CSV format"""
    from .csv_enhanced import save_comprehensive_csv
    
    # Get backtest ID from results or generate new one
    backtest_id = results.get('backtest_id', str(uuid.uuid4()))
    
    memorable_name = generate_memorable_name()
    results['memorable_name'] = memorable_name
    results['strategy'] = strategy_name
    results['start_date'] = start_date
    results['end_date'] = end_date
    
    # Load strategy config if not provided
    if strategy_config is None and strategy_file_path:
        try:
            with open(strategy_file_path, 'r') as f:
                strategy_config = yaml.safe_load(f)
        except:
            strategy_config = {}
    
    # Save comprehensive CSV
    csv_path = save_comprehensive_csv(
        backtest_id=backtest_id,
        trades_df=trades_df,
        results=results,
        strategy_config=strategy_config or {},
        strategy_file_path=strategy_file_path or 'Unknown',
        audit_log=audit_log
    )
    
    # Generate and save plot
    plot_path = csv_path.replace('.csv', '_dashboard.png')
    if not trades_df.empty:
        try:
            # Convert to list for visualization
            trades_list = trades_df.to_dict('records')
            dashboard_plot = create_summary_dashboard(trades_list, results.get('initial_capital', 10000))
            if dashboard_plot:
                dashboard_plot.savefig(str(plot_path), dpi=150, bbox_inches='tight')
        except Exception as e:
            print(f"Warning: Could not generate plot: {e}")
    
    # Update index with minimal metadata for UI
    update_trade_log_index(csv_path, {
        'path': csv_path,
        'memorable_name': memorable_name,
        'strategy': strategy_name,
        'backtest_date': datetime.now().isoformat(),
        'total_return': results.get('total_return', 0),
        'total_trades': len(trades_df)
    })
    
    return str(csv_path), str(csv_path), memorable_name  # Return CSV path twice for compatibility

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
        csv_path = Path(log_path)
        # Handle both .csv extension and any other extension
        if not csv_path.suffix == '.csv':
            csv_path = csv_path.with_suffix('.csv')
        
        plot_path = Path(str(csv_path).replace('.csv', '_dashboard.png'))
        
        # Delete files
        if csv_path.exists():
            csv_path.unlink()
        if plot_path.exists():
            plot_path.unlink()
        
        # Update index
        logs_dir = get_trade_logs_dir()
        index_file = logs_dir / "index.json"
        
        if index_file.exists():
            with open(index_file, 'r') as f:
                index_data = json.load(f)
            
            # Remove from index (match by path)
            index_data['logs'] = [log for log in index_data.get('logs', []) 
                                 if log['path'] != str(csv_path)]
            
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
            
            # Get compliance scorecard
            compliance_scorecard = results.get('compliance_scorecard', {})
            
            # Create summary
            summary = f"""
## 📊 Backtest Results

### Overall Performance
- **Final Value:** ${results['final_value']:,.2f}
- **Total Return:** {results['total_return']:.2%}
- **Initial Capital:** ${initial_capital:,.2f}
- **Total Trades:** {len(completed_trades)}
- **Win Rate:** {win_rate:.1f}%

### 📋 Compliance Scorecard
- **Overall Compliance:** {compliance_scorecard.get('overall_score', 0):.1f}%
- **Delta Compliance:** {compliance_scorecard.get('delta_compliance', 0):.1f}%
- **DTE Compliance:** {compliance_scorecard.get('dte_compliance', 0):.1f}%
- **Fully Compliant Trades:** {compliance_scorecard.get('compliant_trades', 0)}/{compliance_scorecard.get('total_trades', 0)}
"""
            
            # Save results
            if results['trades']:
                full_trades_df = pd.DataFrame(results['trades'])
                results['initial_capital'] = initial_capital
                
                strategy_name = Path(strategy_file).stem.replace('_', '-')
                perm_csv_path, perm_json_path, memorable_name = save_trade_log(
                    full_trades_df, results, strategy_name, start_date, end_date,
                    strategy_file_path=strategy_file, audit_log=audit_log
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
                                ("Summary Dashboard", "dashboard"),
                                ("Delta Histogram", "delta_histogram"),
                                ("DTE Histogram", "dte_histogram"),
                                ("Compliance Scorecard", "compliance_scorecard"),
                                ("📍 Option Coverage Heatmap", "coverage_heatmap"),
                                ("📈 Delta Coverage Timeline", "delta_timeline"),
                                ("📅 DTE Coverage Timeline", "dte_timeline"),
                                ("🎯 Exit Reason Distribution", "exit_distribution"),
                                ("🔥 Exit Efficiency Heatmap", "exit_efficiency")
                            ],
                            value="pnl_curve"
                        )
                        generate_chart_btn = gr.Button("📊 Generate", variant="primary")
                        
                    with gr.Column(scale=3):
                        main_chart = gr.Plot(label="Visualization")
            
            # AI Assistant Tab
            with gr.TabItem("🤖 AI Assistant", id=2):
                # Get the singleton OpenAI assistant (will be updated when model changes)
                ai_assistant = get_openai_assistant()
                
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 🤖 OpenAI Assistant")
                        
                        # Connection status
                        provider_status = gr.Markdown("")
                        
                        # Check status button
                        check_status_btn = gr.Button("🔄 Check Connection", size="sm")
                        
                        # API Key Management Section
                        with gr.Accordion("🔑 API Key Management", open=False):
                            api_key_input = gr.Textbox(
                                label="OpenAI API Key",
                                placeholder="sk-...",
                                type="password",
                                interactive=True
                            )
                            
                            with gr.Row():
                                save_key_btn = gr.Button("💾 Save Key", size="sm", variant="primary")
                                test_key_btn = gr.Button("🧪 Test Key", size="sm")
                                delete_key_btn = gr.Button("🗑️ Delete Key", size="sm", variant="stop")
                            
                            key_status = gr.Markdown("")
                        
                        # Model Selection Section
                        with gr.Accordion("🧠 Model Selection", open=False):
                            model_dropdown = gr.Dropdown(
                                choices=[
                                    ("gpt-4o-mini - Fast and cost-effective (recommended)", "gpt-4o-mini"),
                                    ("gpt-4o - Most capable model, higher cost", "gpt-4o"),
                                    ("gpt-4-turbo - Balanced performance and cost", "gpt-4-turbo"),
                                    ("gpt-3.5-turbo - Fastest and most economical", "gpt-3.5-turbo")
                                ],
                                value="gpt-4o-mini",
                                label="Select AI Model",
                                interactive=True
                            )
                            
                            change_model_btn = gr.Button("🔄 Change Model", size="sm", variant="secondary")
                            current_model_display = gr.Markdown("**Current model:** gpt-4o-mini")
                        
                        start_chat_btn = gr.Button("🤖 Start AI Chat", variant="primary", size="lg")
                        
                        # Preset Analysis Buttons
                        gr.Markdown("### 📊 Quick Analysis")
                        
                        with gr.Row():
                            strategy_btn = gr.Button("🎯 Strategy Adherence", size="sm", variant="secondary")
                            performance_btn = gr.Button("📈 Performance Analysis", size="sm", variant="secondary")
                        
                        with gr.Row():
                            patterns_btn = gr.Button("🔍 Trade Patterns", size="sm", variant="secondary")
                            optimize_btn = gr.Button("⚡ Optimization", size="sm", variant="secondary")
                        
                        with gr.Row():
                            risk_btn = gr.Button("⚠️ Risk Assessment", size="sm", variant="secondary")
                            code_btn = gr.Button("💻 Code Review", size="sm", variant="secondary")
            
                    with gr.Column(scale=2):
                        gr.Markdown("### 💬 Chat")
                        chatbot = gr.Chatbot(
                            height=500, 
                            type="messages",
                            show_label=False,
                            elem_id="chatbot"
                        )
                        
                        with gr.Row():
                            msg_input = gr.Textbox(
                                label="Message",
                                placeholder="Ask about performance, risk metrics, trade patterns...",
                                lines=2,
                                scale=4
                            )
                            send_btn = gr.Button("📤 Send", variant="primary", scale=1)
            
            # AI Visualization Analysis Tab
            with gr.TabItem("🔬 AI Viz Analysis", id=3):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 🎨 Visualization Selection")
                        
                        viz_chart_type = gr.Dropdown(
                            choices=[
                                ("P&L Curve", "pnl_curve"),
                                ("Trade Markers", "trade_markers"),
                                ("Win/Loss Distribution", "win_loss"),
                                ("Strategy Heatmap", "heatmap"),
                                ("Summary Dashboard", "dashboard"),
                                ("Delta Histogram", "delta_histogram"),
                                ("DTE Histogram", "dte_histogram"),
                                ("Compliance Scorecard", "compliance_scorecard"),
                                ("Option Coverage Heatmap", "coverage_heatmap"),
                                ("Delta Timeline", "delta_timeline"),
                                ("DTE Timeline", "dte_timeline"),
                                ("Exit Distribution", "exit_distribution"),
                                ("Exit Efficiency", "exit_efficiency"),
                                ("Greeks Evolution", "greeks_evolution"),
                                ("Technical Indicators", "technical_indicators")
                            ],
                            label="Select Visualization Type",
                            value="pnl_curve"
                        )
                        
                        viz_issue_description = gr.Textbox(
                            label="Describe the Issue",
                            placeholder="e.g., Y-axis scaling is wrong, missing data points, calculation errors...",
                            lines=3
                        )
                        
                        analyze_viz_btn = gr.Button("🔍 Analyze Visualization", variant="primary")
                        
                        gr.Markdown("### 📊 Current Visualization")
                        current_viz_plot = gr.Plot(label="Current Plot")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("### 🤖 AI Analysis & Suggestions")
                        viz_analysis_output = gr.Markdown(
                            value="Select a visualization and click 'Analyze' to get AI suggestions for improvements."
                        )
                        
                        gr.Markdown("### 🛠️ Suggested Code")
                        suggested_code = gr.Code(
                            label="AI Suggested Code",
                            language="python",
                            interactive=False
                        )
                        
                        apply_suggestion_btn = gr.Button("✨ Apply Suggestion", variant="secondary")
                        
                        gr.Markdown("### 📈 Improved Visualization")
                        improved_viz_plot = gr.Plot(label="Improved Plot")
            
            # Log Manager Tab
            with gr.TabItem("📁 Log Manager", id=4):
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
                from .csv_enhanced import load_comprehensive_csv
                
                # Load from CSV file
                csv_data = load_comprehensive_csv(selected_path)
                
                metadata = csv_data.get('metadata', {})
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
                # Add CSV path to metadata for AI access
                metadata['csv_path'] = selected_path
                
                # Convert to format expected by existing code
                data = {
                    'metadata': metadata,
                    'trades': csv_data.get('trades', pd.DataFrame()).to_dict('records') if not csv_data.get('trades', pd.DataFrame()).empty else []
                }
                
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
                elif chart_type == "delta_histogram":
                    return plot_delta_histogram(trades)
                elif chart_type == "dte_histogram":
                    return plot_dte_histogram(trades)
                elif chart_type == "compliance_scorecard":
                    # Calculate compliance scorecard from trades
                    from .backtest_metrics import calculate_compliance_scorecard
                    compliance_data = calculate_compliance_scorecard(trades)
                    return plot_compliance_scorecard(compliance_data)
                elif chart_type == "coverage_heatmap":
                    return plot_option_coverage_heatmap(trades)
                elif chart_type == "delta_timeline":
                    return plot_delta_coverage_time_series(trades)
                elif chart_type == "dte_timeline":
                    return plot_dte_coverage_time_series(trades)
                elif chart_type == "exit_distribution":
                    return plot_exit_reason_distribution(trades)
                elif chart_type == "exit_efficiency":
                    return plot_exit_efficiency_heatmap(trades)
            except Exception as e:
                print(f"Visualization error: {e}")
                import traceback
                traceback.print_exc()
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
        
        # OpenAI status check
        def check_openai_status():
            """Check OpenAI connection status"""
            if ai_assistant.is_configured():
                return "✅ OpenAI connected"
            else:
                # Try to initialize
                if ai_assistant.initialize():
                    return "✅ OpenAI connected"
                else:
                    return "❌ OpenAI not configured. Please set OPENAI_API_KEY"
        
        # Initial status check
        provider_status.value = check_openai_status()
        
        check_status_btn.click(
            fn=check_openai_status,
            outputs=[provider_status]
        )
        
        # API Key Management Handlers
        def save_api_key(api_key):
            """Save API key and test connection"""
            if not api_key or not api_key.strip():
                return "❌ Please enter an API key", check_openai_status()
            
            # Test the key first
            if ai_assistant.test_api_key(api_key):
                # Save and initialize
                if ai_assistant.save_api_key(api_key):
                    return "✅ API key saved and verified!", check_openai_status()
                else:
                    return "❌ Failed to save API key", check_openai_status()
            else:
                return "❌ Invalid API key. Please check and try again.", check_openai_status()
        
        def test_api_key(api_key):
            """Test API key without saving"""
            if not api_key or not api_key.strip():
                return "❌ Please enter an API key"
            
            if ai_assistant.test_api_key(api_key):
                return "✅ API key is valid!"
            else:
                return "❌ Invalid API key. Please check and try again."
        
        def delete_api_key():
            """Delete stored API key"""
            if ai_assistant.delete_api_key():
                return "✅ API key deleted", check_openai_status(), ""
            else:
                return "❌ Failed to delete API key", check_openai_status(), ""
        
        save_key_btn.click(
            fn=save_api_key,
            inputs=[api_key_input],
            outputs=[key_status, provider_status]
        )
        
        test_key_btn.click(
            fn=test_api_key,
            inputs=[api_key_input],
            outputs=[key_status]
        )
        
        delete_key_btn.click(
            fn=delete_api_key,
            outputs=[key_status, provider_status, api_key_input]
        )
        
        def start_ai_chat(backtest_data):
            """Start AI conversation with initial greeting and preset analysis options"""
            if not ai_assistant.is_configured():
                return [{"role": "assistant", "content": "❌ AI not configured. Please set API key."}]
            
            if not backtest_data:
                return [{"role": "assistant", "content": "❌ No backtest selected. Please select a backtest from the dropdown above."}]
            
            metadata = backtest_data.get('metadata', {})
            
            greeting = f"""👋 Hello! I'm your AI Trading Assistant, ready to analyze your backtest.

**Selected Backtest:** {metadata.get('memorable_name', 'Unknown')}
- Total Return: {metadata.get('total_return', 0):.1%}
- Total Trades: {metadata.get('total_trades', 0)}
- Win Rate: {metadata.get('win_rate', 0):.1%}

**📊 Quick Analysis Options:**
1. **Strategy Adherence** - Check if trades follow the strategy rules
2. **Performance Analysis** - Deep dive into returns, risk metrics, and patterns
3. **Trade Pattern Analysis** - Analyze winning vs losing trade characteristics
4. **Risk Assessment** - Evaluate drawdowns, volatility, and risk management
5. **Optimization Suggestions** - Find parameter improvements
6. **Code Review** - Analyze strategy implementation and suggest fixes
7. **Custom Analysis** - Ask me anything specific about your backtest

**💡 I have access to:**
- Complete trade-by-trade data with Greeks and IV
- Strategy configuration files
- Historical market data
- Documentation and guides
- Previous backtest results
- **READ-ONLY codebase access** (Python files, configs)

What would you like to explore?"""
            
            return [{"role": "assistant", "content": greeting}]
        
        def chat_with_ai(message, chat_history, backtest_data):
            """Handle chat messages and maintain conversation"""
            print(f"[DEBUG] Chat request received: {message[:50]}...")
            
            if not ai_assistant.is_configured():
                chat_history.append({"role": "user", "content": message})
                chat_history.append({"role": "assistant", "content": "❌ OpenAI not connected. Please check API key."})
                return chat_history, ""
            
            if not backtest_data:
                chat_history.append({"role": "user", "content": message})
                chat_history.append({"role": "assistant", "content": "❌ No backtest selected. Please select a backtest first."})
                return chat_history, ""
            
            # Add user message to history
            chat_history.append({"role": "user", "content": message})
            
            try:
                print("[DEBUG] Sending request to OpenAI...")
                
                # Add a processing message
                processing_msg = {"role": "assistant", "content": "🤔 Processing your request..."}
                chat_history.append(processing_msg)
                
                # Let the LLM handle all queries naturally
                response = ai_assistant.chat(message, backtest_data)
                
                print(f"[DEBUG] Response received: {type(response)}, length: {len(str(response)) if response else 0}")
                print(f"[DEBUG] Response preview: {str(response)[:200] if response else 'None'}...")
                
                # Validate response
                if response is None:
                    response = "❌ No response received from OpenAI. Please check your API key."
                elif not isinstance(response, str):
                    response = str(response)
                elif response.strip() == "":
                    response = "❌ Empty response received. Please try again."
                
                # Remove processing message and add actual response
                chat_history = chat_history[:-1]  # Remove processing message
                chat_history.append({"role": "assistant", "content": response})
                
            except Exception as e:
                print(f"[ERROR] Exception in chat_with_ai: {str(e)}")
                import traceback
                traceback.print_exc()
                
                # Remove processing message if it exists
                if chat_history and chat_history[-1]["content"] == "🤔 Processing your request...":
                    chat_history = chat_history[:-1]
                
                error_msg = f"❌ Error: {str(e)}\n\nPlease check:\n1. OPENAI_API_KEY is set\n2. API key is valid\n3. You have API credits"
                chat_history.append({"role": "assistant", "content": error_msg})
            
            print(f"[DEBUG] Returning {len(chat_history)} messages")
            # Return updated history and clear input
            return chat_history, ""
        
        # AI Visualization Analysis Handlers
        def analyze_visualization(chart_type, issue_description, backtest_data):
            """Analyze a visualization and get AI suggestions"""
            if not backtest_data:
                return (
                    "❌ No backtest selected. Please select a backtest first.",
                    "",
                    None,
                    None
                )
            
            try:
                from .visualization_utils import plotly_to_base64, prepare_visualization_context, create_ai_visualization_prompt
                
                # Generate the current visualization
                trades = backtest_data.get('trades', [])
                metadata = backtest_data.get('metadata', {})
                
                # Get the appropriate plot function
                plot_funcs = {
                    "pnl_curve": lambda: plot_pnl_curve(trades, metadata.get('initial_capital', 10000)),
                    "trade_markers": lambda: plot_trade_markers(trades),
                    "win_loss": lambda: plot_win_loss_distribution(trades),
                    "heatmap": lambda: plot_strategy_heatmap(trades),
                    "dashboard": lambda: create_summary_dashboard(trades, metadata.get('initial_capital', 10000)),
                    "delta_histogram": lambda: plot_delta_histogram(trades),
                    "dte_histogram": lambda: plot_dte_histogram(trades),
                    "compliance_scorecard": lambda: plot_compliance_scorecard(calculate_compliance_scorecard(trades)),
                    "coverage_heatmap": lambda: plot_option_coverage_heatmap(trades),
                    "delta_timeline": lambda: plot_delta_coverage_time_series(trades),
                    "dte_timeline": lambda: plot_dte_coverage_time_series(trades),
                    "exit_distribution": lambda: plot_exit_reason_distribution(trades),
                    "exit_efficiency": lambda: plot_exit_efficiency_heatmap(trades),
                    "greeks_evolution": lambda: plot_greeks_evolution(trades),
                    "technical_indicators": lambda: plot_technical_indicators_dashboard(trades)
                }
                
                if chart_type not in plot_funcs:
                    return "❌ Unknown chart type", "", None, None
                
                # Generate the plot
                current_plot = plot_funcs[chart_type]()
                
                # Prepare context for AI
                viz_context = prepare_visualization_context(
                    current_plot,
                    chart_type,
                    trades[:10],  # Sample trades
                    issue_description
                )
                
                # Create prompt
                prompt = create_ai_visualization_prompt(viz_context)
                
                # Convert plot to base64 for AI
                plot_image = plotly_to_base64(current_plot) if current_plot else None
                
                # Get AI analysis with vision
                ai_response = ai_assistant.chat(
                    prompt,
                    backtest_data,
                    images=[plot_image] if plot_image else None
                )
                
                # Extract code from response (looking for ```python blocks)
                import re
                code_match = re.search(r'```python\n(.*?)\n```', ai_response, re.DOTALL)
                suggested_code_text = code_match.group(1) if code_match else ""
                
                return (
                    ai_response,
                    suggested_code_text,
                    current_plot,
                    None  # Improved plot will be generated when applied
                )
                
            except Exception as e:
                import traceback
                error_msg = f"❌ Error analyzing visualization: {str(e)}\n\n{traceback.format_exc()}"
                return error_msg, "", None, None
        
        def apply_suggested_code(suggested_code, chart_type, backtest_data):
            """Apply the AI suggested code and generate improved visualization"""
            if not suggested_code or not backtest_data:
                return None
            
            try:
                # Create a safe execution environment
                trades = backtest_data.get('trades', [])
                metadata = backtest_data.get('metadata', {})
                
                # Import necessary modules for the execution context
                exec_globals = {
                    'pd': pd,
                    'np': np,
                    'go': go,
                    'px': px,
                    'make_subplots': make_subplots,
                    'datetime': datetime,
                    'trades': trades,
                    'metadata': metadata,
                    'initial_capital': metadata.get('initial_capital', 10000)
                }
                
                # Execute the suggested code
                exec(suggested_code, exec_globals)
                
                # The function should be defined in exec_globals now
                # Try to find and execute it
                for name, obj in exec_globals.items():
                    if callable(obj) and name.startswith(('plot_', 'create_')):
                        # Found the function, call it
                        if 'initial_capital' in str(suggested_code):
                            result = obj(trades, metadata.get('initial_capital', 10000))
                        else:
                            result = obj(trades)
                        return result
                
                return None
                
            except Exception as e:
                print(f"Error applying suggested code: {e}")
                return None
        
        # Connect the visualization analysis handlers
        analyze_viz_btn.click(
            fn=analyze_visualization,
            inputs=[viz_chart_type, viz_issue_description, selected_backtest_data],
            outputs=[viz_analysis_output, suggested_code, current_viz_plot, improved_viz_plot]
        )
        
        apply_suggestion_btn.click(
            fn=apply_suggested_code,
            inputs=[suggested_code, viz_chart_type, selected_backtest_data],
            outputs=[improved_viz_plot]
        )
        
        start_chat_btn.click(
            fn=start_ai_chat,
            inputs=[selected_backtest_data],
            outputs=[chatbot]
        )
        
        # Connect the send button for continuous conversation
        send_btn.click(
            fn=chat_with_ai,
            inputs=[msg_input, chatbot, selected_backtest_data],
            outputs=[chatbot, msg_input]
        )
        
        # Also handle Enter key press
        msg_input.submit(
            fn=chat_with_ai,
            inputs=[msg_input, chatbot, selected_backtest_data],
            outputs=[chatbot, msg_input]
        )
        
        # Preset Analysis Button Handlers
        def run_strategy_analysis(backtest_data, chat_history):
            """Run strategy adherence analysis"""
            if not backtest_data:
                chat_history.append({"role": "assistant", "content": "❌ No backtest selected. Please select a backtest first."})
                return chat_history
            
            chat_history.append({"role": "user", "content": "Analyze strategy adherence"})
            current_assistant = get_openai_assistant()
            response = current_assistant.analyze_strategy_adherence(backtest_data)
            chat_history.append({"role": "assistant", "content": response})
            return chat_history
        
        def run_performance_analysis(backtest_data, chat_history):
            """Run performance analysis"""
            if not backtest_data:
                chat_history.append({"role": "user", "content": "❌ No backtest selected. Please select a backtest first."})
                return chat_history
            
            chat_history.append({"role": "user", "content": "Analyze performance metrics"})
            current_assistant = get_openai_assistant()
            response = current_assistant.analyze_performance(backtest_data)
            chat_history.append({"role": "assistant", "content": response})
            return chat_history
        
        def run_pattern_analysis(backtest_data, chat_history):
            """Run trade pattern analysis"""
            if not backtest_data:
                chat_history.append({"role": "assistant", "content": "❌ No backtest selected. Please select a backtest first."})
                return chat_history
            
            chat_history.append({"role": "user", "content": "Analyze trade patterns"})
            current_assistant = get_openai_assistant()
            response = current_assistant.analyze_trade_patterns(backtest_data)
            chat_history.append({"role": "assistant", "content": response})
            return chat_history
        
        def run_optimization_analysis(backtest_data, chat_history):
            """Run optimization suggestions"""
            if not backtest_data:
                chat_history.append({"role": "assistant", "content": "❌ No backtest selected. Please select a backtest first."})
                return chat_history
            
            chat_history.append({"role": "user", "content": "Suggest optimizations"})
            current_assistant = get_openai_assistant()
            response = current_assistant.suggest_optimizations(backtest_data)
            chat_history.append({"role": "assistant", "content": response})
            return chat_history
        
        def run_risk_analysis(backtest_data, chat_history):
            """Run risk assessment"""
            if not backtest_data:
                chat_history.append({"role": "assistant", "content": "❌ No backtest selected. Please select a backtest first."})
                return chat_history
            
            chat_history.append({"role": "user", "content": "Analyze risk metrics and drawdowns"})
            current_assistant = get_openai_assistant()
            response = current_assistant.chat("Analyze risk metrics, drawdowns, and risk management effectiveness", backtest_data)
            chat_history.append({"role": "assistant", "content": response})
            return chat_history
        
        def run_code_analysis(backtest_data, chat_history):
            """Run code review"""
            if not backtest_data:
                chat_history.append({"role": "assistant", "content": "❌ No backtest selected. Please select a backtest first."})
                return chat_history
            
            chat_history.append({"role": "user", "content": "Review strategy implementation and suggest code improvements"})
            current_assistant = get_openai_assistant()
            response = current_assistant.chat("Review the strategy implementation, identify any code issues, and suggest improvements", backtest_data)
            chat_history.append({"role": "assistant", "content": response})
            return chat_history
        
        # Connect preset analysis buttons
        strategy_btn.click(
            fn=run_strategy_analysis,
            inputs=[selected_backtest_data, chatbot],
            outputs=[chatbot]
        )
        
        performance_btn.click(
            fn=run_performance_analysis,
            inputs=[selected_backtest_data, chatbot],
            outputs=[chatbot]
        )
        
        patterns_btn.click(
            fn=run_pattern_analysis,
            inputs=[selected_backtest_data, chatbot],
            outputs=[chatbot]
        )
        
        optimize_btn.click(
            fn=run_optimization_analysis,
            inputs=[selected_backtest_data, chatbot],
            outputs=[chatbot]
        )
        
        risk_btn.click(
            fn=run_risk_analysis,
            inputs=[selected_backtest_data, chatbot],
            outputs=[chatbot]
        )
        
        code_btn.click(
            fn=run_code_analysis,
            inputs=[selected_backtest_data, chatbot],
            outputs=[chatbot]
        )
        
        def change_ai_model(model_name):
            """Change the AI model"""
            try:
                # Get fresh assistant instance with new model
                new_assistant = get_openai_assistant(model_name)
                if new_assistant.is_configured():
                    return f"✅ Model changed to: {model_name}"
                else:
                    return f"❌ Failed to change model to: {model_name}"
            except Exception as e:
                return f"❌ Error changing model: {str(e)}"
        
        # Connect model change button
        change_model_btn.click(
            fn=change_ai_model,
            inputs=[model_dropdown],
            outputs=[current_model_display]
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
    import os
    port = int(os.getenv("GRADIO_SERVER_PORT", "7862"))
    app = create_simple_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
        inbrowser=False
    )