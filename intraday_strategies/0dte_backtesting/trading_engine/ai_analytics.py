"""
AI-Powered Analytics Assistant
Analyzes backtest results and provides intelligent insights using LM Studio
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, List, Optional, Tuple
import requests
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AIAnalyticsAssistant:
    """AI assistant for analyzing trading results and providing insights"""
    
    def __init__(self, lm_studio_url: str = "http://localhost:1234/v1"):
        self.lm_studio_url = lm_studio_url
        self.client_available = self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test connection to LM Studio"""
        try:
            response = requests.get(f"{self.lm_studio_url}/models", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LM Studio not available: {e}")
            return False
    
    def _call_llm(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call LM Studio API with improved error handling"""
        if not self.client_available:
            return self._create_fallback_response("LM Studio not available")
        
        try:
            # Get available models first
            models_response = requests.get(f"{self.lm_studio_url}/models", timeout=5)
            if models_response.status_code != 200:
                return self._create_fallback_response("LM Studio not responding")
            
            models = models_response.json()
            if not models.get('data'):
                return self._create_fallback_response("No models loaded in LM Studio")
            
            # Use the first available model
            model_id = models['data'][0]['id']
            
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert trading analyst. Provide concise, actionable insights. Be specific and practical. Limit responses to key recommendations only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": min(max_tokens, 500),  # Limit tokens to reduce processing time
                "temperature": 0.3,  # Lower temperature for more focused responses
                "stream": False
            }
            
            # Increased timeout for complex analysis
            response = requests.post(
                f"{self.lm_studio_url}/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60  # Increased to 60 seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content']
                else:
                    return self._create_fallback_response("Invalid AI response format")
            else:
                return self._create_fallback_response(f"API Error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning("LM Studio request timed out")
            return self._create_fallback_response("AI request timed out")
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to LM Studio")
            return self._create_fallback_response("Could not connect to LM Studio")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._create_fallback_response(f"AI Error: {str(e)}")
    
    def _create_fallback_response(self, error_reason: str) -> str:
        """Create a fallback analysis when AI is not available"""
        return f"""# 📊 Trading Analysis Summary

⚠️ **AI Assistant Unavailable**: {error_reason}

## 📈 Manual Analysis Recommendations

### Key Areas to Investigate:
1. **Win Rate Analysis**: Review trades with win rates below 50%
2. **Time-Based Patterns**: Check performance by hour and day
3. **Volatility Impact**: Analyze performance across different market conditions
4. **Risk Management**: Review position sizing and stop-loss effectiveness

### Immediate Actions:
- ✅ Export your data using the Export tab
- ✅ Use external AI tools (ChatGPT) with the provided templates
- ✅ Focus on trades with highest P&L variability
- ✅ Consider filtering conditions that consistently underperform

### Next Steps:
1. **Restart LM Studio** if you want AI-powered insights
2. **Use the Export feature** to analyze data externally
3. **Check the Analytics tabs** for visual patterns
4. **Review risk metrics** in the main analytics dashboard

*Tip: The export package contains everything needed for external AI analysis!*
"""
    
    def analyze_backtest_results(self, backtest_path: str, analytics_data: Dict) -> str:
        """Comprehensive AI analysis of backtest results"""
        
        # Load CSV data
        trades_csv = self._load_csv_data(backtest_path)
        if trades_csv is None:
            return "❌ Could not load backtest data"
        
        # Create comprehensive analysis prompt
        prompt = self._create_analysis_prompt(trades_csv, analytics_data)
        
        # Get AI insights
        insights = self._call_llm(prompt, max_tokens=1500)
        
        return self._format_ai_response(insights)
    
    def _load_csv_data(self, backtest_path: str) -> Optional[pd.DataFrame]:
        """Load enhanced CSV data from backtest"""
        try:
            # Try enhanced full data first
            enhanced_path = Path(backtest_path) / "trades_enhanced_full.csv"
            if enhanced_path.exists():
                return pd.read_csv(enhanced_path)
            
            # Fallback to basic enhanced data
            basic_path = Path(backtest_path) / "trades_enhanced.csv"
            if basic_path.exists():
                return pd.read_csv(basic_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return None
    
    def _create_analysis_prompt(self, trades_df: pd.DataFrame, analytics_data: Dict) -> str:
        """Create comprehensive analysis prompt for the LLM"""
        
        # Basic statistics
        total_trades = len(trades_df)
        win_rate = (trades_df['pnl'] > 0).mean() * 100
        total_pnl = trades_df['pnl'].sum()
        avg_pnl = trades_df['pnl'].mean()
        best_trade = trades_df['pnl'].max()
        worst_trade = trades_df['pnl'].min()
        
        # Performance by direction if available
        direction_analysis = ""
        if 'breakout_type' in trades_df.columns:
            long_stats = self._analyze_direction(trades_df, 'long')
            short_stats = self._analyze_direction(trades_df, 'short')
            direction_analysis = f"""
DIRECTIONAL PERFORMANCE:
- Long trades: {long_stats['count']} trades, {long_stats['win_rate']:.1f}% win rate, ${long_stats['total_pnl']:.2f} P&L
- Short trades: {short_stats['count']} trades, {short_stats['win_rate']:.1f}% win rate, ${short_stats['total_pnl']:.2f} P&L
"""
        
        # Time-based analysis if available
        time_analysis = ""
        if 'entry_hour' in trades_df.columns:
            hourly_stats = trades_df.groupby('entry_hour')['pnl'].agg(['count', 'mean', 'sum'])
            best_hour = hourly_stats['mean'].idxmax()
            worst_hour = hourly_stats['mean'].idxmin()
            time_analysis = f"""
TIME-BASED PERFORMANCE:
- Best performing hour: {best_hour}:00 (avg P&L: ${hourly_stats.loc[best_hour, 'mean']:.2f})
- Worst performing hour: {worst_hour}:00 (avg P&L: ${hourly_stats.loc[worst_hour, 'mean']:.2f})
"""
        
        # Volatility analysis if available
        vol_analysis = ""
        if 'entry_volatility' in trades_df.columns:
            trades_df['vol_quartile'] = pd.qcut(trades_df['entry_volatility'], 4, labels=['Low', 'Med-Low', 'Med-High', 'High'])
            vol_stats = trades_df.groupby('vol_quartile', observed=False)['pnl'].agg(['count', 'mean'])
            vol_analysis = f"""
VOLATILITY PERFORMANCE:
- Low vol: {vol_stats.loc['Low', 'count']} trades, ${vol_stats.loc['Low', 'mean']:.2f} avg
- Med-Low vol: {vol_stats.loc['Med-Low', 'count']} trades, ${vol_stats.loc['Med-Low', 'mean']:.2f} avg
- Med-High vol: {vol_stats.loc['Med-High', 'count']} trades, ${vol_stats.loc['Med-High', 'mean']:.2f} avg
- High vol: {vol_stats.loc['High', 'count']} trades, ${vol_stats.loc['High', 'mean']:.2f} avg
"""
        
        # Clustering insights from analytics
        clustering_insights = analytics_data.get('clustering_insights', 'No clustering data available')
        
        # Risk metrics
        risk_info = analytics_data.get('risk_metrics', {})
        risk_analysis = f"""
RISK METRICS:
- Sharpe Ratio: {risk_info.get('sharpe_ratio', 'N/A')}
- Max Drawdown: ${risk_info.get('max_drawdown', 'N/A')}
- Profit Factor: {risk_info.get('profit_factor', 'N/A')}
- Win Rate: {risk_info.get('win_rate', win_rate):.1f}%
"""
        
        prompt = f"""
TRADING STRATEGY PERFORMANCE ANALYSIS

OVERVIEW:
- Total Trades: {total_trades}
- Win Rate: {win_rate:.1f}%
- Total P&L: ${total_pnl:.2f}
- Average P&L per trade: ${avg_pnl:.2f}
- Best Trade: ${best_trade:.2f}
- Worst Trade: ${worst_trade:.2f}

{risk_analysis}

{direction_analysis}

{time_analysis}

{vol_analysis}

CLUSTERING ANALYSIS:
{clustering_insights}

AVAILABLE DATA FEATURES:
{list(trades_df.columns)}

TASK: Analyze this trading strategy performance and provide:

1. **KEY PERFORMANCE INSIGHTS**: What patterns do you see? What's working well and what isn't?

2. **IMPROVEMENT OPPORTUNITIES**: Specific, actionable recommendations to improve performance:
   - Parameter adjustments
   - Entry/exit criteria modifications
   - Risk management improvements
   - Time-based filters
   - Market condition filters

3. **RISK MANAGEMENT SUGGESTIONS**: How to reduce drawdowns and improve consistency

4. **SPECIFIC FILTERS TO IMPLEMENT**: Based on the data, what specific conditions should be avoided or favored?

5. **NEXT STEPS**: Concrete actions to take for optimization

Be specific, practical, and focus on actionable insights that can be implemented immediately.
"""
        
        return prompt
    
    def _analyze_direction(self, trades_df: pd.DataFrame, direction: str) -> Dict:
        """Analyze performance by trade direction"""
        direction_trades = trades_df[trades_df['breakout_type'] == direction]
        
        if len(direction_trades) == 0:
            return {'count': 0, 'win_rate': 0, 'total_pnl': 0, 'avg_pnl': 0}
        
        return {
            'count': len(direction_trades),
            'win_rate': (direction_trades['pnl'] > 0).mean() * 100,
            'total_pnl': direction_trades['pnl'].sum(),
            'avg_pnl': direction_trades['pnl'].mean()
        }
    
    def _format_ai_response(self, response: str) -> str:
        """Format AI response for display"""
        
        # Add header
        formatted = f"""# 🤖 AI Analytics Assistant

{response}

---
*Analysis powered by LM Studio - Generated at {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return formatted
    
    def analyze_clustering_results(self, cluster_stats: pd.DataFrame, trades_df: pd.DataFrame) -> str:
        """Analyze clustering results specifically"""
        
        if cluster_stats.empty:
            return "No clustering data available for analysis."
        
        # Create clustering-focused prompt
        cluster_summary = self._summarize_clusters(cluster_stats, trades_df)
        
        prompt = f"""
TRADING CLUSTER ANALYSIS

{cluster_summary}

Based on this clustering analysis:

1. **CLUSTER INSIGHTS**: What do the different clusters tell us about market conditions and performance?

2. **OPTIMAL CONDITIONS**: Which cluster represents the best trading conditions and why?

3. **CONDITIONS TO AVOID**: Which cluster should be filtered out and what characteristics define it?

4. **FEATURE IMPORTANCE**: Which features seem most important for separating good vs bad trades?

5. **ACTIONABLE FILTERS**: Specific filter criteria to implement based on cluster analysis.

Provide specific, implementable recommendations.
"""
        
        insights = self._call_llm(prompt, max_tokens=800)
        return f"## 🔍 Cluster Analysis Insights\n\n{insights}"
    
    def _summarize_clusters(self, cluster_stats: pd.DataFrame, trades_df: pd.DataFrame) -> str:
        """Summarize cluster statistics for AI analysis"""
        
        summary = "CLUSTER PERFORMANCE SUMMARY:\n"
        
        for idx, row in cluster_stats.iterrows():
            if hasattr(row, 'name'):
                cluster_id = row.name
            else:
                cluster_id = idx
                
            # Get cluster trades for detailed analysis
            cluster_trades = trades_df[trades_df.get('cluster', -1) == cluster_id]
            
            summary += f"""
Cluster {cluster_id}:
- Trades: {len(cluster_trades)}
- Avg P&L: ${row.get('pnl', {}).get('mean', 0):.2f}
- Win Rate: {row.get('win_rate', 0):.1f}%
- Total P&L: ${row.get('pnl', {}).get('sum', 0):.2f}
"""
        
        return summary
    
    def suggest_parameter_optimization(self, trades_df: pd.DataFrame) -> str:
        """Suggest parameter optimizations based on data analysis"""
        
        # Analyze parameter sensitivity if ORB range data is available
        optimization_data = ""
        
        if 'orb_range' in trades_df.columns:
            # ORB range analysis
            trades_df['orb_range_quartile'] = pd.qcut(trades_df['orb_range'], 4, labels=['Small', 'Medium', 'Large', 'Very Large'])
            orb_stats = trades_df.groupby('orb_range_quartile', observed=False)['pnl'].agg(['count', 'mean', 'sum'])
            
            optimization_data += f"""
ORB RANGE ANALYSIS:
- Small ranges: {orb_stats.loc['Small', 'count']} trades, ${orb_stats.loc['Small', 'mean']:.2f} avg
- Medium ranges: {orb_stats.loc['Medium', 'count']} trades, ${orb_stats.loc['Medium', 'mean']:.2f} avg
- Large ranges: {orb_stats.loc['Large', 'count']} trades, ${orb_stats.loc['Large', 'mean']:.2f} avg
- Very Large ranges: {orb_stats.loc['Very Large', 'count']} trades, ${orb_stats.loc['Very Large', 'mean']:.2f} avg
"""
        
        if 'duration_minutes' in trades_df.columns:
            # Duration analysis
            trades_df['duration_quartile'] = pd.qcut(trades_df['duration_minutes'], 4, labels=['Quick', 'Short', 'Medium', 'Long'])
            duration_stats = trades_df.groupby('duration_quartile', observed=False)['pnl'].agg(['count', 'mean'])
            
            optimization_data += f"""
TRADE DURATION ANALYSIS:
- Quick exits: {duration_stats.loc['Quick', 'count']} trades, ${duration_stats.loc['Quick', 'mean']:.2f} avg
- Short duration: {duration_stats.loc['Short', 'count']} trades, ${duration_stats.loc['Short', 'mean']:.2f} avg
- Medium duration: {duration_stats.loc['Medium', 'count']} trades, ${duration_stats.loc['Medium', 'mean']:.2f} avg
- Long duration: {duration_stats.loc['Long', 'count']} trades, ${duration_stats.loc['Long', 'mean']:.2f} avg
"""
        
        prompt = f"""
PARAMETER OPTIMIZATION ANALYSIS

{optimization_data}

Based on this data analysis, provide specific recommendations for:

1. **OPTIMAL PARAMETER RANGES**: What parameter values show the best performance?

2. **FILTER CRITERIA**: What conditions should be filtered out to improve performance?

3. **ENTRY IMPROVEMENTS**: How can entry criteria be refined?

4. **EXIT IMPROVEMENTS**: How can exit strategies be optimized?

5. **RISK MANAGEMENT**: Parameter adjustments to reduce risk while maintaining returns.

Be specific with numbers and ranges where possible.
"""
        
        insights = self._call_llm(prompt, max_tokens=800)
        return f"## ⚙️ Parameter Optimization Suggestions\n\n{insights}" 