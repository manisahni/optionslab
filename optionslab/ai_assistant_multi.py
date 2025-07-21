#!/usr/bin/env python3
"""
Multi-provider AI Assistant module for OptionsLab
Supports OpenAI Assistant API, LM Studio, and Google Gemini
"""

import os
import json
import yaml
import time
from typing import Dict, List, Optional, Tuple, Literal
from pathlib import Path
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# Provider-specific imports
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import google.generativeai as genai
    from PIL import Image
except ImportError:
    genai = None
    Image = None

# Standard imports at module level
import pandas as pd
import yaml



class BaseAIProvider(ABC):
    """Base class for AI providers"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the AI provider"""
        pass
    
    @abstractmethod
    def chat(self, message: str, trade_data: Optional[Dict] = None, 
             csv_path: Optional[str] = None, yaml_path: Optional[str] = None) -> str:
        """Send a chat message and get response"""
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured"""
        pass


class OpenAIAssistantProvider(BaseAIProvider):
    """OpenAI Assistant API provider with file handling"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        self.assistant = None
        self.thread = None
        self.uploaded_files = {}
        
    def initialize(self) -> bool:
        """Initialize OpenAI Assistant"""
        if not self.api_key:
            return False
            
        try:
            self.client = OpenAI(api_key=self.api_key)
            
            # Create or retrieve assistant
            self.assistant = self.client.beta.assistants.create(
                name="OptionsLab Trading Analyst",
                instructions="""You are an expert options trader and quantitative analyst specializing in backtesting analysis. 
                You have deep expertise in:
                - Options Greeks (delta, gamma, theta, vega, rho)
                - Trading strategy implementation
                - Risk management and position sizing
                - Performance metrics and statistics
                
                When analyzing trades:
                1. Verify if the implementation matches the strategy specifications
                2. Identify patterns in winning vs losing trades
                3. Analyze exit reasons and their effectiveness
                4. Suggest specific parameter optimizations
                5. Evaluate risk management effectiveness
                
                You have access to trade data files and can run Python code to analyze them.""",
                tools=[{"type": "code_interpreter"}],
                model="gpt-4-turbo-preview"
            )
            
            # Create a thread for the conversation
            self.thread = self.client.beta.threads.create()
            
            return True
        except Exception as e:
            print(f"Failed to initialize OpenAI Assistant: {e}")
            return False
    
    def upload_file(self, file_path: str, purpose: str = "assistants") -> Optional[str]:
        """Upload a file to OpenAI"""
        try:
            with open(file_path, "rb") as f:
                file = self.client.files.create(file=f, purpose=purpose)
                self.uploaded_files[file_path] = file.id
                return file.id
        except Exception as e:
            print(f"Error uploading file {file_path}: {e}")
            return None
    
    def chat(self, message: str, trade_data: Optional[Dict] = None, 
             csv_path: Optional[str] = None, yaml_path: Optional[str] = None) -> str:
        """Chat with OpenAI Assistant"""
        if not self.is_configured():
            return "OpenAI Assistant not configured. Please set OPENAI_API_KEY."
        
        try:
            file_ids = []
            
            # Upload CSV file if provided and not already uploaded
            if csv_path and Path(csv_path).exists():
                if csv_path not in self.uploaded_files:
                    csv_file_id = self.upload_file(csv_path)
                    if csv_file_id:
                        file_ids.append(csv_file_id)
                else:
                    file_ids.append(self.uploaded_files[csv_path])
            
            # Upload YAML file if provided
            if yaml_path and Path(yaml_path).exists():
                if yaml_path not in self.uploaded_files:
                    yaml_file_id = self.upload_file(yaml_path)
                    if yaml_file_id:
                        file_ids.append(yaml_file_id)
                else:
                    file_ids.append(self.uploaded_files[yaml_path])
            
            # Add metadata context to the message
            context = ""
            if trade_data and 'metadata' in trade_data:
                metadata = trade_data['metadata']
                context = f"""
Current Backtest: {metadata.get('memorable_name', 'Unknown')}
Strategy: {metadata.get('strategy', 'Unknown')}
Performance: {metadata.get('total_return', 0):.2%}
Total Trades: {metadata.get('total_trades', 0)}
Date Range: {metadata.get('start_date')} to {metadata.get('end_date')}

"""
            
            # Create message with file attachments
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=context + message,
                file_ids=file_ids if file_ids else None
            )
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id
            )
            
            # Wait for completion
            while run.status in ['queued', 'in_progress']:
                time.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Get the response
                messages = self.client.beta.threads.messages.list(
                    thread_id=self.thread.id,
                    order='desc',
                    limit=1
                )
                
                if messages.data:
                    return messages.data[0].content[0].text.value
                else:
                    return "No response received from assistant."
            else:
                return f"Assistant run failed with status: {run.status}"
                
        except Exception as e:
            return f"Error in OpenAI chat: {str(e)}"
    
    def is_configured(self) -> bool:
        """Check if OpenAI is configured"""
        return bool(self.api_key and self.client and self.assistant)


