# Trading Strategies Guide

## Opening Range Breakout (ORB) Strategy

### Overview
The Opening Range Breakout (ORB) is a momentum-based day trading strategy that capitalizes on the volatility and directional moves that often occur after the market's initial price discovery period.

### How It Works

#### 1. Opening Range Calculation
- **Time Period**: First X minutes after market open (9:30 AM ET)
  - 5-minute ORB: 9:30 - 9:35 AM
  - 15-minute ORB: 9:30 - 9:45 AM
  - 30-minute ORB: 9:30 - 10:00 AM
  - 60-minute ORB: 9:30 - 10:30 AM
- **Range**: High and Low prices during this period

#### 2. Entry Signals
- **Long Entry**: Price breaks above the opening range high
- **Short Entry**: Price breaks below the opening range low
- **Important**: Only the first breakout of the day is traded

#### 3. Exit Rules
- **Stop Loss**: 50% of the opening range width
  - Long: Entry price - (0.5 × range width)
  - Short: Entry price + (0.5 × range width)
- **Target**: 100% of the opening range width
  - Long: Entry price + (1.0 × range width)
  - Short: Entry price - (1.0 × range width)

### Example Trade

```
Market opens at 9:30 AM
SPY trades between $450.00 - $451.00 from 9:30 - 9:45 AM
Opening Range = $1.00

At 10:15 AM, SPY breaks above $451.00

LONG TRADE:
- Entry: $451.00
- Stop Loss: $450.50 (451.00 - 0.5)
- Target: $452.00 (451.00 + 1.0)
```

### Instrument-Specific Calculations

#### Stock Trading
- **P&L Multiplier**: 1.0x
- **Example**: $1 move = $100 profit/loss per 100 shares
- **Capital Required**: Full share price × position size

#### 0DTE Options
- **P&L Multiplier**: 0.1x (typical)
- **Example**: $1 underlying move ≈ $0.10 option move
- **Capital Required**: Premium only
- **Best For**: Defined risk, high frequency

#### Futures
- **P&L Multiplier**: 2.0x (typical leverage)
- **Example**: $1 move = $200 profit/loss per contract
- **Capital Required**: Margin requirements

### Timeframe Selection Guide

#### 5-Minute ORB
- **Pros**: Fastest signals, most trades
- **Cons**: More false breakouts, requires quick execution
- **Best For**: Experienced traders, automated systems

#### 15-Minute ORB
- **Pros**: Balanced signal quality, good frequency
- **Cons**: Moderate false breakout rate
- **Best For**: Most traders, good starting point

#### 30-Minute ORB
- **Pros**: More reliable signals, cleaner breakouts
- **Cons**: Fewer trading opportunities
- **Best For**: Part-time traders, trend followers

#### 60-Minute ORB
- **Pros**: Highest quality signals, trend confirmation
- **Cons**: Very few signals, later entry
- **Best For**: Position traders, lower frequency

### Risk Management

1. **Position Sizing**
   - Risk only 1-2% of account per trade
   - Calculate shares/contracts based on stop loss distance

2. **Daily Limits**
   - Maximum 3 losses per day
   - Stop trading after reaching daily loss limit

3. **Market Conditions**
   - Best in trending markets
   - Avoid on Fed days or major news events
   - Check pre-market activity

### Performance Expectations

Based on historical backtests:
- **Win Rate**: 40-60% (varies by timeframe)
- **Risk/Reward**: 1:2 (risk $1 to make $2)
- **Profit Factor**: 1.2-1.8 (good strategies)
- **Monthly Returns**: 5-15% (with proper position sizing)

### Common Pitfalls

1. **Overtrading**: Taking multiple signals per day
2. **Moving Stops**: Never move stop loss further away
3. **Ignoring Context**: Trade with market trend
4. **Poor Timing**: Avoid first/last 5 minutes of range
5. **Revenge Trading**: Stick to the plan

### Advanced Modifications

#### Filtered ORB
- Add volume confirmation
- Require trend alignment (MA direction)
- Check market internals (TICK, ADD)

#### Dynamic Targets
- Use ATR-based targets
- Trail stops after 1R profit
- Scale out at multiple levels

#### Multi-Timeframe Confirmation
- Confirm with higher timeframe trend
- Use 5-min entry with 15-min direction
- Combine with daily levels

### Backtesting Guidelines

1. **Minimum Sample Size**: 100+ trades
2. **Include Costs**: Commissions and slippage
3. **Out-of-Sample Testing**: Reserve 20% for validation
4. **Parameter Stability**: Test neighboring values
5. **Market Regimes**: Test in different volatility periods

### Live Trading Checklist

- [ ] IB Gateway connected
- [ ] Pre-market analysis complete
- [ ] Position size calculated
- [ ] Stop loss and target set
- [ ] No major news events
- [ ] Mental stop in place
- [ ] Trading journal ready

### Resources

- [Original ORB Research Paper](https://example.com)
- [Video Tutorial](https://example.com)
- [Community Discussion](https://example.com)