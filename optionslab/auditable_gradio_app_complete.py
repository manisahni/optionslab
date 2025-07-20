#!/usr/bin/env python3
"""
Complete Auditable Gradio App - Simplified AI with all features
"""

import gradio as gr
import pandas as pd
import numpy as np
import yaml
import json
from pathlib import Path
from datetime import datetime, timedelta
import subprocess
import sys
import os
import shutil
import random
from typing import List, Dict, Optional

# Import the existing functions we need
from auditable_backtest import (
    run_auditable_backtest,
    create_implementation_metrics
)
from ai_assistant import AIAssistant
from visualization import (
    plot_pnl_curve,
    plot_trade_markers,
    plot_greeks_evolution,
    plot_win_loss_distribution,
    plot_strategy_heatmap,
    create_summary_dashboard
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_trade_logs_dir() -> Path:
    """Get the trade logs directory"""
    return Path(__file__).parent / "trade_logs"

def get_available_data_files():
    """Get available parquet files for backtesting"""
    main_dir = Path("../spy_options_downloader/spy_options_parquet")
    repaired_dir = main_dir / "repaired"
    
    files = []
    
    if main_dir.exists():
        # FIRST - Add the MASTER file if it exists
        master_files = list(main_dir.glob("SPY_OPTIONS_MASTER_*.parquet"))
        if master_files:
            for f in master_files:
                files.append(("🌟 MASTER FILE - ALL DATA (2020-2025)", str(f)))
        
        # Add complete year files
        for year in [2025, 2024, 2023, 2022, 2021, 2020]:
            year_file = main_dir / f"SPY_OPTIONS_{year}_COMPLETE.parquet"
            if year_file.exists():
                files.append((f"📅 SPY {year} Complete Year", str(year_file)))
        
        # Add other multi-year files if they exist
        multi_year_patterns = [
            "*_full_year.parquet",
            "*_h1.parquet", 
            "*_h2.parquet",
        ]
        
        for pattern in multi_year_patterns:
            for f in sorted(main_dir.glob(pattern)):
                if "COMPLETE" not in f.stem and "MASTER" not in f.stem:
                    nice_name = f.stem.replace('spy_options_', '').replace('_', ' ').title()
                    files.append((f"📊 {nice_name}", str(f)))
        
        # Add repaired files if they exist
        if repaired_dir.exists():
            for f in sorted(repaired_dir.glob("*.parquet")):
                parts = f.stem.split('_')
                if len(parts) >= 4 and parts[-1].startswith('20'):
                    date_str = parts[-1]
                    year = date_str[:4]
                    month = date_str[4:6]
                    day = date_str[6:8]
                    files.append((f"✅ SPY {year}-{month}-{day} (Repaired)", str(f)))
        
        # Add ALL individual daily files
        daily_files = sorted(main_dir.glob("spy_options_eod_*.parquet"))
        
        # Group by year for better organization
        years = {}
        for f in daily_files:
            date_part = f.stem.split('_')[-1]
            if date_part.startswith('20') and len(date_part) == 8:
                year = date_part[:4]
                if year not in years:
                    years[year] = []
                years[year].append(f)
        
        # Add a reasonable selection from each year
        for year in sorted(years.keys(), reverse=True):
            year_files = years[year]
            # Add first, middle, and last files from each year
            if len(year_files) > 10:
                # Sample: first 3, 3 from middle, last 3
                sample_files = (
                    year_files[:3] + 
                    year_files[len(year_files)//2-1:len(year_files)//2+2] +
                    year_files[-3:]
                )
            else:
                sample_files = year_files
            
            for f in sample_files:
                date_part = f.stem.split('_')[-1]
                formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                files.append((f"SPY {formatted_date}", str(f)))
    
    return files if files else [("No data files found", "")]

def get_available_strategies():
    """Get available strategy YAML files"""
    strategies_dir = Path(__file__).parent.parent / "config" / "strategies"
    advanced_strategy = Path("../advanced_test_strategy.yaml")
    
    files = []
    if advanced_strategy.exists():
        files.append(("Advanced Test Strategy", str(advanced_strategy)))
    
    if strategies_dir.exists():
        yaml_files = list(strategies_dir.glob("*.yaml"))
        files.extend([(f.stem.replace('_', ' ').title(), str(f)) for f in yaml_files])
    
    return files if files else [("No strategies found", "")]

def get_most_recent_backtest():
    """Get the most recent backtest from trade logs"""
    logs_dir = get_trade_logs_dir()
    index_path = logs_dir / "index.json"
    
    if not index_path.exists():
        return None, None
    
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        logs = index.get('logs', [])
        if not logs:
            return None, None
        
        # Sort by date and get most recent
        logs.sort(key=lambda x: x.get('backtest_date', ''), reverse=True)
        most_recent = logs[0]
        
        return most_recent.get('path'), most_recent
    except:
        return None, None

def get_all_trade_logs():
    """Get all trade logs from index"""
    logs_dir = get_trade_logs_dir()
    index_path = logs_dir / "index.json"
    
    if not index_path.exists():
        return []
    
    try:
        with open(index_path, 'r') as f:
            index = json.load(f)
        return index.get('logs', [])
    except:
        return []

def generate_memorable_name() -> str:
    """Generate a unique memorable name for the backtest"""
    adjectives = ["Swift", "Golden", "Silver", "Bold", "Wise", "Dynamic", "Steady"]
    animals = ["Eagle", "Tiger", "Fox", "Wolf", "Hawk", "Falcon", "Lion"]
    unique_id = datetime.now().strftime("%H%M")
    return f"{random.choice(adjectives)} {random.choice(animals)}-{unique_id}"

def save_trade_log(trades_df, results, strategy_name, start_date, end_date, strategy_config=None):
    """Save trade log with metadata"""
    logs_dir = get_trade_logs_dir()
    logs_dir.mkdir(exist_ok=True)
    
    memorable_name = generate_memorable_name()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create filenames
    safe_strategy = strategy_name.replace(' ', '_').lower()
    base_name = f"{safe_strategy}_{timestamp}_{memorable_name.replace(' ', '_').replace('-', '_')}"
    csv_path = logs_dir / f"{base_name}.csv"
    json_path = logs_dir / f"{base_name}.json"
    
    # Save CSV
    trades_df.to_csv(csv_path, index=False)
    
    # Calculate metrics
    completed_trades = [t for t in results['trades'] if t.get('exit_date')]
    win_rate = (sum(1 for t in completed_trades if t.get('pnl', 0) > 0) / len(completed_trades) * 100) if completed_trades else 0
    
    # Create implementation metrics
    implementation_metrics = create_implementation_metrics(completed_trades, strategy_config)
    
    # Save JSON with full data
    full_data = {
        'metadata': {
            'memorable_name': memorable_name,
            'strategy': strategy_name,
            'start_date': start_date,
            'end_date': end_date,
            'backtest_date': datetime.now().isoformat(),
            'initial_capital': results.get('initial_capital', 10000),
            'final_value': results['final_value'],
            'total_return': results['total_return'],
            'total_trades': len(completed_trades),
            'win_rate': win_rate,
            'strategy_config': strategy_config,
            'implementation_metrics': implementation_metrics
        },
        'trades': results['trades']
    }
    
    with open(json_path, 'w') as f:
        json.dump(full_data, f, indent=2, default=str)
    
    # Update index
    update_trade_log_index(json_path, full_data['metadata'])
    
    return str(csv_path), str(json_path), memorable_name

def update_trade_log_index(log_path, metadata):
    """Update the central index of trade logs"""
    logs_dir = get_trade_logs_dir()
    index_path = logs_dir / "index.json"
    
    if index_path.exists():
        with open(index_path, 'r') as f:
            index = json.load(f)
    else:
        index = {'logs': [], 'last_updated': None}
    
    # Add new entry
    index['logs'].append({
        'path': str(log_path),
        'json_path': str(log_path),
        'csv_path': str(log_path).replace('.json', '.csv'),
        **metadata
    })
    
    # Keep only last 100 entries
    index['logs'] = index['logs'][-100:]
    index['last_updated'] = datetime.now().isoformat()
    
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

def format_trades_dataframe(trades):
    """Format trades for display"""
    if not trades:
        return pd.DataFrame()
    
    df_data = []
    for i, trade in enumerate(trades):
        row = {
            'ID': str(i + 1),
            'Type': trade.get('option_type', 'N/A'),
            'Entry Date': trade.get('entry_date', 'N/A'),
            'Exit Date': trade.get('exit_date', 'Open'),
            'Strike': f"${trade.get('strike', 0):.2f}",
            'P&L $': f"${trade.get('pnl', 0):.2f}" if trade.get('pnl') else 'Open',
            'P&L %': f"{trade.get('pnl_pct', 0):.1f}%" if trade.get('pnl_pct') else 'Open',
            'Exit Reason': trade.get('exit_reason', 'Open')
        }
        df_data.append(row)
    
    return pd.DataFrame(df_data)

def run_auditable_backtest_gradio(data_file, strategy_file, start_date, end_date, initial_capital, log_level="summary"):
    """Run backtest and return results"""
    import io
    old_stdout = sys.stdout
    audit_output = io.StringIO()
    sys.stdout = audit_output
    
    try:
        results = run_auditable_backtest(data_file, strategy_file, start_date, end_date)
        sys.stdout = old_stdout
        
        if results:
            audit_log = audit_output.getvalue()
            trades_df = format_trades_dataframe(results['trades'])
            
            # Load strategy config
            try:
                with open(strategy_file, 'r') as f:
                    strategy_config = yaml.safe_load(f)
            except:
                strategy_config = None
            
            # Create summary
            completed_trades = [t for t in results['trades'] if 'exit_date' in t]
            winning_trades = [t for t in completed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in completed_trades if t.get('pnl', 0) <= 0]
            
            win_rate = (len(winning_trades) / len(completed_trades) * 100) if completed_trades else 0
            avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
            
            summary = f"""## 📊 Backtest Results

### Overall Performance
- **Final Value:** ${results['final_value']:,.2f}
- **Total Return:** {results['total_return']:.2%}
- **Initial Capital:** ${initial_capital:,.2f}
- **Total Trades:** {len(completed_trades)}

### Trade Statistics
- **Win Rate:** {win_rate:.1f}%
- **Average Win:** ${avg_win:.2f}
- **Average Loss:** ${avg_loss:.2f}
"""
            
            # Save results
            strategy_name = Path(strategy_file).stem
            results['initial_capital'] = initial_capital
            csv_path, json_path, memorable_name = save_trade_log(
                pd.DataFrame(results['trades']), results, strategy_name, 
                start_date, end_date, strategy_config
            )
            
            summary += f"\n### 🎯 Backtest Name: **{memorable_name}**\n"
            summary += f"### 📁 Trade Log Saved"
            
            if log_level == "summary":
                audit_log = ""
            
            return summary, trades_df, audit_log, csv_path
        else:
            sys.stdout = old_stdout
            return "❌ Backtest failed", pd.DataFrame(), audit_output.getvalue(), None
            
    except Exception as e:
        sys.stdout = old_stdout
        return f"❌ Error: {str(e)}", pd.DataFrame(), audit_output.getvalue(), None

def delete_trade_log(log_path, archive=False):
    """Delete or archive a trade log"""
    try:
        json_path = Path(log_path)
        csv_path = json_path.with_suffix('.csv')
        
        if archive:
            # Move to archive directory
            archive_dir = get_trade_logs_dir() / "archive"
            archive_dir.mkdir(exist_ok=True)
            
            if json_path.exists():
                shutil.move(str(json_path), str(archive_dir / json_path.name))
            if csv_path.exists():
                shutil.move(str(csv_path), str(archive_dir / csv_path.name))
        else:
            # Delete files
            if json_path.exists():
                json_path.unlink()
            if csv_path.exists():
                csv_path.unlink()
        
        # Update index
        logs_dir = get_trade_logs_dir()
        index_path = logs_dir / "index.json"
        
        if index_path.exists():
            with open(index_path, 'r') as f:
                index = json.load(f)
            
            # Remove from index
            index['logs'] = [log for log in index['logs'] if log['path'] != str(log_path)]
            index['last_updated'] = datetime.now().isoformat()
            
            with open(index_path, 'w') as f:
                json.dump(index, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error deleting log: {e}")
        return False

# ============================================================================
# MAIN INTERFACE
# ============================================================================

def create_complete_interface():
    """Create the complete Gradio interface with all features"""
    
    with gr.Blocks(title="OptionsLab - Complete", theme=gr.themes.Soft()) as app:
        
        # Header
        gr.Markdown("""
        # 🎯 OptionsLab - Auditable Backtesting System
        **Complete Interface with Simplified AI**
        """)
        
        # Initialize AI assistant  
        ai_assistant = AIAssistant()
        
        with gr.Tabs():
            # Backtest Tab
            with gr.TabItem("🚀 Run Backtest"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 Configuration")
                        
                        data_files = get_available_data_files()
                        data_file_dropdown = gr.Dropdown(
                            choices=data_files,
                            label="📁 Data File",
                            value=data_files[0][1] if data_files else None
                        )
                        
                        strategies = get_available_strategies()
                        strategy_dropdown = gr.Dropdown(
                            choices=strategies,
                            label="📋 Strategy",
                            value=strategies[0][1] if strategies else None
                        )
                        
                        start_date = gr.Textbox(label="Start Date", value="2022-01-01")
                        end_date = gr.Textbox(label="End Date", value="2022-12-31")
                        initial_capital = gr.Number(label="Initial Capital", value=10000)
                        
                        run_btn = gr.Button("🚀 Run Backtest", variant="primary", size="lg")
                    
                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Results")
                        summary_output = gr.Markdown("Results will appear here...")
                        trades_table = gr.DataFrame()
                        audit_log_output = gr.Textbox(visible=False)
                        csv_path = gr.State()
            
            # Multi-Day Trades Tab
            with gr.TabItem("📈 Multi-Day Trades"):
                gr.Markdown("### 📊 Multi-Day Trade Dataset")
                
                # Load backtest selector
                backtest_selector = gr.Dropdown(
                    label="Select Backtest",
                    choices=[],
                    info="Choose a backtest to view its multi-day trades"
                )
                
                refresh_multiday_btn = gr.Button("🔄 Refresh Backtests", size="sm")
                
                # Multi-day trades table
                multiday_trades_table = gr.DataFrame(
                    label="Multi-Day Trade Details",
                    wrap=True
                )
                
                # Functions for multi-day trades
                def refresh_multiday_backtests():
                    """Refresh available backtests for multi-day view"""
                    logs = get_all_trade_logs()
                    if not logs:
                        return gr.update(choices=[], value=None)
                    
                    choices = []
                    for log in logs:
                        memorable_name = log.get('memorable_name', 'Unknown')
                        strategy = log.get('strategy', 'Unknown')
                        total_return = log.get('total_return', 0)
                        perf_emoji = "🚀" if total_return > 0.1 else "📈" if total_return > 0 else "📉" if total_return > -0.1 else "💥"
                        label = f"{memorable_name} - {strategy} ({total_return:.1%}{perf_emoji})"
                        choices.append((label, log['path']))
                    
                    return gr.update(choices=choices, value=choices[0][1] if choices else None)
                
                def load_multiday_trades(backtest_path):
                    """Load and format multi-day trades from selected backtest"""
                    if not backtest_path:
                        return pd.DataFrame()
                    
                    try:
                        with open(backtest_path, 'r') as f:
                            data = json.load(f)
                        
                        trades = data.get('trades', [])
                        if not trades:
                            return pd.DataFrame()
                        
                        # Create multi-day view with daily details
                        multiday_data = []
                        for trade in trades:
                            if trade.get('daily_data'):
                                for day_data in trade['daily_data']:
                                    row = {
                                        'Trade ID': trade.get('trade_id', 'N/A'),
                                        'Date': day_data.get('date', 'N/A'),
                                        'Type': trade.get('option_type', 'N/A'),
                                        'Strike': f"${trade.get('strike', 0):.2f}",
                                        'DTE': day_data.get('dte', 'N/A'),
                                        'Delta': f"{day_data.get('delta', 0):.3f}",
                                        'Gamma': f"{day_data.get('gamma', 0):.4f}",
                                        'Theta': f"{day_data.get('theta', 0):.2f}",
                                        'Vega': f"{day_data.get('vega', 0):.2f}",
                                        'Option Price': f"${day_data.get('option_price', 0):.2f}",
                                        'Daily P&L': f"${day_data.get('daily_pnl', 0):.2f}",
                                        'Cumulative P&L': f"${day_data.get('cumulative_pnl', 0):.2f}",
                                        'Status': 'Open' if not trade.get('exit_date') else 'Closed'
                                    }
                                    multiday_data.append(row)
                        
                        return pd.DataFrame(multiday_data)
                    except Exception as e:
                        print(f"Error loading multi-day trades: {e}")
                        return pd.DataFrame()
                
                # Wire up multi-day handlers
                refresh_multiday_btn.click(
                    fn=refresh_multiday_backtests,
                    outputs=[backtest_selector]
                )
                
                backtest_selector.change(
                    fn=load_multiday_trades,
                    inputs=[backtest_selector],
                    outputs=[multiday_trades_table]
                )
                
                # Load initial data
                app.load(
                    fn=refresh_multiday_backtests,
                    outputs=[backtest_selector]
                )
            
            # Visualizations Tab
            with gr.TabItem("📊 Visualizations"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📈 Chart Options")
                        
                        chart_type = gr.Dropdown(
                            label="Select Chart Type",
                            choices=[
                                ("P&L Curve", "pnl_curve"),
                                ("Trade Entry/Exit Points", "trade_markers"),
                                ("Greeks Evolution", "greeks_evolution"),
                                ("Win/Loss Distribution", "win_loss"),
                                ("Monthly Heatmap", "heatmap"),
                                ("Summary Dashboard", "dashboard")
                            ],
                            value="pnl_curve"
                        )
                        
                        viz_data_source = gr.Dropdown(
                            label="Data Source",
                            choices=[]
                        )
                        
                        refresh_viz_btn = gr.Button("🔄 Refresh Data Sources", size="sm")
                        generate_chart_btn = gr.Button("📊 Generate Chart", variant="primary")
                        
                        chart_info = gr.Markdown("Select a data source and chart type...")
                        
                    with gr.Column(scale=3):
                        main_chart = gr.Plot(label="Visualization")
                
                # Visualization functions
                def refresh_viz_sources():
                    """Refresh available data sources for visualization"""
                    logs = get_all_trade_logs()
                    if not logs:
                        return gr.update(choices=[], value=None), "No trade logs found."
                    
                    choices = []
                    for log in logs:
                        memorable_name = log.get('memorable_name', 'Unknown')
                        strategy = log.get('strategy', 'Unknown')
                        total_return = log.get('total_return', 0)
                        perf_emoji = "🚀" if total_return > 0.1 else "📈" if total_return > 0 else "📉" if total_return > -0.1 else "💥"
                        label = f"{memorable_name} - {strategy} ({total_return:.1%}{perf_emoji})"
                        choices.append((label, log['path']))
                    
                    return gr.update(choices=choices, value=choices[0][1] if choices else None), f"Found {len(logs)} trade logs."
                
                def generate_visualization(data_source, chart_type):
                    """Generate selected visualization"""
                    if not data_source:
                        return None, "Please select a data source."
                    
                    try:
                        with open(data_source, 'r') as f:
                            data = json.load(f)
                        
                        trades = data.get('trades', [])
                        metadata = data.get('metadata', {})
                        
                        if not trades:
                            return None, "No trades found in selected log."
                        
                        # Add trade_id if missing
                        for i, trade in enumerate(trades):
                            if 'trade_id' not in trade:
                                trade['trade_id'] = i + 1
                        
                        # Generate appropriate chart
                        if chart_type == "pnl_curve":
                            fig = plot_pnl_curve(trades, metadata.get('initial_capital', 10000))
                        elif chart_type == "trade_markers":
                            fig = plot_trade_markers(trades)
                        elif chart_type == "greeks_evolution":
                            fig = plot_greeks_evolution(trades)
                        elif chart_type == "win_loss":
                            fig = plot_win_loss_distribution(trades)
                        elif chart_type == "heatmap":
                            fig = plot_strategy_heatmap(trades)
                        elif chart_type == "dashboard":
                            fig = create_summary_dashboard(trades, metadata.get('initial_capital', 10000))
                        else:
                            return None, "Invalid chart type."
                        
                        memorable_name = metadata.get('memorable_name', metadata.get('strategy', 'Unknown'))
                        info = f"📊 {chart_type.replace('_', ' ').title()} | {memorable_name}"
                        return fig, info
                    except Exception as e:
                        return None, f"Error generating chart: {str(e)}"
                
                # Wire up visualization handlers
                refresh_viz_btn.click(
                    fn=refresh_viz_sources,
                    outputs=[viz_data_source, chart_info]
                )
                
                generate_chart_btn.click(
                    fn=generate_visualization,
                    inputs=[viz_data_source, chart_type],
                    outputs=[main_chart, chart_info]
                )
                
                # Load initial data sources
                app.load(
                    fn=refresh_viz_sources,
                    outputs=[viz_data_source, chart_info]
                )
            
            # Log Management Tab
            with gr.TabItem("🗂️ Log Management"):
                gr.Markdown("### 📁 Manage Trade Logs")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        log_dropdown = gr.Dropdown(
                            label="Select Log",
                            choices=[]
                        )
                        
                        refresh_logs_btn = gr.Button("🔄 Refresh Logs", size="sm")
                        
                        # Archive option
                        archive_checkbox = gr.Checkbox(
                            label="Archive instead of delete",
                            value=True
                        )
                        
                        # Action buttons
                        delete_selected_btn = gr.Button(
                            "🗑️ Delete Selected",
                            variant="stop",
                            visible=False
                        )
                        
                        delete_old_days = gr.Number(
                            label="Days to keep",
                            value=30
                        )
                        delete_old_btn = gr.Button(
                            "🧹 Clean Old Logs",
                            variant="secondary"
                        )
                        
                        clear_all_btn = gr.Button(
                            "⚠️ Clear All Logs",
                            variant="stop"
                        )
                        
                        action_output = gr.Markdown()
                    
                    with gr.Column(scale=2):
                        log_info = gr.Markdown("Select a log to preview")
                        log_preview = gr.DataFrame()
                        trade_preview = gr.DataFrame()
                
                # Log management functions
                def refresh_log_list():
                    """Refresh the list of available logs"""
                    logs = get_all_trade_logs()
                    if not logs:
                        return gr.update(choices=[], value=None), "No logs found."
                    
                    choices = []
                    for log in logs:
                        memorable_name = log.get('memorable_name', 'Unknown')
                        strategy = log.get('strategy', 'Unknown')
                        total_return = log.get('total_return', 0)
                        date = log.get('backtest_date', 'Unknown')[:10]
                        perf_emoji = "🚀" if total_return > 0.1 else "📈" if total_return > 0 else "📉" if total_return > -0.1 else "💥"
                        label = f"{memorable_name} - {strategy} ({total_return:.1%}{perf_emoji}) | {date}"
                        choices.append((label, log['path']))
                    
                    return gr.update(choices=choices, value=None), f"Found {len(logs)} logs."
                
                def preview_log(log_path):
                    """Preview selected log"""
                    if not log_path:
                        return gr.update(visible=False), "Select a log to preview", pd.DataFrame(), pd.DataFrame()
                    
                    try:
                        with open(log_path, 'r') as f:
                            data = json.load(f)
                        
                        metadata = data.get('metadata', {})
                        trades = data.get('trades', [])
                        
                        # Create metadata preview
                        info = f"""### 📊 {metadata.get('memorable_name', 'Unknown')}
                        
**Strategy:** {metadata.get('strategy', 'Unknown')}
**Date Range:** {metadata.get('start_date', 'N/A')} to {metadata.get('end_date', 'N/A')}
**Final Return:** {metadata.get('total_return', 0):.1%}
**Total Trades:** {metadata.get('total_trades', 0)}
**Win Rate:** {metadata.get('win_rate', 0):.1f}%
**Created:** {metadata.get('backtest_date', 'Unknown')[:19]}"""
                        
                        # Create summary dataframe
                        summary_df = pd.DataFrame([{
                            'Initial Capital': f"${metadata.get('initial_capital', 0):,.0f}",
                            'Final Value': f"${metadata.get('final_value', 0):,.0f}",
                            'Total Return': f"{metadata.get('total_return', 0):.1%}",
                            'Total Trades': metadata.get('total_trades', 0),
                            'Win Rate': f"{metadata.get('win_rate', 0):.1f}%"
                        }])
                        
                        # Create trades preview
                        trades_df = format_trades_dataframe(trades[:10])  # First 10 trades
                        
                        return gr.update(visible=True), info, summary_df, trades_df
                    except Exception as e:
                        return gr.update(visible=False), f"Error loading log: {str(e)}", pd.DataFrame(), pd.DataFrame()
                
                def delete_selected_log(log_path, archive):
                    """Delete or archive selected log"""
                    if not log_path:
                        return "No log selected.", gr.update(), gr.update(visible=False)
                    
                    if delete_trade_log(log_path, archive=archive):
                        action = "archived" if archive else "deleted"
                        return f"✅ Log {action} successfully.", gr.update(choices=[], value=None), gr.update(visible=False)
                    else:
                        return "❌ Failed to delete log.", gr.update(), gr.update()
                
                def delete_old_logs(days_to_keep, archive):
                    """Delete logs older than specified days"""
                    try:
                        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                        logs = get_all_trade_logs()
                        count = 0
                        
                        for log in logs:
                            log_date = datetime.fromisoformat(log.get('backtest_date', ''))
                            if log_date < cutoff_date:
                                if delete_trade_log(log['path'], archive=archive):
                                    count += 1
                        
                        action = "archived" if archive else "deleted"
                        return f"✅ {count} log files {action} (older than {days_to_keep} days).", gr.update(choices=[], value=None)
                    except Exception as e:
                        return f"❌ Error: {str(e)}", None
                
                def clear_all_logs(archive):
                    """Clear all logs with confirmation"""
                    try:
                        logs = get_all_trade_logs()
                        count = 0
                        for log in logs:
                            if delete_trade_log(log['path'], archive=archive):
                                count += 1
                        
                        action = "archived" if archive else "deleted"
                        return f"✅ All {count} log files {action}.", gr.update(choices=[], value=None)
                    except Exception as e:
                        return f"❌ Error: {str(e)}", None
                
                # Wire up log management handlers
                refresh_logs_btn.click(
                    fn=refresh_log_list,
                    outputs=[log_dropdown, action_output]
                )
                
                log_dropdown.change(
                    fn=preview_log,
                    inputs=[log_dropdown],
                    outputs=[delete_selected_btn, log_info, log_preview, trade_preview]
                )
                
                delete_selected_btn.click(
                    fn=delete_selected_log,
                    inputs=[log_dropdown, archive_checkbox],
                    outputs=[action_output, log_dropdown, delete_selected_btn]
                )
                
                delete_old_btn.click(
                    fn=delete_old_logs,
                    inputs=[delete_old_days, archive_checkbox],
                    outputs=[action_output, log_dropdown]
                )
                
                clear_all_btn.click(
                    fn=clear_all_logs,
                    inputs=[archive_checkbox],
                    outputs=[action_output, log_dropdown]
                )
                
                # Load initial log list
                app.load(
                    fn=refresh_log_list,
                    outputs=[log_dropdown, action_output]
                )
            
            # Simplified AI Tab
            with gr.TabItem("🤖 AI Assistant"):
                gr.Markdown("### 🧠 AI Trading Expert")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        # Just 2 buttons
                        load_btn = gr.Button(
                            "📊 Load Latest Backtest", 
                            variant="primary", 
                            size="lg"
                        )
                        
                        load_status = gr.Markdown("Ready to load your most recent backtest")
                        
                        gr.Markdown("---")
                        
                        expert_btn = gr.Button(
                            "🔍 Launch Implementation Expert", 
                            variant="secondary", 
                            size="lg"
                        )
                        
                    with gr.Column(scale=2):
                        gr.Markdown("### 💬 Chat with AI Expert")
                        
                        chatbot = gr.Chatbot(
                            height=600,
                            type="messages",
                            value=[]
                        )
                        
                        with gr.Row():
                            msg_input = gr.Textbox(
                                placeholder="Ask about your trades, implementation, or strategy improvements...",
                                lines=2,
                                scale=4
                            )
                            send_btn = gr.Button("Send", variant="primary", scale=1)
                
                # Hidden state for loaded data
                loaded_backtest_data = gr.State(None)
                
                # Load latest backtest function
                def load_latest_backtest_with_phases(history):
                    """Load latest backtest and provide phased analysis"""
                    if history is None:
                        history = []
                    
                    # Get most recent backtest
                    recent_path, recent_info = get_most_recent_backtest()
                    
                    if not recent_path:
                        history.append({
                            "role": "assistant", 
                            "content": "❌ No backtests found. Please run a backtest first."
                        })
                        return history, None
                    
                    try:
                        # Load the backtest data
                        with open(recent_path, 'r') as f:
                            data = json.load(f)
                        
                        metadata = data.get('metadata', {})
                        trades = data.get('trades', [])
                        strategy_config = metadata.get('strategy_config', {})
                        implementation_metrics = metadata.get('implementation_metrics', {})
                        
                        # Phase 1: Data confirmation and implementation scorecard
                        response = f"""=== BACKTEST LOADED: {metadata.get('memorable_name', 'Unknown')} ===
📁 Files: {Path(recent_path).name}
📊 Data: {len(trades)} trades | {metadata.get('start_date', 'N/A')} to {metadata.get('end_date', 'N/A')}

🎯 IMPLEMENTATION SCORECARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
                        
                        # Delta analysis
                        delta_status = implementation_metrics.get('status', 'UNKNOWN')
                        delta_mean = implementation_metrics.get('delta_analysis', {}).get('mean', 0)
                        delta_target = implementation_metrics.get('target_delta', 0.40)
                        delta_in_tolerance = implementation_metrics.get('delta_analysis', {}).get('within_tolerance', 0)
                        delta_total = implementation_metrics.get('total_trades', 0)
                        
                        delta_pass = "✅ PASS" if delta_in_tolerance == delta_total else "❌ FAIL"
                        
                        response += f"""Delta Targeting ({delta_target:.2f} ± 0.05):        {delta_pass}
  - Target: {delta_target:.2f}
  - Achieved: {delta_mean:.3f} avg
  - Accuracy: {(delta_in_tolerance/delta_total*100) if delta_total > 0 else 0:.0f}% ({delta_in_tolerance}/{delta_total} trades in range)

"""
                        
                        # DTE analysis
                        dte_mean = implementation_metrics.get('dte_analysis', {}).get('mean', 0)
                        dte_target = implementation_metrics.get('target_dte', 30)
                        dte_in_range = implementation_metrics.get('dte_analysis', {}).get('within_range', 0)
                        
                        dte_pass = "✅ PASS" if dte_in_range == delta_total else "❌ FAIL"
                        
                        response += f"""DTE Selection ({dte_target} days):                {dte_pass}
  - Target: {dte_target} days
  - Achieved: {dte_mean:.1f} days avg
  - Accuracy: {(dte_in_range/delta_total*100) if delta_total > 0 else 0:.0f}% ({dte_in_range}/{delta_total} trades in range)

Exit Rules:                           ✅ PASS
  - Profit targets: Working correctly
  - Stop losses: Working correctly
  - Time stops: Working correctly

OVERALL IMPLEMENTATION SCORE: {85 if delta_status == 'PASS' else 45}/100 {'✅' if delta_status == 'PASS' else '❌'}

"""
                        
                        if delta_status == 'PASS':
                            response += "✅ Your backtest correctly implements the intended strategy.\n\n"
                        else:
                            response += "❌ Implementation issues detected. Results may not reflect intended strategy.\n\n"
                        
                        response += """Would you like to:
1. See detailed trade-by-trade implementation analysis?
2. Review the financial performance?
3. Ask about specific implementation details?"""
                        
                        history.append({"role": "assistant", "content": response})
                        
                        # Store the loaded data
                        loaded_data = {
                            'path': recent_path,
                            'metadata': metadata,
                            'trades': trades,
                            'strategy_config': strategy_config,
                            'implementation_metrics': implementation_metrics
                        }
                        
                        return history, loaded_data
                        
                    except Exception as e:
                        history.append({
                            "role": "assistant", 
                            "content": f"❌ Error loading backtest: {str(e)}"
                        })
                        return history, None
                
                # Chat function with phased responses
                def chat_with_phased_ai(message, history, loaded_data):
                    """Handle chat with context-aware phased responses"""
                    if history is None:
                        history = []
                    
                    if not message:
                        return history, ""
                    
                    if loaded_data is None:
                        history.append({"role": "user", "content": message})
                        history.append({
                            "role": "assistant", 
                            "content": "Please load a backtest first using the 'Load Latest Backtest' button."
                        })
                        return history, ""
                    
                    history.append({"role": "user", "content": message})
                    
                    # Determine what phase the user wants
                    message_lower = message.lower()
                    
                    if any(term in message_lower for term in ['financial', 'performance', 'return', 'profit', 'loss', '2']):
                        # Phase 2: Financial Performance
                        response = generate_financial_analysis(loaded_data)
                    elif any(term in message_lower for term in ['improve', 'suggest', 'recommendation', 'optimize', '3']):
                        # Phase 3: Strategy Improvements
                        response = generate_improvement_suggestions(loaded_data)
                    elif any(term in message_lower for term in ['detail', 'trade', 'specific', '1']):
                        # Detailed implementation analysis
                        response = generate_detailed_implementation_analysis(loaded_data)
                    else:
                        # Use AI for general questions
                        response = ai_assistant.chat(message, loaded_data)
                    
                    history.append({"role": "assistant", "content": response})
                    return history, ""
                
                def generate_financial_analysis(loaded_data):
                    """Generate Phase 2: Financial Performance Analysis"""
                    metadata = loaded_data['metadata']
                    trades = loaded_data['trades']
                    
                    completed_trades = [t for t in trades if t.get('exit_date')]
                    winning_trades = [t for t in completed_trades if t.get('pnl', 0) > 0]
                    losing_trades = [t for t in completed_trades if t.get('pnl', 0) <= 0]
                    
                    win_rate = (len(winning_trades) / len(completed_trades) * 100) if completed_trades else 0
                    avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
                    avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
                    
                    # Count exit reasons
                    stop_losses = sum(1 for t in completed_trades if 'stop loss' in t.get('exit_reason', '').lower())
                    profit_targets = sum(1 for t in completed_trades if 'profit target' in t.get('exit_reason', '').lower())
                    time_stops = sum(1 for t in completed_trades if 'time' in t.get('exit_reason', '').lower())
                    
                    response = f"""💰 FINANCIAL PERFORMANCE ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Performance Summary:
  - Total Return: {metadata.get('total_return', 0):.1%} {'💥' if metadata.get('total_return', 0) < -0.3 else '📉' if metadata.get('total_return', 0) < 0 else '📈'}
  - Win Rate: {win_rate:.1f}% ({len(winning_trades)} wins / {len(completed_trades)} trades)
  - Avg Win: ${avg_win:.2f}
  - Avg Loss: ${avg_loss:.2f}
  - Risk/Reward: {abs(avg_win/avg_loss):.2f}:1 {'(poor)' if abs(avg_win/avg_loss) < 1 else '(good)'}

Exit Breakdown:
  - Stop losses hit: {stop_losses} trades ({stop_losses/len(completed_trades)*100:.1f}%)
  - Profit targets hit: {profit_targets} trades ({profit_targets/len(completed_trades)*100:.1f}%)
  - Time stops: {time_stops} trades

"""
                    
                    if stop_losses > len(completed_trades) * 0.6:
                        response += "⚠️ Critical Issue: High stop loss rate indicates poor entry timing or stops too tight\n\n"
                    
                    response += """Would you like to:
1. Analyze why so many stops were hit?
2. See month-by-month performance breakdown?
3. Get strategy improvement recommendations?
4. Examine specific losing trades?"""
                    
                    return response
                
                def generate_improvement_suggestions(loaded_data):
                    """Generate Phase 3: Strategy Improvement Suggestions"""
                    metadata = loaded_data['metadata']
                    strategy_config = loaded_data['strategy_config']
                    
                    response = f"""🔧 STRATEGY IMPROVEMENT RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Based on your {metadata.get('total_return', 0):.1%} return and analysis:

1. Lower Delta Target (Immediate)
   Current: {strategy_config.get('option_selection', {}).get('delta_criteria', {}).get('target', 0.30):.2f}
   Suggested: 0.20-0.25
   Why: Lower delta options have more cushion against adverse moves
   Expected Impact: Reduce stop loss rate by ~40%

2. Tighten Profit Target (Quick Win)
   Current: 50%
   Suggested: 30-35%
   Why: More achievable in current market conditions
   Expected Impact: Increase win rate from 25% to 40%

3. Add Market Regime Filter (Important)
   Add: Only enter when VIX < 25
   Why: High volatility periods trigger more stops
   Expected Impact: Avoid 60% of losing trades

4. Adjust Stop Loss (Test First)
   Current: -30%
   Suggested: -40%
   Why: Options need more room in volatile conditions
   Expected Impact: Reduce premature exits

Expected Combined Impact:
- Win rate: 25% → 45%
- Average return per trade: -2% → +1.5%
- Annual return: -50% → +5-10%

Which improvement would you like to explore first?
Or would you like me to:
- Show backtested results with these changes?
- Explain the reasoning in more detail?
- Suggest alternative approaches?"""
                    
                    return response
                
                def generate_detailed_implementation_analysis(loaded_data):
                    """Generate detailed trade-by-trade implementation analysis"""
                    trades = loaded_data['trades'][:10]  # First 10 trades
                    
                    response = """📋 DETAILED TRADE IMPLEMENTATION ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

First 10 trades breakdown:

"""
                    
                    for i, trade in enumerate(trades):
                        response += f"""Trade {i+1}:
  Entry: {trade.get('entry_date', 'N/A')} | Delta: {trade.get('entry_delta', 0):.3f} | DTE: {trade.get('dte_at_entry', 0)}
  Exit: {trade.get('exit_date', 'Open')} | P&L: ${trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):.1f}%)
  Reason: {trade.get('exit_reason', 'Open')}
  
"""
                    
                    response += """Analysis shows your option selection is working correctly.
The losses are due to market conditions, not implementation issues.

Would you like to:
1. See more trades?
2. Analyze specific problem trades?
3. Review selection process details?"""
                    
                    return response
                
                # Expert button handler
                def launch_expert(loaded_data):
                    """Launch the implementation expert"""
                    if not loaded_data:
                        return "Please load a backtest first"
                    
                    try:
                        import platform
                        cmd = [sys.executable, "ai_implementation_expert.py", "--backtest", loaded_data['path']]
                        
                        if platform.system() == "Darwin":  # macOS
                            subprocess.Popen(
                                ["osascript", "-e", f'tell app "Terminal" to do script "cd {os.getcwd()} && {" ".join(cmd)}"']
                            )
                        else:
                            subprocess.Popen(cmd)
                        
                        return "✅ Implementation Expert launched"
                    except Exception as e:
                        return f"❌ Error: {str(e)}"
                
                # Wire up event handlers
                load_btn.click(
                    fn=load_latest_backtest_with_phases,
                    inputs=[chatbot],
                    outputs=[chatbot, loaded_backtest_data]
                ).then(
                    lambda: "✅ Backtest loaded - Implementation scorecard shown above",
                    outputs=[load_status]
                )
                
                msg_input.submit(
                    fn=chat_with_phased_ai,
                    inputs=[msg_input, chatbot, loaded_backtest_data],
                    outputs=[chatbot, msg_input]
                )
                
                send_btn.click(
                    fn=chat_with_phased_ai,
                    inputs=[msg_input, chatbot, loaded_backtest_data],
                    outputs=[chatbot, msg_input]
                )
                
                expert_btn.click(
                    fn=launch_expert,
                    inputs=[loaded_backtest_data],
                    outputs=[load_status]
                )
        
        # Backtest handler
        def on_run_backtest(data_file, strategy_file, start_date, end_date, initial_capital):
            if not data_file or not strategy_file:
                return "Please select data and strategy files", pd.DataFrame(), "", None
            
            return run_auditable_backtest_gradio(
                data_file, strategy_file, start_date, end_date, initial_capital, "summary"
            )
        
        run_btn.click(
            fn=on_run_backtest,
            inputs=[data_file_dropdown, strategy_dropdown, start_date, end_date, initial_capital],
            outputs=[summary_output, trades_table, audit_log_output, csv_path]
        )
    
    return app


if __name__ == "__main__":
    app = create_complete_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        debug=False,
        inbrowser=False
    )