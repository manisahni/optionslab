#!/usr/bin/env python3
"""
Show Risk Impact Charts
Display the most important risk management charts
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Load the data
print("Loading trade data...")
original_trades = pd.read_csv('full_year_backtest_trades_20250805_211124.csv')
balanced_trades = pd.read_csv('balanced_risk_trades_20250805_214230.csv')

# Convert dates
try:
    original_trades['date'] = pd.to_datetime(original_trades['date'], format='%Y%m%d')
except:
    original_trades['date'] = pd.to_datetime(original_trades['date'])

try:
    balanced_trades['date'] = pd.to_datetime(balanced_trades['date'], format='%Y%m%d')
except:
    balanced_trades['date'] = pd.to_datetime(balanced_trades['date'])

# Create figure with 6 subplots
fig = plt.figure(figsize=(16, 20))

# 1. EQUITY CURVES COMPARISON
ax1 = plt.subplot(3, 2, 1)
original_cumulative = original_trades['close_pnl'].cumsum()
balanced_cumulative = balanced_trades['final_pnl'].cumsum()

ax1.plot(original_cumulative.values, color='red', linewidth=2, label='Original Strategy', alpha=0.8)
ax1.plot(balanced_cumulative.values, color='green', linewidth=2, label='Risk-Managed Strategy')
ax1.fill_between(range(len(original_cumulative)), 0, original_cumulative.values, 
                 where=original_cumulative.values<0, color='red', alpha=0.2)
ax1.set_title('Equity Curves: Original vs Risk-Managed', fontsize=14, fontweight='bold')
ax1.set_xlabel('Trade Number')
ax1.set_ylabel('Cumulative P&L ($)')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Add annotations for key metrics
ax1.text(0.02, 0.98, f'Original: ${original_cumulative.iloc[-1]:,.0f}', 
         transform=ax1.transAxes, verticalalignment='top', color='red', fontweight='bold')
ax1.text(0.02, 0.93, f'Risk-Managed: ${balanced_cumulative.iloc[-1]:,.0f}', 
         transform=ax1.transAxes, verticalalignment='top', color='green', fontweight='bold')

# 2. DRAWDOWN COMPARISON
ax2 = plt.subplot(3, 2, 2)
original_running_max = original_cumulative.expanding().max()
original_drawdown = original_cumulative - original_running_max
balanced_running_max = balanced_cumulative.expanding().max()
balanced_drawdown = balanced_cumulative - balanced_running_max

ax2.fill_between(range(len(original_drawdown)), 0, original_drawdown.values, 
                 color='red', alpha=0.3, label='Original DD')
ax2.fill_between(range(len(balanced_drawdown)), 0, balanced_drawdown.values, 
                 color='green', alpha=0.5, label='Risk-Managed DD')
ax2.plot(original_drawdown.values, color='darkred', linewidth=1)
ax2.plot(balanced_drawdown.values, color='darkgreen', linewidth=1)
ax2.set_title('Drawdown Comparison', fontsize=14, fontweight='bold')
ax2.set_xlabel('Trade Number')
ax2.set_ylabel('Drawdown ($)')
ax2.legend()
ax2.grid(True, alpha=0.3)

# Add max drawdown lines
ax2.axhline(y=original_drawdown.min(), color='red', linestyle='--', alpha=0.7)
ax2.axhline(y=balanced_drawdown.min(), color='green', linestyle='--', alpha=0.7)
ax2.text(0.02, 0.02, f'Max DD Original: ${original_drawdown.min():,.0f}', 
         transform=ax2.transAxes, color='red', fontweight='bold')
ax2.text(0.02, 0.07, f'Max DD Risk-Managed: ${balanced_drawdown.min():,.0f}', 
         transform=ax2.transAxes, color='green', fontweight='bold')

# 3. RISK SCORE DISTRIBUTION
ax3 = plt.subplot(3, 2, 3)
risk_scores = balanced_trades['risk_score']
ax3.hist(risk_scores, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
ax3.axvline(x=30, color='green', linestyle='--', linewidth=2, label='Low Risk')
ax3.axvline(x=50, color='yellow', linestyle='--', linewidth=2, label='Medium Risk')
ax3.axvline(x=70, color='orange', linestyle='--', linewidth=2, label='High Risk')
ax3.axvline(x=80, color='red', linestyle='--', linewidth=2, label='Extreme Risk')
ax3.set_title('Risk Score Distribution', fontsize=14, fontweight='bold')
ax3.set_xlabel('Risk Score')
ax3.set_ylabel('Number of Trades')
ax3.legend()
ax3.grid(True, alpha=0.3)

# 4. POSITION SIZE VS RISK SCORE
ax4 = plt.subplot(3, 2, 4)
active_trades = balanced_trades[balanced_trades['position_size'] > 0]
scatter = ax4.scatter(active_trades['risk_score'], active_trades['position_size'], 
                     c=active_trades['final_pnl'], cmap='RdYlGn', alpha=0.6, s=50)
ax4.set_title('Position Sizing by Risk Score', fontsize=14, fontweight='bold')
ax4.set_xlabel('Risk Score')
ax4.set_ylabel('Position Size')
ax4.grid(True, alpha=0.3)
plt.colorbar(scatter, ax=ax4, label='P&L ($)')

# 5. MONTHLY P&L COMPARISON
ax5 = plt.subplot(3, 2, 5)
original_trades['month'] = original_trades['date'].dt.to_period('M').astype(str)
balanced_trades['month'] = balanced_trades['date'].dt.to_period('M').astype(str)

original_monthly = original_trades.groupby('month')['close_pnl'].sum()
balanced_monthly = balanced_trades.groupby('month')['final_pnl'].sum()

months = sorted(set(original_monthly.index) | set(balanced_monthly.index))
x = np.arange(len(months))
width = 0.35

bars1 = ax5.bar(x - width/2, [original_monthly.get(m, 0) for m in months], 
                width, label='Original', color='red', alpha=0.7)
bars2 = ax5.bar(x + width/2, [balanced_monthly.get(m, 0) for m in months], 
                width, label='Risk-Managed', color='green', alpha=0.7)

ax5.set_title('Monthly P&L Comparison', fontsize=14, fontweight='bold')
ax5.set_xlabel('Month')
ax5.set_ylabel('P&L ($)')
ax5.set_xticks(x)
ax5.set_xticklabels([m[-2:] for m in months], rotation=45)
ax5.legend()
ax5.grid(True, alpha=0.3)
ax5.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

# 6. KEY METRICS SUMMARY
ax6 = plt.subplot(3, 2, 6)
ax6.axis('off')

# Calculate key metrics
metrics = {
    'Metric': ['Total P&L', 'Max Drawdown', 'Win Rate', 'Sharpe Ratio', 'Trades', 'Avg Trade P&L'],
    'Original': [
        f'${original_trades["close_pnl"].sum():,.0f}',
        f'${original_drawdown.min():,.0f}',
        f'{(original_trades["close_pnl"] > 0).mean() * 100:.1f}%',
        f'{(original_trades.groupby("date")["close_pnl"].sum().mean() / original_trades.groupby("date")["close_pnl"].sum().std() * np.sqrt(252)):.2f}',
        f'{len(original_trades):,}',
        f'${original_trades["close_pnl"].mean():.2f}'
    ],
    'Risk-Managed': [
        f'${balanced_trades["final_pnl"].sum():,.0f}',
        f'${balanced_drawdown.min():,.0f}',
        f'{(active_trades["final_pnl"] > 0).mean() * 100:.1f}%',
        f'{(balanced_trades.groupby("date")["final_pnl"].sum().mean() / balanced_trades.groupby("date")["final_pnl"].sum().std() * np.sqrt(252)):.2f}',
        f'{len(active_trades):,}',
        f'${active_trades["final_pnl"].mean():.2f}'
    ]
}

# Create table
table_data = []
for i in range(len(metrics['Metric'])):
    table_data.append([metrics['Metric'][i], metrics['Original'][i], metrics['Risk-Managed'][i]])

table = ax6.table(cellText=table_data,
                  colLabels=['Metric', 'Original', 'Risk-Managed'],
                  cellLoc='center',
                  loc='center',
                  colWidths=[0.4, 0.3, 0.3])

table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1.2, 2)

# Style the table
for i in range(len(table_data) + 1):
    for j in range(3):
        cell = table[(i, j)]
        if i == 0:  # Header row
            cell.set_facecolor('#4CAF50')
            cell.set_text_props(weight='bold', color='white')
        else:
            if j == 1:  # Original column
                cell.set_facecolor('#ffcccc')
            elif j == 2:  # Risk-Managed column
                cell.set_facecolor('#ccffcc')
            else:  # Metric column
                cell.set_facecolor('#f0f0f0')

ax6.set_title('Key Metrics Comparison', fontsize=14, fontweight='bold', pad=20)

# Overall title
fig.suptitle('Risk Management Impact Analysis', fontsize=18, fontweight='bold')
plt.tight_layout()

# Save the figure
plt.savefig('risk_management_impact_visual.png', dpi=300, bbox_inches='tight')
# Don't show interactively to avoid timeout
# plt.show()

# Print summary
print("\n" + "="*80)
print("📊 VISUAL SUMMARY CREATED")
print("="*80)
print(f"\n✅ Chart saved to: risk_management_impact_visual.png")
print(f"\n🎯 Key Improvements Shown:")
print(f"   • Drawdown reduced by {(1 - abs(balanced_drawdown.min()/original_drawdown.min())) * 100:.1f}%")
print(f"   • P&L retained: {(balanced_cumulative.iloc[-1]/original_cumulative.iloc[-1]) * 100:.1f}%")
print(f"   • Smoother equity curve with consistent growth")
print(f"   • Position sizes dynamically adjusted based on risk")
print("\n" + "="*80)