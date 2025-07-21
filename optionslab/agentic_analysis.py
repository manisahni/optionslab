#!/usr/bin/env python3
"""
Agentic Analysis module for OptionsLab
Provides LangChain + Ollama integration for deep trade analysis
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path

# LangChain imports
try:
    from langchain_experimental.agents import create_pandas_dataframe_agent
    from langchain.agents import AgentType
    from langchain.tools import tool
    from langchain_community.llms import Ollama
    from langchain.callbacks import StreamingStdOutCallbackHandler
except ImportError as e:
    print(f"Warning: Some LangChain imports failed: {e}")
    create_pandas_dataframe_agent = None
    AgentType = None
    tool = lambda x: x  # Dummy decorator
    Ollama = None
    StreamingStdOutCallbackHandler = None

# Local imports
from .ai_assistant_multi import BaseAIProvider


class TradeAnalysisTools:
    """Collection of specialized tools for trade analysis"""
    
    @staticmethod
    def find_losing_patterns(trades_df: pd.DataFrame) -> str:
        """Analyze common patterns in losing trades"""
        losing_trades = trades_df[trades_df['pnl'] < 0].copy()
        
        if losing_trades.empty:
            return "No losing trades found in the dataset."
        
        patterns = []
        
        # Pattern 1: Exit reasons
        exit_reasons = losing_trades['exit_reason'].value_counts()
        patterns.append(f"Exit Reasons for Losses:\n{exit_reasons.to_string()}")
        
        # Pattern 2: Days held
        avg_days = losing_trades['days_held'].mean()
        patterns.append(f"\nAverage days held for losing trades: {avg_days:.1f}")
        
        # Pattern 3: Entry conditions
        if 'entry_delta' in losing_trades.columns:
            avg_delta = losing_trades['entry_delta'].mean()
            patterns.append(f"\nAverage entry delta for losing trades: {avg_delta:.3f}")
        
        # Pattern 4: Market conditions
        if 'underlying_move_pct' in losing_trades.columns:
            avg_move = losing_trades['underlying_move_pct'].mean()
            patterns.append(f"\nAverage underlying move: {avg_move:.2f}%")
        
        # Pattern 5: Loss magnitude
        avg_loss = losing_trades['pnl_pct'].mean()
        max_loss = losing_trades['pnl_pct'].min()
        patterns.append(f"\nAverage loss: {avg_loss:.1f}%")
        patterns.append(f"Maximum loss: {max_loss:.1f}%")
        
        return "\n".join(patterns)
    
    @staticmethod
    def calculate_risk_metrics(trades_df: pd.DataFrame, initial_capital: float = 10000) -> str:
        """Calculate comprehensive risk metrics"""
        if trades_df.empty or 'pnl' not in trades_df.columns:
            return "Insufficient data to calculate risk metrics."
        
        completed_trades = trades_df[trades_df['exit_date'].notna()].copy()
        
        if completed_trades.empty:
            return "No completed trades to analyze."
        
        # Sort by exit date
        completed_trades['exit_date'] = pd.to_datetime(completed_trades['exit_date'])
        completed_trades = completed_trades.sort_values('exit_date')
        
        # Calculate returns
        completed_trades['cumulative_pnl'] = completed_trades['pnl'].cumsum()
        completed_trades['portfolio_value'] = initial_capital + completed_trades['cumulative_pnl']
        completed_trades['returns'] = completed_trades['pnl'] / initial_capital
        
        # Calculate metrics
        total_return = completed_trades['cumulative_pnl'].iloc[-1] / initial_capital
        
        # Sharpe Ratio (assuming 252 trading days, 0% risk-free rate)
        if len(completed_trades) > 1:
            daily_returns = completed_trades.groupby(completed_trades['exit_date'].dt.date)['returns'].sum()
            sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        else:
            sharpe = 0
        
        # Sortino Ratio
        downside_returns = completed_trades[completed_trades['returns'] < 0]['returns']
        if len(downside_returns) > 0:
            downside_std = downside_returns.std()
            sortino = np.sqrt(252) * completed_trades['returns'].mean() / downside_std if downside_std > 0 else 0
        else:
            sortino = float('inf') if completed_trades['returns'].mean() > 0 else 0
        
        # Maximum Drawdown
        cummax = completed_trades['portfolio_value'].cummax()
        drawdown = (completed_trades['portfolio_value'] - cummax) / cummax
        max_drawdown = drawdown.min()
        
        # Win rate
        winning_trades = completed_trades[completed_trades['pnl'] > 0]
        win_rate = len(winning_trades) / len(completed_trades) if len(completed_trades) > 0 else 0
        
        # Profit factor
        gross_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(completed_trades[completed_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        metrics = f"""
