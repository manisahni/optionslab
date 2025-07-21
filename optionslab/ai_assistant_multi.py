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

# Import agentic analysis if available
try:
    from .agentic_analysis import OllamaAgentProvider, create_analysis_report
except ImportError:
    OllamaAgentProvider = None
    create_analysis_report = None


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
            # Build context with data summaries (LM Studio can't upload files)
            context = self._build_context(trade_data, csv_path, yaml_path)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert options trader and quantitative analyst specializing in backtesting analysis. Focus on providing specific, actionable insights."},
                    {"role": "user", "content": context + "\n\nUser Query: " + message}
                ],
                temperature=0.7,
                max_tokens=4000  # Increased for more detailed responses
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error in LM Studio chat: {str(e)}"
    
    def _build_context(self, trade_data: Optional[Dict], 
                      csv_path: Optional[str], yaml_path: Optional[str]) -> str:
        """Build context from files for LM Studio"""
        context = ""
        
        # Add metadata
        if trade_data and 'metadata' in trade_data:
            metadata = trade_data['metadata']
            context += f"""
Current Backtest: {metadata.get('memorable_name', 'Unknown')}
Strategy: {metadata.get('strategy', 'Unknown')}
Performance: {metadata.get('total_return', 0):.2%}
Total Trades: {metadata.get('total_trades', 0)}
Date Range: {metadata.get('start_date')} to {metadata.get('end_date')}

"""
        
        # Add strategy config
        if yaml_path and Path(yaml_path).exists():
            try:
                with open(yaml_path, 'r') as f:
                    strategy_config = yaml.safe_load(f)
                context += f"\nSTRATEGY CONFIGURATION:\n{yaml.dump(strategy_config, default_flow_style=False)}\n"
            except Exception as e:
                context += f"\nError loading strategy config: {e}\n"
        
        # Add trade summary (first 10 trades)
        if trade_data and 'trades' in trade_data:
            trades = trade_data['trades']
            context += f"\nTRADE SUMMARY ({len(trades)} total trades):\n"
            for i, trade in enumerate(trades[:10]):
                context += f"\nTrade {i+1}:"
                context += f"\n  Entry: {trade.get('entry_date')} at ${trade.get('entry_price', 0):.2f}"
                context += f"\n  Exit: {trade.get('exit_date')} at ${trade.get('exit_price', 0):.2f}"
                context += f"\n  P&L: {trade.get('pnl_percent', 0):.1f}%"
                context += f"\n  Exit reason: {trade.get('exit_reason')}\n"
        
        return context
    
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
    
    def __init__(self, provider: Literal["openai", "lm_studio", "gemini", "ollama_agent"] = "lm_studio"):
        self.provider_name = provider
        self.provider = None
        self.trade_logs_dir = Path(__file__).parent / "trade_logs"
        self._initialized = False
        
        # Load environment variables
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
        # Don't initialize provider in __init__ to avoid deepcopy issues
    
    def set_provider(self, provider: Literal["openai", "lm_studio", "gemini", "ollama_agent"]) -> bool:
        """Switch to a different AI provider"""
        self.provider_name = provider
        
        if provider == "openai":
            self.provider = OpenAIAssistantProvider()
        elif provider == "lm_studio":
            base_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
            self.provider = LMStudioProvider(base_url)
        elif provider == "ollama_agent":
            if OllamaAgentProvider:
                self.provider = OllamaAgentProvider()
            else:
                print("Ollama agent not available. Please install langchain and ollama.")
                return False
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
            return "LM Studio (Local)"
        elif self.provider_name == "ollama_agent":
            return "Ollama Agent (Mixtral with LangChain)"
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
        if self.provider_name == "ollama_agent" and create_analysis_report:
            # Use the specialized report generator
            csv_path = None
            yaml_path = None
            
            if backtest_data:
                metadata = backtest_data.get('metadata', {})
                json_path = metadata.get('json_path', '')
                if json_path:
                    csv_path = json_path.replace('.json', '.csv')
                
                # Load data
                if csv_path and Path(csv_path).exists():
                    import yaml
                    trades_df = pd.read_csv(csv_path)
                    
                    # Find strategy config
                    strategy_name = metadata.get('strategy', '')
                    strategy_config = {}
                    if strategy_name:
                        yaml_paths = [
                            Path(__file__).parent.parent / f"{strategy_name}.yaml",
                            Path(__file__).parent.parent / "config" / "strategies" / f"{strategy_name}.yaml",
                        ]
                        for path in yaml_paths:
                            if path.exists():
                                with open(path, 'r') as f:
                                    strategy_config = yaml.safe_load(f)
                                break
                    
                    initial_capital = metadata.get('initial_capital', 10000)
                    return create_analysis_report(trades_df, strategy_config, initial_capital)
        
        # Fallback to regular chat
        return self.chat(
            "Please generate a comprehensive analysis report including risk metrics, "
            "strategy adherence, market regime analysis, and optimization suggestions.",
            backtest_data
        )