#!/usr/bin/env python3
"""
Simple Gradio App for OptionsLab
A lightweight alternative to Streamlit
"""
import gradio as gr
import requests
import json
import base64
import io
from PIL import Image
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta

# API configuration
API_URL = "http://localhost:8000"

def check_api_status():
    """Check if the API server is running"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_ai_status():
    """Check AI system status"""
    try:
        response = requests.get(f"{API_URL}/ai/status", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"available": False, "error": "API error"}
    except:
        return {"available": False, "error": "Connection error"}

def get_strategies():
    """Get available strategies from API"""
    try:
        response = requests.get(f"{API_URL}/strategies", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [strategy["name"] for strategy in data["strategies"]]
        return ["Long Call", "Long Put"]  # Fallback
    except:
        return ["Long Call", "Long Put"]  # Fallback

def run_backtest(strategy, start_date, end_date, initial_capital):
    """Run backtest via API"""
    try:
        # Prepare request data
        data = {
            "strategy": strategy,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": float(initial_capital)
        }
        
        # Make API request
        response = requests.post(f"{API_URL}/backtest", json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                formatted_results = format_results(result["results"], result.get("plots", {}))
                return formatted_results, result["results"]  # Return both formatted and raw data
            else:
                return f"❌ Backtest failed: {result.get('error', 'Unknown error')}", None
        else:
            return f"❌ API Error: {response.status_code} - {response.text}", None
            
    except requests.exceptions.RequestException as e:
        return f"❌ Connection Error: {str(e)}", None
    except Exception as e:
        return f"❌ Error: {str(e)}", None

def generate_ai_strategy(market_conditions, risk_tolerance, strategy_type):
    """Generate AI strategy"""
    try:
        data = {
            "market_conditions": market_conditions,
            "risk_tolerance": risk_tolerance,
            "strategy_type": strategy_type
        }
        
        response = requests.post(f"{API_URL}/ai/generate-strategy", json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return format_ai_strategy(result)
        else:
            return f"❌ AI Error: {response.status_code} - {response.text}"
            
    except requests.exceptions.RequestException as e:
        return f"❌ Connection Error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def analyze_backtest_with_ai(results_json):
    """Analyze backtest results with AI"""
    try:
        # Parse results JSON
        results = json.loads(results_json)
        
        data = {"results": results}
        response = requests.post(f"{API_URL}/ai/analyze-backtest", json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return format_ai_analysis(result)
        else:
            return f"❌ AI Error: {response.status_code} - {response.text}"
            
    except json.JSONDecodeError:
        return "❌ Invalid JSON format for results"
    except requests.exceptions.RequestException as e:
        return f"❌ Connection Error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def format_ai_strategy(strategy):
    """Format AI strategy results"""
    if "error" in strategy:
        return f"❌ {strategy['error']}"
    
    formatted = f"""
## 🤖 AI Generated Strategy

### 📋 Strategy Details
- **Name**: {strategy.get('name', 'N/A')}
- **Description**: {strategy.get('description', 'N/A')}

### 🎯 Entry Conditions
"""
    
    entry_conditions = strategy.get('entry_conditions', [])
    if isinstance(entry_conditions, list):
        for condition in entry_conditions:
            formatted += f"- {condition}\n"
    else:
        formatted += f"- {entry_conditions}\n"
    
    formatted += "\n### 🚪 Exit Conditions\n"
    exit_conditions = strategy.get('exit_conditions', [])
    if isinstance(exit_conditions, list):
        for condition in exit_conditions:
            formatted += f"- {condition}\n"
    else:
        formatted += f"- {exit_conditions}\n"
    
    formatted += f"""
### 🛡️ Risk Management
{strategy.get('risk_management', 'N/A')}

### 📈 Expected Outcomes
{strategy.get('expected_outcomes', 'N/A')}
"""
    
    return formatted

def format_ai_analysis(analysis):
    """Format AI analysis results"""
    if "error" in analysis:
        return f"❌ {analysis['error']}"
    
    formatted = f"""
## 🤖 AI Performance Analysis

### 📊 Overall Assessment
**{analysis.get('assessment', 'N/A')}**

