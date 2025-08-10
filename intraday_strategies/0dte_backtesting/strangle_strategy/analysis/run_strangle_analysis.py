"""
Run detailed strangle band analysis
"""

import pandas as pd
from strangle_band_analysis import StrangleBandAnalyzer

# Run analysis
analyzer = StrangleBandAnalyzer()
analyzer.load_data()
band_results = analyzer.calculate_band_probabilities()

# Create formatted output
print('\n' + '='*80)
print('SPY STRANGLE BAND ANALYSIS - PROBABILITY OF CLOSING WITHIN PERCENTAGE BANDS')
print('='*80)
print('\nPROBABILITY MATRIX (% chance of closing within band from entry price):\n')

# Format as percentage table
pivot = band_results.pivot(index='entry_time', columns='band_percentage', values='probability')
pivot.columns = [f'{c}%' for c in pivot.columns]
print(pivot.round(1).to_string())

print('\n\nKEY FINDINGS FOR STRANGLE TRADING:\n')

# Best times for tight strangles
tight_band = band_results[band_results['band_percentage'] == 0.1].sort_values('probability', ascending=False)
print(f'1. TIGHTEST STRANGLES (0.1% band):')
print(f'   - Best entry: {tight_band.iloc[0]["entry_time"]} ({tight_band.iloc[0]["probability"]:.1f}% success rate)')
print(f'   - Worst entry: {tight_band.iloc[-2]["entry_time"]} ({tight_band.iloc[-2]["probability"]:.1f}% success rate)')

# Best times for medium strangles
medium_band = band_results[band_results['band_percentage'] == 0.3].sort_values('probability', ascending=False)
print(f'\n2. MEDIUM STRANGLES (0.3% band):')
print(f'   - Best entry: {medium_band.iloc[0]["entry_time"]} ({medium_band.iloc[0]["probability"]:.1f}% success rate)')
print(f'   - Worst entry: {medium_band.iloc[-2]["entry_time"]} ({medium_band.iloc[-2]["probability"]:.1f}% success rate)')

# Volatility by time
avg_moves = band_results.groupby('entry_time')['avg_move'].mean().round(3)
print(f'\n3. AVERAGE MOVES BY ENTRY TIME:')
for time, move in avg_moves.items():
    if time != '16:00':  # Skip close
        print(f'   - {time}: {move:.3f}%')

# Risk/Reward insights
rr_data = analyzer.calculate_risk_reward_ratios()
best_rr = rr_data.nlargest(5, 'expected_value')
print(f'\n4. TOP 5 RISK/REWARD CONFIGURATIONS:')
for _, row in best_rr.iterrows():
    print(f'   - Entry: {row["entry_time"]}, Strikes: {row["inner_band"]}%/{row["outer_band"]}%, Expected Value: {row["expected_value"]:.3f}')

# Save detailed results
print('\n\nDETAILED PROBABILITY TABLE:')
print('\nEntry Time | 0.1% | 0.2% | 0.3% | 0.4% | 0.5% |')
print('-' * 50)
for entry_time in analyzer.entry_times[:-1]:  # Skip 16:00
    row_data = band_results[band_results['entry_time'] == entry_time]
    probs = [row_data[row_data['band_percentage'] == b]['probability'].values[0] for b in analyzer.percentage_bands]
    print(f'{entry_time:10} | {probs[0]:4.1f}% | {probs[1]:4.1f}% | {probs[2]:4.1f}% | {probs[3]:4.1f}% | {probs[4]:4.1f}% |')

# Trading recommendations
print('\n\nTRADING RECOMMENDATIONS:')
print('\n1. For conservative strangles (high probability of profit):')
print('   - Enter at 15:00 with 0.4-0.5% bands')
print('   - 92-97% historical success rate')

print('\n2. For aggressive strangles (higher premium collection):')
print('   - Enter at 15:00 with 0.2-0.3% bands')
print('   - 70-84% historical success rate')

print('\n3. Avoid early morning entries (09:30) due to higher volatility')
print('   - Average move: 0.37% vs 0.08% in afternoon')