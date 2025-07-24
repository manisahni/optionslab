#!/usr/bin/env python3
"""
Data Scientist Engine for OptionsLab
AI-powered analysis engine for SPY options data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from .data_scientist_utils import DataScientistUtils
from .ai_openai import get_openai_assistant

class DataScientistEngine:
    """AI-powered engine for options data analysis"""
    
    def __init__(self):
        self.utils = DataScientistUtils()
        self.ai_assistant = get_openai_assistant()
        self.query_cache = {}
        
    def process_natural_language_query(self, query: str, date_context: Optional[str] = None) -> Dict[str, Any]:
        """Process natural language query and return analysis results
        
        Args:
            query: Natural language query from user
            date_context: Optional date context for the query
            
        Returns:
            Dictionary with analysis results, visualizations, and insights
        """
        # Parse query intent using AI
        intent = self._parse_query_intent(query, date_context)
        
        # Execute appropriate analysis based on intent
        if intent['type'] == 'iv_analysis':
            return self._analyze_implied_volatility(intent['params'])
        elif intent['type'] == 'greeks_analysis':
            return self._analyze_greeks(intent['params'])
        elif intent['type'] == 'flow_analysis':
            return self._analyze_option_flow(intent['params'])
        elif intent['type'] == 'gamma_exposure':
            return self._analyze_gamma_exposure(intent['params'])
        elif intent['type'] == 'historical_comparison':
            return self._analyze_historical_comparison(intent['params'])
        elif intent['type'] == 'market_summary':
            return self._get_market_summary(intent['params'])
        else:
            return self._general_analysis(query, intent['params'])
    
    def _parse_query_intent(self, query: str, date_context: Optional[str] = None) -> Dict:
        """Parse user query to determine intent and parameters"""
        
        # First try simple keyword matching for better reliability
        query_lower = query.lower()
        
        # Default params
        params = {
            'date': date_context or datetime.now().strftime('%Y-%m-%d'),
            'query': query
        }
        
        # Keyword-based intent detection
        if any(word in query_lower for word in ['iv', 'implied volatility', 'volatility', 'smile', 'skew']):
            return {'type': 'iv_analysis', 'params': params}
        elif any(word in query_lower for word in ['gamma', 'exposure', 'pin', 'pinning']):
            return {'type': 'gamma_exposure', 'params': params}
        elif any(word in query_lower for word in ['flow', 'volume', 'unusual', 'activity']):
            return {'type': 'flow_analysis', 'params': params}
        elif any(word in query_lower for word in ['greek', 'delta', 'theta', 'vega', 'rho']):
            # Extract which greek
            for greek in ['delta', 'gamma', 'theta', 'vega', 'rho']:
                if greek in query_lower:
                    params['greek_type'] = greek
                    break
            else:
                params['greek_type'] = 'delta'  # default
            return {'type': 'greeks_analysis', 'params': params}
        elif any(word in query_lower for word in ['summary', 'market', 'overview', 'put/call', 'put call']):
            return {'type': 'market_summary', 'params': params}
        elif any(word in query_lower for word in ['historical', 'compare', 'percentile', 'rank']):
            return {'type': 'historical_comparison', 'params': params}
        
        # Try AI parsing as fallback
        try:
            prompt = f"""
Parse this options data analysis query and return a JSON object with 'type' and 'params' fields.

Query: "{query}"

The type must be one of: iv_analysis, greeks_analysis, flow_analysis, gamma_exposure, historical_comparison, market_summary, general

Example response:
{{"type": "iv_analysis", "params": {{"date": "2024-07-24"}}}}

