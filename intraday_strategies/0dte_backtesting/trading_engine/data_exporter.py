"""
Data Export Module for Trading Analysis
Packages all analysis data for external AI tools like ChatGPT
"""

import os
import json
import zipfile
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TradingDataExporter:
    """Export trading analysis data for external AI analysis"""
    
    def __init__(self, export_base_path: str = "exports"):
        self.export_base_path = Path(export_base_path)
        self.export_base_path.mkdir(exist_ok=True)
    
    def create_comprehensive_export(self, backtest_path: str, analytics_data: Dict, 
                                   plots: Dict[str, go.Figure], predictions: Optional[Dict] = None) -> str:
        """Create a comprehensive export package for external AI analysis"""
        
        # Create timestamp-based export folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"trading_analysis_export_{timestamp}"
        export_folder = self.export_base_path / export_name
        export_folder.mkdir(exist_ok=True)
        
        try:
            # 1. Copy all CSV files
            self._export_csv_files(backtest_path, export_folder)
            
            # 2. Export plots as images
            self._export_plots(plots, export_folder)
            
            # 3. Create analysis summary document
            self._create_analysis_summary(backtest_path, analytics_data, export_folder)
            
            # 4. Export strategy configuration
            self._export_strategy_config(backtest_path, export_folder)
            
            # 5. Create comprehensive AI prompt template
            self._create_ai_prompt_template(export_folder)
            
            # 6. Create data dictionary
            self._create_data_dictionary(export_folder)
            
            # 7. No predictions to export (removed HMM/XGBoost)
            
            # 8. Package everything into a ZIP file
            zip_path = self._create_zip_package(export_folder)
            
            return str(zip_path)
            
        except Exception as e:
            logger.error(f"Error creating export: {e}")
            return f"Error creating export: {str(e)}"
    
    def _export_csv_files(self, backtest_path: str, export_folder: Path):
        """Copy all relevant CSV files"""
        backtest_dir = Path(backtest_path)
        csv_folder = export_folder / "csv_data"
        csv_folder.mkdir(exist_ok=True)
        
        # Copy enhanced trades data
        enhanced_full_path = backtest_dir / "trades_enhanced_full.csv"
        if enhanced_full_path.exists():
            enhanced_df = pd.read_csv(enhanced_full_path)
            enhanced_df.to_csv(csv_folder / "trades_enhanced_full.csv", index=False)
        
        # Copy basic enhanced data as fallback
        enhanced_basic_path = backtest_dir / "trades_enhanced.csv"
        if enhanced_basic_path.exists():
            basic_df = pd.read_csv(enhanced_basic_path)
            basic_df.to_csv(csv_folder / "trades_enhanced_basic.csv", index=False)
        
        # Copy daily timeseries
        daily_path = backtest_dir / "daily_timeseries.csv"
        if daily_path.exists():
            daily_df = pd.read_csv(daily_path)
            daily_df.to_csv(csv_folder / "daily_timeseries.csv", index=False)
    
    def _export_plots(self, plots: Dict[str, go.Figure], export_folder: Path):
        """Export all plots as PNG images"""
        plots_folder = export_folder / "plots"
        plots_folder.mkdir(exist_ok=True)
        
        for plot_name, figure in plots.items():
            if figure is not None:
                try:
                    # Export as PNG
                    png_path = plots_folder / f"{plot_name}.png"
                    pio.write_image(figure, png_path, format='png', width=1200, height=800)
                    
                    # Also export as HTML for interactive viewing
                    html_path = plots_folder / f"{plot_name}.html"
                    pio.write_html(figure, html_path)
                    
                except Exception as e:
                    logger.warning(f"Could not export plot {plot_name}: {e}")
    
    def _create_analysis_summary(self, backtest_path: str, analytics_data: Dict, export_folder: Path):
        """Create comprehensive analysis summary document"""
        
        # Load backtest results
        from trading_engine.backtest_results import BacktestResults
        try:
            backtest = BacktestResults.load(os.path.basename(backtest_path))
            
            summary_content = f"""# Trading Strategy Analysis Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Strategy Configuration
- Strategy: {backtest.strategy}
- Total Trades: {len(backtest.trades_df)}
- Date Range: {backtest.trades_df['date'].min()} to {backtest.trades_df['date'].max()}
- Backtest ID: {os.path.basename(backtest_path)}

## Performance Summary
- Total P&L: ${backtest.summary_stats.get('total_pnl', 0):,.2f}
- Win Rate: {backtest.summary_stats.get('win_rate', 0)*100:.1f}%
- Average Trade: ${backtest.summary_stats.get('avg_pnl', 0):.2f}
- Best Trade: ${backtest.trades_df['pnl'].max():.2f}
- Worst Trade: ${backtest.trades_df['pnl'].min():.2f}

## Risk Metrics
{self._format_risk_metrics(analytics_data.get('risk_metrics', {}))}

## Key Insights
{analytics_data.get('clustering_insights', 'No clustering insights available')}

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
"""
            
            with open(export_folder / "ANALYSIS_SUMMARY.md", 'w') as f:
                f.write(summary_content)
                
        except Exception as e:
            logger.error(f"Error creating analysis summary: {e}")
    
    def _format_risk_metrics(self, risk_metrics: Dict) -> str:
        """Format risk metrics for the summary"""
        if not risk_metrics:
            return "Risk metrics not available"
        
        return f"""- Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 'N/A')}
- Max Drawdown: ${risk_metrics.get('max_drawdown', 'N/A')}
- Profit Factor: {risk_metrics.get('profit_factor', 'N/A')}
- Value at Risk (95%): ${risk_metrics.get('var_95', 'N/A')}
- Calmar Ratio: {risk_metrics.get('calmar_ratio', 'N/A')}"""
    
    def _export_strategy_config(self, backtest_path: str, export_folder: Path):
        """Export strategy configuration"""
        config_path = Path(backtest_path) / "config.json"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Pretty print the config
            with open(export_folder / "strategy_config.json", 'w') as f:
                json.dump(config_data, f, indent=2)
    
    def _create_ai_prompt_template(self, export_folder: Path):
        """Create AI prompt template for external analysis"""
        
        prompt_template = """# AI Analysis Prompt Template for Trading Strategy

## Instructions for AI Analysis
Use this template when analyzing the trading data with ChatGPT or other AI tools:

---

**CONTEXT:**
I'm analyzing a 0-day-to-expiration (0DTE) SPY options trading strategy. I have comprehensive backtest data with 43 technical features per trade.

**DATA PROVIDED:**
1. trades_enhanced_full.csv - Complete trade data with technical indicators
2. daily_timeseries.csv - Daily performance metrics
3. Multiple analysis plots (PNG format)
4. Strategy configuration and risk metrics

**ANALYSIS REQUEST:**
Please analyze this trading strategy performance and provide:

1. **PERFORMANCE INSIGHTS**
   - What patterns indicate strong vs weak performance?
   - Which technical conditions correlate with winning trades?
   - Are there clear time-based patterns (hourly, daily)?

2. **RISK ANALYSIS**
   - What are the main risk factors?
   - How can drawdowns be reduced?
   - What position sizing adjustments would help?

3. **OPTIMIZATION OPPORTUNITIES**
   - Which parameters should be adjusted?
   - What filter criteria would improve win rate?
   - Are there market conditions to avoid?

4. **FEATURE IMPORTANCE**
   - Which of the 43 technical features are most predictive?
   - What combinations of indicators work best?
   - Which features add noise vs signal?

5. **ACTIONABLE RECOMMENDATIONS**
   - Specific parameter changes to implement
   - Entry/exit criteria modifications
   - Risk management improvements
   - Market timing suggestions

**KEY COLUMNS TO FOCUS ON:**
- pnl (profit/loss)
- entry_hour (timing patterns)
- orb_range (breakout size)
- entry_volatility (market conditions)
- rsi_entry, bb_position, vwap_distance (technical indicators)
- duration_minutes (holding period)
- breakout_type (long/short direction)

**OUTPUT FORMAT:**
Provide specific, implementable recommendations with supporting data analysis.

---

## How to Use This Template:
1. Copy the above prompt
2. Upload the CSV files to your AI tool
3. Reference the plots for visual confirmation
4. Ask for specific analysis areas as needed

## Sample Follow-up Questions:
- "What ORB range values show the best performance?"
- "Should I filter out trades during certain hours?"
- "Which volatility conditions favor long vs short trades?"
- "How can I reduce the worst 10% of trades?"
"""
        
        with open(export_folder / "ai_prompt_template.txt", 'w') as f:
            f.write(prompt_template)
    
    def _create_data_dictionary(self, export_folder: Path):
        """Create comprehensive data dictionary"""
        
        data_dict = """# Data Dictionary - Trading Strategy Analysis

## File Descriptions

### trades_enhanced_full.csv
Complete trade data with all 43 technical features calculated.

### trades_enhanced_basic.csv  
Basic trade data with core features only.

### daily_timeseries.csv
Daily aggregated performance metrics and statistics.

## Column Definitions

### Core Trade Data
- **date**: Trade date (YYYY-MM-DD format)
- **pnl**: Profit/Loss in dollars
- **entry_price**: Entry price for the trade
- **exit_price**: Exit price for the trade
- **outcome**: Trade result ('win' or 'loss')

### Strategy Specific
- **orb_high**: Opening Range Breakout high level
- **orb_low**: Opening Range Breakout low level  
- **orb_range**: ORB range size in dollars
- **breakout**: Boolean - whether breakout occurred
- **breakout_type**: Direction ('long' or 'short')
- **breakout_time**: Time of breakout occurrence

### Technical Indicators
- **rsi_entry**: RSI (14-period) at trade entry
- **bb_upper/bb_lower**: Bollinger Band levels
- **bb_position**: Position relative to Bollinger Bands
- **vwap**: Volume Weighted Average Price
- **vwap_distance**: Distance from VWAP (%)
- **ema_20/ema_50**: Exponential Moving Averages
- **sma_20**: Simple Moving Average
- **macd/macd_signal**: MACD indicator values

### Market Conditions
- **entry_hour**: Hour of trade entry (24hr format)
- **entry_volatility**: Implied volatility at entry
- **volume**: Trading volume
- **duration_minutes**: Trade holding period

### Performance Metrics
- **daily_pnl**: P&L for the trading day
- **cumulative_pnl**: Running total P&L
- **drawdown**: Current drawdown amount
- **win_rate**: Rolling win rate percentage

### Risk Metrics
- **position_size**: Trade size/exposure
- **risk_amount**: Amount at risk per trade
- **return_pct**: Return as percentage
- **sharpe_daily**: Daily Sharpe ratio

## Data Quality Notes
- All prices are in USD
- Times are in Eastern Time (ET)
- Missing values denoted as NaN
- Boolean values: True/False or 1/0
- Percentages stored as decimals (0.50 = 50%)

## Analysis Tips
1. Focus on 'pnl' as primary outcome variable
2. Use 'entry_hour' for time-based filtering
3. 'orb_range' indicates breakout opportunity size
4. 'entry_volatility' represents market conditions
5. Technical indicators help identify setup quality
"""
        
        with open(export_folder / "data_dictionary.txt", 'w') as f:
            f.write(data_dict)
    
    # REMOVED: _export_hmm_predictions method
    # Prediction models showed no predictive value (AUC < 0.5)
    
    def _create_zip_package(self, export_folder: Path) -> str:
        """Package everything into a ZIP file"""
        zip_path = f"{export_folder}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(export_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, export_folder.parent)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    def get_export_summary(self, export_path: str) -> str:
        """Generate summary of exported data"""
        
        summary = f"""# Export Package Created Successfully! 📦

## 📁 Export Location
`{export_path}`

## 📊 Package Contents
✅ **CSV Data Files**
- trades_enhanced_full.csv (Complete 43-feature dataset)
- trades_enhanced_basic.csv (Core features)  
- daily_timeseries.csv (Daily performance)

✅ **Visual Analysis**
- regime_analysis.png (Market regime performance)
- cluster_analysis.png (Trade clustering)
- feature_importance.png (ML feature rankings)
- performance_heatmap.png (Time/volatility patterns)
- tsne_visualization.png (Trade similarity map)
- dbscan_outliers.png (Outlier detection)

✅ **Configuration & Documentation**
- strategy_config.json (Strategy parameters)
- ANALYSIS_SUMMARY.md (Comprehensive summary)
- data_dictionary.txt (Column explanations)
- ai_prompt_template.txt (ChatGPT analysis template)

## 🤖 Using with External AI Tools

### For ChatGPT Analysis:
1. **Upload the CSV files** to ChatGPT
2. **Copy the AI prompt template** from the package
3. **Reference the analysis summary** for context
4. **Use the data dictionary** for column explanations

### Sample ChatGPT Prompt:
```
I have trading strategy backtest data with 43 technical features. 
Please analyze the trades_enhanced_full.csv file and identify:
1. The most profitable trading conditions
2. Risk factors to avoid
3. Optimal parameter ranges
4. Specific filter recommendations

[Include the full prompt template from ai_prompt_template.txt]
```

## 📈 Next Steps
1. Download the ZIP package
2. Extract and review the analysis summary
3. Use with your preferred AI tool for deeper insights
4. Implement recommended optimizations in your strategy

**Happy Trading! 🚀**
"""
        
        return summary 