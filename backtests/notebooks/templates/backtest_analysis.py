# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
# ---

# %% [markdown]
# # Backtest Analysis Template
# 
# This notebook provides a standardized way to analyze backtest results from the centralized management system.

# %% tags=["parameters"]
# Papermill parameters - these will be overridden during execution
RESULT_ID = None  # Specific backtest result ID to analyze
COMPARE_IDS = []  # List of result IDs to compare
OUTPUT_DIR = "backtests/notebooks/analysis/"

# %%
# Setup and imports
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import json
from datetime import datetime

# Add project to path
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')

# Import BacktestManager
from backtests.backtest_manager import BacktestManager

# Initialize manager
manager = BacktestManager()

print("📊 Backtest Analysis Notebook")
print(f"Initialized at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %% [markdown]
# ## 1. Load Backtest Results

# %%
# Load specific backtest or get latest
if RESULT_ID:
    print(f"Loading backtest: {RESULT_ID}")
    backtest = manager.get_backtest(RESULT_ID)
    if not backtest:
        print(f"❌ Backtest {RESULT_ID} not found!")
        raise ValueError(f"Backtest {RESULT_ID} not found")
else:
    # Get the most recent backtest
    all_backtests = manager.list_backtests()
    if all_backtests:
        RESULT_ID = all_backtests[0]["result_id"]
        print(f"Using most recent backtest: {RESULT_ID}")
        backtest = manager.get_backtest(RESULT_ID)
    else:
        print("❌ No backtests found in the system!")
        raise ValueError("No backtests available")

# Display metadata
print("\n📋 Backtest Metadata:")
print(f"Strategy: {backtest['metadata']['strategy_name']}")
print(f"Type: {backtest['metadata']['strategy_type']}")
print(f"Period: {backtest['metadata']['start_date']} to {backtest['metadata']['end_date']}")
print(f"Description: {backtest['metadata'].get('description', 'N/A')}")

# %% [markdown]
# ## 2. Performance Metrics

# %%
# Display key metrics
metrics = backtest['results']['metrics']

print("📈 Performance Metrics:")
for key, value in metrics.items():
    if isinstance(value, (int, float)):
        if 'return' in key or 'rate' in key or 'drawdown' in key:
            print(f"{key.replace('_', ' ').title()}: {value:.2f}%")
        else:
            print(f"{key.replace('_', ' ').title()}: {value:.2f}")
    else:
        print(f"{key.replace('_', ' ').title()}: {value}")

# Create metrics visualization
if metrics:
    fig = go.Figure()
    
    # Create a bar chart of key metrics
    metric_names = []
    metric_values = []
    
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            metric_names.append(key.replace('_', ' ').title())
            metric_values.append(value)
    
    fig.add_trace(go.Bar(
        x=metric_names,
        y=metric_values,
        text=[f"{v:.2f}" for v in metric_values],
        textposition='auto',
        marker_color='lightblue'
    ))
    
    fig.update_layout(
        title=f"Performance Metrics - {backtest['metadata']['strategy_name']}",
        xaxis_title="Metric",
        yaxis_title="Value",
        height=400
    )
    
    fig.show()

# %% [markdown]
# ## 3. Audit Log Analysis

# %%
# Parse audit log for key insights
audit_lines = backtest['audit_log'].split('\n')

# Extract trade information
trades_info = []
for i, line in enumerate(audit_lines):
    if 'TRADE #' in line or 'Trade #' in line:
        # Capture this trade and next few lines
        trade_block = '\n'.join(audit_lines[i:min(i+10, len(audit_lines))])
        trades_info.append(trade_block)

print(f"📝 Found {len(trades_info)} trades in audit log")

# Display first and last trade if available
if trades_info:
    print("\n🔍 First Trade:")
    print(trades_info[0])
    
    if len(trades_info) > 1:
        print("\n🔍 Last Trade:")
        print(trades_info[-1])

# %% [markdown]
# ## 4. Strategy Comparison (Optional)

# %%
# Compare multiple backtests if IDs provided
if COMPARE_IDS and len(COMPARE_IDS) > 1:
    print(f"\n📊 Comparing {len(COMPARE_IDS)} backtests...")
    
    # Get comparison dataframe
    comparison_df = manager.compare_backtests(COMPARE_IDS)
    
    # Display comparison table
    print("\nComparison Table:")
    print(comparison_df.to_string())
    
    # Create comparison chart
    comparison_fig = manager.create_comparison_chart(COMPARE_IDS)
    comparison_fig.show()
    
elif not COMPARE_IDS:
    # Show comparison with other backtests of the same strategy
    same_strategy = [bt for bt in manager.list_backtests() 
                     if bt['strategy_type'] == backtest['metadata']['strategy_type']][:5]
    
    if len(same_strategy) > 1:
        print(f"\n📊 Comparing with other {backtest['metadata']['strategy_type']} backtests...")
        compare_ids = [bt['result_id'] for bt in same_strategy]
        
        comparison_df = manager.compare_backtests(compare_ids)
        print("\nComparison with similar strategies:")
        print(comparison_df.to_string())

# %% [markdown]
# ## 5. Historical Performance Context

# %%
# Get all backtests and show performance over time
all_backtests = manager.list_backtests()

if len(all_backtests) > 1:
    # Create a scatter plot of returns over time
    timestamps = []
    returns = []
    strategies = []
    
    for bt in all_backtests:
        if 'total_return' in bt.get('metrics', {}):
            timestamps.append(bt['timestamp'])
            returns.append(bt['metrics']['total_return'])
            strategies.append(bt['strategy_type'])
    
    if timestamps:
        fig = px.scatter(
            x=timestamps,
            y=returns,
            color=strategies,
            title="Backtest Returns Over Time",
            labels={'x': 'Run Date', 'y': 'Total Return (%)'},
            hover_data={'Strategy': strategies}
        )
        
        # Highlight current backtest
        current_timestamp = backtest['metadata']['timestamp']
        current_return = backtest['results']['metrics'].get('total_return', 0)
        
        fig.add_trace(go.Scatter(
            x=[current_timestamp],
            y=[current_return],
            mode='markers',
            marker=dict(size=15, color='red', symbol='star'),
            name='Current Backtest',
            showlegend=True
        ))
        
        fig.show()

# %% [markdown]
# ## 6. Summary Statistics

# %%
# Get overall system statistics
summary_stats = manager.get_summary_stats()

print("\n📊 Overall Backtest System Statistics:")
print(f"Total Backtests Run: {summary_stats['total_backtests']}")
print(f"Unique Strategies: {summary_stats['unique_strategies']}")
print(f"Average Return: {summary_stats.get('average_return', 0):.2f}%")

if summary_stats.get('best_performing'):
    print(f"\n🏆 Best Performing:")
    print(f"  Strategy: {summary_stats['best_performing']['strategy']}")
    print(f"  Return: {summary_stats['best_performing']['return']:.2f}%")
    print(f"  ID: {summary_stats['best_performing']['result_id']}")

if summary_stats.get('worst_performing'):
    print(f"\n📉 Worst Performing:")
    print(f"  Strategy: {summary_stats['worst_performing']['strategy']}")
    print(f"  Return: {summary_stats['worst_performing']['return']:.2f}%")
    print(f"  ID: {summary_stats['worst_performing']['result_id']}")

# %% [markdown]
# ## 7. Export Results

# %%
# Export analysis results
if OUTPUT_DIR:
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save analysis summary
    analysis_summary = {
        "analysis_date": datetime.now().isoformat(),
        "analyzed_backtest": RESULT_ID,
        "metadata": backtest['metadata'],
        "metrics": backtest['results']['metrics'],
        "summary_stats": summary_stats
    }
    
    output_file = output_path / f"analysis_{RESULT_ID}_{datetime.now():%Y%m%d_%H%M%S}.json"
    
    with open(output_file, 'w') as f:
        json.dump(analysis_summary, f, indent=2, default=str)
    
    print(f"\n✅ Analysis saved to: {output_file}")

# %% [markdown]
# ## Notes and Observations
# 
# Add your observations and insights here:
# - Key findings from this backtest
# - Comparison with expectations
# - Potential improvements or parameter adjustments
# - Next steps for strategy refinement