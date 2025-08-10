#!/usr/bin/env python3
"""
0DTE Trading Analysis System - Single Unified Interface
Complete trading analysis platform with manual controls and AI assistant
"""

import gradio as gr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from typing import Tuple, Optional, Dict, Any, List
import os
import re
from trading_engine.backtest_results import BacktestResults

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('system_logs/trading_app.log')
    ]
)
logger = logging.getLogger(__name__)

# Import core modules
try:
    from trading_engine.data_manager import DTEAnalystAgent
    from trading_engine.strategies.opening_range_breakout import ORBStrategy
    from trading_engine.strategies.vwap_reversion import VWAPBounceStrategy
    from trading_engine.strategies.gap_momentum import GapAndGoStrategy
    from trading_engine.charting.chart_generator import Visualizer
    from trading_engine.helpers.orb_utilities import test_orb_strategy
    from trading_engine.helpers.strategy_comparison import (
        test_vwap_bounce_strategy, 
        test_gap_and_go_strategy, 
        compare_all_strategies
    )
    
    # Initialize once
    agent = DTEAnalystAgent()
    visualizer = Visualizer()
    logger.info(f"Successfully loaded {len(agent.df)} bars of SPY data")
    DATA_AVAILABLE = True
except Exception as e:
    logger.error(f"Failed to initialize: {e}")
    agent = None
    visualizer = None
    DATA_AVAILABLE = False

# Try to import AI components (optional)
try:
    from langchain_experimental.agents import create_pandas_dataframe_agent
    from langchain_openai import ChatOpenAI
    from langchain.agents.agent_types import AgentType
    from configuration import app_settings as config
    AI_AVAILABLE = bool(config.AI_API_KEY)
except Exception as e:
    logger.warning(f"AI components not available: {e}")
    AI_AVAILABLE = False
    config = None