### ✅ Strengths
"""
    
    strengths = analysis.get('strengths', [])
    if isinstance(strengths, list):
        for strength in strengths:
            formatted += f"- {strength}\n"
    else:
        formatted += f"- {strengths}\n"
    
    formatted += "\n### ⚠️ Areas for Improvement\n"
    weaknesses = analysis.get('weaknesses', [])
    if isinstance(weaknesses, list):
        for weakness in weaknesses:
            formatted += f"- {weakness}\n"
    else:
        formatted += f"- {weaknesses}\n"
    
    formatted += f"""
### 🎯 Risk Analysis
{analysis.get('risk_analysis', 'N/A')}

### 💡 Recommendations
"""
    
    recommendations = analysis.get('recommendations', [])
    if isinstance(recommendations, list):
        for rec in recommendations:
            formatted += f"- {rec}\n"
    else:
        formatted += f"- {recommendations}\n"
    
    formatted += f"""
### 🌍 Market Suitability
{analysis.get('market_suitability', 'N/A')}
"""
    
    return formatted

def format_results(results, plots):
    """Format backtest results for display"""
    try:
        # Extract key metrics from the nested structure
        performance_metrics = results.get("performance_metrics", {})
        total_return = performance_metrics.get("total_return", 0)
        sharpe_ratio = performance_metrics.get("sharpe_ratio", 0)
        max_drawdown = performance_metrics.get("max_drawdown", 0)
        win_rate = performance_metrics.get("win_rate", 0)
        num_trades = performance_metrics.get("total_trades", 0)
        final_value = performance_metrics.get("final_value", 0)
        
        # Format the results
        formatted = f"""
## 📊 Backtest Results

### 📈 Performance Metrics
- **Final Portfolio Value**: ${final_value:,.2f}
- **Total Return**: {total_return:.2%}
- **Sharpe Ratio**: {sharpe_ratio:.2f}
- **Max Drawdown**: {max_drawdown:.2%}
- **Win Rate**: {win_rate:.2%}
- **Number of Trades**: {num_trades}

### 📋 Trade Summary
"""
        
        # Add trade log if available
        if "trade_logs" in results:
            trades = results["trade_logs"]
            if isinstance(trades, list) and len(trades) > 0:
                # Summary table
                formatted += "| Entry Date | Exit Date | Type | Strike | Quantity | Entry Price | Exit Price | P&L | Exit Reason |\n"
                formatted += "|------------|-----------|------|--------|----------|-------------|------------|-----|-------------|\n"
                
                for i, trade in enumerate(trades):
                    entry_date = trade.get("entry_date", "N/A")
                    exit_date = trade.get("exit_date", "N/A")
                    option_type = trade.get("option_type", "N/A")
                    strike = trade.get("strike", 0)
                    quantity = trade.get("quantity", 0)
                    entry_price = trade.get("entry_price", 0)
                    exit_price = trade.get("exit_price", 0)
                    pnl = trade.get("pnl", 0)
                    exit_reason = trade.get("exit_reason", "N/A")
                    
                    pnl_color = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                    formatted += f"| {entry_date} | {exit_date} | {option_type} | ${strike:.2f} | {quantity} | ${entry_price:.2f} | ${exit_price:.2f} | {pnl_color} ${pnl:.2f} | {exit_reason} |\n"
                
                # Add trade details section (will be handled by separate component)
                formatted += f"\n\n### 🔍 Detailed Trade Information ({len(trades)} trades)\n"
                formatted += "*Click on individual trades below to see detailed information*"
                
            else:
                formatted += "\nNo trades executed during this period."
        
        # Add plots if available
        if plots:
            formatted += "\n\n### 📊 Charts\n"
            for plot_name, plot_data in plots.items():
                if plot_data:
                    formatted += f"\n**{plot_name.replace('_', ' ').title()}**\n"
                    formatted += f"![{plot_name}](data:image/png;base64,{plot_data})\n"
        
        return formatted
        
    except Exception as e:
        return f"❌ Error formatting results: {str(e)}"

def format_trade_details(trade, trade_number):
    """Format detailed information for a single trade"""
    try:
        pnl = trade.get("pnl", 0)
        pnl_color = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        
        # Calculate return
        entry_price = trade.get('entry_price', 0)
        quantity = trade.get('quantity', 0)
        if entry_price and quantity:
            trade_return = (pnl / (entry_price * quantity * 100)) * 100
            return_str = f"{trade_return:.1f}%"
        else:
            return_str = "N/A"
        
        # Format IV display
        exit_iv = trade.get('exit_iv')
        exit_iv_str = f"{exit_iv*100:.1f}%" if exit_iv is not None else "N/A"
        
        formatted = f"""
