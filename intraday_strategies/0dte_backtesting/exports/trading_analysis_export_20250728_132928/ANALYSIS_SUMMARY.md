# Trading Strategy Analysis Summary
Generated: 2025-07-28 13:29:40

## Strategy Configuration
- Strategy: ORB
- Total Trades: 495
- Date Range: 2023-07-26 to 2025-07-24
- Backtest ID: 20250728_125534_orb

## Performance Summary
- Total P&L: $2,071.41
- Win Rate: 40.8%
- Average Trade: $4.18
- Best Trade: $108.64
- Worst Trade: $-54.72

## Risk Metrics
- Sharpe Ratio: 1.0147670486807845
- Max Drawdown: $-1234.0650000000246
- Profit Factor: 1.1468648459956474
- Value at Risk (95%): $-53.784999999998426
- Calmar Ratio: 0.8681061175869659

## Key Insights
**K-means Best Performing Cluster:**
- Cluster 1.0: $13.83 avg P&L
- Win rate: 46.9%
- 196 trades

**K-means Worst Performing Cluster:**
- Cluster 2.0: $-9.34 avg P&L
- Consider avoiding these market conditions

**DBSCAN Outlier Detection:**
- Found 432 outlier trades (87.3% of total)
- Outlier avg P&L: $1.39
- ✅ Outliers are winning trades - investigate what made them special

## Data Files Included
1. **trades_enhanced_full.csv** - Complete trade data with 43 technical features
2. **trades_enhanced_basic.csv** - Basic trade data (fallback)
3. **daily_timeseries.csv** - Daily P&L and performance metrics
4. **strategy_config.json** - Strategy parameters and settings
5. **data_dictionary.txt** - Explanation of all data columns
6. **ai_prompt_template.txt** - Template for AI analysis

## Plots Included
1. **regime_analysis.png** - Performance by market regime
2. **cluster_analysis.png** - Trade clustering visualization  
3. **feature_importance.png** - ML feature importance
4. **performance_heatmap.png** - P&L heatmap by time/volatility
5. **tsne_visualization.png** - t-SNE trade patterns
6. **dbscan_outliers.png** - Outlier detection analysis

## Column Descriptions (Key Features)
- **pnl**: Profit/Loss per trade
- **win_rate**: Trade win percentage
- **entry_hour**: Hour of trade entry
- **entry_volatility**: Market volatility at entry
- **orb_range**: Opening Range Breakout range size
- **breakout_type**: Long or short breakout
- **duration_minutes**: Trade duration
- **rsi_entry**: RSI indicator at entry
- **bb_position**: Bollinger Band position
- **vwap_distance**: Distance from VWAP

## Usage Instructions
1. Review the analysis summary above
2. Examine CSV files for detailed trade data
3. View plots for visual insights
4. Use the AI prompt template to analyze with external AI tools
5. Reference the data dictionary for column explanations

---
Export created by 0DTE Trading Analysis System