class TradingAnalyzer:
    """Unified trading analyzer with all strategies and AI capabilities"""
    
    def __init__(self):
        self.agent = agent
        self.visualizer = visualizer
        self.ai_agent = None
        # Export-related variables
        self.current_backtest_id = None
        self.current_analytics_data = None
        self.current_plots = None
        
        # Initialize AI if available
        if AI_AVAILABLE and config and config.AI_API_KEY:
            try:
                # Configure for LM Studio or OpenAI
                if config.AI_BASE_URL:
                    # LM Studio configuration
                    self.llm = ChatOpenAI(
                        model=config.MODEL_NAME,
                        temperature=config.TEMPERATURE,
                        openai_api_key=config.AI_API_KEY,
                        openai_api_base=config.AI_BASE_URL
                    )
                else:
                    # Standard OpenAI configuration
                    self.llm = ChatOpenAI(
                        model=config.MODEL_NAME,
                        temperature=config.TEMPERATURE,
                        openai_api_key=config.AI_API_KEY
                    )
                logger.info("AI components initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize AI: {e}")
                self.llm = None
        else:
            self.llm = None
    
    def analyze_strategy(
        self, 
        strategy: str,
        timeframe: int,
        days: int,
        instrument: str,
        min_gap_pct: float = 0.3,
        min_distance_pct: float = 0.02,
        starting_capital: float = 25000,
        risk_per_trade: float = 2.0
    ) -> Tuple[str, Optional[go.Figure], Optional[go.Figure], Optional[go.Figure], Optional[str]]:
        """Analyze selected strategy with given parameters"""
        if not DATA_AVAILABLE:
            return "❌ Data not available. Please ensure SPY data is downloaded.", None, None, None, None
        
        try:
            # Get data for the period
            df = self.agent.get_last_n_days(days)
            if df is None or df.empty:
                return f"❌ No data for the last {days} days", None, None, None, None
            
            # Run the selected strategy
            if strategy == "ORB":
                result = self._run_orb_strategy(df, timeframe, instrument, starting_capital, risk_per_trade)
            elif strategy == "VWAP Bounce":
                result = self._run_vwap_strategy(df, min_distance_pct)
            elif strategy == "Gap and Go":
                result = self._run_gap_strategy(df, min_gap_pct)
            elif strategy == "Compare All":
                return self._compare_all_strategies(df, days)
            else:
                return f"❌ Unknown strategy: {strategy}", None, None, None, None
            
            if result is None:
                return f"❌ No trades found for {strategy} strategy", None, None, None, None
            
            # Format results with parameters
            params = {}
            if strategy == "ORB":
                params = {'timeframe': timeframe, 'instrument': instrument, 
                         'starting_capital': starting_capital, 'risk_per_trade': risk_per_trade}
                summary = self._format_results(result, strategy, **params)
            elif strategy == "VWAP Bounce":
                params = {'min_distance_pct': min_distance_pct}
                summary = self._format_results(result, strategy, **params)
            elif strategy == "Gap and Go":
                params = {'min_gap_pct': min_gap_pct}
                summary = self._format_results(result, strategy, **params)
            else:
                summary = self._format_results(result, strategy)
            
            # Create visualizations with params
            price_plot = None
            pnl_plot = None
            drawdown_plot = None
            
            if 'trades_df' in result and not result['trades_df'].empty:
                # Create price plot
                price_plot = self._create_price_plot(result['trades_df'])
                
                # Create P&L plot
                pnl_plot = self._create_strategy_plot(result, strategy, **params)
                
                # Create drawdown plot
                drawdown_plot = self._create_drawdown_plot(result['trades_df'], **params)
            
            # Prepare export data with enhanced market context
            export_csv = None
            if 'trades_df' in result and not result['trades_df'].empty:
                # Create enhanced export with market data and indicators
                enhanced_df = self._create_enhanced_export(result['trades_df'], self.agent.df)
                
                # Create a temporary file for export
                import tempfile
                import os
                from datetime import datetime
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                strategy_name = strategy.replace(' ', '_').lower()
                filename = f"{strategy_name}_enhanced_{timestamp}.csv"
                
                # Create temp file
                temp_dir = tempfile.gettempdir()
                filepath = os.path.join(temp_dir, filename)
                
                # Save enhanced CSV to file
                enhanced_df.to_csv(filepath, index=False)
                export_csv = filepath
                
                # Save complete backtest results
                save_message = ""
                try:
                    print(f"DEBUG: Creating BacktestResults with {len(enhanced_df)} trades")
                    print(f"DEBUG: Enhanced df columns: {list(enhanced_df.columns)[:10]}...")
                    
                    # Try saving with original trades_df first
                    backtest = BacktestResults(
                        strategy=strategy,
                        params=params,
                        trades_df=result['trades_df'],  # Use original, not enhanced
                        market_df=self.agent.df
                    )
                    print(f"DEBUG: BacktestResults created, calling save_all()")
                    save_path = backtest.save_all()
                    
                    # Now try to save enhanced CSV separately
                    try:
                        import os
                        enhanced_path = os.path.join(save_path, "trades_enhanced_full.csv")
                        enhanced_df.to_csv(enhanced_path, index=False)
                        print(f"DEBUG: Enhanced CSV saved to {enhanced_path}")
                    except Exception as e2:
                        print(f"DEBUG: Failed to save enhanced CSV: {e2}")
                    
                    save_message = f"\n\n✅ **Backtest saved to:** `{save_path}`"
                    logger.info(f"Backtest results saved to: {save_path}")
                    print(f"DEBUG: Save completed successfully")
                except Exception as e:
                    save_message = f"\n\n❌ **Failed to save backtest:** {str(e)}"
                    logger.error(f"Error saving backtest results: {e}")
                    print(f"DEBUG: Error saving backtest: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Add save message to summary
            summary = summary + save_message if summary else save_message
            
            return summary, price_plot, pnl_plot, drawdown_plot, export_csv
            
        except Exception as e:
            logger.error(f"Strategy analysis error: {e}", exc_info=True)
            return f"❌ Error during analysis: {str(e)}", None, None, None, None
    
    def _run_orb_strategy(self, df: pd.DataFrame, timeframe: int, instrument: str, 
                          starting_capital: float = 25000, risk_per_trade: float = 2.0) -> Dict:
        """Run ORB strategy"""
        orb = ORBStrategy(
            timeframe_minutes=timeframe,
            instrument_type=instrument.lower(),
            starting_capital=starting_capital,
            risk_per_trade=risk_per_trade
        )
        results_df = orb.backtest(df)
        
        if results_df.empty:
            return None
            
        stats = orb.calculate_statistics(results_df)
        
        # Use current_capital if available, otherwise calculate cumulative P&L
        if 'current_capital' in results_df.columns:
            # Calculate P&L as difference from starting capital
            results_df['cumulative_pnl'] = results_df['current_capital'] - starting_capital
        else:
            # Fallback to simple cumsum
            results_df['cumulative_pnl'] = results_df['pnl'].cumsum()
        
        return {
            'trades_df': results_df,
            'stats': stats,
            'strategy_name': f"{timeframe}-Minute ORB",
            'starting_capital': starting_capital
        }
    
    def _run_vwap_strategy(self, df: pd.DataFrame, min_distance_pct: float) -> Dict:
        """Run VWAP Bounce strategy"""
        result = test_vwap_bounce_strategy(df, min_distance_pct=min_distance_pct)
        if result is None or result.get('results_df', pd.DataFrame()).empty:
            return None
        # Convert results_df to trades_df for consistency
        result['trades_df'] = result.get('results_df', pd.DataFrame())
        return result
    
    def _run_gap_strategy(self, df: pd.DataFrame, min_gap_pct: float) -> Dict:
        """Run Gap and Go strategy"""
        result = test_gap_and_go_strategy(df, min_gap_pct=min_gap_pct)
        if result is None or result.get('results_df', pd.DataFrame()).empty:
            return None
        # Convert results_df to trades_df for consistency
        result['trades_df'] = result.get('results_df', pd.DataFrame())
        return result
    
    def _compare_all_strategies(self, df: pd.DataFrame, days: int) -> Tuple[str, Optional[go.Figure], Optional[go.Figure], Optional[go.Figure], Optional[str]]:
        """Compare all strategies"""
        comparison_df = compare_all_strategies(df, days=days)
        
        # Create comparison visualization with proper scaling
        fig = go.Figure()
        
        # Get all available strategies from the comparison_df
        all_strategies = list(comparison_df.columns)
        
        # Define color scheme
        color_map = {
            'ORB_5min': 'blue',
            'ORB_5min_Long': 'lightblue', 
            'ORB_5min_Short': 'darkblue',
            'ORB_15min': 'green',
            'ORB_15min_Long': 'lightgreen',
            'ORB_15min_Short': 'darkgreen', 
            'ORB_30min': 'red',
            'ORB_30min_Long': 'lightcoral',
            'ORB_30min_Short': 'darkred',
            'ORB_60min': 'purple',
            'ORB_60min_Long': 'plum',
            'ORB_60min_Short': 'indigo',
            'VWAP_Bounce': 'orange',
            'Gap_and_Go': 'brown'
        }
        
        # Calculate the range for each strategy to determine scaling
        strategy_ranges = {}
        for strategy in all_strategies:
            if strategy in comparison_df.columns:
                strategy_data = comparison_df[strategy].dropna()
                if not strategy_data.empty:
                    strategy_ranges[strategy] = {
                        'min': strategy_data.min(),
                        'max': strategy_data.max(),
                        'range': strategy_data.max() - strategy_data.min()
                    }
        
        # Find the overall range for scaling
        if strategy_ranges:
            all_min = min([r['min'] for r in strategy_ranges.values()])
            all_max = max([r['max'] for r in strategy_ranges.values()])
            overall_range = all_max - all_min
        else:
            overall_range = 1  # Fallback
        
        # Sort strategies to group related ones together
        sorted_strategies = sorted(all_strategies, key=lambda x: (
            x.replace('_Long', '').replace('_Short', ''),  # Group by base strategy
            '_Long' in x,  # Then by direction
            '_Short' in x
        ))
        
        for strategy in sorted_strategies:
            if strategy in comparison_df.columns:
                strategy_data = comparison_df[strategy].dropna()
                if not strategy_data.empty:
                    # Determine line style based on strategy type
                    if '_Long' in strategy:
                        line_style = dict(dash='dot')
                    elif '_Short' in strategy:
                        line_style = dict(dash='dash')
                    else:
                        line_style = dict()
                    
                    # Get color from map
                    color = color_map.get(strategy, 'gray')
                    
                    # Use actual P&L values without normalization
                    fig.add_trace(go.Scatter(
                        x=comparison_df.index,
                        y=strategy_data,
                        mode='lines',
                        name=f"{strategy.replace('_', ' ')}",
                        line=dict(color=color, width=2, **line_style),
                        hovertemplate=f"{strategy.replace('_', ' ')}<br>" +
                                    "P&L: $%{y:,.2f}<br>" +
                                    "<extra></extra>"
                    ))
        
        fig.update_layout(
            title=f"Strategy Comparison - Last {days} Days",
            xaxis_title="Date",
            yaxis_title="Cumulative P&L ($)",
            height=600,
            hovermode='x unified',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="gray",
                borderwidth=1
            ),
            margin=dict(r=200)  # Make room for legend
        )
        
        # Add a second subplot for absolute P&L values
        fig2 = go.Figure()
        
        for strategy in sorted_strategies:
            if strategy in comparison_df.columns:
                strategy_data = comparison_df[strategy].dropna()
                if not strategy_data.empty:
                    # Determine line style based on strategy type
                    if '_Long' in strategy:
                        line_style = dict(dash='dot')
                    elif '_Short' in strategy:
                        line_style = dict(dash='dash')
                    else:
                        line_style = dict()
                    
                    # Get color from map
                    color = color_map.get(strategy, 'gray')
                    
                    fig2.add_trace(go.Scatter(
                        x=comparison_df.index,
                        y=strategy_data,
                        mode='lines',
                        name=strategy.replace('_', ' '),
                        line=dict(color=color, width=2, **line_style),
                        hovertemplate=f"{strategy.replace('_', ' ')}<br>" +
                                    "P&L: $%{y:.2f}<br>" +
                                    "<extra></extra>"
                    ))
        
        fig2.update_layout(
            title=f"Strategy Comparison - Last {days} Days (Absolute P&L)",
            xaxis_title="Date",
            yaxis_title="Cumulative P&L ($)",
            height=600,
            hovermode='x unified',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="gray",
                borderwidth=1
            ),
            margin=dict(r=200)  # Make room for legend
        )
        
        # Summary statistics with strategy descriptions
        summary = "# Strategy Comparison Results\n\n"
        if days == 0:
            summary += f"Period: All Available Data ({len(comparison_df)} trading days)\n\n"
        else:
            summary += f"Period: Last {days} days\n\n"
        
        # Add strategy descriptions
        summary += "## Strategy Overview\n\n"
        summary += "### ORB (Opening Range Breakout) Strategies\n"
        summary += "**What they do:** Capture momentum from opening range breakouts. Calculate high/low during first 5-60 minutes, then trade breakouts above/below that range.\n"
        summary += "**Best for:** High volatility at market open, trending markets, strong volume.\n\n"
        
        summary += "### VWAP Bounce Strategy\n"
        summary += "**What it does:** Trades mean reversion off the Volume Weighted Average Price (VWAP) line.\n"
        summary += "**Best for:** Ranging markets, strong institutional volume at VWAP, support/resistance levels.\n\n"
        
        summary += "### Gap and Go Strategy\n"
        summary += "**What it does:** Trades opening gaps that continue in the gap direction.\n"
        summary += "**Best for:** High pre-market volatility, overnight news/earnings, momentum continuation.\n\n"
        
        summary += "## Final P&L by Strategy:\n"
        
        # Group strategies by base name for organized display
        strategy_groups = {}
        for strategy in sorted_strategies:
            if strategy in comparison_df.columns:
                base_name = strategy.replace('_Long', '').replace('_Short', '')
                if base_name not in strategy_groups:
                    strategy_groups[base_name] = {}
                
                final_pnl = comparison_df[strategy].iloc[-1]
                max_pnl = strategy_ranges[strategy]['max'] if strategy in strategy_ranges else 0
                
                if '_Long' in strategy:
                    strategy_groups[base_name]['long'] = (final_pnl, max_pnl)
                elif '_Short' in strategy:
                    strategy_groups[base_name]['short'] = (final_pnl, max_pnl)
                else:
                    strategy_groups[base_name]['total'] = (final_pnl, max_pnl)
        
        # Display results grouped
        for base_strategy, results in strategy_groups.items():
            if 'total' in results:
                final_pnl, max_pnl = results['total']
                summary += f"- **{base_strategy.replace('_', ' ')}**: ${final_pnl:,.2f} (Max: ${max_pnl:,.0f})\n"
                
                if 'long' in results:
                    long_pnl, long_max = results['long']
                    summary += f"  - Long: ${long_pnl:,.2f} (Max: ${long_max:,.0f})\n"
                
                if 'short' in results:
                    short_pnl, short_max = results['short']
                    summary += f"  - Short: ${short_pnl:,.2f} (Max: ${short_max:,.0f})\n"
        
        # Export comparison data
        export_csv = None
        if not comparison_df.empty:
            # Create a temporary file for export
            import tempfile
            import os
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"strategy_comparison_{timestamp}.csv"
            
            # Create temp file
            temp_dir = tempfile.gettempdir()
            filepath = os.path.join(temp_dir, filename)
            
            # Save CSV to file
            comparison_df.to_csv(filepath)
            export_csv = filepath
        
        # Wrap in scrollable div with pre-formatted text for better visibility
        wrapped_summary = f"""<div style='height: 500px; overflow-y: auto; padding: 20px; background-color: #ffffff; border: 2px solid #333333; border-radius: 8px;'>
<pre style='font-family: "Courier New", Monaco, monospace; color: #000000; font-size: 14px; white-space: pre-wrap; margin: 0; line-height: 1.5;'>
{summary}
</pre>
</div>"""
        
        return wrapped_summary, None, fig, fig2, export_csv  # Return both normalized and absolute plots
    
    def _format_results(self, result: Dict, strategy: str, **params) -> str:
        """Format strategy results into readable summary with strategy description and parameters"""
        stats = result.get('stats', {})
        trades_df = result.get('trades_df', pd.DataFrame())
        
        # Calculate additional metrics if needed
        if not trades_df.empty and 'cumulative_pnl' not in trades_df.columns:
            trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        
        max_drawdown = 0
        if not trades_df.empty:
            max_drawdown = (trades_df['cumulative_pnl'] - 
                           trades_df['cumulative_pnl'].expanding().max()).min()
        
        # Calculate long/short statistics
        long_stats = self._calculate_direction_stats(trades_df, 'long')
        short_stats = self._calculate_direction_stats(trades_df, 'short')
        
        # Get strategy description and parameters
        strategy_info = self._get_strategy_description(strategy, **params)
        
        # Get instrument type and multiplier
        instrument = params.get('instrument', 'Options')
        multiplier_map = {'Stock': 1.0, 'Options': 0.1, 'Futures': 2.0}
        multiplier = multiplier_map.get(instrument, 0.1)
        
        # Add position sizing info only if the columns exist
        position_info = ""
        if not trades_df.empty:
            if 'position_size' in trades_df.columns:
                avg_pos = int(trades_df['position_size'].mean())
                position_info += f"- **Average Position Size**: {avg_pos} units\n"
            if 'capital_used' in trades_df.columns:
                avg_capital = trades_df['capital_used'].mean()
                position_info += f"- **Average Capital Used**: ${avg_capital:,.0f} per trade\n"
        
        summary = f"""# {strategy} Strategy Analysis

{strategy_info}

## 💰 P&L Calculation Details
- **Instrument Type**: {instrument}
- **P&L Multiplier**: {multiplier}x
- **What this means**: For every $1 SPY moves, your P&L changes by ${multiplier:.2f}
- **Example**: If SPY moves $2.00, your profit/loss = $2.00 × {multiplier} = ${2.0 * multiplier:.2f}

## 💵 Capital & Position Sizing
- **Starting Capital**: ${params.get('starting_capital', 25000):,.0f}
- **Risk Per Trade**: {params.get('risk_per_trade', 2.0):.1f}%
{position_info}

## Overall Performance
- **Total Trades**: {stats.get('total_trades', 0)}
- **Win Rate**: {stats.get('win_rate', 0):.1%}
- **Total P&L**: ${stats.get('total_pnl', 0):,.2f} ({instrument} adjusted)
- **Profit Factor**: {stats.get('profit_factor', 0):.2f}
- **Average Win**: ${stats.get('avg_win', 0):.2f}
- **Average Loss**: ${stats.get('avg_loss', 0):.2f}
- **Max Drawdown**: ${max_drawdown:,.2f}
- **Sharpe Ratio**: {stats.get('sharpe_ratio', 0):.2f}

## Long Trades Performance
- **Total Long Trades**: {long_stats['total']}
- **Long Win Rate**: {long_stats['win_rate']:.1%}
- **Long P&L**: ${long_stats['total_pnl']:,.2f}
- **Avg Long Win**: ${long_stats['avg_win']:.2f}
- **Avg Long Loss**: ${long_stats['avg_loss']:.2f}

## Short Trades Performance
- **Total Short Trades**: {short_stats['total']}
- **Short Win Rate**: {short_stats['win_rate']:.1%}
- **Short P&L**: ${short_stats['total_pnl']:,.2f}
- **Avg Short Win**: ${short_stats['avg_win']:.2f}
- **Avg Short Loss**: ${short_stats['avg_loss']:.2f}

## Direction Analysis
- **Best Direction**: {'Long' if long_stats['total_pnl'] > short_stats['total_pnl'] else 'Short'}
- **Long vs Short Ratio**: {long_stats['total']}/{short_stats['total']}

## Recent Trades
{self._format_recent_trades(trades_df)}
"""
        
        # Wrap in scrollable div with pre-formatted text for better visibility
        return f"""<div style='height: 500px; overflow-y: auto; padding: 20px; background-color: #ffffff; border: 2px solid #333333; border-radius: 8px;'>
<pre style='font-family: "Courier New", Monaco, monospace; color: #000000; font-size: 14px; white-space: pre-wrap; margin: 0; line-height: 1.5;'>
{summary}
</pre>
</div>"""
    
    def _get_strategy_description(self, strategy: str, **params) -> str:
        """Get detailed strategy description and parameters"""
        
        if "ORB" in strategy:
            timeframe = params.get('timeframe', 15)
            instrument = params.get('instrument', 'Options')
            
            return f"""## Strategy Description: Opening Range Breakout (ORB)

**What This Strategy Does:**
The ORB strategy captures momentum from the opening range breakout. It calculates the high and low during the first {timeframe} minutes of trading (9:30 AM to {9 + timeframe//60}:{timeframe%60:02d} AM), then enters trades when price breaks above the high (long) or below the low (short).

**Entry Logic:**
- **Long Signal**: Price breaks above the {timeframe}-minute opening range high
- **Short Signal**: Price breaks below the {timeframe}-minute opening range low
- **Entry Price**: At the breakout level (opening range high/low)
- **Only First Breakout**: Only the first breakout of the day is traded

**Exit Logic:**
- **Stop Loss**: 50% of the opening range width
- **Target**: 100% of the opening range width
- **Exit**: First to hit stop loss or target

**Example Scenario:**
If SPY opens at $500 and trades between $500.50-$501.50 in the first {timeframe} minutes (1-point range):
- Long entry at $501.50 (breakout above high)
- Stop loss at $501.00 (50% of 1-point range)
- Target at $502.50 (100% of 1-point range)

## Strategy Parameters
- **Timeframe**: {timeframe} minutes (opening range calculation period)
- **Instrument Type**: {instrument}
- **Stop Loss**: 50% of opening range width (hardcoded)
- **Target**: 100% of opening range width (hardcoded)
- **P&L Multiplier**: {0.1 if instrument == 'Options' else 1.0 if instrument == 'Stock' else 2.0}x ({'10% of underlying move' if instrument == 'Options' else 'Full price difference' if instrument == 'Stock' else '2x leverage'})

**Best Market Conditions:**
- High volatility in first {timeframe} minutes after market open
- Trending markets with clear directional moves
- Strong volume at market open
- Avoid choppy/ranging markets"""

        elif "VWAP" in strategy:
            min_distance = params.get('min_distance_pct', 0.02)
            
            return f"""## Strategy Description: VWAP Bounce

**What This Strategy Does:**
The VWAP Bounce strategy trades mean reversion off the Volume Weighted Average Price (VWAP) line. VWAP acts as a dynamic support/resistance level throughout the day, and price tends to revert to VWAP after deviations.

**Entry Logic:**
- **Long Signal**: Price touches VWAP from above (bounce up)
- **Short Signal**: Price touches VWAP from below (bounce down)
- **Entry Price**: At VWAP level when bounce occurs
- **Minimum Distance**: {min_distance}% from VWAP to trigger signal

**Exit Logic:**
- **Stop Loss**: 1.2 ATR (Average True Range) from entry
- **Target**: 1.8 ATR from entry
- **Time Stop**: No new positions after 3:30 PM

**Example Scenario:**
If SPY is trading at $500 and VWAP is at $499.50:
- Price drops to $499.50 (touches VWAP from above)
- Long signal triggered at $499.50
- Stop loss at $498.26 (1.2 ATR below entry)
- Target at $500.74 (1.8 ATR above entry)

## Strategy Parameters
- **Min Distance from VWAP**: {min_distance}% (minimum distance for bounce signals)
- **Stop Loss**: 1.2 ATR (tighter stops for mean reversion)
- **Target**: 1.8 ATR (realistic targets for mean reversion)
- **Trading Hours**: 9:30 AM - 3:30 PM (no new positions after 3:30 PM)
- **P&L Multiplier**: 0.1x (10% of underlying move for options simulation)

**Best Market Conditions:**
- Ranging/choppy markets
- Strong institutional volume at VWAP
- Markets with clear support/resistance levels
- Avoid strong trending markets"""

        elif "Gap" in strategy:
            min_gap = params.get('min_gap_pct', 0.3)
            
            return f"""## Strategy Description: Gap and Go

**What This Strategy Does:**
The Gap and Go strategy trades opening gaps that continue in the direction of the gap. Large gaps indicate overnight sentiment shift and often continue in the morning session.

**Entry Logic:**
- **Gap Detection**: Opening gap > {min_gap}% from previous close
- **Confirmation**: Price continues in gap direction for 3 bars
- **Entry**: In direction of gap (long for gap up, short for gap down)
- **Entry Cutoff**: Only enter in first hour (before 10:30 AM)

**Exit Logic:**
- **Stop Loss**: {min_gap * 1.67:.1f}% from entry
- **Target**: {min_gap * 3.33:.1f}% from entry
- **Time Stop**: Exit after 120 minutes (2 hours)

**Example Scenario:**
If SPY closed at $500 and opens at $501.50 (0.3% gap up):
- Gap detected: $501.50 vs $500 (0.3% gap)
- Price continues higher for 3 bars → Long confirmation
- Entry at $501.50
- Stop loss at $499.50 (0.5% below entry)
- Target at $504.50 (1.0% above entry)

## Strategy Parameters
- **Minimum Gap Size**: {min_gap}% (minimum gap to consider)
- **Confirmation Bars**: 3 bars (to confirm gap continuation)
- **Stop Loss**: 0.5% from entry
- **Target**: 1.0% from entry
- **Time Stop**: 120 minutes (2 hours maximum hold)
- **Entry Cutoff**: 10:30 AM (only enter in first hour)
- **P&L Multiplier**: 0.1x (10% of underlying move for options simulation)

**Best Market Conditions:**
- High pre-market volatility
- Strong overnight news/earnings
- Markets with clear momentum continuation
- First 2 hours of trading session
- Avoid choppy/ranging markets"""


        else:
            return f"""## Strategy Description: {strategy}

Strategy details and parameters not available for this strategy type.

## Strategy Parameters
- **Parameters**: {params if params else 'No parameters specified'}"""

    def _calculate_direction_stats(self, trades_df: pd.DataFrame, direction: str) -> Dict:
        """Calculate statistics for a specific trade direction"""
        if trades_df.empty:
            return {
                'total': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        

        
        # Handle different column names for different strategies
        if 'breakout_type' in trades_df.columns:
            # ORB strategy uses 'breakout_type' with 'long'/'short'
            direction_trades = trades_df[trades_df['breakout_type'] == direction]
        elif 'signal_type' in trades_df.columns:
            # VWAP strategy uses 'signal_type' with 'bounce_up'/'bounce_down'
            if direction == 'long':
                direction_trades = trades_df[trades_df['signal_type'] == 'bounce_up']
            elif direction == 'short':
                direction_trades = trades_df[trades_df['signal_type'] == 'bounce_down']
            else:
                direction_trades = pd.DataFrame()
        else:
            # No direction column found
            return {
                'total': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        if direction_trades.empty:
            return {
                'total': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_win': 0,
                'avg_loss': 0
            }
        
        wins = direction_trades[direction_trades['pnl'] > 0]
        losses = direction_trades[direction_trades['pnl'] <= 0]
        
        return {
            'total': len(direction_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(direction_trades) if len(direction_trades) > 0 else 0,
            'total_pnl': float(direction_trades['pnl'].sum()) if len(direction_trades) > 0 else 0.0,
            'avg_win': float(wins['pnl'].mean()) if len(wins) > 0 else 0.0,
            'avg_loss': float(losses['pnl'].mean()) if len(losses) > 0 else 0.0
        }
    
    def _format_recent_trades(self, trades_df: pd.DataFrame) -> str:
        """Format recent trades with direction information"""
        if trades_df.empty:
            return "No trades"
        
        recent = trades_df.tail(10).copy()
        
        # Check if 'date' is in index instead of columns
        if 'date' not in recent.columns and isinstance(recent.index, pd.DatetimeIndex):
            recent = recent.reset_index()
            if 'index' in recent.columns:
                recent = recent.rename(columns={'index': 'date'})
        
        # Handle different column names for different strategies
        if 'breakout_type' in recent.columns:
            # ORB strategy
            recent['direction'] = recent['breakout_type'].apply(lambda x: '↑ Long' if x == 'long' else '↓ Short' if x == 'short' else '')
            return recent[['date', 'direction', 'pnl']].to_string(index=False)
        elif 'signal_type' in recent.columns:
            # VWAP strategy
            recent['direction'] = recent['signal_type'].apply(lambda x: '↑ Long' if x == 'bounce_up' else '↓ Short' if x == 'bounce_down' else '')
            return recent[['date', 'direction', 'pnl']].to_string(index=False)
        else:
            return recent[['date', 'pnl']].to_string(index=False)
    
    def _create_price_plot(self, trades_df: pd.DataFrame) -> go.Figure:
        """Create SPY price chart with candlesticks and EMAs"""
        if trades_df.empty:
            return None
            
        # Import technical indicators
        from market_analysis.technical_indicators import ema
        import plotly.graph_objects as go
        
        # Ensure trades_df has 'date' column
        if 'date' not in trades_df.columns and isinstance(trades_df.index, pd.DatetimeIndex):
            trades_df = trades_df.reset_index()
            if 'index' in trades_df.columns:
                trades_df = trades_df.rename(columns={'index': 'date'})
        
        # Get SPY price data for the period
        start_date = trades_df['date'].min()
        end_date = trades_df['date'].max()
        
        # Get price data from agent - handle timezone comparison
        if 'date' in self.agent.df.columns:
            # Check if timezone aware and convert if needed
            agent_tz = self.agent.df['date'].dt.tz
            if agent_tz is not None and hasattr(start_date, 'tz'):
                # Both are timezone aware - ensure same timezone
                if start_date.tz is None:
                    start_date = start_date.tz_localize(agent_tz)
                    end_date = end_date.tz_localize(agent_tz)
                elif start_date.tz != agent_tz:
                    start_date = start_date.tz_convert(agent_tz)
                    end_date = end_date.tz_convert(agent_tz)
            elif agent_tz is not None and not hasattr(start_date, 'tz'):
                # Agent data is timezone aware but dates are not
                start_date = pd.Timestamp(start_date).tz_localize(agent_tz)
                end_date = pd.Timestamp(end_date).tz_localize(agent_tz)
            
            price_data = self.agent.df[
                (self.agent.df['date'] >= start_date) & 
                (self.agent.df['date'] <= end_date)
            ].copy()
        else:
            # Date is in index
            price_data = self.agent.df[
                (self.agent.df.index >= start_date) & 
                (self.agent.df.index <= end_date)
            ].copy()
        
        # Ensure we have valid OHLC data
        if price_data.empty or not all(col in price_data.columns for col in ['open', 'high', 'low', 'close']):
            return None
            
        # Aggregate to daily candlesticks
        price_data['date_only'] = pd.to_datetime(price_data['date']).dt.date
        price_data_daily = price_data.groupby('date_only').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min', 
            'close': 'last',
            'volume': 'sum'
        }).reset_index()
        price_data_daily['date'] = pd.to_datetime(price_data_daily['date_only'])
        price_data = price_data_daily
            
        # Calculate EMAs
        ema_20 = ema(price_data['close'], 20)
        ema_50 = ema(price_data['close'], 50)
        ema_200 = ema(price_data['close'], 200)
        
        # Determine x-axis data based on whether date is in columns or index
        if 'date' in price_data.columns:
            x_data = price_data['date']
        else:
            x_data = price_data.index
        
        # Create figure
        fig = go.Figure()
        
        # Add SPY candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=x_data,
                open=price_data['open'],
                high=price_data['high'],
                low=price_data['low'],
                close=price_data['close'],
                name='SPY',
                increasing_line_color='green',
                decreasing_line_color='red',
                increasing_fillcolor='lightgreen',
                decreasing_fillcolor='lightcoral',
                showlegend=False
            )
        )
        
        # Add EMA lines
        fig.add_trace(
            go.Scatter(
                x=x_data,
                y=ema_20,
                mode='lines',
                name='EMA 20',
                line=dict(color='blue', width=1),
                showlegend=True
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=x_data,
                y=ema_50,
                mode='lines',
                name='EMA 50',
                line=dict(color='orange', width=1),
                showlegend=True
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=x_data,
                y=ema_200,
                mode='lines',
                name='EMA 200',
                line=dict(color='red', width=1),
                showlegend=True
            )
        )
        
        # Update layout
        fig.update_layout(
            title="SPY Daily Price with EMAs",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            hovermode='x unified',
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='white',
            xaxis_rangeslider_visible=False
        )
        
        # Update axes
        fig.update_xaxes(
            showgrid=True, 
            gridcolor='lightgray', 
            gridwidth=0.5,
            zeroline=False
        )
        fig.update_yaxes(
            showgrid=True, 
            gridcolor='lightgray', 
            gridwidth=0.5,
            zeroline=False
        )
        
        return fig
    
    def _create_enhanced_export(self, trades_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
        """Create enhanced export with market data and technical indicators for LLM analysis"""
        from market_analysis.technical_indicators import ema, rsi, atr, bollinger_bands, macd
        
        # Make a copy to avoid modifying original
        enhanced_df = trades_df.copy()
        
        # Ensure we have datetime columns for merging
        if 'entry_time' in enhanced_df.columns or 'breakout_time' in enhanced_df.columns:
            entry_col = 'entry_time' if 'entry_time' in enhanced_df.columns else 'breakout_time'
            exit_col = 'exit_time' if 'exit_time' in enhanced_df.columns else 'date'
        else:
            # If no time columns, use date
            entry_col = 'date'
            exit_col = 'date'
        
        # Calculate technical indicators on the full market data
        market_df = market_df.copy()
        market_df['ema_20'] = ema(market_df['close'], 20)
        market_df['ema_50'] = ema(market_df['close'], 50)
        market_df['ema_200'] = ema(market_df['close'], 200)
        market_df['rsi'] = rsi(market_df['close'], 14)
        market_df['atr'] = atr(market_df['high'], market_df['low'], market_df['close'], 14)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = bollinger_bands(market_df['close'], 20, 2)
        market_df['bb_upper'] = bb_upper
        market_df['bb_middle'] = bb_middle
        market_df['bb_lower'] = bb_lower
        market_df['bb_position'] = (market_df['close'] - bb_lower) / (bb_upper - bb_lower)
        
        # MACD
        macd_line, signal_line, histogram = macd(market_df['close'])
        market_df['macd'] = macd_line
        market_df['macd_signal'] = signal_line
        market_df['macd_histogram'] = histogram
        
        # Volume analysis
        market_df['volume_sma'] = market_df['volume'].rolling(20).mean()
        market_df['volume_ratio'] = market_df['volume'] / market_df['volume_sma']
        
        # Volatility metrics
        market_df['returns'] = market_df['close'].pct_change()
        market_df['volatility_20'] = market_df['returns'].rolling(20).std() * np.sqrt(252)
        
        # Time-based features
        market_df['hour'] = pd.to_datetime(market_df['date']).dt.hour
        market_df['minute'] = pd.to_datetime(market_df['date']).dt.minute
        market_df['time_from_open'] = (market_df['hour'] - 9) * 60 + (market_df['minute'] - 30)
        
        # Day's range and position
        market_df['day'] = pd.to_datetime(market_df['date']).dt.date
        daily_stats = market_df.groupby('day').agg({
            'high': 'max',
            'low': 'min',
            'open': 'first',
            'volume': 'sum'
        }).rename(columns={
            'high': 'day_high',
            'low': 'day_low',
            'open': 'day_open',
            'volume': 'day_volume'
        })
        
        # Merge entry time market data
        for idx, trade in enhanced_df.iterrows():
            if pd.notna(trade[entry_col]):
                # Find the closest market data point
                entry_time = pd.to_datetime(trade[entry_col])
                market_dates = pd.to_datetime(market_df['date'])
                
                # Handle timezone mismatches
                if market_dates.dt.tz is not None and entry_time.tz is None:
                    entry_time = entry_time.tz_localize(market_dates.dt.tz)
                elif market_dates.dt.tz is None and entry_time.tz is not None:
                    entry_time = entry_time.tz_localize(None)
                
                closest_idx = (market_dates - entry_time).abs().idxmin()
                entry_data = market_df.iloc[closest_idx]
                
                # Add entry market data
                enhanced_df.loc[idx, 'entry_open'] = entry_data['open']
                enhanced_df.loc[idx, 'entry_high'] = entry_data['high']
                enhanced_df.loc[idx, 'entry_low'] = entry_data['low']
                enhanced_df.loc[idx, 'entry_close'] = entry_data['close']
                enhanced_df.loc[idx, 'entry_volume'] = entry_data['volume']
                enhanced_df.loc[idx, 'entry_ema_20'] = entry_data['ema_20']
                enhanced_df.loc[idx, 'entry_ema_50'] = entry_data['ema_50']
                enhanced_df.loc[idx, 'entry_ema_200'] = entry_data['ema_200']
                enhanced_df.loc[idx, 'entry_rsi'] = entry_data['rsi']
                enhanced_df.loc[idx, 'entry_atr'] = entry_data['atr']
                enhanced_df.loc[idx, 'entry_bb_position'] = entry_data['bb_position']
                enhanced_df.loc[idx, 'entry_macd'] = entry_data['macd']
                enhanced_df.loc[idx, 'entry_macd_histogram'] = entry_data['macd_histogram']
                enhanced_df.loc[idx, 'entry_volume_ratio'] = entry_data['volume_ratio']
                enhanced_df.loc[idx, 'entry_volatility'] = entry_data['volatility_20']
                enhanced_df.loc[idx, 'entry_hour'] = entry_data['hour']
                enhanced_df.loc[idx, 'entry_time_from_open'] = entry_data['time_from_open']
                
                # Add day's stats at entry
                entry_day = entry_data['day']
                if entry_day in daily_stats.index:
                    day_stats = daily_stats.loc[entry_day]
                    enhanced_df.loc[idx, 'entry_day_high'] = day_stats['day_high']
                    enhanced_df.loc[idx, 'entry_day_low'] = day_stats['day_low']
                    enhanced_df.loc[idx, 'entry_day_range'] = day_stats['day_high'] - day_stats['day_low']
                    enhanced_df.loc[idx, 'entry_opening_gap'] = (day_stats['day_open'] / entry_data['close'] - 1) * 100
                
            # Add exit market data if available
            if exit_col in trade and pd.notna(trade[exit_col]) and exit_col != entry_col:
                exit_time = pd.to_datetime(trade[exit_col])
                
                # Handle timezone mismatches for exit time
                if market_dates.dt.tz is not None and exit_time.tz is None:
                    exit_time = exit_time.tz_localize(market_dates.dt.tz)
                elif market_dates.dt.tz is None and exit_time.tz is not None:
                    exit_time = exit_time.tz_localize(None)
                
                closest_idx = (market_dates - exit_time).abs().idxmin()
                exit_data = market_df.iloc[closest_idx]
                
                enhanced_df.loc[idx, 'exit_close'] = exit_data['close']
                enhanced_df.loc[idx, 'exit_volume'] = exit_data['volume']
                enhanced_df.loc[idx, 'exit_rsi'] = exit_data['rsi']
                enhanced_df.loc[idx, 'exit_volatility'] = exit_data['volatility_20']
        
        # Add trade quality metrics
        if 'stop_loss' in enhanced_df.columns and 'entry_price' in enhanced_df.columns:
            enhanced_df['risk_reward_ratio'] = np.where(
                (enhanced_df['pnl'] > 0) & (enhanced_df['stop_loss'].notna()),
                enhanced_df['pnl'] / abs(enhanced_df['stop_loss'] - enhanced_df['entry_price']),
                np.nan
            )
        else:
            enhanced_df['risk_reward_ratio'] = np.nan
        
        # Round numeric columns for readability
        numeric_cols = enhanced_df.select_dtypes(include=[np.number]).columns
        enhanced_df[numeric_cols] = enhanced_df[numeric_cols].round(4)
        
        return enhanced_df
    
    def _create_strategy_plot(self, result: Dict, strategy: str, **params) -> go.Figure:
        """Create strategy P&L visualization with separate long/short curves"""
        trades_df = result.get('trades_df', pd.DataFrame()).copy()
        
        if trades_df.empty:
            return None
        
        # Ensure trades_df has 'date' column
        if 'date' not in trades_df.columns and isinstance(trades_df.index, pd.DatetimeIndex):
            trades_df = trades_df.reset_index()
            if 'index' in trades_df.columns:
                trades_df = trades_df.rename(columns={'index': 'date'})
        
        # Create figure for P&L only
        import plotly.graph_objects as go
        fig = go.Figure()
        
        # Get starting capital if available
        starting_capital = result.get('starting_capital', params.get('starting_capital', 25000))
        
        # Ensure cumulative P&L is calculated
        if 'cumulative_pnl' not in trades_df.columns:
            if 'current_capital' in trades_df.columns:
                # Use actual capital balance
                trades_df['cumulative_pnl'] = trades_df['current_capital'] - starting_capital
            else:
                trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
        
        # Calculate separate cumulative P&L for long and short trades
        show_direction_curves = False
        if 'breakout_type' in trades_df.columns:
            # ORB strategy - Create cumulative P&L for each direction
            trades_df['long_pnl'] = trades_df.apply(
                lambda x: x['pnl'] if x['breakout_type'] == 'long' else 0, axis=1
            )
            trades_df['short_pnl'] = trades_df.apply(
                lambda x: x['pnl'] if x['breakout_type'] == 'short' else 0, axis=1
            )
            trades_df['cumulative_long_pnl'] = trades_df['long_pnl'].cumsum()
            trades_df['cumulative_short_pnl'] = trades_df['short_pnl'].cumsum()
            show_direction_curves = True
        elif 'signal_type' in trades_df.columns:
            # VWAP strategy - Create cumulative P&L for each direction
            trades_df['long_pnl'] = trades_df.apply(
                lambda x: x['pnl'] if x['signal_type'] == 'bounce_up' else 0, axis=1
            )
            trades_df['short_pnl'] = trades_df.apply(
                lambda x: x['pnl'] if x['signal_type'] == 'bounce_down' else 0, axis=1
            )
            trades_df['cumulative_long_pnl'] = trades_df['long_pnl'].cumsum()
            trades_df['cumulative_short_pnl'] = trades_df['short_pnl'].cumsum()
            show_direction_curves = True
        
        # Add long/short curves if we have direction data
        if show_direction_curves:
            # Add long trades curve
            fig.add_trace(go.Scatter(
                x=trades_df['date'],
                y=trades_df['cumulative_long_pnl'],
                mode='lines',
                name='Long P&L',
                line=dict(color='green', width=2, dash='dot'),
                hovertemplate='Long P&L: $%{y:,.2f}<extra></extra>'
            ))
            
            # Add short trades curve
            fig.add_trace(go.Scatter(
                x=trades_df['date'],
                y=trades_df['cumulative_short_pnl'],
                mode='lines',
                name='Short P&L',
                line=dict(color='red', width=2, dash='dot'),
                hovertemplate='Short P&L: $%{y:,.2f}<extra></extra>'
            ))
        
        # Combined equity curve (always show this)
        fig.add_trace(go.Scatter(
            x=trades_df['date'],
            y=trades_df['cumulative_pnl'],
            mode='lines',
            name='Combined P&L',
            line=dict(color='purple', width=3),
            hovertemplate='Combined P&L: $%{y:,.2f}<extra></extra>'
        ))
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        # Add direction-specific win/loss markers
        if 'outcome' in trades_df.columns and 'breakout_type' in trades_df.columns:
            # Long wins
            long_wins = trades_df[(trades_df['outcome'] == 'target') & 
                                 (trades_df['breakout_type'] == 'long')]
            if not long_wins.empty:
                fig.add_trace(go.Scatter(
                    x=long_wins['date'],
                    y=long_wins['cumulative_pnl'],
                    mode='markers',
                    name='Long Wins',
                    marker=dict(color='lightgreen', size=10, symbol='triangle-up'),
                    hovertemplate='Long Win<br>Date: %{x}<br>P&L: $%{y:,.2f}<extra></extra>'
                ))
            
            # Long losses
            long_losses = trades_df[(trades_df['outcome'] == 'stop_loss') & 
                                   (trades_df['breakout_type'] == 'long')]
            if not long_losses.empty:
                fig.add_trace(go.Scatter(
                    x=long_losses['date'],
                    y=long_losses['cumulative_pnl'],
                    mode='markers',
                    name='Long Losses',
                    marker=dict(color='darkgreen', size=8, symbol='x'),
                    hovertemplate='Long Loss<br>Date: %{x}<br>P&L: $%{y:,.2f}<extra></extra>'
                ))
            
            # Short wins
            short_wins = trades_df[(trades_df['outcome'] == 'target') & 
                                  (trades_df['breakout_type'] == 'short')]
            if not short_wins.empty:
                fig.add_trace(go.Scatter(
                    x=short_wins['date'],
                    y=short_wins['cumulative_pnl'],
                    mode='markers',
                    name='Short Wins',
                    marker=dict(color='lightcoral', size=10, symbol='triangle-down'),
                    hovertemplate='Short Win<br>Date: %{x}<br>P&L: $%{y:,.2f}<extra></extra>'
                ))
            
            # Short losses
            short_losses = trades_df[(trades_df['outcome'] == 'stop_loss') & 
                                    (trades_df['breakout_type'] == 'short')]
            if not short_losses.empty:
                fig.add_trace(go.Scatter(
                    x=short_losses['date'],
                    y=short_losses['cumulative_pnl'],
                    mode='markers',
                    name='Short Losses',
                    marker=dict(color='darkred', size=8, symbol='x'),
                    hovertemplate='Short Loss<br>Date: %{x}<br>P&L: $%{y:,.2f}<extra></extra>'
                ))
        elif 'outcome' in trades_df.columns:
            # Fallback to simple win/loss markers if no direction info
            wins = trades_df[trades_df['outcome'] == 'target']
            losses = trades_df[trades_df['outcome'] == 'stop_loss']
            
            if not wins.empty:
                fig.add_trace(go.Scatter(
                    x=wins['date'],
                    y=wins['cumulative_pnl'],
                    mode='markers',
                    name='Wins',
                    marker=dict(color='green', size=8, symbol='triangle-up')
                ))
            
            if not losses.empty:
                fig.add_trace(go.Scatter(
                    x=losses['date'],
                    y=losses['cumulative_pnl'],
                    mode='markers',
                    name='Losses',
                    marker=dict(color='red', size=8, symbol='triangle-down')
                ))
        
        # Add horizontal line at zero (break-even)
        fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                      annotation_text="Break-even", annotation_position="right")
        
        # Get instrument type and multiplier for title
        instrument = params.get('instrument', 'Options')
        multiplier_map = {'Stock': 1.0, 'Options': 0.1, 'Futures': 2.0}
        multiplier = multiplier_map.get(instrument, 0.1)
        
        # Update layout with enhanced styling
        fig.update_layout(
            title=f"{strategy} Strategy P&L - {instrument} ({multiplier}x leverage) | Starting Capital: ${starting_capital:,.0f}",
            xaxis_title="Date",
            yaxis_title=f"Cumulative P&L ($) - {instrument}",
            hovermode='x unified',
            height=400,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="gray",
                borderwidth=1
            ),
            margin=dict(r=150),  # Make room for legend
            plot_bgcolor='white'
        )
        
        # Update axes
        fig.update_xaxes(showgrid=True, gridcolor='lightgray', gridwidth=0.5)
        fig.update_yaxes(
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=0.5,
            zeroline=True,
            zerolinecolor='black',
            zerolinewidth=1
        )
        
        # Add annotations for final P&L values and leverage info
        if not trades_df.empty:
            final_combined = trades_df['cumulative_pnl'].iloc[-1]
            
            # Calculate what the P&L would be without leverage
            base_movement = final_combined / multiplier
            
            annotation_text = f"<b>Final P&L ({instrument})</b><br>"
            annotation_text += f"Total: ${final_combined:,.2f}<br>"
            annotation_text += f"<br><b>Leverage Effect:</b><br>"
            annotation_text += f"SPY movement: ${base_movement:,.2f}<br>"
            annotation_text += f"× {multiplier} multiplier<br>"
            annotation_text += f"= ${final_combined:,.2f} P&L"
            
            if 'breakout_type' in trades_df.columns:
                final_long = trades_df['cumulative_long_pnl'].iloc[-1]
                final_short = trades_df['cumulative_short_pnl'].iloc[-1]
                annotation_text += f"<br><br><b>By Direction:</b><br>Long: ${final_long:,.2f}<br>Short: ${final_short:,.2f}"
            
            fig.add_annotation(
                x=1.02,
                y=0.5,
                xref="paper",
                yref="paper",
                text=annotation_text,
                showarrow=False,
                font=dict(size=12),
                align="left",
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="gray",
                borderwidth=1
            )
        
        return fig
    
    def _create_drawdown_plot(self, trades_df: pd.DataFrame, **params) -> go.Figure:
        """Create a drawdown visualization showing underwater equity curve"""
        if trades_df.empty or 'cumulative_pnl' not in trades_df.columns:
            return None
        
        # Ensure trades_df has 'date' column
        if 'date' not in trades_df.columns and isinstance(trades_df.index, pd.DatetimeIndex):
            trades_df = trades_df.reset_index()
            if 'index' in trades_df.columns:
                trades_df = trades_df.rename(columns={'index': 'date'})
        
        # Get parameters
        starting_capital = params.get('starting_capital', 25000)
        instrument = params.get('instrument', 'Options')
        
        # Calculate account balance (starting capital + cumulative P&L)
        account_balance = starting_capital + trades_df['cumulative_pnl']
        
        # Calculate drawdown from peak account balance
        running_max_balance = account_balance.expanding().max()
        drawdown = account_balance - running_max_balance
        
        # Calculate drawdown as percentage of peak balance
        drawdown_pct_of_peak = (drawdown / running_max_balance.where(running_max_balance != 0, 1)) * 100
        
        # Calculate drawdown as percentage of starting capital
        drawdown_pct_of_capital = (drawdown / starting_capital) * 100
        
        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.6, 0.4],
            subplot_titles=("Cumulative P&L", "Drawdown"),
            vertical_spacing=0.12,
            shared_xaxes=True
        )
        
        # Add account balance line
        fig.add_trace(
            go.Scatter(
                x=trades_df['date'],
                y=account_balance,
                mode='lines',
                name='Account Balance',
                line=dict(color='blue', width=2),
                hovertemplate='Balance: $%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Add running maximum balance line
        fig.add_trace(
            go.Scatter(
                x=trades_df['date'],
                y=running_max_balance,
                mode='lines',
                name='Peak Balance',
                line=dict(color='green', width=1, dash='dot'),
                hovertemplate='Peak: $%{y:,.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Add starting capital reference line
        fig.add_hline(y=starting_capital, line_dash="dash", line_color="gray",
                      annotation_text=f"Starting Capital: ${starting_capital:,.0f}",
                      annotation_position="right", row=1, col=1)
        
        # Add drawdown area chart (as % of starting capital)
        fig.add_trace(
            go.Scatter(
                x=trades_df['date'],
                y=drawdown_pct_of_capital,
                mode='lines',
                name='Drawdown (% of Capital)',
                fill='tozeroy',
                fillcolor='rgba(255, 0, 0, 0.3)',
                line=dict(color='red', width=2),
                hovertemplate='Drawdown: %{y:.1f}% of capital<br>$%{customdata:,.2f}<extra></extra>',
                customdata=drawdown
            ),
            row=2, col=1
        )
        
        # Find max drawdown for annotation
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        max_dd_pct_capital = drawdown_pct_of_capital[max_dd_idx]
        max_dd_pct_peak = drawdown_pct_of_peak[max_dd_idx]
        max_dd_date = trades_df.loc[max_dd_idx, 'date']
        
        # Add max drawdown annotation
        fig.add_annotation(
            x=max_dd_date,
            y=max_dd_pct_capital,
            text=f"Max Drawdown<br>{max_dd_pct_capital:.1f}% of capital<br>${max_dd_value:,.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor='red',
            ax=0,
            ay=-40,
            bgcolor='white',
            bordercolor='red',
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title=f"Drawdown Analysis - {instrument} | Starting Capital: ${starting_capital:,.0f}",
            height=500,
            showlegend=True,
            hovermode='x unified'
        )
        
        # Update y-axes
        fig.update_yaxes(title_text="Account Balance ($)", row=1, col=1)
        fig.update_yaxes(title_text="Drawdown (% of Capital)", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=1)
        
        
        return fig
    
    def ai_analysis(self, query: str, chat_history: List = None) -> Tuple[str, Optional[go.Figure]]:
        """AI-powered analysis for complex queries with chat history support"""
        if not AI_AVAILABLE or not self.llm:
            return """❌ AI Assistant not available. 

To enable AI features with LM Studio (recommended):
1. Download and install LM Studio from https://lmstudio.ai/
2. Load a model in LM Studio (e.g., Llama, Mistral, etc.)
3. Start the local server in LM Studio (usually on port 1234)
4. The app will automatically connect to http://localhost:1234/v1

Alternatively, to use OpenAI:
1. Add your OpenAI API key to `.env` file:
   ```
   OPENAI_API_KEY=your-key-here
   ```
2. Set USE_LOCAL_AI=False in configuration/app_settings.py
3. Restart the application
""", None
        
        try:
            # Check for common queries that we can handle directly
            query_lower = query.lower()
            if ("volatility" in query_lower and "hour" in query_lower and 
                ("calm" in query_lower or "volatile" in query_lower or "pattern" in query_lower)):
                # Use direct analysis for volatility queries
                return self.direct_volatility_analysis(), None
            
            # Build context from chat history
            context = ""
            if chat_history:
                # Format previous conversations for context
                for user_msg, ai_msg in chat_history[-3:]:  # Use last 3 exchanges for context
                    context += f"User: {user_msg}\nAssistant: {ai_msg}\n\n"
            
            # Create full prompt with context
            full_query = query
            if context:
                full_query = f"Previous conversation:\n{context}\nCurrent question: {query}"
            
            # Create agent if not exists
            if not self.ai_agent:
                # Create agent with execution-focused configuration
                agent_kwargs = {
                    "prefix": config.SYSTEM_PROMPT + "\n\nYou MUST execute Python code to analyze the data. Use the python_repl_ast tool to run code and return results.",
                    "format_instructions": "Always use the python_repl_ast tool to execute code and show results.",
                    "max_iterations": 15,  # More iterations for complex calculations
                    "early_stopping_method": "generate",
                    "handle_parsing_errors": True
                }
                
                # Create pandas agent with explicit execution capability
                self.ai_agent = create_pandas_dataframe_agent(
                    self.llm,
                    self.agent.df,
                    verbose=False,
                    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    allow_dangerous_code=True,
                    agent_kwargs=agent_kwargs,
                    include_df_in_prompt=True,  # Include df info in prompt
                    number_of_head_rows=5  # Show sample data
                )
            
            # Add execution reminder to query
            execution_query = full_query + "\n\nIMPORTANT: Execute all code and show the actual numerical results. Include specific values in your response."
            
            # Process query with context
            response = self.ai_agent.invoke(execution_query)
            
            # Check if visualization is needed
            viz_keywords = ['plot', 'chart', 'graph', 'visualiz', 'show', 'display']
            needs_viz = any(keyword in query.lower() for keyword in viz_keywords)
            
            figure = None
            if needs_viz:
                # Try to create appropriate visualization based on query
                if 'volatility' in query.lower():
                    figure = self._create_volatility_chart()
                elif 'volume' in query.lower():
                    figure = self._create_volume_chart()
                else:
                    figure = self._create_price_chart()
            
            # Extract string from response if it's a dict
            if isinstance(response, dict):
                response_text = response.get('output', str(response))
            else:
                response_text = str(response)
            
            # If response contains code blocks, try to execute them
            if "```python" in response_text:
                # Extract code blocks
                import re
                code_blocks = re.findall(r'```python\n(.*?)\n```', response_text, re.DOTALL)
                
                if code_blocks and not any(char.isdigit() for char in response_text.split("```")[-1]):
                    # AI provided code but no results - execute it
                    response_text += "\n\n📊 **Executing the code to show results:**\n"
                    
                    for i, code_block in enumerate(code_blocks):
                        if i > 0:
                            response_text += "\n---\n"
                        
                        # Execute the code
                        execution_result = self._execute_code_from_response(code_block)
                        response_text += f"\n```\n{execution_result}\n```"
                    
                    response_text += "\n\n✅ Code executed automatically to show actual results."
            
            return response_text, figure
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"AI analysis error: {e}", exc_info=True)
            
            # Check if it's a parsing error with useful content
            if "Could not parse LLM output:" in error_msg:
                # Extract the unparsed content
                try:
                    unparsed_content = error_msg.split("Could not parse LLM output: `")[1].split("`")[0]
                    
                    # Look for code in the unparsed content
                    if "df[" in unparsed_content or "import" in unparsed_content or "=" in unparsed_content:
                        # Extract and execute any Python-like code
                        lines = unparsed_content.split('\n')
                        code_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            if (line and 
                                not line.startswith(('Thought:', 'Action:', 'Observation:')) and
                                ('=' in line or 'df' in line or 'import' in line or 'print' in line)):
                                code_lines.append(line)
                        
                        if code_lines:
                            code_to_execute = '\n'.join(code_lines)
                            result = self._execute_code_from_response(code_to_execute)
                            
                            response_text = f"The AI tried to analyze your query but had formatting issues. Here's what it was trying to calculate:\n\n"
                            response_text += f"```python\n{code_to_execute}\n```\n\n"
                            response_text += f"📊 **Results:**\n```\n{result}\n```"
                            
                            return response_text, None
                except:
                    pass
            
            return f"❌ AI Error: {error_msg}\n\nTry a simpler query or check your API key.", None
    
    def _create_price_chart(self) -> go.Figure:
        """Create basic price chart"""
        recent_df = self.agent.df.tail(2000).copy()  # Last 2000 bars
        
        # Aggregate to 5-minute bars for better visibility
        recent_df['date_rounded'] = pd.to_datetime(recent_df['date']).dt.floor('5min')
        agg_df = recent_df.groupby('date_rounded').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).reset_index()
        
        fig = go.Figure(data=[go.Candlestick(
            x=agg_df['date_rounded'],
            open=agg_df['open'],
            high=agg_df['high'],
            low=agg_df['low'],
            close=agg_df['close'],
            name='SPY',
            increasing_line_color='green',
            decreasing_line_color='red',
            increasing_fillcolor='rgba(0,255,0,0.3)',
            decreasing_fillcolor='rgba(255,0,0,0.3)'
        )])
        
        fig.update_layout(
            title="SPY Price Chart (5-min bars)",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            height=600,
            xaxis_rangeslider_visible=False,
            template='plotly_white'
        )
        
        return fig
    
    def _create_volatility_chart(self) -> go.Figure:
        """Create volatility analysis chart"""
        df = self.agent.df.tail(2000).copy()
        
        # Calculate returns and rolling volatility
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std() * np.sqrt(252)
        
        # Aggregate data for better visibility
        df['date_rounded'] = pd.to_datetime(df['date']).dt.floor('15min')
        df_agg = df.groupby('date_rounded').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volatility': 'mean'
        }).reset_index()
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3]
        )
        
        # Price chart with better visibility
        fig.add_trace(
            go.Candlestick(
                x=df_agg['date_rounded'],
                open=df_agg['open'],
                high=df_agg['high'],
                low=df_agg['low'],
                close=df_agg['close'],
                name='SPY',
                increasing_line_color='green',
                decreasing_line_color='red',
                increasing_fillcolor='rgba(0,255,0,0.3)',
                decreasing_fillcolor='rgba(255,0,0,0.3)'
            ),
            row=1, col=1
        )
        
        # Volatility chart
        fig.add_trace(
            go.Scatter(
                x=df_agg['date_rounded'],
                y=df_agg['volatility'],
                name='20-Day Volatility',
                line=dict(color='orange', width=2)
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=700, 
            title="SPY Price and Volatility Analysis (15-min bars)",
            xaxis_rangeslider_visible=False
        )
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volatility", row=2, col=1)
        
        return fig
    
    def _execute_code_from_response(self, code_str: str) -> str:
        """Execute code extracted from AI response and return results"""
        try:
            # Create execution namespace with data and common imports
            namespace = {
                'df': self.agent.df,
                'pd': pd,
                'np': np,
                'plt': None,  # Disable matplotlib in execution
                'go': go,
                'make_subplots': make_subplots,
                'analyzer': self,
                'print_results': []  # Capture print outputs
            }
            
            # Override print to capture output
            original_print = print
            def capture_print(*args, **kwargs):
                namespace['print_results'].append(' '.join(str(arg) for arg in args))
            
            # Execute with captured print
            import builtins
            builtins.print = capture_print
            
            try:
                exec(code_str, namespace)
                result = '\n'.join(namespace['print_results'])
                
                # Check if any variables were created that might be results
                for key, value in namespace.items():
                    if key not in ['df', 'pd', 'np', 'plt', 'go', 'make_subplots', 'analyzer', 'print_results', '__builtins__']:
                        if isinstance(value, pd.DataFrame):
                            result += f"\n\n{key}:\n{value.to_string()}"
                        elif isinstance(value, (int, float, str)):
                            result += f"\n{key}: {value}"
                
                return result if result else "Code executed but no output was produced."
            finally:
                builtins.print = original_print
                
        except Exception as e:
            return f"Error executing code: {str(e)}"
    
    def direct_volatility_analysis(self) -> str:
        """Direct volatility analysis without agent"""
        df = self.agent.df.copy()
        
        # Calculate hourly volatility
        df['hour'] = df['date'].dt.hour
        df['returns'] = df['close'].pct_change()
        df['range'] = df['high'] - df['low']
        df['range_pct'] = (df['range'] / df['close']) * 100
        
        # Group by hour
        hourly_stats = df.groupby('hour').agg({
            'returns': lambda x: x.std() * np.sqrt(252 * 390) * 100,  # Annualized volatility %
            'range_pct': 'mean',  # Average range as % of price
            'volume': 'mean'
        }).round(2)
        
        hourly_stats.columns = ['volatility_pct', 'avg_range_pct', 'avg_volume']
        hourly_stats = hourly_stats.sort_values('volatility_pct')
        
        # Build response
        result = "📊 **Intraday Volatility Analysis**\n\n"
        
        result += "**🕊️ Calmest Trading Hours (Lowest Volatility):**\n"
        for hour, row in hourly_stats.head(3).iterrows():
            time_str = f"{hour}:00-{hour+1}:00"
            result += f"• {time_str}: {row['volatility_pct']:.1f}% volatility (avg range: {row['avg_range_pct']:.2f}%)\n"
        
        result += "\n**🔥 Most Volatile Trading Hours:**\n"
        for hour, row in hourly_stats.tail(3).iterrows():
            time_str = f"{hour}:00-{hour+1}:00"
            result += f"• {time_str}: {row['volatility_pct']:.1f}% volatility (avg range: {row['avg_range_pct']:.2f}%)\n"
        
        result += f"\n**Key Insights:**\n"
        result += f"• Opening hour (9:00-10:00) is {hourly_stats.loc[9, 'volatility_pct'] / hourly_stats.loc[12, 'volatility_pct']:.1f}x more volatile than lunch hour\n"
        result += f"• Volatility typically drops {((hourly_stats.loc[9, 'volatility_pct'] - hourly_stats.loc[12, 'volatility_pct']) / hourly_stats.loc[9, 'volatility_pct'] * 100):.0f}% from open to midday\n"
        
        return result
    
    def calculate_hourly_volatility(self) -> pd.DataFrame:
        """Calculate average volatility by hour for the AI to use"""
        df = self.agent.df.copy()
        
        # Calculate returns and ATR-like volatility
        df['returns'] = df['close'].pct_change()
        df['range'] = df['high'] - df['low']
        df['hour'] = df['date'].dt.hour
        
        # Calculate hourly statistics
        hourly_stats = df.groupby('hour').agg({
            'returns': lambda x: x.std() * np.sqrt(252 * 390),  # Annualized volatility
            'range': 'mean',  # Average range
            'volume': 'mean'   # Average volume
        }).reset_index()
        
        hourly_stats.columns = ['hour', 'volatility', 'avg_range', 'avg_volume']
        hourly_stats['volatility_pct'] = hourly_stats['volatility'] * 100
        
        return hourly_stats
    
    def _create_volume_chart(self) -> go.Figure:
        """Create volume analysis chart"""
        df = self.agent.df.tail(1000).copy()
        
        # Aggregate to 5-minute bars for better visibility
        df['date_rounded'] = pd.to_datetime(df['date']).dt.floor('5min')
        df_agg = df.groupby('date_rounded').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).reset_index()
        
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3]
        )
        
        # Price chart with enhanced candlesticks
        fig.add_trace(
            go.Candlestick(
                x=df_agg['date_rounded'],
                open=df_agg['open'],
                high=df_agg['high'],
                low=df_agg['low'],
                close=df_agg['close'],
                name='SPY',
                increasing_line_color='green',
                decreasing_line_color='red',
                increasing_fillcolor='rgba(0,255,0,0.3)',
                decreasing_fillcolor='rgba(255,0,0,0.3)'
            ),
            row=1, col=1
        )
        
        # Volume chart with colors
        colors = ['red' if close < open else 'green' 
                 for close, open in zip(df_agg['close'], df_agg['open'])]
        
        fig.add_trace(
            go.Bar(
                x=df_agg['date_rounded'],
                y=df_agg['volume'],
                name='Volume',
                marker_color=colors
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=700, 
            title="SPY Price and Volume Analysis (5-min bars)",
            xaxis_rangeslider_visible=False
        )
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        
        return fig
    
    def load_saved_backtest(self, backtest_id: str) -> Tuple[str, go.Figure, go.Figure, go.Figure, str]:
        """Load and analyze a saved backtest with comprehensive analytics"""
        try:
            # Load the backtest
            backtest = BacktestResults.load(backtest_id)
            
            # Import analytics
            from trading_engine.analytics import TradingAnalytics
            from trading_engine.ai_analytics import AIAnalyticsAssistant
            
            # Create analytics instance
            analytics = TradingAnalytics(backtest.daily_df, backtest.trades_df)
            
            # Generate all analytics
            regime_stats, regime_fig = analytics.analyze_regime_performance()
            
            # Generate clustering with error handling
            try:
                cluster_stats, cluster_fig = analytics.cluster_trades()
                if cluster_fig is None or not cluster_fig.data:
                    # Create placeholder figure if clustering failed
                    cluster_fig = go.Figure()
                    cluster_fig.add_annotation(
                        text="Insufficient data for clustering analysis",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=14)
                    )
                    cluster_fig.update_layout(
                        title="Clustering Analysis",
                        height=400
                    )
            except Exception as e:
                logger.error(f"Clustering analysis failed: {e}")
                cluster_stats = pd.DataFrame()
                cluster_fig = go.Figure()
                cluster_fig.add_annotation(
                    text=f"Clustering analysis failed: {str(e)}",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=14, color="red")
                )
                cluster_fig.update_layout(
                    title="Clustering Analysis Error",
                    height=400
                )
            
            importance_df, importance_fig = analytics.feature_importance_analysis()
            
            # Risk metrics
            risk_metrics = analytics.calculate_risk_metrics()
            
            # Get clustering insights
            insights = analytics._generate_clustering_insights(cluster_stats, None)
            
            # AI Analysis
            ai_assistant = AIAnalyticsAssistant()
            analytics_data = {
                'clustering_insights': insights,
                'risk_metrics': risk_metrics,
                'cluster_stats': cluster_stats
            }
            ai_analysis = ai_assistant.analyze_backtest_results(backtest.save_path, analytics_data)
            
            # Store data for export (store as instance variables)
            self.current_backtest_id = backtest_id
            self.current_analytics_data = analytics_data
            self.current_plots = {
                'regime_analysis': regime_fig,
                'cluster_analysis': cluster_fig,
                'feature_importance': importance_fig
            }
            
            # Create enhanced summary
            summary = f"""## Loaded Backtest: {backtest.strategy}
            
### Summary Statistics
- Total P&L: ${backtest.summary_stats.get('total_pnl', 0):,.2f}
- Win Rate: {backtest.summary_stats.get('win_rate', 0)*100:.1f}%
- Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 0):.2f}
- Max Drawdown: ${risk_metrics.get('max_drawdown', 0):,.2f} ({risk_metrics.get('max_drawdown_pct', 0):.1f}%)

### Risk Metrics
- Value at Risk (95%): ${risk_metrics.get('var_95', 0):,.2f}
- Profit Factor: {risk_metrics.get('profit_factor', 0):.2f}
- Calmar Ratio: {risk_metrics.get('calmar_ratio', 0):.2f}

### Clustering Insights
{insights}
            """
            
            return summary, regime_fig, cluster_fig, importance_fig, ai_analysis
            
        except Exception as e:
            logger.error(f"Error loading backtest: {e}")
            return f"Error loading backtest: {str(e)}", None, None, None, "Error loading AI analysis"
    
    def get_saved_backtests(self) -> List[Tuple[str, str]]:
        """Get list of saved backtests for dropdown"""
        try:
            backtests = BacktestResults.list_saved_backtests()
            choices = []
            for bt in backtests:
                label = f"{bt['strategy']} - {bt['timestamp'][:10]} ({bt['data_range']['trading_days']} days)"
                value = bt['folder_name']
                choices.append((label, value))
            return choices
        except Exception as e:
            logger.error(f"Error listing backtests: {e}")
            return []
    
    # REMOVED: HMM and XGBoost prediction methods were here
    # These methods were removed because they showed no predictive value (AUC < 0.5)
    pass
    
    '''def train_hmm_predictor(self, backtest_id: str) -> Tuple[str, go.Figure, go.Figure]:
        """Train HMM predictor on backtest daily data"""
        try:
            # Import HMM predictor
            from trading_engine.hmm_daily_predictor import HMMDailyPredictor
            
            # Load backtest data
            backtest = BacktestResults.load(backtest_id)
            
            if backtest.daily_df is None or backtest.daily_df.empty:
                return "❌ No daily data available for this backtest", None, None
            
            # Initialize predictor
            self.hmm_predictor = HMMDailyPredictor(n_states=4, lag_days=10)
            
            # Create features
            features_df = self.hmm_predictor.create_lagged_features(backtest.daily_df)
            
            if len(features_df) < 100:
                return f"❌ Insufficient data for training. Need at least 100 days, found {len(features_df)}", None, None
            
            # Train with validation
            validation_results = self.hmm_predictor.train_with_validation(features_df)
            
            # Create validation plots
            validation_plot = self.hmm_predictor.create_validation_plots()
            
            # Create feature importance plot
            importance_df = validation_results['feature_importance']
            
            importance_plot = go.Figure()
            importance_plot.add_trace(
                go.Bar(
                    x=importance_df['importance'],
                    y=importance_df['feature'],
                    orientation='h',
                    marker_color='lightblue'
                )
            )
            importance_plot.update_layout(
                title="Top Predictive Features",
                xaxis_title="Importance Score",
                yaxis_title="Feature",
                height=400,
                margin=dict(l=150)
            )
            
            # Create summary
            summary = self.hmm_predictor.create_prediction_summary()
            
            # Store current features for prediction
            self.current_features_df = features_df
            
            return summary, validation_plot, importance_plot
            
        except Exception as e:
            logger.error(f"Error training HMM: {e}", exc_info=True)
            return f"❌ Error training HMM model: {str(e)}", None, None
    
    def predict_next_day(self) -> str:
        """Make next day prediction using trained HMM"""
        try:
            if not hasattr(self, 'hmm_predictor') or self.hmm_predictor is None:
                return "❌ No trained model available. Please train HMM model first."
            
            if not hasattr(self, 'current_features_df') or self.current_features_df is None:
                return "❌ No feature data available. Please train HMM model first."
            
            # Make prediction
            prediction = self.hmm_predictor.predict_next_day(self.current_features_df)
            
            # Create visual prediction display
            prob_up = prediction['probability_up']
            prob_down = prediction['probability_down']
            
            # Determine color based on prediction
            if prob_up > 0.6:
                color = "🟢"
                strength = "Strong"
            elif prob_up > 0.5:
                color = "🟡"
                strength = "Weak"
            elif prob_up > 0.4:
                color = "🟡"
                strength = "Weak"
            else:
                color = "🔴"
                strength = "Strong"
            
            result = f"""### Next Day Prediction

## {color} {prediction['prediction']} ({strength})

**Probability of UP day**: {prob_up:.1%}  
**Probability of DOWN day**: {prob_down:.1%}

**Confidence Level**: {prediction['confidence']:.1%}  
**Current Market Regime**: {prediction['current_regime']}

**Model Performance**:
- Historical Accuracy: {prediction['historical_accuracy']:.1%}
- Model AUC: {prediction['model_auc']:.3f}

---
*Note: Predictions are based on historical patterns and should not be used as sole trading decisions.*
"""
            
            return result
            
        except Exception as e:
            logger.error(f"Error making prediction: {e}", exc_info=True)
            return f"❌ Error making prediction: {str(e)}"
    
    def train_xgboost_predictor(self, backtest_id: str, task: str = 'classification', use_shap: bool = False) -> Tuple[str, go.Figure, Optional[go.Figure]]:
        """Train XGBoost predictor on backtest daily data"""
        try:
            # Import XGBoost predictor
            from trading_engine.xgboost_daily_predictor import XGBoostDailyPredictor
            
            # Load backtest data
            backtest = BacktestResults.load(backtest_id)
            
            if backtest.daily_df is None or backtest.daily_df.empty:
                return "❌ No daily data available for this backtest", None, None
            
            # Initialize predictor
            self.xgboost_predictor = XGBoostDailyPredictor(
                task=task.lower(),
                lag_days=10,
                use_shap=use_shap,
                optimize_hyperparams=False  # Set to True for better performance but slower training
            )
            
            # Create features
            features_df = self.xgboost_predictor.create_advanced_features(backtest.daily_df)
            
            if len(features_df) < 100:
                return f"❌ Insufficient data for training. Need at least 100 days, found {len(features_df)}", None, None
            
            # Train with validation
            validation_results = self.xgboost_predictor.train_with_validation(features_df)
            
            # Create validation plots
            validation_plot = self.xgboost_predictor.create_validation_plots()
            
            # Create SHAP plot if enabled
            shap_plot = None
            if use_shap:
                shap_plot = self.xgboost_predictor.create_shap_plots()
            
            # Create summary
            summary = self.xgboost_predictor.create_prediction_summary()
            
            # Store current features for prediction
            self.current_xgb_features_df = features_df
            
            return summary, validation_plot, shap_plot
            
        except Exception as e:
            logger.error(f"Error training XGBoost: {e}", exc_info=True)
            return f"❌ Error training XGBoost model: {str(e)}", None, None
    
    def predict_next_day_xgboost(self) -> str:
        """Make next day prediction using trained XGBoost"""
        try:
            if not hasattr(self, 'xgboost_predictor') or self.xgboost_predictor is None:
                return "❌ No trained XGBoost model available. Please train model first."
            
            if not hasattr(self, 'current_xgb_features_df') or self.current_xgb_features_df is None:
                return "❌ No feature data available. Please train model first."
            
            # Make prediction
            prediction = self.xgboost_predictor.predict_next_day(self.current_xgb_features_df)
            
            # Create visual prediction display
            if self.xgboost_predictor.task == 'classification':
                prob_up = prediction['probability_up']
                prob_down = prediction['probability_down']
                
                # Determine color based on prediction
                if prob_up > 0.6:
                    color = "🟢"
                    strength = "Strong"
                elif prob_up > 0.5:
                    color = "🟡"
                    strength = "Weak"
                elif prob_up > 0.4:
                    color = "🟡"
                    strength = "Weak"
                else:
                    color = "🔴"
                    strength = "Strong"
                
                result = f"""### Next Day Prediction (XGBoost)

## {color} {prediction['prediction']} ({strength})

**Probability of UP day**: {prob_up:.1%}  
**Probability of DOWN day**: {prob_down:.1%}

**Confidence Level**: {prediction['confidence']:.1%}  
**Model AUC**: {prediction['model_auc']:.3f}"""
                
                # Add feature contributions if available
                if 'feature_contributions' in prediction and prediction['feature_contributions']:
                    result += "\n\n### Top Contributing Features:"
                    
                    if 'top_positive' in prediction['feature_contributions']:
                        result += "\n**Bullish Factors:**\n"
                        for feat in prediction['feature_contributions']['top_positive'][:3]:
                            result += f"- {feat['feature']}: +{feat['shap_value']:.3f}\n"
                    
                    if 'top_negative' in prediction['feature_contributions']:
                        result += "\n**Bearish Factors:**\n"
                        for feat in prediction['feature_contributions']['top_negative'][:3]:
                            result += f"- {feat['feature']}: {feat['shap_value']:.3f}\n"
            else:
                # Regression result
                pred_return = prediction['predicted_return']
                direction = prediction['predicted_direction']
                magnitude = prediction['predicted_magnitude']
                
                color = "🟢" if direction == "UP" else "🔴"
                
                result = f"""### Next Day Prediction (XGBoost Regression)

## {color} {direction}

**Predicted Return**: {pred_return:.2%}  
**Expected Move**: {magnitude:.2%}

**Model RMSE**: {prediction['model_rmse']:.4f}"""
            
            result += "\n\n---\n*Note: Predictions are based on historical patterns and should not be used as sole trading decisions.*"
            
            return result
            
        except Exception as e:
            logger.error(f"Error making XGBoost prediction: {e}", exc_info=True)
            return f"❌ Error making prediction: {str(e)}"
    
'''  # End of removed prediction methods