Return only valid JSON.
"""
            
            response = self.ai_assistant.chat(prompt, {})
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Ensure required fields exist
                if 'type' in result and 'params' in result:
                    # Add date if missing
                    if 'date' not in result['params']:
                        result['params']['date'] = params['date']
                    return result
        except Exception as e:
            print(f"AI parsing error: {e}")
        
        # Default fallback
        return {
            'type': 'general',
            'params': params
        }
    
    def _analyze_implied_volatility(self, params: Dict) -> Dict[str, Any]:
        """Analyze implied volatility surface and patterns"""
        date = params.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get IV surface data
        iv_data = self.utils.get_iv_surface(date)
        
        if iv_data.empty:
            return {
                'success': False,
                'message': f"No data available for {date}",
                'visualizations': [],
                'insights': []
            }
        
        # Create visualizations
        visualizations = []
        
        # 1. IV Surface 3D plot
        fig_surface = self._create_iv_surface_plot(iv_data)
        visualizations.append(('IV Surface', fig_surface))
        
        # 2. IV Smile by expiration
        fig_smile = self._create_iv_smile_plot(iv_data)
        visualizations.append(('IV Smile', fig_smile))
        
        # 3. Term structure
        fig_term = self._create_iv_term_structure(iv_data)
        visualizations.append(('IV Term Structure', fig_term))
        
        # Generate insights
        insights = self._generate_iv_insights(iv_data)
        
        # Create summary statistics
        summary = {
            'avg_iv_call': iv_data[iv_data['right'] == 'C']['implied_vol'].mean(),
            'avg_iv_put': iv_data[iv_data['right'] == 'P']['implied_vol'].mean(),
            'iv_skew': self._calculate_iv_skew(iv_data),
            'total_contracts': len(iv_data),
            'unique_expirations': iv_data['expiration'].nunique()
        }
        
        return {
            'success': True,
            'data': iv_data,
            'visualizations': visualizations,
            'insights': insights,
            'summary': summary
        }
    
    def _analyze_greeks(self, params: Dict) -> Dict[str, Any]:
        """Analyze Greeks distributions"""
        date = params.get('date', datetime.now().strftime('%Y-%m-%d'))
        greek = params.get('greek_type', 'delta')
        
        # Get Greeks data
        greeks_data = self.utils.get_greeks_distribution(date, greek)
        
        if greeks_data.empty:
            return {
                'success': False,
                'message': f"No data available for {date}",
                'visualizations': [],
                'insights': []
            }
        
        visualizations = []
        
        # 1. Greeks distribution by strike
        fig_dist = self._create_greeks_distribution_plot(greeks_data, greek)
        visualizations.append((f'{greek.capitalize()} Distribution', fig_dist))
        
        # 2. Greeks heatmap by strike/expiration
        fig_heatmap = self._create_greeks_heatmap(greeks_data, greek)
        visualizations.append((f'{greek.capitalize()} Heatmap', fig_heatmap))
        
        # Generate insights
        insights = self._generate_greeks_insights(greeks_data, greek)
        
        return {
            'success': True,
            'data': greeks_data,
            'visualizations': visualizations,
            'insights': insights
        }
    
    def _analyze_option_flow(self, params: Dict) -> Dict[str, Any]:
        """Analyze option flow and unusual activity"""
        date = params.get('date', datetime.now().strftime('%Y-%m-%d'))
        min_volume = params.get('min_volume', 1000)
        
        # Get flow data
        flow_data = self.utils.analyze_option_flow(date, min_volume)
        
        if flow_data.empty:
            return {
                'success': False,
                'message': f"No high-volume options found for {date}",
                'visualizations': [],
                'insights': []
            }
        
        visualizations = []
        
        # 1. Top flows bar chart
        fig_flows = self._create_option_flow_chart(flow_data.head(20))
        visualizations.append(('Top Option Flows', fig_flows))
        
        # 2. Volume/OI scatter
        fig_scatter = self._create_volume_oi_scatter(flow_data)
        visualizations.append(('Volume vs Open Interest', fig_scatter))
        
        # Generate insights
        insights = self._generate_flow_insights(flow_data)
        
        # Create summary table of top flows
        top_flows = flow_data.head(10)[['strike', 'expiration', 'right', 'volume', 
                                        'premium', 'volume_oi_ratio', 'implied_vol']]
        
        return {
            'success': True,
            'data': flow_data,
            'visualizations': visualizations,
            'insights': insights,
            'top_flows': top_flows
        }
    
    def _analyze_gamma_exposure(self, params: Dict) -> Dict[str, Any]:
        """Analyze gamma exposure and potential pinning levels"""
        date = params.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get gamma exposure data
        gamma_data = self.utils.calculate_gamma_exposure(date)
        
        if gamma_data.empty:
            return {
                'success': False,
                'message': f"No data available for {date}",
                'visualizations': [],
                'insights': []
            }
        
        visualizations = []
        
        # 1. Gamma exposure by strike
        fig_gamma = self._create_gamma_exposure_plot(gamma_data)
        visualizations.append(('Gamma Exposure by Strike', fig_gamma))
        
        # 2. Cumulative gamma
        fig_cumulative = self._create_cumulative_gamma_plot(gamma_data)
        visualizations.append(('Cumulative Gamma Exposure', fig_cumulative))
        
        # Find potential pin strikes
        pin_strikes = self._identify_pin_strikes(gamma_data)
        
        # Generate insights
        insights = self._generate_gamma_insights(gamma_data, pin_strikes)
        
        return {
            'success': True,
            'data': gamma_data,
            'visualizations': visualizations,
            'insights': insights,
            'pin_strikes': pin_strikes
        }
    
    def _create_iv_surface_plot(self, data: pd.DataFrame) -> go.Figure:
        """Create 3D IV surface plot"""
        # Pivot data for surface plot
        pivot = data.pivot_table(
            values='implied_vol',
            index='strike',
            columns='dte',
            aggfunc='mean'
        )
        
        fig = go.Figure(data=[
            go.Surface(
                x=pivot.columns,
                y=pivot.index,
                z=pivot.values,
                colorscale='Viridis',
                name='IV Surface'
            )
        ])
        
        fig.update_layout(
            title='Implied Volatility Surface',
            scene=dict(
                xaxis_title='Days to Expiration',
                yaxis_title='Strike Price',
                zaxis_title='Implied Volatility'
            ),
            height=600
        )
        
        return fig
    
    def _create_iv_smile_plot(self, data: pd.DataFrame) -> go.Figure:
        """Create IV smile plot by expiration"""
        fig = go.Figure()
        
        # Get top 5 nearest expirations
        nearest_exp = data.groupby('expiration')['dte'].mean().nsmallest(5).index
        
        for exp in nearest_exp:
            exp_data = data[data['expiration'] == exp]
            
            # Separate calls and puts
            calls = exp_data[exp_data['right'] == 'C'].sort_values('strike')
            puts = exp_data[exp_data['right'] == 'P'].sort_values('strike')
            
            dte = exp_data['dte'].iloc[0]
            
            fig.add_trace(go.Scatter(
                x=calls['strike'],
                y=calls['implied_vol'],
                mode='lines+markers',
                name=f'Calls {dte}DTE',
                line=dict(dash='solid')
            ))
            
            fig.add_trace(go.Scatter(
                x=puts['strike'],
                y=puts['implied_vol'],
                mode='lines+markers',
                name=f'Puts {dte}DTE',
                line=dict(dash='dash')
            ))
        
        # Add ATM line
        atm_price = data['underlying_price'].iloc[0]
        fig.add_vline(x=atm_price, line_dash="dash", line_color="red", 
                      annotation_text="ATM")
        
        fig.update_layout(
            title='Implied Volatility Smile',
            xaxis_title='Strike Price',
            yaxis_title='Implied Volatility',
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    def _create_iv_term_structure(self, data: pd.DataFrame) -> go.Figure:
        """Create IV term structure plot"""
        # Calculate ATM IV by expiration
        atm_price = data['underlying_price'].iloc[0]
        
        # Find ATM options (closest to underlying)
        data['distance'] = abs(data['strike'] - atm_price)
        atm_data = data.loc[data.groupby(['expiration', 'right'])['distance'].idxmin()]
        
        # Average calls and puts
        term_structure = atm_data.groupby('expiration').agg({
            'implied_vol': 'mean',
            'dte': 'first'
        }).sort_values('dte')
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=term_structure['dte'],
            y=term_structure['implied_vol'],
            mode='lines+markers',
            name='ATM IV',
            line=dict(width=3)
        ))
        
        fig.update_layout(
            title='Implied Volatility Term Structure',
            xaxis_title='Days to Expiration',
            yaxis_title='ATM Implied Volatility',
            hovermode='x',
            height=400
        )
        
        return fig
    
    def _calculate_iv_skew(self, data: pd.DataFrame) -> float:
        """Calculate 25-delta skew"""
        # Simplified skew calculation
        otm_puts = data[(data['right'] == 'P') & (data['delta'] > -0.3) & (data['delta'] < -0.2)]
        otm_calls = data[(data['right'] == 'C') & (data['delta'] > 0.2) & (data['delta'] < 0.3)]
        
        if not otm_puts.empty and not otm_calls.empty:
            return otm_puts['implied_vol'].mean() - otm_calls['implied_vol'].mean()
        return 0.0
    
    def _generate_iv_insights(self, data: pd.DataFrame) -> List[str]:
        """Generate insights from IV data using AI"""
        # Prepare summary for AI
        summary = {
            'date': data['date'].iloc[0].strftime('%Y-%m-%d'),
            'underlying_price': float(data['underlying_price'].iloc[0]),
            'avg_call_iv': float(data[data['right'] == 'C']['implied_vol'].mean()),
            'avg_put_iv': float(data[data['right'] == 'P']['implied_vol'].mean()),
            'iv_skew': float(self._calculate_iv_skew(data)),
            'highest_iv': float(data['implied_vol'].max()),
            'lowest_iv': float(data['implied_vol'].min())
        }
        
        prompt = f"""