### Trade {trade_number}: {trade.get('option_type', 'N/A').upper()} {pnl_color} ${pnl:.2f}

**Entry Details:**
- **Date**: {trade.get('entry_date', 'N/A')}
- **Option Type**: {trade.get('option_type', 'N/A').upper()}
- **Strike**: ${trade.get('strike', 0):.2f}
- **Quantity**: {trade.get('quantity', 0)} contracts
- **Entry Price**: ${trade.get('entry_price', 0):.2f}
- **Spot Price**: ${trade.get('entry_spot_price', 0):.2f}

**Entry Greeks & Metrics:**
- **DTE**: {trade.get('entry_dte', 'N/A')} days
- **IV**: {trade.get('entry_iv', 0)*100:.1f}%
- **Delta**: {trade.get('entry_delta', 0):.3f}
- **Gamma**: {trade.get('entry_gamma', 0):.3f}
- **Theta**: {trade.get('entry_theta', 0):.3f}
- **Vega**: {trade.get('entry_vega', 0):.3f}

**Exit Details:**
- **Date**: {trade.get('exit_date', 'N/A')}
- **Exit Price**: ${trade.get('exit_price', 0):.2f}
- **Spot Price**: ${trade.get('exit_spot_price', 0):.2f}
- **Exit Reason**: {trade.get('exit_reason', 'N/A')}

**Exit Greeks & Metrics:**
- **DTE**: {trade.get('exit_dte', 'N/A')} days
- **IV**: {exit_iv_str}
- **Delta**: {trade.get('exit_delta', 0):.3f}
- **Gamma**: {trade.get('exit_gamma', 0):.3f}
- **Theta**: {trade.get('exit_theta', 0):.3f}
- **Vega**: {trade.get('exit_vega', 0):.3f}