# Initialize analyzer
analyzer = TradingAnalyzer()

# Create Gradio interface - Tabbed design
with gr.Blocks(
    title="0DTE Trading Analysis System",
    theme=gr.themes.Soft(),
    css="""
    .gradio-container {
        max-width: 1400px;
        margin: auto;
    }
    .strategy-section {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
    }
    .ai-section {
        border: 2px solid #2196F3;
        border-radius: 8px;
        padding: 20px;
        margin-top: 30px;
        background-color: #f0f7ff;
    }
    """
) as app:
    
    gr.Markdown("""
    # 🎯 0DTE Trading Analysis System
    
    Complete trading analysis platform for Zero Days to Expiration (0DTE) strategies.
    """)
    
    if not DATA_AVAILABLE:
        gr.Markdown("""
        <div style='background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px;'>
        ⚠️ <b>Warning:</b> SPY data not loaded. Please run `python market_data/spy_data_downloader.py` first.
        </div>
        """)
    
    # Create tabbed interface
    with gr.Tabs():
        # Tab 1: Strategy Backtesting
        with gr.Tab("🎯 Strategy Backtesting"):
            gr.Markdown("""
            ## Strategy Analysis & Backtesting
            
            Test proven 0DTE strategies on historical SPY data. Start with quick presets or customize parameters.
            """)
            
            
            gr.Markdown("### 🎯 Custom Analysis")
            
            # Add instrument type explanation
            with gr.Accordion("📊 Understanding Instrument Types", open=False):
                gr.Markdown("""
                **How Instrument Types Affect Your P&L:**
                
                🏢 **Stock (1x multiplier)**
                - Trading direct SPY shares
                - $1 price move = $1 profit/loss per share
                - Example: SPY moves from $500 to $502 = $2 profit per share
                - Best for: Conservative traders, no leverage risk
                
                📈 **Options (0.1x multiplier)**  
                - Simulates 0DTE (zero days to expiration) options
                - Captures ~10% of underlying price movement
                - $1 SPY move = $0.10 profit/loss per contract
                - Example: SPY moves from $500 to $502 = $0.20 profit per contract
                - Best for: Limited risk exposure, learning strategies
                
                🚀 **Futures (2x multiplier)**
                - Simulates leveraged SPY futures contracts
                - 2x leverage on price movements
                - $1 SPY move = $2 profit/loss per contract
                - Example: SPY moves from $500 to $502 = $4 profit per contract
                - Best for: Experienced traders, higher risk/reward
                
                **Note:** The trading signals are identical - only the profit/loss calculations differ!
                """)
            with gr.Row():
                with gr.Column(scale=1):
                    # Strategy selector
                    strategy = gr.Dropdown(
                        choices=["ORB", "VWAP Bounce", "Gap and Go", "Compare All"],
                        value="ORB",
                        label="Select Strategy",
                        info="Choose a trading strategy to analyze"
                    )
                    
                    # Common parameters
                    days = gr.Dropdown(
                        choices=[
                            ("Last 7 days", 7),
                            ("Last 14 days", 14),
                            ("Last 30 days", 30),
                            ("Last 60 days", 60),
                            ("Last 90 days", 90),
                            ("Last 180 days", 180),
                            ("Last 365 days", 365),
                            ("All Available Data", 0)
                        ],
                        value=30,
                        label="Analysis Period",
                        info="Select time period for backtesting"
                    )
                    
                    # Capital and Risk Management
                    starting_capital = gr.Number(
                        value=25000,
                        label="Starting Capital ($)",
                        info="Initial trading capital (min $25k for PDT compliance)"
                    )
                    
                    risk_per_trade = gr.Slider(
                        minimum=0.5,
                        maximum=5.0,
                        value=2.0,
                        step=0.5,
                        label="Risk Per Trade (%)",
                        info="Maximum risk as % of capital per trade"
                    )
                    
                    
                    # Strategy-specific parameters (shown/hidden based on selection)
                    with gr.Column(visible=True) as orb_params:
                        timeframe = gr.Radio(
                            choices=[5, 15, 30, 60],
                            value=15,
                            label="ORB Timeframe (minutes)",
                            info="Opening range calculation period"
                        )
                        
                        instrument = gr.Radio(
                            choices=["Stock", "Options", "Futures"],
                            value="Options",
                            label="Instrument Type",
                            info="Stock: 1x (direct SPY shares) | Options: 0.1x (0DTE simulation) | Futures: 2x (leveraged)"
                        )
                    
                    with gr.Column(visible=False) as vwap_params:
                        min_distance = gr.Slider(
                            minimum=0.01,
                            maximum=0.5,
                            value=0.02,
                            step=0.01,
                            label="Min Distance from VWAP (%)",
                            info="Minimum distance for bounce signals (0.01-0.03% recommended for more trades)"
                        )
                    
                    with gr.Column(visible=False) as gap_params:
                        min_gap = gr.Slider(
                            minimum=0.1,
                            maximum=1.0,
                            value=0.3,
                            step=0.1,
                            label="Minimum Gap Size (%)",
                            info="Minimum gap for entry signal"
                        )
                    
                    # Run button
                    analyze_btn = gr.Button(
                        "🚀 Run Analysis",
                        variant="primary",
                        size="lg"
                    )
                    
                
                with gr.Column(scale=2):
                    results_display = gr.HTML(
                        value="<div style='height: 500px; overflow-y: auto; padding: 20px; background-color: #ffffff; border: 2px solid #333333; border-radius: 8px;'><pre style='font-family: \"Courier New\", Monaco, monospace; color: #000000; font-size: 14px; margin: 0;'>Results will appear here...</pre></div>",
                        label="Analysis Results"
                    )
            
            # Visualizations - Stacked vertically for better visibility
            with gr.Column():
                price_display = gr.Plot(label="SPY Price Chart")
                plot_display = gr.Plot(label="Strategy P&L")
                comparison_plot = gr.Plot(label="Strategy Comparison (Absolute P&L)", visible=False)
                drawdown_display = gr.Plot(label="Drawdown Analysis")
            
            # Export options
            with gr.Row():
                export_data = gr.File(label="Export Results (CSV)", visible=False)
                export_btn = gr.Button("📥 Download Results", visible=False)
        
        # Tab 2: Analytics Dashboard
        with gr.Tab("📊 Analytics Dashboard"):
            gr.Markdown("""
            ## Advanced Analytics
            Load and analyze saved backtest results with ML-powered insights
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    # Backtest selector
                    backtest_selector = gr.Dropdown(
                        choices=analyzer.get_saved_backtests(),
                        label="Select Saved Backtest",
                        info="Choose a previous backtest to analyze"
                    )
                    
                    with gr.Row():
                        load_btn = gr.Button("🔍 Load & Analyze", variant="secondary")
                        refresh_btn = gr.Button("🔄 Refresh List", variant="secondary", scale=0.5)
                    
                    # Analytics summary
                    analytics_summary = gr.Markdown("Select a backtest to view analytics...")
                    
                    # Debug info
                    debug_info = gr.Textbox(label="Debug Info", visible=True, interactive=False)
                
                with gr.Column(scale=2):
                    # Analytics plots - Organized in tabs for better visibility
                    with gr.Tabs():
                        with gr.Tab("📈 Performance Analytics"):
                            with gr.Column():
                                regime_plot = gr.Plot(label="Performance by Market Regime")
                        
                        with gr.Tab("🔍 Trade Analysis"):
                            with gr.Column():
                                cluster_plot = gr.Plot(label="Trade Clustering Analysis")
                                gr.Markdown("---")  # Separator
                                feature_plot = gr.Plot(label="Feature Importance")
                        
                        
                        with gr.Tab("🤖 AI Assistant"):
                            with gr.Column():
                                with gr.Row():
                                    ai_optimization_btn = gr.Button("🔧 Get Parameter Optimization", variant="secondary")
                                    ai_cluster_btn = gr.Button("🎯 Analyze Clusters", variant="secondary")
                                
                                ai_analysis_output = gr.Markdown(
                                    value="Select a backtest and click 'Load & Analyze' to get AI-powered insights and recommendations.\n\nOr use the buttons above for specific AI analysis:\n- **Parameter Optimization**: Get suggestions for improving strategy parameters\n- **Analyze Clusters**: Deep dive into cluster analysis and trading conditions",
                                    label="AI Analysis & Recommendations"
                                )
                        
                        with gr.Tab("📦 Export Data"):
                            with gr.Column():
                                gr.Markdown("### Export Complete Analysis Package")
                                gr.Markdown("Package all CSV files, plots, analysis results, and AI prompt templates for external use with ChatGPT or other AI tools.")
                                
                                with gr.Row():
                                    export_btn = gr.Button("📦 Create Export Package", variant="primary", size="lg")
                                    download_link = gr.File(label="Download Export Package", visible=False)
                                
                                export_status = gr.Markdown(
                                    value="### What gets exported:\n- **CSV Files**: Complete trade data with 43 technical features\n- **Plots**: All analysis charts as PNG images\n- **Documentation**: Data dictionary and AI prompt templates\n- **Configuration**: Strategy parameters and settings\n\nClick 'Create Export Package' to generate a comprehensive ZIP file for external AI analysis.",
                                    label="Export Status"
                                )
    
    # Event handlers
    def update_param_visibility(strategy_name):
        """Update parameter visibility based on strategy selection"""
        return (
            gr.update(visible=strategy_name == "ORB"),
            gr.update(visible=strategy_name == "VWAP Bounce"),
            gr.update(visible=strategy_name == "Gap and Go")
        )
    
    strategy.change(
        update_param_visibility,
        inputs=[strategy],
        outputs=[orb_params, vwap_params, gap_params]
    )
    
    def run_analysis(strategy_name, days_val, timeframe_val, instrument_val, min_distance_val, min_gap_val, starting_capital_val, risk_per_trade_val):
        """Run the selected strategy analysis"""
        result = analyzer.analyze_strategy(
            strategy_name, 
            timeframe_val, 
            days_val, 
            instrument_val,
            min_gap_val,
            min_distance_val,
            starting_capital_val,
            risk_per_trade_val
        )
        
        # Handle different return types
        if strategy_name == "Compare All":
            # Compare All returns: (summary, None, normalized_plot, absolute_plot, csv_data)
            summary, price_plot, normalized_plot, absolute_plot, csv_data = result
            drawdown_plot = None
        else:
            # Regular strategies return: (summary, price_plot, pnl_plot, drawdown_plot, csv_data)
            summary, price_plot, pnl_plot, drawdown_plot, csv_data = result
            normalized_plot = pnl_plot
            absolute_plot = None
        
        # Update export visibility
        export_visible = csv_data is not None
        
        # Handle comparison plot visibility
        comparison_visible = strategy_name == "Compare All"
        
        return (
            summary, 
            price_plot,
            normalized_plot,
            gr.update(visible=comparison_visible, value=absolute_plot),
            drawdown_plot,
            csv_data if csv_data else None,
            gr.update(visible=export_visible),
            gr.update(visible=export_visible)
        )
    
    analyze_btn.click(
        run_analysis,
        inputs=[strategy, days, timeframe, instrument, min_distance, min_gap, starting_capital, risk_per_trade],
        outputs=[results_display, price_display, plot_display, comparison_plot, drawdown_display, export_data, export_data, export_btn]
    )
    
    # Analytics event handler
    def load_and_analyze_backtest(backtest_id):
        """Load saved backtest and generate analytics"""
        if not backtest_id:
            return "Please select a backtest to analyze", None, None, None, "Please select a backtest to get AI insights"
        
        summary, regime_fig, cluster_fig, feature_fig, ai_analysis = analyzer.load_saved_backtest(backtest_id)
        
        return summary, regime_fig, cluster_fig, feature_fig, ai_analysis
    
    load_btn.click(
        load_and_analyze_backtest,
        inputs=[backtest_selector],
        outputs=[analytics_summary, regime_plot, cluster_plot, feature_plot, ai_analysis_output]
    )
    
    # AI-specific analysis handlers
    def ai_parameter_optimization(backtest_id):
        """Generate AI parameter optimization suggestions"""
        if not backtest_id:
            return "Please select a backtest first"
        
        try:
            from trading_engine.ai_analytics import AIAnalyticsAssistant
            from trading_engine.backtest_results import BacktestResults
            
            # Load backtest data
            backtest = BacktestResults.load(backtest_id)
            ai_assistant = AIAnalyticsAssistant()
            
            # Generate parameter optimization suggestions
            optimization_analysis = ai_assistant.suggest_parameter_optimization(backtest.trades_df)
            
            return optimization_analysis
            
        except Exception as e:
            return f"❌ Error generating optimization suggestions: {str(e)}"
    
    def ai_cluster_analysis(backtest_id):
        """Generate AI cluster analysis"""
        if not backtest_id:
            return "Please select a backtest first"
        
        try:
            from trading_engine.ai_analytics import AIAnalyticsAssistant
            from trading_engine.backtest_results import BacktestResults
            from trading_engine.analytics import TradingAnalytics
            
            # Load backtest data
            backtest = BacktestResults.load(backtest_id)
            analytics = TradingAnalytics(backtest.daily_df, backtest.trades_df)
            ai_assistant = AIAnalyticsAssistant()
            
            # Generate cluster analysis
            cluster_stats, _ = analytics.cluster_trades()
            cluster_analysis = ai_assistant.analyze_clustering_results(cluster_stats, backtest.trades_df)
            
            return cluster_analysis
            
        except Exception as e:
            return f"❌ Error generating cluster analysis: {str(e)}"
    
    ai_optimization_btn.click(
        ai_parameter_optimization,
        inputs=[backtest_selector],
        outputs=[ai_analysis_output]
    )
    
    ai_cluster_btn.click(
        ai_cluster_analysis,
        inputs=[backtest_selector],
        outputs=[ai_analysis_output]
    )
    
    
    
    # Export functionality
    def create_export_package(backtest_id):
        """Create comprehensive export package"""
        if not backtest_id:
            return None, "❌ Please select and load a backtest first"
        
        if not hasattr(analyzer, 'current_backtest_id') or analyzer.current_backtest_id != backtest_id:
            return None, "❌ Please click 'Load & Analyze' first to generate all analytics"
        
        try:
            from trading_engine.data_exporter import TradingDataExporter
            from trading_engine.backtest_results import BacktestResults
            
            # Get backtest path
            backtest = BacktestResults.load(backtest_id)
            
            # Create exporter
            exporter = TradingDataExporter()
            
            # No predictions to export
            
            # Create export package
            zip_path = exporter.create_comprehensive_export(
                backtest.save_path,
                analyzer.current_analytics_data,
                analyzer.current_plots,
                None  # No predictions to export
            )
            
            # Generate success message
            success_message = exporter.get_export_summary(zip_path)
            
            return gr.File(value=zip_path, visible=True), success_message
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return None, f"❌ Export failed: {str(e)}"
    
    export_btn.click(
        create_export_package,
        inputs=[backtest_selector],
        outputs=[download_link, export_status]
    )
    
    # Refresh backtest list when page loads or button clicked
    def refresh_backtest_list():
        try:
            backtests = analyzer.get_saved_backtests()
            debug_msg = f"Found {len(backtests)} saved backtests"
            if backtests:
                debug_msg += f"\nLatest: {backtests[0][0]}"
            else:
                # Check what's in the directory
                import os
                backtest_dir = "backtest_results"
                if os.path.exists(backtest_dir):
                    folders = os.listdir(backtest_dir)
                    debug_msg += f"\nFolders in {backtest_dir}: {folders[:5]}"
                    if folders:
                        # Check first folder
                        first_folder = os.path.join(backtest_dir, folders[0])
                        files = os.listdir(first_folder) if os.path.isdir(first_folder) else []
                        debug_msg += f"\nFiles in {folders[0]}: {files}"
            
            return gr.update(choices=backtests), debug_msg
        except Exception as e:
            return gr.update(choices=[]), f"Error: {str(e)}"
    
    app.load(refresh_backtest_list, outputs=[backtest_selector, debug_info])
    refresh_btn.click(refresh_backtest_list, outputs=[backtest_selector, debug_info])
    


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎯 0DTE Trading Analysis System")
    print("="*60)
    
    if DATA_AVAILABLE:
        print(f"✅ Loaded {len(agent.df):,} bars of SPY data")
        if 'date' in agent.df.columns:
            print(f"📅 Date range: {agent.df['date'].min()} to {agent.df['date'].max()}")
        else:
            print(f"📅 Date range: {agent.df.index.min()} to {agent.df.index.max()}")
    else:
        print("❌ SPY data not available")
        print("💡 Run: python market_data/spy_data_downloader.py")
    
    if AI_AVAILABLE:
        if config.USE_LOCAL_AI:
            print(f"🤖 AI Assistant: ENABLED (LM Studio at {config.LM_STUDIO_URL})")
        else:
            print("🤖 AI Assistant: ENABLED (OpenAI API)")
    else:
        print("🤖 AI Assistant: DISABLED (start LM Studio or configure API key)")
    
    # Get port from environment variable or use default
    port = int(os.environ.get('GRADIO_SERVER_PORT', '7866'))
    
    print(f"\n🌐 Starting application at: http://127.0.0.1:{port}")
    print("📊 Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.launch(
        server_name="127.0.0.1",
        server_port=port,
        share=False,
        quiet=True
    )