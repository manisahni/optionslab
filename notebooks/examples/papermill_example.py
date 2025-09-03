# %% [markdown]
# # Papermill Example: Parameterized Strategy Backtest
#
# This notebook demonstrates how to use Papermill for parameterized execution.
# It can be run with different parameters to test various market conditions and settings.
#
# ## How to Execute This Notebook
#
# ### Single Execution
# ```bash
# papermill papermill_example.py output.ipynb \
#     -p START_DATE "2023-01-01" \
#     -p END_DATE "2023-12-31" \
#     -p STRATEGY_TYPE "conservative"
# ```
#
# ### Batch Execution
# ```python
# from notebooks.utils.batch_execute import run_parameter_sweep
#
# params = [
#     {"START_DATE": "2022-01-01", "END_DATE": "2022-12-31", "STRATEGY_TYPE": "aggressive"},
#     {"START_DATE": "2023-01-01", "END_DATE": "2023-12-31", "STRATEGY_TYPE": "conservative"},
#     {"START_DATE": "2024-01-01", "END_DATE": "2024-06-30", "STRATEGY_TYPE": "balanced"}
# ]
#
# results = run_parameter_sweep("notebooks/examples/papermill_example.py", params)
# ```

# %%
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import json
from pathlib import Path

print("="*60)
print("PAPERMILL EXAMPLE NOTEBOOK")
print("="*60)
print(f"Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# %%
# Papermill Parameters Cell
# These parameters can be overridden during execution

# Date parameters
START_DATE = "2024-01-01"
END_DATE = "2024-06-30"

# Strategy parameters
STRATEGY_TYPE = "balanced"  # Options: aggressive, balanced, conservative
INITIAL_CAPITAL = 10000

# Position sizing based on strategy type
POSITION_SIZE_MAP = {
    "aggressive": 0.20,    # 20% per position
    "balanced": 0.10,      # 10% per position
    "conservative": 0.05   # 5% per position
}

# Risk parameters based on strategy type
RISK_MAP = {
    "aggressive": {"stop_loss": 0.30, "take_profit": 1.00},
    "balanced": {"stop_loss": 0.20, "take_profit": 0.50},
    "conservative": {"stop_loss": 0.10, "take_profit": 0.25}
}

# Output configuration
OUTPUT_DIR = "results/papermill_example/"
SAVE_RESULTS = True
RUN_ID = None  # Will be auto-generated if None

# %%
# Generate run ID if not provided
if RUN_ID is None:
    RUN_ID = f"{STRATEGY_TYPE}_{START_DATE}_{END_DATE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"\n📋 Execution Parameters:")
print(f"   Run ID: {RUN_ID}")
print(f"   Date Range: {START_DATE} to {END_DATE}")
print(f"   Strategy Type: {STRATEGY_TYPE}")
print(f"   Initial Capital: ${INITIAL_CAPITAL:,}")

# Get strategy-specific parameters
position_size = POSITION_SIZE_MAP[STRATEGY_TYPE]
risk_params = RISK_MAP[STRATEGY_TYPE]

print(f"   Position Size: {position_size:.0%}")
print(f"   Stop Loss: {risk_params['stop_loss']:.0%}")
print(f"   Take Profit: {risk_params['take_profit']:.0%}")

# %% [markdown]
# ## Simulated Strategy Backtest
#
# This is a simplified example that demonstrates the Papermill workflow.
# In a real implementation, this would load actual data and run a real backtest.

# %%
# Simulate a simple backtest based on parameters
np.random.seed(42)  # For reproducibility

# Generate simulated daily returns based on strategy type
days = pd.bdate_range(start=START_DATE, end=END_DATE)
n_days = len(days)

# Different return profiles for different strategies
if STRATEGY_TYPE == "aggressive":
    daily_returns = np.random.normal(0.002, 0.03, n_days)  # Higher vol, higher return
elif STRATEGY_TYPE == "conservative":
    daily_returns = np.random.normal(0.0005, 0.01, n_days)  # Lower vol, lower return
else:  # balanced
    daily_returns = np.random.normal(0.001, 0.02, n_days)   # Medium vol, medium return

# Calculate portfolio value
portfolio_values = [INITIAL_CAPITAL]
for ret in daily_returns:
    # Apply position sizing
    effective_return = ret * position_size
    
    # Apply stop loss
    if effective_return < -risk_params['stop_loss']:
        effective_return = -risk_params['stop_loss']
    
    # Apply take profit
    if effective_return > risk_params['take_profit']:
        effective_return = risk_params['take_profit']
    
    new_value = portfolio_values[-1] * (1 + effective_return)
    portfolio_values.append(new_value)

# Create results dataframe
results_df = pd.DataFrame({
    'date': days,
    'portfolio_value': portfolio_values[1:],
    'daily_return': daily_returns
})

# Calculate metrics
total_return = (portfolio_values[-1] - INITIAL_CAPITAL) / INITIAL_CAPITAL
sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252)
max_drawdown = (pd.Series(portfolio_values).cummax() - pd.Series(portfolio_values)).max() / pd.Series(portfolio_values).cummax().max()

