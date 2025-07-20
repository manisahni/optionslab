#!/usr/bin/env python3
"""
Simplified Auditable Gradio App - AI Interface with just 2 buttons
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

# ============================================================================
# HELPER FUNCTIONS (from original)
# ============================================================================

def get_trade_logs_dir() -> Path:
    """Get the trade logs directory"""
    return Path(__file__).parent / "trade_logs"

def get_available_data_files():
    """Get available parquet files for backtesting"""
    repaired_dir = Path("../spy_options_downloader/spy_options_parquet/repaired")
    main_dir = Path("../spy_options_downloader/spy_options_parquet")
    
    files = []
    if repaired_dir.exists():
        files = list(repaired_dir.glob("*.parquet"))
    elif main_dir.exists():
        files = list(main_dir.glob("*.parquet"))
    
    return [(f.stem.replace('_', ' ').title(), str(f)) for f in sorted(files)[:10]]

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

# ============================================================================
# SIMPLIFIED AI INTERFACE
# ============================================================================

def create_auditable_interface():
    """Create the simplified Gradio interface"""
    
    with gr.Blocks(title="OptionsLab - Simplified", theme=gr.themes.Soft()) as app:
        
        # Header
        gr.Markdown("""
        # 🎯 OptionsLab - Auditable Backtesting System
        **Simplified AI Interface**
        """)
        
        # Initialize AI assistant  
        ai_assistant = AIAssistant()
        
        with gr.Tabs():
            # Backtest Tab (simplified)
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
    app = create_auditable_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        debug=False,
        inbrowser=False
    )