Risk Metrics Summary:
- Total Return: {total_return:.2%}
- Sharpe Ratio: {sharpe:.2f}
- Sortino Ratio: {sortino:.2f}
- Maximum Drawdown: {max_drawdown:.2%}
- Win Rate: {win_rate:.2%}
- Profit Factor: {profit_factor:.2f}
- Total Trades: {len(completed_trades)}
- Average Trade: {completed_trades['pnl'].mean():.2f}
- Best Trade: {completed_trades['pnl'].max():.2f}
- Worst Trade: {completed_trades['pnl'].min():.2f}
"""
        return metrics
    
    @staticmethod
    def validate_strategy_adherence(trades_df: pd.DataFrame, strategy_config: Dict) -> str:
        """Check if trades follow strategy rules"""
        violations = []
        
        if trades_df.empty:
            return "No trades to validate."
        
        # Check delta targeting
        if 'delta_target' in strategy_config.get('entry_rules', {}):
            target_delta = strategy_config['entry_rules']['delta_target']
            delta_range = strategy_config['entry_rules'].get('delta_range', 0.05)
            
            if 'entry_delta' in trades_df.columns:
                out_of_range = trades_df[
                    (trades_df['entry_delta'] < target_delta - delta_range) |
                    (trades_df['entry_delta'] > target_delta + delta_range)
                ]
                
                if not out_of_range.empty:
                    violations.append(f"Delta violations: {len(out_of_range)} trades outside target range {target_delta}±{delta_range}")
                    avg_delta = trades_df['entry_delta'].mean()
                    violations.append(f"Average entry delta: {avg_delta:.3f} (target: {target_delta})")
        
        # Check DTE requirements
        if 'dte_min' in strategy_config.get('entry_rules', {}):
            dte_min = strategy_config['entry_rules']['dte_min']
            dte_max = strategy_config['entry_rules'].get('dte_max', 60)
            
            if 'dte_at_entry' in trades_df.columns:
                dte_violations = trades_df[
                    (trades_df['dte_at_entry'] < dte_min) |
                    (trades_df['dte_at_entry'] > dte_max)
                ]
                
                if not dte_violations.empty:
                    violations.append(f"DTE violations: {len(dte_violations)} trades outside range {dte_min}-{dte_max}")
        
        # Check position sizing
        if 'contracts' in trades_df.columns and 'contracts' in strategy_config:
            expected_contracts = strategy_config['contracts']
            wrong_size = trades_df[trades_df['contracts'] != expected_contracts]
            
            if not wrong_size.empty:
                violations.append(f"Position size violations: {len(wrong_size)} trades with incorrect contract count")
        
        # Check exit rules
        exit_rules = strategy_config.get('exit_rules', {})
        if 'stop_loss' in exit_rules and 'pnl_pct' in trades_df.columns:
            stop_loss = exit_rules['stop_loss']
            # Check if losses exceeded stop loss
            excessive_losses = trades_df[trades_df['pnl_pct'] < stop_loss]
            if not excessive_losses.empty:
                violations.append(f"Stop loss violations: {len(excessive_losses)} trades exceeded {stop_loss:.0%} loss")
        
        if violations:
            return "Strategy Adherence Issues Found:\n" + "\n".join(violations)
        else:
            return "All trades adhere to strategy rules. ✓"
    
    @staticmethod
    def find_optimal_parameters(trades_df: pd.DataFrame) -> str:
        """Suggest parameter optimizations based on trade data"""
        if trades_df.empty:
            return "No trades to analyze for optimization."
        
        suggestions = []
        
        # Analyze by delta buckets
        if 'entry_delta' in trades_df.columns and 'pnl_pct' in trades_df.columns:
            trades_df['delta_bucket'] = pd.cut(trades_df['entry_delta'], 
                                               bins=[0, 0.2, 0.3, 0.4, 0.5, 0.6, 1.0],
                                               labels=['0.0-0.2', '0.2-0.3', '0.3-0.4', '0.4-0.5', '0.5-0.6', '0.6+'])
            
            delta_performance = trades_df.groupby('delta_bucket').agg({
                'pnl_pct': ['mean', 'count'],
                'trade_id': 'count'
            }).round(2)
            
            best_delta_bucket = trades_df.groupby('delta_bucket')['pnl_pct'].mean().idxmax()
            suggestions.append(f"Optimal delta range: {best_delta_bucket} (avg return: {trades_df[trades_df['delta_bucket'] == best_delta_bucket]['pnl_pct'].mean():.1f}%)")
        
        # Analyze by DTE
        if 'dte_at_entry' in trades_df.columns:
            trades_df['dte_bucket'] = pd.cut(trades_df['dte_at_entry'],
                                             bins=[0, 15, 30, 45, 60, 100],
                                             labels=['0-15', '15-30', '30-45', '45-60', '60+'])
            
            best_dte_bucket = trades_df.groupby('dte_bucket')['pnl_pct'].mean().idxmax()
            suggestions.append(f"Optimal DTE range: {best_dte_bucket} days")
        
        # Analyze holding periods
        if 'days_held' in trades_df.columns:
            winning_trades = trades_df[trades_df['pnl'] > 0]
            losing_trades = trades_df[trades_df['pnl'] < 0]
            
            avg_win_days = None
            avg_loss_days = None
            
            if not winning_trades.empty:
                avg_win_days = winning_trades['days_held'].mean()
                suggestions.append(f"Average winning trade duration: {avg_win_days:.1f} days")
            
            if not losing_trades.empty:
                avg_loss_days = losing_trades['days_held'].mean()
                suggestions.append(f"Average losing trade duration: {avg_loss_days:.1f} days")
                
                if avg_win_days is not None and avg_loss_days > avg_win_days:
                    suggestions.append("⚠️ Consider tighter stop losses - losing trades held longer than winners")
        
        # Exit reason analysis
        if 'exit_reason' in trades_df.columns:
            exit_performance = trades_df.groupby('exit_reason')['pnl_pct'].agg(['mean', 'count'])
            best_exit = exit_performance['mean'].idxmax()
            suggestions.append(f"Most profitable exit type: {best_exit} ({exit_performance.loc[best_exit, 'mean']:.1f}% avg return)")
        
        return "Parameter Optimization Suggestions:\n" + "\n".join(suggestions)
    
    @staticmethod
    def analyze_market_regimes(trades_df: pd.DataFrame) -> str:
        """Identify market conditions affecting performance"""
        if trades_df.empty or 'underlying_move_pct' not in trades_df.columns:
            return "Insufficient data for market regime analysis."
        
        # Classify market moves
        trades_df['market_regime'] = pd.cut(trades_df['underlying_move_pct'],
                                           bins=[-100, -2, -0.5, 0.5, 2, 100],
                                           labels=['Strong Down', 'Mild Down', 'Neutral', 'Mild Up', 'Strong Up'])
        
        regime_performance = trades_df.groupby('market_regime').agg({
            'pnl_pct': ['mean', 'count'],
            'trade_id': 'count'
        })
        
        analysis = ["Market Regime Analysis:"]
        
        for regime in ['Strong Down', 'Mild Down', 'Neutral', 'Mild Up', 'Strong Up']:
            if regime in trades_df['market_regime'].values:
                regime_trades = trades_df[trades_df['market_regime'] == regime]
                avg_return = regime_trades['pnl_pct'].mean()
                count = len(regime_trades)
                win_rate = (regime_trades['pnl'] > 0).mean()
                
                analysis.append(f"\n{regime} ({count} trades):")
                analysis.append(f"  - Average return: {avg_return:.1f}%")
                analysis.append(f"  - Win rate: {win_rate:.1%}")
        
        # Volatility analysis if IV data available
        if 'entry_iv' in trades_df.columns:
            trades_df['iv_bucket'] = pd.cut(trades_df['entry_iv'],
                                           bins=[0, 0.15, 0.25, 0.35, 1.0],
                                           labels=['Low Vol', 'Normal Vol', 'High Vol', 'Extreme Vol'])
            
            analysis.append("\n\nVolatility Regime Analysis:")
            for vol_regime in ['Low Vol', 'Normal Vol', 'High Vol', 'Extreme Vol']:
                if vol_regime in trades_df['iv_bucket'].values:
                    vol_trades = trades_df[trades_df['iv_bucket'] == vol_regime]
                    avg_return = vol_trades['pnl_pct'].mean()
                    count = len(vol_trades)
                    
                    analysis.append(f"\n{vol_regime} ({count} trades): {avg_return:.1f}% avg return")
        
        return "\n".join(analysis)


class OllamaAgentProvider(BaseAIProvider):
    """Ollama provider with LangChain agents for deep analysis"""
    
    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.llm = None
        self.tools = None
        self.df_agent = None
        
    def initialize(self) -> bool:
        """Initialize Ollama and tools"""
        try:
            # Initialize Ollama LLM
            self.llm = Ollama(
                model=self.model,
                base_url=self.base_url,
                temperature=0.1,  # Lower temperature for more consistent analysis
                callbacks=[StreamingStdOutCallbackHandler()]
            )
            
            # Initialize analysis tools
            self.tools = [
                TradeAnalysisTools.find_losing_patterns,
                TradeAnalysisTools.calculate_risk_metrics,
                TradeAnalysisTools.validate_strategy_adherence,
                TradeAnalysisTools.find_optimal_parameters,
                TradeAnalysisTools.analyze_market_regimes,
            ]
            
            # Test connection
            response = self.llm.invoke("Test connection")
            return True
            
        except Exception as e:
            print(f"Failed to initialize Ollama: {e}")
            return False
    
    def create_dataframe_agent(self, df: pd.DataFrame) -> Any:
        """Create a pandas dataframe agent"""
        try:
            agent = create_pandas_dataframe_agent(
                self.llm,
                df,
                verbose=True,
                agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                handle_parsing_errors=True,
                max_iterations=5,
                early_stopping_method="generate"
            )
            return agent
        except Exception as e:
            print(f"Error creating dataframe agent: {e}")
            return None
    
    def chat(self, message: str, trade_data: Optional[Dict] = None, 
             csv_path: Optional[str] = None, yaml_path: Optional[str] = None) -> str:
        """Chat with Ollama using agents for complex analysis"""
        if not self.is_configured():
            return "Ollama not configured. Please ensure Ollama is running and Mixtral model is available."
        
        try:
            # Load trade data
            trades_df = None
            if csv_path and Path(csv_path).exists():
                trades_df = pd.read_csv(csv_path)
            elif trade_data and 'trades' in trade_data:
                trades_df = pd.DataFrame(trade_data['trades'])
            
            if trades_df is None or trades_df.empty:
                return "No trade data available for analysis."
            
            # Load strategy config
            strategy_config = {}
            if yaml_path and Path(yaml_path).exists():
                import yaml
                with open(yaml_path, 'r') as f:
                    strategy_config = yaml.safe_load(f)
            
            # Determine which analysis to perform based on the message
            message_lower = message.lower()
            
            # Route to appropriate tool or agent
            if any(word in message_lower for word in ['losing', 'loss', 'pattern']):
                result = TradeAnalysisTools.find_losing_patterns(trades_df)
                
            elif any(word in message_lower for word in ['risk', 'sharpe', 'sortino', 'drawdown']):
                metadata = trade_data.get('metadata', {}) if trade_data else {}
                initial_capital = metadata.get('initial_capital', 10000)
                result = TradeAnalysisTools.calculate_risk_metrics(trades_df, initial_capital)
                
            elif any(word in message_lower for word in ['adherence', 'validate', 'rules', 'violation']):
                result = TradeAnalysisTools.validate_strategy_adherence(trades_df, strategy_config)
                
            elif any(word in message_lower for word in ['optimize', 'optimal', 'parameter', 'improve']):
                result = TradeAnalysisTools.find_optimal_parameters(trades_df)
                
            elif any(word in message_lower for word in ['market', 'regime', 'condition', 'volatility']):
                result = TradeAnalysisTools.analyze_market_regimes(trades_df)
                
            else:
                # For complex queries, use the DataFrame agent
                agent = self.create_dataframe_agent(trades_df)
                if agent:
                    # Add context about the data
                    context = f"""
