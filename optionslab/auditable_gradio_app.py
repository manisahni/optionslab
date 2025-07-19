#!/usr/bin/env python3
"""
Auditable Gradio App for OptionsLab
This app provides a clean, trustworthy interface for running auditable backtests.
Every step is logged and traceable, giving users confidence in the results.
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
from typing import List, Dict, Optional

# Import our auditable backtest functions
from auditable_backtest import (
    load_and_audit_data,
    audit_strategy_config,
    find_suitable_options,
    calculate_position_size,
    run_auditable_backtest
)

# Import visualization and AI modules
from visualization import (
    plot_pnl_curve,
    plot_trade_markers,
    plot_greeks_evolution,
    plot_win_loss_distribution,
    plot_strategy_heatmap,
    create_summary_dashboard
)
from ai_assistant import AIAssistant

# Trade log management functions
def get_trade_logs_dir() -> Path:
    """Get the trade logs directory"""
    return Path(__file__).parent / "trade_logs"

def save_trade_log(trades_df: pd.DataFrame, results: dict, strategy_name: str, 
                   start_date: str, end_date: str) -> tuple[str, str]:
    """Save trade log to permanent storage and return paths"""
    # Create directory structure
    logs_dir = get_trade_logs_dir()
    now = datetime.now()
    year_dir = logs_dir / str(now.year)
    month_dir = year_dir / f"{now.month:02d}"
    month_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    base_name = f"trades_{strategy_name}_{start_date}_to_{end_date}_{timestamp}"
    csv_path = month_dir / f"{base_name}.csv"
    json_path = month_dir / f"{base_name}.json"
    
    # Save CSV
    if not trades_df.empty:
        trades_df.to_csv(csv_path, index=False)
    
    # Prepare JSON data with metadata
    json_data = {
        "metadata": {
            "strategy": strategy_name,
            "backtest_date": now.isoformat(),
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": results.get('initial_capital', 0),
            "final_value": results.get('final_value', 0),
            "total_return": results.get('total_return', 0),
            "total_trades": len(results.get('trades', [])),
            "win_rate": calculate_win_rate(results.get('trades', []))
        },
        "trades": results.get('trades', [])
    }
    
    # Save JSON
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2, default=str)
    
    # Update index
    update_trade_log_index(json_path, json_data['metadata'])
    
    return str(csv_path), str(json_path)

def calculate_win_rate(trades: list) -> float:
    """Calculate win rate from trades"""
    completed = [t for t in trades if 'pnl' in t]
    if not completed:
        return 0.0
    winners = [t for t in completed if t.get('pnl', 0) > 0]
    return len(winners) / len(completed)

def update_trade_log_index(log_path: Path, metadata: dict):
    """Update the index file with new log entry"""
    index_path = get_trade_logs_dir() / "index.json"
    
    # Load existing index or create new
    if index_path.exists():
        with open(index_path, 'r') as f:
            index = json.load(f)
    else:
        index = {"logs": [], "last_updated": None}
    
    # Add new entry
    log_entry = {
        "path": str(log_path),
        "year": datetime.now().year,
        "month": datetime.now().month,
        **metadata
    }
    index["logs"].append(log_entry)
    index["last_updated"] = datetime.now().isoformat()
    
    # Save updated index
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

def get_all_trade_logs() -> List[Dict]:
    """Get list of all trade logs from index"""
    index_path = get_trade_logs_dir() / "index.json"
    if not index_path.exists():
        return []
    
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    # Add file size and ensure paths exist
    logs = []
    for log in index.get('logs', []):
        if Path(log['path']).exists():
            log['size'] = Path(log['path']).stat().st_size
            logs.append(log)
    
    return sorted(logs, key=lambda x: x['backtest_date'], reverse=True)

def delete_trade_log(log_path: str, archive: bool = True) -> bool:
    """Delete or archive a trade log"""
    log_file = Path(log_path)
    if not log_file.exists():
        return False
    
    if archive:
        # Move to archive directory
        archive_dir = get_trade_logs_dir() / "archived"
        archive_dir.mkdir(exist_ok=True)
        archive_path = archive_dir / log_file.name
        shutil.move(str(log_file), str(archive_path))
        
        # Also move the corresponding file (csv/json)
        if log_file.suffix == '.json':
            csv_file = log_file.with_suffix('.csv')
        else:
            csv_file = log_file.with_suffix('.json')
        
        if csv_file.exists():
            shutil.move(str(csv_file), str(archive_dir / csv_file.name))
    else:
        # Permanent delete
        log_file.unlink()
        # Also delete the corresponding file
        if log_file.suffix == '.json':
            csv_file = log_file.with_suffix('.csv')
        else:
            csv_file = log_file.with_suffix('.json')
        if csv_file.exists():
            csv_file.unlink()
    
    # Update index
    remove_from_index(log_path)
    return True

def remove_from_index(log_path: str):
    """Remove entry from index"""
    index_path = get_trade_logs_dir() / "index.json"
    if not index_path.exists():
        return
    
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    index['logs'] = [log for log in index['logs'] if log['path'] != log_path]
    index['last_updated'] = datetime.now().isoformat()
    
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)

def clear_old_logs(days_to_keep: int = 30, archive: bool = True) -> int:
    """Clear logs older than specified days"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    logs = get_all_trade_logs()
    deleted_count = 0
    
    for log in logs:
        log_date = datetime.fromisoformat(log['backtest_date'])
        if log_date < cutoff_date:
            if delete_trade_log(log['path'], archive=archive):
                deleted_count += 1
    
    return deleted_count