Analyze this SPY options implied volatility data and provide 3-4 key insights:

{json.dumps(summary, indent=2)}

Consider:
1. Overall IV levels (high/low/normal)
2. Put/call skew implications
3. Term structure shape
4. Trading opportunities

Provide actionable insights for options traders.
"""
        
        try:
            response = self.ai_assistant.chat(prompt, {})
            # Split into bullet points
            insights = [line.strip() for line in response.split('\n') if line.strip() and not line.startswith('#')]
            return insights[:4]  # Return top 4 insights
        except:
            return [
                f"Average IV: Calls {summary['avg_call_iv']:.1%}, Puts {summary['avg_put_iv']:.1%}",
                f"IV Skew: {summary['iv_skew']:.1%} (puts vs calls)",
                f"IV Range: {summary['lowest_iv']:.1%} to {summary['highest_iv']:.1%}"
            ]
    
    def _get_market_summary(self, params: Dict) -> Dict[str, Any]:
        """Get comprehensive market summary"""
        date = params.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get summary stats
        summary = self.utils.get_market_summary(date)
        
        # Create visualizations
        visualizations = []
        
        # Market stats dashboard
        fig = self._create_market_dashboard(summary)
        visualizations.append(('Market Dashboard', fig))
        
        # Generate AI insights
        insights = self._generate_market_insights(summary)
        
        return {
            'success': True,
            'summary': summary,
            'visualizations': visualizations,
            'insights': insights
        }
    
    def _create_market_dashboard(self, summary: Dict) -> go.Figure:
        """Create market summary dashboard"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Put/Call Ratios', 'Volume Distribution', 
                          'IV Comparison', 'Market Metrics'),
            specs=[[{'type': 'bar'}, {'type': 'pie'}],
                   [{'type': 'scatter'}, {'type': 'indicator'}]]
        )
        
        # Put/Call ratios
        fig.add_trace(go.Bar(
            x=['Volume', 'Open Interest'],
            y=[summary['put_call_volume_ratio'], summary['put_call_oi_ratio']],
            name='Put/Call Ratio'
        ), row=1, col=1)
        
        # Volume distribution (simplified)
        fig.add_trace(go.Pie(
            labels=['Calls', 'Puts'],
            values=[summary['total_volume'] / (1 + summary['put_call_volume_ratio']),
                   summary['total_volume'] * summary['put_call_volume_ratio'] / (1 + summary['put_call_volume_ratio'])],
            name='Volume'
        ), row=1, col=2)
        
        # IV comparison
        fig.add_trace(go.Scatter(
            x=['Calls', 'Puts'],
            y=[summary['avg_iv_calls'], summary['avg_iv_puts']],
            mode='markers+lines',
            marker=dict(size=15),
            name='Average IV'
        ), row=2, col=1)
        
        # Key metric
        fig.add_trace(go.Indicator(
            mode='number+delta',
            value=summary['underlying_price'],
            title={'text': 'SPY Price'},
            delta={'reference': summary['underlying_price'] * 0.99}
        ), row=2, col=2)
        
        fig.update_layout(height=700, showlegend=False)
        
        return fig
    
    def _generate_market_insights(self, summary: Dict) -> List[str]:
        """Generate market insights using AI"""
        prompt = f"""
Analyze this SPY options market summary and provide key insights:

{json.dumps(summary, indent=2, default=str)}

Focus on:
1. Put/call ratios and sentiment
2. Volume patterns
3. IV levels and skew
4. Potential market direction

Provide 3-4 actionable insights.
"""
        
        try:
            response = self.ai_assistant.chat(prompt, {})
            insights = [line.strip() for line in response.split('\n') if line.strip() and not line.startswith('#')]
            return insights[:4]
        except:
            return [
                f"Put/Call Volume Ratio: {summary['put_call_volume_ratio']:.2f}",
                f"Total Volume: {summary['total_volume']:,} contracts",
                f"Average IV: Calls {summary['avg_iv_calls']:.1%}, Puts {summary['avg_iv_puts']:.1%}"
            ]
    
    def _create_greeks_distribution_plot(self, data: pd.DataFrame, greek: str) -> go.Figure:
        """Create Greeks distribution plot"""
        fig = go.Figure()
        
        # Separate by right
        for right in ['C', 'P']:
            right_data = data[data['right'] == right].sort_values('strike')
            
            fig.add_trace(go.Scatter(
                x=right_data['strike'],
                y=right_data[greek],
                mode='lines+markers',
                name=f'{right} {greek.capitalize()}',
                line=dict(width=2)
            ))
        
        # Add underlying price line
        underlying = data['underlying_price'].iloc[0]
        fig.add_vline(x=underlying, line_dash="dash", line_color="red",
                     annotation_text="Underlying")
        
        fig.update_layout(
            title=f'{greek.capitalize()} Distribution by Strike',
            xaxis_title='Strike Price',
            yaxis_title=greek.capitalize(),
            hovermode='x unified',
            height=500
        )
        
        return fig
    
    def _create_greeks_heatmap(self, data: pd.DataFrame, greek: str) -> go.Figure:
        """Create Greeks heatmap"""
        # Pivot data
        pivot = data.pivot_table(
            values=greek,
            index='strike',
            columns='dte',
            aggfunc='mean'
        )
        
        fig = go.Figure(data=go.Heatmap(
            x=pivot.columns,
            y=pivot.index,
            z=pivot.values,
            colorscale='RdBu',
            zmid=0
        ))
        
        fig.update_layout(
            title=f'{greek.capitalize()} Heatmap',
            xaxis_title='Days to Expiration',
            yaxis_title='Strike Price',
            height=500
        )
        
        return fig
    
    def _create_option_flow_chart(self, data: pd.DataFrame) -> go.Figure:
        """Create option flow bar chart"""
        fig = go.Figure()
        
        # Create labels
        data['label'] = data.apply(
            lambda x: f"{x['strike']:.0f}{x['right']} {x['expiration'].strftime('%m/%d')}",
            axis=1
        )
        
        # Color by call/put
        colors = ['green' if x == 'C' else 'red' for x in data['right']]
        
        fig.add_trace(go.Bar(
            x=data['premium'],
            y=data['label'],
            orientation='h',
            marker_color=colors,
            text=data['volume'],
            textposition='auto'
        ))
        
        fig.update_layout(
            title='Top Option Flows by Premium',
            xaxis_title='Premium ($)',
            yaxis_title='Contract',
            height=600
        )
        
        return fig
    
    def _create_volume_oi_scatter(self, data: pd.DataFrame) -> go.Figure:
        """Create volume vs OI scatter plot"""
        fig = go.Figure()
        
        for right in ['C', 'P']:
            right_data = data[data['right'] == right]
            
            fig.add_trace(go.Scatter(
                x=right_data['open_interest'],
                y=right_data['volume'],
                mode='markers',
                name=f'{right}',
                marker=dict(
                    size=right_data['premium'] / 1000,  # Size by premium
                    sizemode='area',
                    sizeref=2.*max(data['premium']/1000)/(40.**2),
                    sizemin=4
                ),
                text=right_data.apply(
                    lambda x: f"{x['strike']:.0f} {x['expiration'].strftime('%m/%d')}",
                    axis=1
                ),
                hovertemplate='%{text}<br>Volume: %{y:,}<br>OI: %{x:,}<extra></extra>'
            ))
        
        # Add diagonal line for volume = OI
        max_val = max(data['volume'].max(), data['open_interest'].max())
        fig.add_trace(go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode='lines',
            name='Volume = OI',
            line=dict(dash='dash', color='gray')
        ))
        
        fig.update_layout(
            title='Volume vs Open Interest (size = premium)',
            xaxis_title='Open Interest',
            yaxis_title='Volume',
            xaxis_type='log',
            yaxis_type='log',
            height=500
        )
        
        return fig
    
    def _create_gamma_exposure_plot(self, data: pd.DataFrame) -> go.Figure:
        """Create gamma exposure plot"""
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=data['strike'],
            y=data['gamma_exposure'],
            name='Gamma Exposure',
            marker_color=data['gamma_exposure'].apply(
                lambda x: 'red' if x < 0 else 'green'
            )
        ))
        
        # Add zero line
        fig.add_hline(y=0, line_dash="solid", line_color="black")
        
        fig.update_layout(
            title='Gamma Exposure by Strike (Market Maker Perspective)',
            xaxis_title='Strike Price',
            yaxis_title='Gamma Exposure ($)',
            height=500
        )
        
        return fig
    
    def _create_cumulative_gamma_plot(self, data: pd.DataFrame) -> go.Figure:
        """Create cumulative gamma plot"""
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=data['strike'],
            y=data['cumulative_gamma'],
            mode='lines',
            name='Cumulative Gamma',
            line=dict(width=3)
        ))
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        # Find zero gamma strike
        zero_gamma_idx = (data['cumulative_gamma'] > 0).idxmax()
        if zero_gamma_idx:
            zero_gamma_strike = data.loc[zero_gamma_idx, 'strike']
            fig.add_vline(x=zero_gamma_strike, line_dash="dash", line_color="red",
                         annotation_text=f"Zero Gamma: {zero_gamma_strike:.0f}")
        
        fig.update_layout(
            title='Cumulative Gamma Exposure',
            xaxis_title='Strike Price',
            yaxis_title='Cumulative Gamma ($)',
            height=400
        )
        
        return fig
    
    def _identify_pin_strikes(self, gamma_data: pd.DataFrame) -> List[float]:
        """Identify potential pin strikes based on gamma exposure"""
        # Find strikes with highest absolute gamma exposure
        gamma_data['abs_gamma'] = gamma_data['gamma_exposure'].abs()
        top_strikes = gamma_data.nlargest(3, 'abs_gamma')['strike'].tolist()
        
        # Also find zero gamma crossing
        zero_gamma_idx = (gamma_data['cumulative_gamma'] > 0).idxmax()
        if zero_gamma_idx:
            zero_gamma_strike = gamma_data.loc[zero_gamma_idx, 'strike']
            if zero_gamma_strike not in top_strikes:
                top_strikes.append(zero_gamma_strike)
        
        return sorted(top_strikes)
    
    def _generate_greeks_insights(self, data: pd.DataFrame, greek: str) -> List[str]:
        """Generate insights from Greeks data"""
        # Calculate summary stats
        summary = {
            'greek': greek,
            'max_value': float(data[greek].max()),
            'min_value': float(data[greek].min()),
            'total_exposure': float(data[greek].sum()),
            'high_greek_strikes': data.nlargest(3, greek)['strike'].tolist()
        }
        
        insights = [
            f"Highest {greek} exposure at strikes: {', '.join(map(str, summary['high_greek_strikes']))}",
            f"Total {greek} exposure: {summary['total_exposure']:.4f}",
            f"{greek.capitalize()} range: {summary['min_value']:.4f} to {summary['max_value']:.4f}"
        ]
        
        return insights
    
    def _generate_flow_insights(self, data: pd.DataFrame) -> List[str]:
        """Generate insights from option flow data"""
        total_call_volume = data[data['right'] == 'C']['volume'].sum()
        total_put_volume = data[data['right'] == 'P']['volume'].sum()
        
        insights = [
            f"Total high-volume trades: {len(data)} contracts",
            f"Call/Put volume ratio: {total_call_volume/total_put_volume:.2f}",
            f"Largest trade: {data.iloc[0]['strike']:.0f}{data.iloc[0]['right']} with {data.iloc[0]['volume']:,} volume",
            f"Total premium traded: ${data['premium'].sum():,.0f}"
        ]
        
        return insights
    
    def _generate_gamma_insights(self, data: pd.DataFrame, pin_strikes: List[float]) -> List[str]:
        """Generate insights from gamma exposure data"""
        total_gamma = data['gamma_exposure'].sum()
        
        insights = [
            f"Potential pin strikes: {', '.join(map(lambda x: f'{x:.0f}', pin_strikes))}",
            f"Total gamma exposure: ${total_gamma:,.0f}",
            f"Negative gamma below {data[data['gamma_exposure'] < 0]['strike'].max():.0f}",
            f"Maximum gamma concentration at {data.loc[data['gamma_exposure'].abs().idxmax(), 'strike']:.0f}"
        ]
        
        return insights
    
    def _analyze_historical_comparison(self, params: Dict) -> Dict[str, Any]:
        """Analyze historical IV comparisons and percentiles"""
        date = params.get('date', datetime.now().strftime('%Y-%m-%d'))
        lookback_days = params.get('lookback_period', 252)
        
        try:
            # Get IV percentile data
            iv_percentile_data = self.utils.get_historical_iv_percentile(date, lookback_days)
            
            if iv_percentile_data.empty:
                return {
                    'success': False,
                    'message': f"No historical data available for {date}",
                    'visualizations': [],
                    'insights': []
                }
            
            visualizations = []
            
            # Create percentile visualization
            fig = go.Figure()
            
            # Scatter plot of IV percentiles
            for right in ['C', 'P']:
                right_data = iv_percentile_data[iv_percentile_data['right'] == right]
                
                fig.add_trace(go.Scatter(
                    x=right_data['strike'],
                    y=right_data['iv_percentile'],
                    mode='markers',
                    name=f'{right} IV Percentile',
                    marker=dict(
                        size=8,
                        color=right_data['iv_percentile'],
                        colorscale='RdYlBu_r',
                        showscale=True
                    )
                ))
            
            fig.update_layout(
                title=f'IV Percentile Rank ({lookback_days} day lookback)',
                xaxis_title='Strike Price',
                yaxis_title='IV Percentile (%)',
                height=500
            )
            
            visualizations.append(('IV Percentile Rank', fig))
            
            # Generate insights
            high_iv = iv_percentile_data[iv_percentile_data['iv_percentile'] > 80]
            low_iv = iv_percentile_data[iv_percentile_data['iv_percentile'] < 20]
            
            insights = [
                f"Options with IV in top 20th percentile: {len(high_iv)} contracts",
                f"Options with IV in bottom 20th percentile: {len(low_iv)} contracts",
                f"Average IV percentile: {iv_percentile_data['iv_percentile'].mean():.1f}%"
            ]
            
            if not high_iv.empty:
                insights.append(f"Highest IV percentile at strike {high_iv.iloc[0]['strike']:.0f}")
            
            return {
                'success': True,
                'data': iv_percentile_data,
                'visualizations': visualizations,
                'insights': insights
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error in historical analysis: {str(e)}",
                'visualizations': [],
                'insights': []
            }
    
    def _general_analysis(self, query: str, params: Dict) -> Dict[str, Any]:
        """Handle general analysis queries"""
        # Use AI to determine what analysis to perform
        date = params.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        prompt = f"""
Given this query about SPY options data: "{query}"

Suggest what specific analysis to perform and what data to show.
Available data: implied volatility, Greeks, volume, open interest, prices
Date context: {date}

Provide a brief response focusing on actionable analysis.
"""
        
        try:
            response = self.ai_assistant.chat(prompt, {})
            
            # Default to market summary
            return self._get_market_summary(params)
            
        except:
            return {
                'success': False,
                'message': "Unable to process query",
                'visualizations': [],
                'insights': []
            }