You are analyzing options trading backtest data. The dataframe contains these key columns:
- trade_id: Unique identifier for each trade
- entry_date/exit_date: When positions were opened/closed
- option_type: C for calls, P for puts
- strike: Option strike price
- entry_delta/exit_delta: Option delta at entry/exit
- pnl: Profit/loss in dollars
- pnl_pct: Profit/loss percentage
- exit_reason: Why the trade was closed
- days_held: Duration of the trade
- entry_iv/exit_iv: Implied volatility

User question: {message}
"""
                    result = agent.run(context)
                else:
                    result = "Unable to create analysis agent."
            
            return result
            
        except Exception as e:
            return f"Error during analysis: {str(e)}"
    
    def is_configured(self) -> bool:
        """Check if Ollama is configured"""
        return self.llm is not None


def create_analysis_report(trades_df: pd.DataFrame, strategy_config: Dict, 
                          initial_capital: float = 10000) -> str:
    """Generate a comprehensive analysis report"""
    report_sections = []
    
    # Header
    report_sections.append("# Comprehensive Trading Analysis Report\n")
    report_sections.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Risk Metrics
    report_sections.append("## Risk Metrics")
    report_sections.append(TradeAnalysisTools.calculate_risk_metrics(trades_df, initial_capital))
    
    # Strategy Adherence
    report_sections.append("\n## Strategy Adherence")
    report_sections.append(TradeAnalysisTools.validate_strategy_adherence(trades_df, strategy_config))
    
    # Market Regime Analysis
    report_sections.append("\n## Market Regime Performance")
    report_sections.append(TradeAnalysisTools.analyze_market_regimes(trades_df))
    
    # Losing Pattern Analysis
    report_sections.append("\n## Losing Trade Patterns")
    report_sections.append(TradeAnalysisTools.find_losing_patterns(trades_df))
    
    # Optimization Suggestions
    report_sections.append("\n## Optimization Recommendations")
    report_sections.append(TradeAnalysisTools.find_optimal_parameters(trades_df))
    
    return "\n".join(report_sections)