def get_available_data_files():
    """Get list of available parquet files for selection"""
    repaired_dir = Path("../spy_options_downloader/spy_options_parquet/repaired")
    main_dir = Path("../spy_options_downloader/spy_options_parquet")
    
    files = []
    
    # Count files in each directory
    main_count = len(list(main_dir.glob("spy_options_eod_*.parquet"))) if main_dir.exists() else 0
    repaired_count = len(list(repaired_dir.glob("spy_options_eod_*.parquet"))) if repaired_dir.exists() else 0
    
    # Add main directory first if it has more files
    if main_count > 0:
        files.append((f"📊 Multi-Day Backtest - Main Directory ({main_count} files)", str(main_dir)))
    
    # Add repaired directory if it exists
    if repaired_count > 0:
        files.append((f"✅ Multi-Day Backtest - Repaired Directory ({repaired_count} files)", str(repaired_dir)))
    
    # Don't add individual date files - they're not useful for backtesting
    # A backtest needs multiple days to be meaningful
    
    if not files:
        files.append(("❌ No data files found", ""))
    
    return files

def get_data_coverage_info(data_dir):
    """Get information about date coverage in the data directory"""
    data_path = Path(data_dir)
    if not data_path.exists():
        return "No data directory found"
    
    files = list(data_path.glob("spy_options_eod_*.parquet"))
    if not files:
        return "No data files found"
    
    # Extract dates
    dates = []
    for file in files:
        try:
            date_str = file.stem.split('_')[-1]
            date = datetime.strptime(date_str, '%Y%m%d')
            dates.append(date)
        except:
            continue
    
    if not dates:
        return "Could not parse dates from files"
    
    dates.sort()
    first_date = dates[0].strftime('%Y-%m-%d')
    last_date = dates[-1].strftime('%Y-%m-%d')
    
    # Count by year
    years = {}
    for date in dates:
        year = date.year
        years[year] = years.get(year, 0) + 1
    
    info = f"📊 Data Coverage: {first_date} to {last_date}\n"
    info += f"📁 Total Files: {len(files)}\n"
    info += "📅 Files by Year:\n"
    for year in sorted(years.keys()):
        info += f"   • {year}: {years[year]} days\n"
    
    return info

def get_available_strategies():
    """Get list of available strategy files"""
    strategies = []
    
    # Check config/strategies directory
    config_dir = Path("../config/strategies")
    if config_dir.exists():
        for file in config_dir.glob("*.yaml"):
            try:
                with open(file, 'r') as f:
                    config = yaml.safe_load(f)
                    name = config.get('name', file.stem)
                    strategies.append((f"📋 {name}", str(file)))
            except:
                strategies.append((f"📋 {file.stem}", str(file)))
    
    # Add our simple test strategy
    test_strategy = Path("../simple_test_strategy.yaml")
    if test_strategy.exists():
        strategies.append(("🧪 Simple Long Call Test", str(test_strategy)))
    
    # Add advanced test strategy
    advanced_strategy = Path("../advanced_test_strategy.yaml")
    if advanced_strategy.exists():
        strategies.append(("🚀 Advanced Long Call (Delta/DTE/Liquidity)", str(advanced_strategy)))
    
    return strategies