class LMStudioProvider(BaseAIProvider):
    """LM Studio local provider (OpenAI-compatible)"""
    
    def __init__(self, base_url: str = "http://localhost:1234/v1"):
        self.base_url = base_url
        self.client = None
        self.model = None
        
    def initialize(self) -> bool:
        """Initialize LM Studio client"""
        try:
            if not OpenAI:
                print("OpenAI library not available for LM Studio")
                return False
                
            self.client = OpenAI(
                base_url=self.base_url,
                api_key="not-needed"  # LM Studio doesn't require API key
            )
            
            # Test connection by listing models
            try:
                models = self.client.models.list()
                if models.data:
                    self.model = models.data[0].id
                    print(f"Connected to LM Studio. Using model: {self.model}")
                else:
                    # Fallback to common model IDs if list fails
                    self.model = "magistral-small-2506-mlx"
                    print(f"Connected to LM Studio. Using default model: {self.model}")
                return True
            except:
                # Some LM Studio versions don't support model listing
                self.model = "magistral-small-2506-mlx"
                print(f"Connected to LM Studio (model list unavailable). Using: {self.model}")
                return True
                
        except Exception as e:
            print(f"Failed to connect to LM Studio: {e}")
            return False
    
    def chat(self, message: str, trade_data: Optional[Dict] = None, 
             csv_path: Optional[str] = None, yaml_path: Optional[str] = None) -> str:
        """Chat with LM Studio"""
        if not self.is_configured():
            return "LM Studio not configured. Make sure LM Studio is running."
        
        try:
            # Check if this is a code troubleshooting request
            include_code = any(word in message.lower() for word in ['error', 'bug', 'crash', 'fix', 'debug', 'code', 'implementation'])
            
            # Build context from available data
            context = self._build_context(trade_data, csv_path, yaml_path, include_code_context=include_code)
            
            # Comprehensive system prompt
            system_prompt = """You are an expert options trader, quantitative analyst, and code troubleshooting specialist for OptionsLab.
            
            Your expertise includes:
            1. OPTIONS TRADING: Deep understanding of Greeks, strategies (spreads, straddles, condors), and market mechanics
            2. BACKTESTING ANALYSIS: Evaluating strategy performance, risk metrics (Sharpe, Sortino, max drawdown), and trade patterns
            3. CODE TROUBLESHOOTING: Debugging Python trading systems, understanding ThetaData API, and fixing implementation issues
            4. STRATEGY VALIDATION: Ensuring trades match strategy rules (delta targets, DTE, exit conditions)
            5. PERFORMANCE OPTIMIZATION: Identifying parameter improvements and market regime adaptations
            
            When analyzing:
            - Provide specific numbers and percentages
            - Identify patterns in winning vs losing trades
            - Suggest concrete parameter adjustments
            - Explain any code errors or implementation issues
            - Recommend actionable improvements
            
            You have access to trade logs, strategy configurations, and can help debug code issues."""
            
            # Single LLM call for all requests
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context + "\n\nUser Query: " + message}
                ],
                temperature=0.5,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
                
        except Exception as e:
            return f"Error in LM Studio chat: {str(e)}"
    
    def _build_context(self, trade_data: Optional[Dict], 
                      csv_path: Optional[str], yaml_path: Optional[str], 
                      include_code_context: bool = False) -> str:
        """Build comprehensive context from all available data"""
        context_parts = []
        
        # Add metadata and performance overview
        if trade_data and 'metadata' in trade_data:
            metadata = trade_data['metadata']
            context_parts.append(f"""=== BACKTEST OVERVIEW ===
Name: {metadata.get('memorable_name', 'Unknown')}
Strategy: {metadata.get('strategy', 'Unknown')}
Total Return: {metadata.get('total_return', 0):.2%}
Sharpe Ratio: {metadata.get('sharpe_ratio', 'N/A')}
Max Drawdown: {metadata.get('max_drawdown', 'N/A')}
Total Trades: {metadata.get('total_trades', 0)}
Date Range: {metadata.get('start_date')} to {metadata.get('end_date')}
Initial Capital: ${metadata.get('initial_capital', 10000):,}""")
        
        # Add detailed strategy configuration
        if yaml_path and Path(yaml_path).exists():
            try:
                with open(yaml_path, 'r') as f:
                    strategy_config = yaml.safe_load(f)
                
                # Extract key strategy parameters
                context_parts.append("\n=== STRATEGY CONFIGURATION ===")
                context_parts.append(f"Name: {strategy_config.get('name', 'Unknown')}")
                context_parts.append(f"Type: {strategy_config.get('type', 'Unknown')}")
                
                if 'entry_rules' in strategy_config:
                    entry = strategy_config['entry_rules']
                    context_parts.append(f"\nEntry Rules:")
                    context_parts.append(f"  - Delta Target: {entry.get('delta_target', 'N/A')}")
                    context_parts.append(f"  - DTE Range: {entry.get('dte_min', 'N/A')} to {entry.get('dte_max', 'N/A')} days")
                    context_parts.append(f"  - IV Percentile Min: {entry.get('iv_percentile_min', 'N/A')}")
                
                if 'exit_rules' in strategy_config:
                    exit = strategy_config['exit_rules']
                    context_parts.append(f"\nExit Rules:")
                    context_parts.append(f"  - Profit Target: {exit.get('profit_target', 'N/A')}")
                    context_parts.append(f"  - Stop Loss: {exit.get('stop_loss', 'N/A')}")
                    context_parts.append(f"  - DTE Exit: {exit.get('dte_exit', 'N/A')} days")
                
                if 'position_sizing' in strategy_config:
                    sizing = strategy_config['position_sizing']
                    context_parts.append(f"\nPosition Sizing:")
                    context_parts.append(f"  - Method: {sizing.get('method', 'N/A')}")
                    context_parts.append(f"  - Max Risk: {sizing.get('max_risk_per_trade', 'N/A')}")
                    
            except Exception as e:
                context_parts.append(f"\nError loading strategy config: {e}")
        
        # Add comprehensive trade data if CSV is available
        if csv_path and Path(csv_path).exists():
            try:
                trades_df = pd.read_csv(csv_path)
                if not trades_df.empty:
                    # Calculate detailed statistics
                    winning_trades = trades_df[trades_df['pnl'] > 0]
                    losing_trades = trades_df[trades_df['pnl'] < 0]
                    
                    context_parts.append(f"""\n=== TRADE STATISTICS ===
Total Trades: {len(trades_df)}
Winning Trades: {len(winning_trades)} ({(len(winning_trades) / len(trades_df) * 100):.1f}%)
Losing Trades: {len(losing_trades)} ({(len(losing_trades) / len(trades_df) * 100):.1f}%)
Breakeven Trades: {len(trades_df) - len(winning_trades) - len(losing_trades)}

Profit/Loss:
  - Total P&L: ${trades_df['pnl'].sum():.2f}
  - Average Win: ${winning_trades['pnl'].mean():.2f if len(winning_trades) > 0 else 0:.2f}
  - Average Loss: ${losing_trades['pnl'].mean():.2f if len(losing_trades) > 0 else 0:.2f}
  - Max Win: ${trades_df['pnl'].max():.2f}
  - Max Loss: ${trades_df['pnl'].min():.2f}
  - Profit Factor: {abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()):.2f if len(losing_trades) > 0 and losing_trades['pnl'].sum() != 0 else 'N/A'}""")
                    
                    # Add exit reason analysis
                    if 'exit_reason' in trades_df.columns:
                        exit_counts = trades_df['exit_reason'].value_counts()
                        context_parts.append("\nExit Reasons:")
                        for reason, count in exit_counts.items():
                            context_parts.append(f"  - {reason}: {count} ({count/len(trades_df)*100:.1f}%)")
                    
                    # Add timing analysis
                    if 'days_held' in trades_df.columns:
                        context_parts.append(f"\nTiming Analysis:")
                        context_parts.append(f"  - Average Days Held: {trades_df['days_held'].mean():.1f}")
                        context_parts.append(f"  - Min Days Held: {trades_df['days_held'].min():.0f}")
                        context_parts.append(f"  - Max Days Held: {trades_df['days_held'].max():.0f}")
                    
                    # Add sample trades with more detail
                    context_parts.append("\n=== SAMPLE TRADES (Recent 10) ===")
                    for i, trade in trades_df.tail(10).iterrows():
                        context_parts.append(f"""\nTrade {len(trades_df) - 9 + i}:
  Type: {trade.get('option_type', 'N/A')} | Strike: ${trade.get('strike_price', 0):.2f}
  Entry: {trade.get('entry_date')} at ${trade.get('entry_price', 0):.2f}
  Exit: {trade.get('exit_date')} at ${trade.get('exit_price', 0):.2f}  
  P&L: ${trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):.1f}%)
  Days Held: {trade.get('days_held', 'N/A')}
  Exit Reason: {trade.get('exit_reason', 'N/A')}
  Entry Delta: {trade.get('entry_delta', 'N/A')}
  Entry IV: {trade.get('entry_iv', 'N/A')}""")
                    
            except Exception as e:
                context_parts.append(f"\nError loading trade data: {e}")
        
        # Add code context if requested (for troubleshooting)
        if include_code_context and trade_data:
            strategy_name = trade_data.get('metadata', {}).get('strategy', '')
            if strategy_name:
                context_parts.append(f"\n=== CODE CONTEXT ===\nStrategy Implementation: {strategy_name}")
                
                # Try to read the strategy code
                code_content = self._read_strategy_code(strategy_name)
                if code_content:
                    # Include first 1000 chars of code for context
                    context_parts.append("\nRelevant code snippet:")
                    context_parts.append(f"```python\n{code_content[:1000]}...\n```")
                    context_parts.append("(Full code available for detailed troubleshooting)")
                else:
                    context_parts.append("Strategy code file not found - may need to check implementation")
        
        return "\n".join(context_parts)
    
    
    
    
    def _read_strategy_code(self, strategy_name: str) -> Optional[str]:
        """Read strategy implementation code for troubleshooting"""
        if not strategy_name:
            return None
            
        # Common paths for strategy files
        possible_paths = [
            Path(__file__).parent / f"{strategy_name}.py",
            Path(__file__).parent / "strategies" / f"{strategy_name}.py",
            Path(__file__).parent.parent / f"{strategy_name}.py",
            Path(__file__).parent.parent / "strategies" / f"{strategy_name}.py"
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        return f.read()
                except Exception:
                    pass
        
        return None
    
    def is_configured(self) -> bool:
        """Check if LM Studio is configured"""
        return bool(self.client and self.model)


class GeminiProvider(BaseAIProvider):
    """Google Gemini provider (legacy compatibility)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = None
        self.chat_session = None
        
    def initialize(self) -> bool:
        """Initialize Gemini"""
        if not self.api_key or not genai:
            return False
            
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.chat_session = self.model.start_chat(history=[])
            return True
        except Exception as e:
            print(f"Failed to initialize Gemini: {e}")
            return False
    
    def chat(self, message: str, trade_data: Optional[Dict] = None, 
             csv_path: Optional[str] = None, yaml_path: Optional[str] = None) -> str:
        """Chat with Gemini (limited file support)"""
        if not self.is_configured():
            return "Gemini not configured. Please set GEMINI_API_KEY."
        
        # Use similar context building as LM Studio
        lm_provider = LMStudioProvider()
        context = lm_provider._build_context(trade_data, csv_path, yaml_path)
        
        try:
            response = self.chat_session.send_message(context + "\n\nUser Query: " + message)
            return response.text
        except Exception as e:
            return f"Error in Gemini chat: {str(e)}"
    
    def is_configured(self) -> bool:
        """Check if Gemini is configured"""
        return bool(self.api_key and self.model and self.chat_session)


class MultiProviderAIAssistant:
    """Main AI Assistant supporting multiple providers"""
    
    def __init__(self, provider: Literal["openai", "lm_studio", "gemini"] = "lm_studio"):
        self.provider_name = provider
        self.provider = None
        self.trade_logs_dir = Path(__file__).parent / "trade_logs"
        self._initialized = False
        
        # Load environment variables
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
        # Don't initialize provider in __init__ to avoid deepcopy issues
    
    def set_provider(self, provider: Literal["openai", "lm_studio", "gemini"]) -> bool:
        """Switch to a different AI provider"""
        self.provider_name = provider
        
        if provider == "openai":
            self.provider = OpenAIAssistantProvider()
        elif provider == "lm_studio":
            base_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
            self.provider = LMStudioProvider(base_url)
        else:  # gemini
            self.provider = GeminiProvider()
        
        return self.provider.initialize()
    
    def is_configured(self) -> bool:
        """Check if current provider is configured"""
        if not self._initialized:
            self._initialized = self.set_provider(self.provider_name)
        return self.provider is not None and self.provider.is_configured()
    
    def chat(self, message: str, current_data: Optional[Dict] = None) -> str:
        """Chat with the AI assistant"""
        if not self.is_configured():
            return f"{self.provider_name} not configured properly."
        
        # Extract file paths from current_data
        csv_path = None
        yaml_path = None
        
        if current_data:
            metadata = current_data.get('metadata', {})
            
            # Get CSV path
            json_path = metadata.get('json_path', '')
            if json_path:
                csv_path = json_path.replace('.json', '.csv')
                if not Path(csv_path).exists():
                    csv_path = None
            
            # Get YAML path
            strategy_name = metadata.get('strategy', '')
            if strategy_name:
                yaml_paths = [
                    Path(__file__).parent.parent / f"{strategy_name}.yaml",
                    Path(__file__).parent.parent / "config" / "strategies" / f"{strategy_name}.yaml",
                    Path(__file__).parent.parent / "simple_test_strategy.yaml"
                ]
                for path in yaml_paths:
                    if path.exists():
                        yaml_path = str(path)
                        break
        
        # Call the provider's chat method
        return self.provider.chat(message, current_data, csv_path, yaml_path)
    
    def get_provider_info(self) -> str:
        """Get information about the current provider"""
        if self.provider_name == "openai":
            return "OpenAI Assistant API with Code Interpreter"
        elif self.provider_name == "lm_studio":
            return "LM Studio (Local) - Smart Analysis Mode"
        else:
            return "Google Gemini"
    
    # Legacy compatibility methods
    def set_api_key(self, api_key: str) -> bool:
        """Set API key (for Gemini compatibility)"""
        if self.provider_name == "gemini" and isinstance(self.provider, GeminiProvider):
            self.provider.api_key = api_key
            return self.provider.initialize()
        return False
    
    def analyze_implementation_adequacy(self, backtest_data: Dict) -> str:
        """Analyze if implementation matches strategy (legacy method)"""
        return self.chat(
            "Please analyze if the trade executions match the strategy specifications. "
            "Check delta targeting, DTE selection, exit rules, and position sizing.",
            backtest_data
        )
    
    def generate_analysis_report(self, backtest_data: Dict) -> str:
        """Generate a comprehensive analysis report"""
        return self.chat(
            "Please generate a comprehensive analysis report including risk metrics, "
            "strategy adherence, market regime analysis, and optimization suggestions.",
            backtest_data
        )