print(f"\n📊 Backtest Results:")
print(f"   Total Return: {total_return:.2%}")
print(f"   Sharpe Ratio: {sharpe_ratio:.2f}")
print(f"   Max Drawdown: {max_drawdown:.2%}")
print(f"   Final Value: ${portfolio_values[-1]:,.2f}")

# %% [markdown]
# ## Visualization

# %%
# Create performance chart
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=results_df['date'],
    y=results_df['portfolio_value'],
    mode='lines',
    name='Portfolio Value',
    line=dict(color='blue', width=2)
))

# Add initial capital reference line
fig.add_hline(
    y=INITIAL_CAPITAL,
    line_dash="dash",
    line_color="gray",
    annotation_text="Initial Capital"
)

fig.update_layout(
    title=f"{STRATEGY_TYPE.title()} Strategy Performance ({START_DATE} to {END_DATE})",
    xaxis_title="Date",
    yaxis_title="Portfolio Value ($)",
    height=500,
    hovermode='x unified'
)

fig.show()

# %% [markdown]
# ## Save Results

# %%
if SAVE_RESULTS:
    # Create output directory
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Prepare results summary
    results_summary = {
        "run_id": RUN_ID,
        "execution_time": datetime.now().isoformat(),
        "parameters": {
            "start_date": START_DATE,
            "end_date": END_DATE,
            "strategy_type": STRATEGY_TYPE,
            "initial_capital": INITIAL_CAPITAL,
            "position_size": position_size,
            "stop_loss": risk_params['stop_loss'],
            "take_profit": risk_params['take_profit']
        },
        "results": {
            "total_return": float(total_return),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            "final_value": float(portfolio_values[-1])
        }
    }
    
    # Save JSON summary
    json_file = output_path / f"{RUN_ID}_summary.json"
    with open(json_file, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    # Save CSV data
    csv_file = output_path / f"{RUN_ID}_data.csv"
    results_df.to_csv(csv_file, index=False)
    
    # Save plot as HTML
    html_file = output_path / f"{RUN_ID}_chart.html"
    fig.write_html(str(html_file))
    
    print(f"\n💾 Results saved to {OUTPUT_DIR}")
    print(f"   Summary: {json_file.name}")
    print(f"   Data: {csv_file.name}")
    print(f"   Chart: {html_file.name}")

# %% [markdown]
# ## Parameter Sweep Example
#
# This notebook is designed to be run multiple times with different parameters.
# Here's an example of how to run a parameter sweep:

# %%
# Example code for running parameter sweep (don't execute in notebook)
example_code = """
from notebooks.utils.batch_execute import run_parameter_sweep, generate_date_ranges

# Test different strategy types across different periods
parameter_sets = []

# Generate quarterly periods for 2023-2024
date_ranges = generate_date_ranges(2023, 2024, period="quarterly")

# Test each strategy type in each period
for date_params in date_ranges:
    for strategy in ["aggressive", "balanced", "conservative"]:
        params = {
            "START_DATE": date_params["START_DATE"],
            "END_DATE": date_params["END_DATE"],
            "STRATEGY_TYPE": strategy,
            "INITIAL_CAPITAL": 10000
        }
        parameter_sets.append(params)

# Run all combinations
results = run_parameter_sweep(
    "notebooks/examples/papermill_example.py",
    parameter_sets,
    output_dir="results/strategy_comparison/",
    parallel=True,  # Run in parallel for speed
    max_workers=4
)

# Analyze results
print(f"Completed {len(results)} backtests")
print(f"Best performing: {results.nlargest(1, 'total_return')}")
"""

print("Example Parameter Sweep Code:")
print("="*60)
print(example_code)

# %% [markdown]
# ## Summary
#
# This notebook demonstrates:
# 1. **Parameterization**: Using tagged parameter cells for Papermill
# 2. **Strategy Mapping**: Different parameters based on strategy type
# 3. **Results Saving**: Structured output for analysis
# 4. **Batch Execution**: How to run parameter sweeps
#
# Key benefits of this approach:
# - **Reproducibility**: Same notebook, different parameters
# - **Scalability**: Easy to test hundreds of parameter combinations
# - **Automation**: Can be integrated into CI/CD pipelines
# - **Analysis**: Structured outputs enable systematic comparison