def format_trades_dataframe(trades):
    """Format trades into a clean DataFrame for display"""
    if not trades:
        return pd.DataFrame()
    
    # Filter completed trades
    completed_trades = [t for t in trades if 'exit_date' in t]
    if not completed_trades:
        return pd.DataFrame()
    
    # Create DataFrame with selected columns for display
    df_data = []
    for trade in completed_trades:
        row = {
            'ID': trade.get('trade_id', ''),
            'Type': trade.get('option_type', ''),
            'Entry Date': trade.get('entry_date', ''),
            'Exit Date': trade.get('exit_date', ''),
            'Strike': f"${trade.get('strike', 0):.2f}",
            'Expiry': trade.get('expiration', ''),
            'DTE': trade.get('dte_at_entry', ''),
            'Entry $': f"${trade.get('option_price', 0):.2f}",
            'Exit $': f"${trade.get('exit_price', 0):.2f}",
            'Contracts': trade.get('contracts', 0),
            'Entry Bid/Ask': f"${trade.get('entry_bid', 0):.2f}/{trade.get('entry_ask', 0):.2f}",
            'Spread %': f"{trade.get('entry_spread_pct', 0):.1f}%",
            'Entry Δ': f"{trade.get('entry_delta', 0):.3f}" if trade.get('entry_delta') is not None else 'N/A',
            'Exit Δ': f"{trade.get('exit_delta', 0):.3f}" if trade.get('exit_delta') is not None else 'N/A',
            'Entry IV': f"{trade.get('entry_iv', 0):.1%}" if trade.get('entry_iv') is not None else 'N/A',
            'Exit IV': f"{trade.get('exit_iv', 0):.1%}" if trade.get('exit_iv') is not None else 'N/A',
            'Days Held': trade.get('days_held', 0),
            'Entry Reason': trade.get('entry_reason', ''),
            'Exit Reason': trade.get('exit_reason', ''),
            'P&L $': f"${trade.get('pnl', 0):.2f}",
            'P&L %': f"{trade.get('pnl_pct', 0):.1f}%",
            'Ann. Return': f"{trade.get('annualized_return', 0):.1f}%",
            'Underlying Entry': f"${trade.get('underlying_at_entry', 0):.2f}",
            'Underlying Exit': f"${trade.get('underlying_at_exit', 0):.2f}",
            'Underlying Move': f"{trade.get('underlying_move_pct', 0):.1f}%"
        }
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    return df

def run_auditable_backtest_gradio(data_file, strategy_file, start_date, end_date, initial_capital, log_level="summary"):
    """Run auditable backtest and return results for Gradio"""
    
    # Capture the audit output
    import io
    import sys
    import tempfile
    
    # Redirect stdout to capture audit messages
    old_stdout = sys.stdout
    audit_output = io.StringIO()
    sys.stdout = audit_output
    
    try:
        # Run the auditable backtest
        results = run_auditable_backtest(data_file, strategy_file, start_date, end_date)
        
        # Restore stdout
        sys.stdout = old_stdout
        
        if results:
            # Format results for display
            audit_log = audit_output.getvalue()
            
            # Create trades DataFrame
            trades_df = format_trades_dataframe(results['trades'])
            
            # Calculate summary statistics
            completed_trades = [t for t in results['trades'] if 'exit_date' in t]
            winning_trades = [t for t in completed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in completed_trades if t.get('pnl', 0) <= 0]
            
            win_rate = (len(winning_trades) / len(completed_trades) * 100) if completed_trades else 0
            avg_win = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
            profit_factor = abs(sum(t.get('pnl', 0) for t in winning_trades) / sum(t.get('pnl', 0) for t in losing_trades)) if losing_trades and sum(t.get('pnl', 0) for t in losing_trades) != 0 else 0
            
            # Create summary
            summary = f"""
## 📊 Backtest Results

### Overall Performance
- **Final Value:** ${results['final_value']:,.2f}
- **Total Return:** {results['total_return']:.2%}
- **Initial Capital:** ${initial_capital:,.2f}
- **Total Trades:** {len(completed_trades)}

### Trade Statistics
- **Win Rate:** {win_rate:.1f}%
- **Average Win:** ${avg_win:.2f}
- **Average Loss:** ${avg_loss:.2f}
- **Profit Factor:** {profit_factor:.2f}
- **Best Trade:** ${max(t.get('pnl', 0) for t in completed_trades):.2f} if completed_trades else $0.00
- **Worst Trade:** ${min(t.get('pnl', 0) for t in completed_trades):.2f} if completed_trades else $0.00
"""
            
            # Prepare audit log based on log level
            if log_level == "standard":
                # Show key events only
                key_events = []
                for line in audit_log.split('\n'):
                    if any(keyword in line for keyword in ['✅ AUDIT: Executing trade', '🔍 AUDIT: Exiting position', 
                                                           '💰 AUDIT: Initial Capital', '📊 AUDIT: Final Results',
                                                           '✅ AUDIT: Strategy:', '🎯 AUDIT: Profit target hit',
                                                           '🛑 AUDIT: Stop loss hit']):
                        key_events.append(line)
                
                audit_log = '\n'.join(key_events)
            elif log_level == "summary":
                audit_log = ""  # No audit log for summary
            
            # Save comprehensive trades data to CSV for export and viewing
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            trades_csv_path = os.path.join(tempfile.gettempdir(), f"trades_log_{timestamp}.csv")
            
            # Create comprehensive trades DataFrame with all fields
            if results['trades']:
                full_trades_df = pd.DataFrame(results['trades'])
                full_trades_df.to_csv(trades_csv_path, index=False)
                
                # Also save to permanent storage
                strategy_name = Path(strategy_file).stem.replace('_', '-')
                # Add initial_capital to results for saving
                results['initial_capital'] = initial_capital
                perm_csv_path, perm_json_path = save_trade_log(
                    full_trades_df, results, strategy_name, start_date, end_date
                )
                
                # Add permanent storage info to summary
                summary += f"\n\n### 📁 Trade Log Saved\n- CSV: `{Path(perm_csv_path).name}`\n- JSON: `{Path(perm_json_path).name}`"
            else:
                trades_csv_path = None
            
            return summary, trades_df, audit_log, trades_csv_path
        else:
            sys.stdout = old_stdout
            error_msg = f"❌ Backtest failed!\n\n## 🔍 Error Log\n```\n{audit_output.getvalue()}\n```"
            return error_msg, pd.DataFrame(), "", None
            
    except Exception as e:
        sys.stdout = old_stdout
        error_msg = f"❌ Error during backtest: {str(e)}\n\n## 🔍 Error Log\n```\n{audit_output.getvalue()}\n```"
        return error_msg, pd.DataFrame(), "", None