**Trade Performance:**
- **P&L**: {pnl_color} ${pnl:.2f}
- **Return**: {return_str}
"""
        return formatted
        
    except Exception as e:
        return f"❌ Error formatting trade details: {str(e)}"

def create_interface():
    """Create the Gradio interface"""
    
    # Check API status
    api_running = check_api_status()
    ai_status = get_ai_status()
    strategies = get_strategies() if api_running else ["Long Call", "Long Put"]
    
    with gr.Blocks(title="OptionsLab - Simple Backtester with AI", theme=gr.themes.Soft()) as app:
        gr.Markdown("# 🚀 OptionsLab - Simple Options Backtester with AI")
        
        # Status indicators
        status_color = "🟢" if api_running else "🔴"
        status_text = "API Connected" if api_running else "API Not Connected"
        gr.Markdown(f"**Status**: {status_color} {status_text}")
        
        ai_color = "🟢" if ai_status.get("available", False) else "🔴"
        ai_text = "AI Available" if ai_status.get("available", False) else "AI Not Available"
        gr.Markdown(f"**AI Status**: {ai_color} {ai_text}")
        
        if not api_running:
            gr.Markdown("⚠️ **Please start the API server first**: `python backend.py`")
        
        # Create tabs
        with gr.Tabs():
            # Backtest Tab
            with gr.TabItem("📊 Backtest"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### ⚙️ Configuration")
                        
                        strategy = gr.Dropdown(
                            choices=strategies,
                            value=strategies[0] if strategies else "Long Call",
                            label="Strategy",
                            info="Select the options strategy to backtest"
                        )
                        
                        start_date = gr.Textbox(
                            value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                            label="Start Date",
                            info="Start date for backtest (YYYY-MM-DD)"
                        )
                        
                        end_date = gr.Textbox(
                            value=datetime.now().strftime("%Y-%m-%d"),
                            label="End Date", 
                            info="End date for backtest (YYYY-MM-DD)"
                        )
                        
                        initial_capital = gr.Number(
                            value=10000.0,
                            label="Initial Capital ($)",
                            info="Starting capital for the backtest"
                        )
                        
                        run_btn = gr.Button("🚀 Run Backtest", variant="primary")
                    
                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Results")
                        results_output = gr.Markdown("Ready to run backtest...")
                        
                        # Trade Details section (collapsible)
                        with gr.Accordion("🔍 Detailed Trade Information", open=False):
                            trade_details_output = gr.Markdown("Run a backtest to see detailed trade information")
                        
                        # AI Analysis section
                        gr.Markdown("### 🤖 AI Analysis")
                        analyze_btn = gr.Button("🧠 Analyze with AI", variant="secondary")
                        ai_analysis_output = gr.Markdown("Run a backtest first, then click 'Analyze with AI'")
                
                # Event handlers
                def run_backtest_with_details(strategy, start_date, end_date, initial_capital):
                    """Run backtest and return both results and trade details"""
                    results_text, raw_results = run_backtest(strategy, start_date, end_date, initial_capital)
                    
                    # Extract trade details if available
                    try:
                        if raw_results and "trade_logs" in raw_results:
                            trades = raw_results["trade_logs"]
                            if isinstance(trades, list) and len(trades) > 0:
                                details_text = "### 🔍 Detailed Trade Information\n\n"
                                for i, trade in enumerate(trades, 1):
                                    details_text += format_trade_details(trade, i) + "\n\n"
                                return results_text, details_text
                    except Exception as e:
                        print(f"Error parsing trade details: {e}")
                    
                    return results_text, "Run a backtest to see detailed trade information"
                
                run_btn.click(
                    fn=run_backtest_with_details,
                    inputs=[strategy, start_date, end_date, initial_capital],
                    outputs=[results_output, trade_details_output]
                )
                
                # AI Analysis handler
                def analyze_results(results_text):
                    if "Backtest Results" not in results_text:
                        return "❌ Please run a backtest first"
                    return analyze_backtest_with_ai(json.dumps({"results": results_text}))
                
                analyze_btn.click(
                    fn=analyze_results,
                    inputs=[results_output],
                    outputs=ai_analysis_output
                )
            
            # AI Strategy Generator Tab
            with gr.TabItem("🤖 AI Strategy Generator"):
                gr.Markdown("### 🎯 Generate AI-Powered Strategies")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        market_conditions = gr.Textbox(
                            label="Market Conditions",
                            placeholder="e.g., Bullish market with low volatility",
                            info="Describe current market conditions"
                        )
                        
                        risk_tolerance = gr.Dropdown(
                            choices=["Conservative", "Moderate", "Aggressive"],
                            value="Moderate",
                            label="Risk Tolerance",
                            info="Select your risk tolerance level"
                        )
                        
                        strategy_type = gr.Dropdown(
                            choices=["Long Call", "Long Put", "Covered Call", "Cash Secured Put", "Iron Condor", "Butterfly Spread"],
                            value="Long Call",
                            label="Strategy Type",
                            info="Type of options strategy to generate"
                        )
                        
                        generate_btn = gr.Button("🧠 Generate Strategy", variant="primary")
                    
                    with gr.Column(scale=2):
                        gr.Markdown("### 🤖 Generated Strategy")
                        strategy_output = gr.Markdown("Click 'Generate Strategy' to create an AI-powered options strategy")
                
                # Event handler
                generate_btn.click(
                    fn=generate_ai_strategy,
                    inputs=[market_conditions, risk_tolerance, strategy_type],
                    outputs=strategy_output
                )
        
        # Auto-refresh strategies when API comes online
        def refresh_strategies():
            api_running = check_api_status()
            if api_running:
                return gr.Dropdown(choices=get_strategies())
            return gr.Dropdown(choices=["Long Call", "Long Put"])
        
        # Refresh button
        refresh_btn = gr.Button("🔄 Refresh", size="sm")
        refresh_btn.click(fn=refresh_strategies, outputs=strategy)
    
    return app

if __name__ == "__main__":
    app = create_interface()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False) 