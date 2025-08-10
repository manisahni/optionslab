"""
Visualize Zero DTE sample data
"""

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase
from zero_dte_analysis_tools import ZeroDTEAnalyzer
import pandas as pd
import matplotlib.pyplot as plt

# Initialize
db = ZeroDTESPYOptionsDatabase()
analyzer = ZeroDTEAnalyzer(db)

# Load sample day
sample_date = '20250505'
data = db.load_zero_dte_data(sample_date)

if not data.empty:
    print(f"\n0DTE Options Data for {sample_date}")
    print("="*60)
    
    # Get unique timestamps
    print(f"Trading hours covered: {data['timestamp'].min()} to {data['timestamp'].max()}")
    print(f"Total contracts: {data.groupby(['strike', 'right']).size().shape[0]}")
    
    # Underlying price movement
    underlying_prices = data.groupby('timestamp')['underlying_price_dollar'].first()
    print(f"\nUnderlying movement:")
    print(f"  Open: ${underlying_prices.iloc[0]:.2f}")
    print(f"  Close: ${underlying_prices.iloc[-1]:.2f}")
    print(f"  High: ${underlying_prices.max():.2f}")
    print(f"  Low: ${underlying_prices.min():.2f}")
    print(f"  Range: ${underlying_prices.max() - underlying_prices.min():.2f}")
    
    # Get strangles
    strangles = db.get_zero_dte_strangles(sample_date, delta_target=0.30)
    
    if not strangles.empty:
        print(f"\n30-Delta Strangle Analysis:")
        print(f"  Call strike: ${strangles.iloc[0]['call_strike']:.0f}")
        print(f"  Put strike: ${strangles.iloc[0]['put_strike']:.0f}")
        print(f"  Strike width: ${strangles.iloc[0]['strike_width']:.0f}")
        
        # Entry at 10:00
        entry_time = f"{sample_date[:4]}-{sample_date[4:6]}-{sample_date[6:]}T10:00:00"
        entry = strangles[strangles['timestamp'] == entry_time]
        
        if not entry.empty:
            entry = entry.iloc[0]
            print(f"\nEntry at 10:00 AM:")
            print(f"  Total credit (bid): ${entry['total_credit']:.2f}")
            print(f"  Total credit (mid): ${entry['total_mid']:.2f}")
            
            # Show intraday P&L
            print(f"\nIntraday strangle value (mid prices):")
            times = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '15:50']
            
            for time in times:
                ts = f"{sample_date[:4]}-{sample_date[4:6]}-{sample_date[6:]}T{time}:00"
                row = strangles[strangles['timestamp'] == ts]
                if not row.empty:
                    value = row.iloc[0]['total_mid']
                    pnl = entry['total_mid'] - value
                    pnl_pct = (pnl / entry['total_mid']) * 100
                    print(f"  {time}: ${value:.2f} (P&L: ${pnl:.2f}, {pnl_pct:+.1f}%)")
    
    # Create visualization
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1. Underlying price
    times = pd.to_datetime(data['timestamp']).dt.hour + pd.to_datetime(data['timestamp']).dt.minute/60
    unique_times = sorted(times.unique())
    underlying_by_time = data.groupby('timestamp')['underlying_price_dollar'].first()
    
    ax1.plot(unique_times, underlying_by_time.values)
    ax1.set_title('SPY Price Movement')
    ax1.set_xlabel('Hour')
    ax1.set_ylabel('Price ($)')
    ax1.grid(True, alpha=0.3)
    
    # 2. Bid-Ask Spreads
    atm_strike = data['strike'].median()
    atm_call = data[(data['strike'] == atm_strike) & (data['right'] == 'CALL')]
    
    if not atm_call.empty:
        ax2.plot(times[:len(atm_call)], atm_call['spread'].values)
        ax2.set_title(f'ATM Call Bid-Ask Spread (Strike: ${atm_strike:.0f})')
        ax2.set_xlabel('Hour')
        ax2.set_ylabel('Spread ($)')
        ax2.grid(True, alpha=0.3)
    
    # 3. Implied Volatility
    avg_iv_by_time = data.groupby('timestamp')['implied_vol'].mean()
    
    ax3.plot(unique_times, avg_iv_by_time.values * 100)
    ax3.set_title('Average Implied Volatility')
    ax3.set_xlabel('Hour')
    ax3.set_ylabel('IV (%)')
    ax3.grid(True, alpha=0.3)
    
    # 4. Strangle Value
    if not strangles.empty:
        strangle_times = pd.to_datetime(strangles['timestamp']).dt.hour + pd.to_datetime(strangles['timestamp']).dt.minute/60
        ax4.plot(strangle_times, strangles['total_mid'].values)
        ax4.set_title('30-Delta Strangle Value')
        ax4.set_xlabel('Hour')
        ax4.set_ylabel('Premium ($)')
        ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('zero_dte_sample_analysis.png', dpi=150)
    print(f"\n✅ Visualization saved to: zero_dte_sample_analysis.png")
    
else:
    print("No data found for sample date")