def create_auditable_interface():
    """Create the main Gradio interface"""
    
    with gr.Blocks(title="OptionsLab - Auditable Backtesting", theme=gr.themes.Soft()) as app:
        
        # Header
        gr.Markdown("""
        # 🎯 OptionsLab - Auditable Backtesting System
        
        **Trustworthy, traceable options backtesting with full data flow auditing.**
        
        Every step is logged and verifiable, giving you confidence in your results.
        """)
        
        with gr.Tabs():
            with gr.TabItem("🚀 Run Backtest"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 Configuration")
                        
                        # Data file selection
                        data_files = get_available_data_files()
                        data_file_dropdown = gr.Dropdown(
                            choices=data_files,
                            label="📁 Select Data File",
                            info="Choose a parquet file with real SPY options data",
                            value=data_files[0][1] if data_files else None
                        )
                        
                        # Strategy selection
                        strategies = get_available_strategies()
                        strategy_dropdown = gr.Dropdown(
                            choices=strategies,
                            label="📋 Select Strategy",
                            info="Choose a YAML strategy configuration",
                            value=strategies[0][1] if strategies else None
                        )
                        
                        # Date inputs with better defaults
                        start_date = gr.Textbox(
                            label="📅 Start Date",
                            placeholder="YYYY-MM-DD",
                            value="2022-01-01",
                            info="Start date for backtest. Available: 2020-07 to 2025-07"
                        )
                        
                        end_date = gr.Textbox(
                            label="📅 End Date", 
                            placeholder="YYYY-MM-DD",
                            value="2022-12-31",
                            info="End date for backtest. Full years available: 2021-2024"
                        )
                        
                        # Capital input
                        initial_capital = gr.Number(
                            label="💰 Initial Capital",
                            value=10000,
                            minimum=1000,
                            maximum=1000000,
                            step=1000,
                            info="Starting capital in dollars"
                        )
                        
                        # Log level control
                        log_level = gr.Dropdown(
                            label="📝 Log Detail Level",
                            choices=[
                                ("Summary - Just results and trades", "summary"),
                                ("Standard - Key events only", "standard"),
                                ("Detailed - Full audit log", "detailed")
                            ],
                            value="summary",
                            info="Control how much detail to show in the output"
                        )
                        
                        # Run button
                        run_btn = gr.Button("🚀 Run Auditable Backtest", variant="primary", size="lg")
                        
                        # Data coverage info
                        data_info = gr.Markdown("### 📊 Data Coverage\nSelect a data source to see available dates...")
                        
                        # Status
                        status = gr.Markdown("### 📈 Status\nReady to run backtest...")
                    
                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Results")
                        
                        # Summary statistics
                        summary_output = gr.Markdown(
                            value="**Results will appear here after running a backtest.**"
                        )
                        
                        # Trade details table
                        with gr.Row():
                            gr.Markdown("### 📈 Trade Details")
                            export_btn = gr.Button("📥 Export to CSV", size="sm", variant="secondary")
                        
                        trades_table = gr.DataFrame(
                            headers=["ID", "Type", "Entry Date", "Exit Date", "Strike", "P&L $", "P&L %", "Exit Reason"],
                            datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                            wrap=True
                        )
                        
                        # Hidden component to store CSV path
                        csv_path = gr.State()
                        
                        # File output for CSV download
                        csv_output = gr.File(visible=False, label="Download Trade Log CSV")
                        
                        # Audit log (collapsible)
                        with gr.Accordion("🔍 Audit Log", open=False):
                            audit_log_output = gr.Textbox(
                                label="Detailed Audit Trail",
                                lines=20,
                                max_lines=50,
                                show_copy_button=True
                            )
            
            with gr.TabItem("📁 Log Management"):
                gr.Markdown("### 🗂️ Trade Log Management")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        # Log selection
                        gr.Markdown("#### 📋 Available Logs")
                        
                        # Refresh button
                        refresh_logs_btn = gr.Button("🔄 Refresh Log List", size="sm")
                        
                        # Log dropdown
                        log_dropdown = gr.Dropdown(
                            label="Select Log File",
                            choices=[],
                            info="Choose a log file to view or delete"
                        )
                        
                        # Log info display
                        log_info = gr.Markdown("Select a log to see details...")
                        
                        # Delete controls
                        gr.Markdown("#### 🗑️ Delete Options")
                        
                        delete_selected_btn = gr.Button(
                            "🗑️ Delete Selected Log", 
                            variant="stop",
                            interactive=False
                        )
                        
                        delete_old_days = gr.Number(
                            label="Days to Keep",
                            value=30,
                            minimum=1,
                            maximum=365,
                            step=1
                        )
                        
                        delete_old_btn = gr.Button(
                            "📅 Delete Logs Older Than X Days",
                            variant="secondary"
                        )
                        
                        clear_all_btn = gr.Button(
                            "⚠️ Clear All Logs",
                            variant="stop"
                        )
                        
                        # Archive option
                        archive_checkbox = gr.Checkbox(
                            label="Archive logs instead of permanent deletion",
                            value=True,
                            info="Archived logs can be recovered from the 'archived' folder"
                        )
                        
                    with gr.Column(scale=2):
                        # Log preview
                        gr.Markdown("#### 👁️ Log Preview")
                        
                        log_preview = gr.DataFrame(
                            headers=["Field", "Value"],
                            datatype=["str", "str"],
                            wrap=True,
                            label="Log Metadata"
                        )
                        
                        # Trade preview
                        trade_preview = gr.DataFrame(
                            headers=["ID", "Type", "Entry", "Exit", "P&L $", "P&L %"],
                            datatype=["str", "str", "str", "str", "str", "str"],
                            wrap=True,
                            label="First 10 Trades"
                        )
                        
                        # Actions output
                        action_output = gr.Markdown("")
                
                # Log management functions
                def refresh_log_list():
                    """Refresh the list of available logs"""
                    logs = get_all_trade_logs()
                    if not logs:
                        return gr.update(choices=[], value=None), "No logs found."
                    
                    choices = []
                    for log in logs:
                        size_mb = log.get('size', 0) / 1024 / 1024
                        label = f"{Path(log['path']).name} ({size_mb:.1f} MB) - {log.get('backtest_date', 'Unknown date')}"
                        choices.append((label, log['path']))
                    
                    return gr.update(choices=choices, value=choices[0][1] if choices else None), f"Found {len(logs)} log files."
                
                def preview_log(log_path):
                    """Preview selected log file"""
                    if not log_path or not Path(log_path).exists():
                        return gr.update(interactive=False), "Select a log file", pd.DataFrame(), pd.DataFrame()
                    
                    # Load JSON file for preview
                    json_path = Path(log_path)
                    if json_path.suffix == '.csv':
                        json_path = json_path.with_suffix('.json')
                    
                    if not json_path.exists():
                        return gr.update(interactive=True), "JSON file not found", pd.DataFrame(), pd.DataFrame()
                    
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                    
                    # Extract metadata
                    metadata = data.get('metadata', {})
                    info_data = [
                        ["Strategy", metadata.get('strategy', 'N/A')],
                        ["Backtest Date", metadata.get('backtest_date', 'N/A')],
                        ["Date Range", f"{metadata.get('start_date', 'N/A')} to {metadata.get('end_date', 'N/A')}"],
                        ["Initial Capital", f"${metadata.get('initial_capital', 0):,.2f}"],
                        ["Final Value", f"${metadata.get('final_value', 0):,.2f}"],
                        ["Total Return", f"{metadata.get('total_return', 0):.2%}"],
                        ["Total Trades", str(metadata.get('total_trades', 0))],
                        ["Win Rate", f"{metadata.get('win_rate', 0):.1%}"]
                    ]
                    
                    # Extract first 10 trades
                    trades = data.get('trades', [])[:10]
                    trade_data = []
                    for trade in trades:
                        if 'exit_date' in trade:
                            trade_data.append([
                                str(trade.get('trade_id', '')),
                                trade.get('option_type', ''),
                                trade.get('entry_date', ''),
                                trade.get('exit_date', ''),
                                f"${trade.get('pnl', 0):.2f}",
                                f"{trade.get('pnl_pct', 0):.1f}%"
                            ])
                    
                    info_df = pd.DataFrame(info_data, columns=["Field", "Value"])
                    trades_df = pd.DataFrame(trade_data, columns=["ID", "Type", "Entry", "Exit", "P&L $", "P&L %"])
                    
                    info_text = f"### 📊 Log Details\n**File:** {Path(log_path).name}\n**Size:** {Path(log_path).stat().st_size / 1024:.1f} KB"
                    
                    return gr.update(interactive=True), info_text, info_df, trades_df
                
                def delete_selected_log(log_path, archive):
                    """Delete the selected log file"""
                    if not log_path:
                        return "❌ No log file selected.", None, None
                    
                    try:
                        if delete_trade_log(log_path, archive=archive):
                            action = "archived" if archive else "permanently deleted"
                            # Refresh the list
                            logs = get_all_trade_logs()
                            if logs:
                                choices = [(f"{Path(log['path']).name} - {log.get('backtest_date', 'Unknown')}", log['path']) for log in logs]
                                return f"✅ Log file {action} successfully.", gr.update(choices=choices, value=None), gr.update(interactive=False)
                            else:
                                return f"✅ Log file {action} successfully.", gr.update(choices=[], value=None), gr.update(interactive=False)
                        else:
                            return "❌ Failed to delete log file.", None, None
                    except Exception as e:
                        return f"❌ Error: {str(e)}", None, None
                
                def delete_old_logs(days_to_keep, archive):
                    """Delete logs older than specified days"""
                    try:
                        count = clear_old_logs(days_to_keep, archive=archive)
                        action = "archived" if archive else "deleted"
                        # Refresh the list
                        logs = get_all_trade_logs()
                        if logs:
                            choices = [(f"{Path(log['path']).name} - {log.get('backtest_date', 'Unknown')}", log['path']) for log in logs]
                            return f"✅ {count} log files {action} (older than {days_to_keep} days).", gr.update(choices=choices, value=None)
                        else:
                            return f"✅ {count} log files {action} (older than {days_to_keep} days).", gr.update(choices=[], value=None)
                    except Exception as e:
                        return f"❌ Error: {str(e)}", None
                
                def clear_all_logs(archive):
                    """Clear all logs with confirmation"""
                    # This would ideally have a confirmation dialog
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
                
                # Wire up event handlers
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
            
            # Visualizations Tab
            with gr.TabItem("📊 Visualizations"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📈 Chart Options")
                        
                        # Chart type selection
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
                            value="pnl_curve",
                            info="Choose visualization type"
                        )
                        
                        # Data source selection
                        viz_data_source = gr.Dropdown(
                            label="Data Source",
                            choices=[],
                            info="Select trade log to visualize"
                        )
                        
                        # Refresh and generate buttons
                        refresh_viz_btn = gr.Button("🔄 Refresh Data Sources", size="sm")
                        generate_chart_btn = gr.Button("📊 Generate Chart", variant="primary")
                        
                        # Chart info
                        chart_info = gr.Markdown("Select a data source and chart type...")
                        
                    with gr.Column(scale=3):
                        # Main chart display
                        main_chart = gr.Plot(label="Visualization")
                        
                        # Export button
                        export_chart_btn = gr.Button("📥 Export Chart", size="sm", variant="secondary")
                
                # Visualization functions
                def refresh_viz_sources():
                    """Refresh available data sources for visualization"""
                    logs = get_all_trade_logs()
                    if not logs:
                        return gr.update(choices=[], value=None), "No trade logs found."
                    
                    choices = []
                    for log in logs:
                        label = f"{log.get('strategy', 'Unknown')} - {log.get('backtest_date', 'Unknown')[:10]} ({log.get('total_trades', 0)} trades)"
                        choices.append((label, log['path']))
                    
                    return gr.update(choices=choices, value=choices[0][1] if choices else None), f"Found {len(logs)} trade logs."
                
                def generate_visualization(data_source, chart_type):
                    """Generate selected visualization"""
                    if not data_source:
                        return None, "Please select a data source."
                    
                    # Load trade data
                    json_path = Path(data_source)
                    if json_path.suffix == '.csv':
                        json_path = json_path.with_suffix('.json')
                    
                    if not json_path.exists():
                        return None, "Data file not found."
                    
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                    
                    trades = data.get('trades', [])
                    metadata = data.get('metadata', {})
                    
                    if not trades:
                        return None, "No trades found in selected log."
                    
                    # Generate appropriate chart
                    try:
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
                        
                        info = f"Generated {chart_type.replace('_', ' ').title()} for {metadata.get('strategy', 'Unknown')} strategy"
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
            
            # AI Assistant Tab
            with gr.TabItem("🤖 AI Assistant"):
                # Initialize AI assistant
                ai_assistant = gr.State(AIAssistant())
                
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 🔧 AI Configuration")
                        
                        # API Key management
                        api_key_input = gr.Textbox(
                            type="password",
                            label="Gemini API Key",
                            placeholder="Enter API key or leave blank to use .env",
                            info="API key is loaded from .env file by default"
                        )
                        
                        save_key_btn = gr.Button("💾 Update API Key", size="sm")
                        api_status = gr.Markdown("Checking API status...")
                        
                        gr.Markdown("### 📊 Context Selection")
                        
                        context_type = gr.Dropdown(
                            label="Load Context",
                            choices=[
                                ("All Data", "all"),
                                ("Trade Logs Only", "trades"),
                                ("Strategies Only", "strategies"),
                                ("Source Code", "code")
                            ],
                            value="all",
                            info="Select data to load for AI analysis"
                        )
                        
                        load_context_btn = gr.Button("📥 Load Context", variant="secondary")
                        context_status = gr.Markdown("Context not loaded")
                        
                        # Quick actions
                        gr.Markdown("### ⚡ Quick Actions")
                        analyze_current_btn = gr.Button("📊 Analyze Current Backtest", size="sm")
                        suggest_improvements_btn = gr.Button("💡 Suggest Improvements", size="sm")
                        
                    with gr.Column(scale=2):
                        gr.Markdown("### 💬 AI Chat")
                        
                        chatbot = gr.Chatbot(
                            height=500,
                            label="AI Trading Assistant",
                            type="messages"
                        )
                        
                        msg_input = gr.Textbox(
                            label="Your Message",
                            placeholder="Ask about trades, strategies, or market analysis...",
                            lines=2
                        )
                        
                        with gr.Row():
                            send_btn = gr.Button("📤 Send", variant="primary")
                            clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
                        
                        # Example prompts
                        gr.Examples(
                            examples=[
                                "Analyze my losing trades and identify common patterns",
                                "What's the optimal delta range for entry based on my results?",
                                "How can I improve my risk management?",
                                "Compare the performance of different exit strategies",
                                "What market conditions favor my strategy?"
                            ],
                            inputs=msg_input
                        )
                
                # Current backtest data storage
                current_backtest_data = gr.State(None)
                
                # AI Assistant functions
                def check_api_status(ai_assistant):
                    """Check if AI is configured"""
                    if ai_assistant.is_configured():
                        return "✅ API Configured and Ready"
                    else:
                        return "❌ API Not Configured - Enter API key or check .env file"
                
                def update_api_key(api_key, ai_assistant):
                    """Update API key"""
                    if not api_key:
                        # Try to reload from .env
                        ai_assistant._load_api_key_from_env()
                    else:
                        ai_assistant.set_api_key(api_key)
                    
                    if ai_assistant.is_configured():
                        return "✅ API Key Updated Successfully", ai_assistant
                    else:
                        return "❌ Failed to Configure API", ai_assistant
                
                def load_ai_context(context_type, ai_assistant):
                    """Load context for AI"""
                    if not ai_assistant.is_configured():
                        return "❌ Please configure API first"
                    
                    result = ai_assistant.load_context(context_type)
                    return result
                
                def chat_with_ai(message, history, ai_assistant, current_data):
                    """Chat with AI assistant"""
                    if not message:
                        return history
                    
                    if not ai_assistant.is_configured():
                        history.append({"role": "user", "content": message})
                        history.append({"role": "assistant", "content": "❌ AI not configured. Please set API key."})
                        return history
                    
                    # Get AI response
                    response = ai_assistant.chat(message, current_data)
                    history.append({"role": "user", "content": message})
                    history.append({"role": "assistant", "content": response})
                    return history
                
                def analyze_current_backtest(ai_assistant, current_data):
                    """Analyze current backtest results"""
                    if not ai_assistant.is_configured():
                        return [{"role": "system", "content": "❌ AI not configured. Please set API key."}]
                    
                    if not current_data or 'trades' not in current_data:
                        return [{"role": "system", "content": "No backtest data available. Please run a backtest first."}]
                    
                    analysis = ai_assistant.analyze_trades(current_data['trades'])
                    return [{"role": "user", "content": "Analyze Current Backtest"}, {"role": "assistant", "content": analysis}]
                
                def suggest_improvements(ai_assistant, current_data):
                    """Get improvement suggestions"""
                    if not ai_assistant.is_configured():
                        return [{"role": "system", "content": "❌ AI not configured. Please set API key."}]
                    
                    strategy_type = "options trading"
                    market_conditions = "variable volatility"
                    
                    if current_data and 'strategy_name' in current_data:
                        strategy_type = current_data['strategy_name']
                    
                    suggestions = ai_assistant.get_suggestions(strategy_type, market_conditions)
                    return [{"role": "user", "content": "Suggest Improvements"}, {"role": "assistant", "content": suggestions}]
                
                # Wire up AI handlers
                app.load(
                    fn=check_api_status,
                    inputs=[ai_assistant],
                    outputs=[api_status]
                )
                
                save_key_btn.click(
                    fn=update_api_key,
                    inputs=[api_key_input, ai_assistant],
                    outputs=[api_status, ai_assistant]
                )
                
                load_context_btn.click(
                    fn=load_ai_context,
                    inputs=[context_type, ai_assistant],
                    outputs=[context_status]
                )
                
                send_btn.click(
                    fn=chat_with_ai,
                    inputs=[msg_input, chatbot, ai_assistant, current_backtest_data],
                    outputs=[chatbot]
                ).then(
                    lambda: "",
                    outputs=[msg_input]
                )
                
                clear_btn.click(
                    lambda: [],
                    outputs=[chatbot]
                )
                
                analyze_current_btn.click(
                    fn=analyze_current_backtest,
                    inputs=[ai_assistant, current_backtest_data],
                    outputs=[chatbot]
                )
                
                suggest_improvements_btn.click(
                    fn=suggest_improvements,
                    inputs=[ai_assistant, current_backtest_data],
                    outputs=[chatbot]
                )
        
        # Event handlers
        def on_run_backtest(data_file, strategy_file, start_date, end_date, initial_capital, log_level):
            if not data_file or not strategy_file:
                return "❌ Please select both a data file and strategy file.", pd.DataFrame(), "", None, None
            
            # Update status
            status_text = "🔄 Running auditable backtest..."
            
            # Run the backtest
            summary, trades_df, audit_log, csv_path = run_auditable_backtest_gradio(data_file, strategy_file, start_date, end_date, initial_capital, log_level)
            
            # Extract backtest data for AI assistant
            if csv_path and os.path.exists(csv_path):
                # Load the full data from the saved JSON
                csv_file = Path(csv_path)
                json_file = csv_file.with_suffix('.json')
                if json_file.exists():
                    with open(json_file, 'r') as f:
                        full_data = json.load(f)
                        backtest_data = {
                            'trades': full_data.get('trades', []),
                            'final_value': full_data['metadata'].get('final_value', 0),
                            'total_return': full_data['metadata'].get('total_return', 0),
                            'initial_capital': initial_capital,
                            'strategy_name': Path(strategy_file).stem,
                            'start_date': start_date,
                            'end_date': end_date
                        }
                else:
                    backtest_data = None
            else:
                backtest_data = None
            
            # Return results with CSV path and backtest data
            return summary, trades_df, audit_log, csv_path, backtest_data
        
        def export_trades_to_csv(csv_path):
            """Return the CSV file for download"""
            if not csv_path or not os.path.exists(csv_path):
                return gr.update(visible=False)
            
            return gr.update(visible=True, value=csv_path)
        
        # Update data info when data source is selected
        def update_data_info(data_file):
            if not data_file:
                return "### 📊 Data Coverage\nSelect a data source to see available dates..."
            return f"### 📊 Data Coverage\n{get_data_coverage_info(data_file)}"
        
        data_file_dropdown.change(
            fn=update_data_info,
            inputs=[data_file_dropdown],
            outputs=[data_info]
        )
        
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
        
        # Footer
        gr.Markdown("""
        ---
        
        ### 🔍 About This System
        
        **Auditable Backtesting** provides complete transparency in options trading simulation:
        
        - ✅ **Real Market Data**: Uses actual SPY options data from parquet files
        - ✅ **Full Traceability**: Every calculation and decision is logged
        - ✅ **Strategy Transparency**: YAML-based strategy definitions
        - ✅ **Verifiable Results**: All P&L calculations are auditable
        - ✅ **No Black Box**: No mysterious calculations or hidden logic
        
        **Trust but verify** - this system gives you both.
        """)
    
    return app

if __name__ == "__main__":
    # Create and launch the interface
    app = create_auditable_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        show_error=True,
        inbrowser=False
    ) 