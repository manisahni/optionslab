#!/usr/bin/env python3
"""
AI Assistant module for OptionsLab
Provides intelligent analysis of trades and strategies using Google Gemini
"""

import os
import json
import google.generativeai as genai
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv


class AIAssistant:
    """AI Assistant for options trading analysis"""
    
    def __init__(self):
        """Initialize AI Assistant"""
        self.api_key = None
        self.model = None
        self.chat_session = None
        self.context_loaded = False
        self.trade_logs_dir = Path(__file__).parent / "trade_logs"
        self.debug_logs_dir = Path(__file__).parent.parent / "debug_logs"
        
        # Load API key from .env file
        self._load_api_key_from_env()
    
    def _load_api_key_from_env(self):
        """Load API key from .env file"""
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            self.api_key = os.getenv("GEMINI_API_KEY")
            if self.api_key:
                self._initialize_model()
    
    def set_api_key(self, api_key: str) -> bool:
        """Set or update the API key"""
        if not api_key:
            return False
        
        self.api_key = api_key
        return self._initialize_model()
    
    def _initialize_model(self) -> bool:
        """Initialize the Gemini model"""
        try:
            genai.configure(api_key=self.api_key)
            # Try newer model first, fallback to older
            try:
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            except:
                try:
                    self.model = genai.GenerativeModel('gemini-1.5-pro')
                except:
                    self.model = genai.GenerativeModel('gemini-pro')
            
            self.chat_session = self.model.start_chat(history=[])
            return True
        except Exception as e:
            print(f"Failed to initialize model: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if AI is properly configured"""
        return self.api_key is not None and self.model is not None
    
    def load_context(self, context_type: str = "all") -> str:
        """Load context data for the AI"""
        context_parts = []
        
        if context_type in ["all", "trades"]:
            # Load recent trade logs
            trade_context = self._load_trade_logs()
            if trade_context:
                context_parts.append(f"=== RECENT TRADE LOGS ===\n{trade_context}")
        
        if context_type in ["all", "strategies"]:
            # Load strategy configurations
            strategy_context = self._load_strategies()
            if strategy_context:
                context_parts.append(f"=== STRATEGY CONFIGURATIONS ===\n{strategy_context}")
        
        if context_type in ["all", "code"]:
            # Load relevant source code
            code_context = self._load_source_code()
            if code_context:
                context_parts.append(f"=== SOURCE CODE CONTEXT ===\n{code_context}")
        
        full_context = "\n\n".join(context_parts)
        
        if full_context and self.chat_session:
            # Send context to AI
            try:
                self.chat_session.send_message(
                    f"I'm going to provide you with context about an options trading system. "
                    f"Please analyze this data and be ready to answer questions about trades, "
                    f"strategies, and performance:\n\n{full_context}"
                )
                self.context_loaded = True
                return "Context loaded successfully!"
            except Exception as e:
                return f"Error loading context: {str(e)}"
        
        return "No context available or AI not configured"
    
    def _load_trade_logs(self, limit: int = 5) -> str:
        """Load recent trade logs"""
        if not self.trade_logs_dir.exists():
            return ""
        
        # Load index
        index_path = self.trade_logs_dir / "index.json"
        if not index_path.exists():
            return ""
        
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        logs = index.get('logs', [])
        # Sort by date and get most recent
        logs = sorted(logs, key=lambda x: x.get('backtest_date', ''), reverse=True)[:limit]
        
        summaries = []
        for log in logs:
            summary = f"""
Strategy: {log.get('strategy')}
Date Range: {log.get('start_date')} to {log.get('end_date')}
Total Trades: {log.get('total_trades')}
Final Return: {log.get('total_return', 0):.2%}
Win Rate: {log.get('win_rate', 0):.1%}
"""
            summaries.append(summary)
        
        return "\n---\n".join(summaries)
    
    def _load_strategies(self) -> str:
        """Load strategy configurations"""
        strategies_dir = Path(__file__).parent.parent / "config" / "strategies"
        if not strategies_dir.exists():
            return ""
        
        summaries = []
        for yaml_file in strategies_dir.glob("*.yaml"):
            try:
                import yaml
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                
                summary = f"""
Strategy: {config.get('name', yaml_file.stem)}
Type: {config.get('type')}
Description: {config.get('description', 'N/A')}
Parameters: {json.dumps(config.get('parameters', {}), indent=2)}
"""
                summaries.append(summary)
            except:
                continue
        
        return "\n---\n".join(summaries)
    
    def _load_source_code(self) -> str:
        """Load key source code snippets"""
        # Load key function signatures and docstrings
        key_files = [
            "auditable_backtest.py",
            "auditable_gradio_app.py"
        ]
        
        code_summaries = []
        for filename in key_files:
            file_path = Path(__file__).parent / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                # Extract function definitions and docstrings
                functions = []
                for i, line in enumerate(lines):
                    if line.strip().startswith('def '):
                        func_name = line.strip()
                        # Get docstring if exists
                        if i + 1 < len(lines) and '"""' in lines[i + 1]:
                            docstring = lines[i + 1].strip()
                            functions.append(f"{func_name}\n    {docstring}")
                
                if functions:
                    code_summaries.append(f"File: {filename}\nFunctions:\n" + "\n".join(functions[:10]))
        
        return "\n---\n".join(code_summaries)
    
    def analyze_trades(self, trades: List[Dict]) -> str:
        """Analyze a list of trades and provide insights"""
        if not self.is_configured():
            return "AI not configured. Please set API key."
        
        if not trades:
            return "No trades to analyze."
        
        # Prepare trade summary
        df = pd.DataFrame(trades)
        completed = df[df['exit_date'].notna()]
        
        if completed.empty:
            return "No completed trades to analyze."
        
        summary = f"""
Trade Analysis Request:
- Total Trades: {len(completed)}
- Win Rate: {(completed['pnl'] > 0).mean():.1%}
- Average P&L: ${completed['pnl'].mean():.2f}
- Best Trade: ${completed['pnl'].max():.2f}
- Worst Trade: ${completed['pnl'].min():.2f}
- Most Common Exit: {completed['exit_reason'].mode().values[0] if not completed['exit_reason'].mode().empty else 'N/A'}

Sample trades:
{completed[['trade_id', 'option_type', 'strike', 'entry_date', 'exit_date', 'pnl', 'pnl_pct', 'exit_reason']].head(5).to_string()}

Please provide:
1. Key patterns in winning vs losing trades
2. Suggestions for strategy improvement
3. Risk management recommendations
"""
        
        try:
            response = self.chat_session.send_message(summary)
            return response.text
        except Exception as e:
            return f"Error analyzing trades: {str(e)}"
    
    def chat(self, message: str, current_data: Optional[Dict] = None) -> str:
        """Chat with the AI assistant"""
        if not self.is_configured():
            return "AI not configured. Please set API key."
        
        # Add current data context if provided
        full_message = message
        if current_data:
            context = f"\nCurrent backtest data:\n"
            if 'final_value' in current_data:
                context += f"- Final Value: ${current_data['final_value']:,.2f}\n"
            if 'total_return' in current_data:
                context += f"- Total Return: {current_data['total_return']:.2%}\n"
            if 'trades' in current_data:
                context += f"- Total Trades: {len(current_data['trades'])}\n"
            
            full_message = f"{context}\n{message}"
        
        try:
            response = self.chat_session.send_message(full_message)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_suggestions(self, strategy_type: str, market_conditions: str) -> str:
        """Get strategy suggestions based on market conditions"""
        if not self.is_configured():
            return "AI not configured. Please set API key."
        
        prompt = f"""
Given the following:
- Strategy Type: {strategy_type}
- Market Conditions: {market_conditions}
- System: Options trading backtesting system

Please provide:
1. Optimal parameter suggestions for this strategy
2. Risk management rules to implement
3. Market conditions where this strategy works best
4. Common pitfalls to avoid
"""
        
        try:
            response = self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            return f"Error getting suggestions: {str(e)}"