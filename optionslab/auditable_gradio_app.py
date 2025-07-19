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

# Import our auditable backtest functions
from auditable_backtest import (
    load_and_audit_data,
    audit_strategy_config,
    find_suitable_options,
    calculate_position_size,
    run_auditable_backtest
)

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

def run_auditable_backtest_gradio(data_file, strategy_file, start_date, end_date, initial_capital):
    """Run auditable backtest and return results for Gradio"""
    
    # Capture the audit output
    import io
    import sys
    
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
            
            # Create summary
            summary = f"""
## 📊 Backtest Results

**Final Value:** ${results['final_value']:,.2f}
**Total Return:** {results['total_return']:.2%}
**Initial Capital:** ${initial_capital:,.2f}
**Total Trades:** {len([t for t in results['trades'] if 'exit_date' in t])}

### 📋 Trade Summary
"""
            
            for i, trade in enumerate(results['trades'], 1):
                if 'exit_date' in trade:
                    pnl_color = "🟢" if trade['pnl'] > 0 else "🔴"
                    summary += f"{pnl_color} **Trade {i}:** Entry ${trade['option_price']:.2f} → Exit ${trade['exit_date']:.2f} → P&L ${trade['pnl']:.2f}\n"
            
            return f"{summary}\n\n## 🔍 Full Audit Log\n```\n{audit_log}\n```"
        else:
            sys.stdout = old_stdout
            return f"❌ Backtest failed!\n\n## 🔍 Error Log\n```\n{audit_output.getvalue()}\n```"
            
    except Exception as e:
        sys.stdout = old_stdout
        return f"❌ Error during backtest: {str(e)}\n\n## 🔍 Error Log\n```\n{audit_output.getvalue()}\n```"

def create_auditable_interface():
    """Create the main Gradio interface"""
    
    with gr.Blocks(title="OptionsLab - Auditable Backtesting", theme=gr.themes.Soft()) as app:
        
        # Header
        gr.Markdown("""
        # 🎯 OptionsLab - Auditable Backtesting System
        
        **Trustworthy, traceable options backtesting with full data flow auditing.**
        
        Every step is logged and verifiable, giving you confidence in your results.
        """)
        
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
                
                # Run button
                run_btn = gr.Button("🚀 Run Auditable Backtest", variant="primary", size="lg")
                
                # Data coverage info
                data_info = gr.Markdown("### 📊 Data Coverage\nSelect a data source to see available dates...")
                
                # Status
                status = gr.Markdown("### 📈 Status\nReady to run backtest...")
            
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Results & Audit Log")
                
                # Results output
                results_output = gr.Markdown(
                    value="**Results will appear here after running a backtest.**\n\n"
                          "The audit log will show every step of the process, including:\n"
                          "• Data loading and validation\n"
                          "• Strategy configuration\n"
                          "• Option selection and pricing\n"
                          "• Trade execution and P&L calculation\n"
                          "• Final performance metrics"
                )
        
        # Event handlers
        def on_run_backtest(data_file, strategy_file, start_date, end_date, initial_capital):
            if not data_file or not strategy_file:
                return "❌ Please select both a data file and strategy file."
            
            # Update status
            status_text = "🔄 Running auditable backtest..."
            
            # Run the backtest
            results = run_auditable_backtest_gradio(data_file, strategy_file, start_date, end_date, initial_capital)
            
            return results
        
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
            inputs=[data_file_dropdown, strategy_dropdown, start_date, end_date, initial_capital],
            outputs=[results_output]
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
        server_port=7860,
        share=False,
        show_error=True
    ) 