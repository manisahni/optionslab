#!/usr/bin/env python3
"""
AI Implementation Expert - Assesses how well backtests implement their strategy YAML
A financial programmer and options trader that analyzes code implementation adequacy
"""

import json
import os
import sys
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv


class ImplementationExpert:
    """AI Expert that assesses backtest implementation adequacy"""
    
    def __init__(self):
        """Initialize the AI expert"""
        self.api_key = None
        self.model = None
        self.chat_session = None
        self.backtest_data = None
        self.strategy_yaml = None
        self.source_code = {}
        
        # Load API key
        self._load_api_key()
    
    def _load_api_key(self):
        """Load API key from environment"""
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Try different model versions
                try:
                    self.model = genai.GenerativeModel('gemini-1.5-flash')
                except:
                    try:
                        self.model = genai.GenerativeModel('gemini-1.5-pro')
                    except:
                        self.model = genai.GenerativeModel('gemini-pro')
                
                self.chat_session = self.model.start_chat(history=[])
                print("✅ AI Expert initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize AI: {e}")
                print("Please set GEMINI_API_KEY in .env file")
                sys.exit(1)
        else:
            print("❌ No API key found. Please set GEMINI_API_KEY in .env file")
            sys.exit(1)
    
    def load_backtest(self, backtest_path: str):
        """Load a specific backtest and all related data"""
        print(f"\n🔄 Loading backtest: {backtest_path}")
        
        try:
            # Load the backtest JSON
            with open(backtest_path, 'r') as f:
                self.backtest_data = json.load(f)
            
            metadata = self.backtest_data.get('metadata', {})
            trades = self.backtest_data.get('trades', [])
            
            print(f"✅ Loaded {metadata.get('memorable_name', 'Unknown')} backtest")
            print(f"   - {len(trades)} trades")
            print(f"   - {metadata.get('start_date')} to {metadata.get('end_date')}")
            print(f"   - Strategy: {metadata.get('strategy', 'Unknown')}")
            
            # Load the strategy YAML
            self._load_strategy_yaml(metadata.get('strategy_config'))
            
            # Load source code
            self._load_source_code()
            
            # Calculate implementation metrics if not present
            if 'implementation_metrics' not in metadata:
                print("⚠️  No implementation metrics found, calculating...")
                self._calculate_implementation_metrics()
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading backtest: {e}")
            return False
    
    def _load_strategy_yaml(self, strategy_config: dict):
        """Load the strategy YAML configuration"""
        if strategy_config:
            self.strategy_yaml = strategy_config
            print(f"✅ Loaded strategy configuration: {strategy_config.get('name', 'Unknown')}")
        else:
            print("⚠️  No strategy configuration found in backtest")
            # Try to find it based on strategy name
            strategy_name = self.backtest_data.get('metadata', {}).get('strategy', '')
            strategy_file = Path(__file__).parent.parent / "config" / "strategies" / f"{strategy_name}.yaml"
            if strategy_file.exists():
                with open(strategy_file, 'r') as f:
                    self.strategy_yaml = yaml.safe_load(f)
                print(f"✅ Loaded strategy from file: {strategy_file}")
    
    def _load_source_code(self):
        """Load relevant source code for analysis"""
        print("📂 Loading source code for analysis...")
        
        # Load key functions from auditable_backtest.py
        backtest_file = Path(__file__).parent / "auditable_backtest.py"
        if backtest_file.exists():
            with open(backtest_file, 'r') as f:
                content = f.read()
            
            # Extract key functions
            import re
            
            # Find find_suitable_options_advanced function
            pattern = r'def find_suitable_options_advanced\(.*?\):\s*\n(.*?)(?=\ndef|\nclass|\Z)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                self.source_code['find_suitable_options_advanced'] = match.group(0)
            
            # Find exit logic sections
            exit_pattern = r'# Check profit target.*?(?=# Check|$)'
            exit_match = re.search(exit_pattern, content, re.DOTALL)
            if exit_match:
                self.source_code['exit_logic'] = exit_match.group(0)
            
            print("✅ Loaded source code context")
    
    def _calculate_implementation_metrics(self):
        """Calculate implementation metrics from trades"""
        trades = self.backtest_data.get('trades', [])
        completed_trades = [t for t in trades if t.get('exit_date')]
        
        if not completed_trades:
            return
        
        # Get target values from YAML
        entry_rules = self.strategy_yaml.get('entry_rules', {})
        option_selection = self.strategy_yaml.get('option_selection', {})
        
        target_delta = option_selection.get('delta_criteria', {}).get('target', 
                                          entry_rules.get('delta_target', 0.40))
        delta_tolerance = option_selection.get('delta_criteria', {}).get('tolerance', 0.05)
        
        target_dte = option_selection.get('dte_criteria', {}).get('target',
                                        entry_rules.get('dte', 30))
        dte_min = option_selection.get('dte_criteria', {}).get('minimum', 25)
        dte_max = option_selection.get('dte_criteria', {}).get('maximum', 35)
        
        # Analyze deltas
        deltas = [abs(t.get('entry_delta', 0)) for t in completed_trades if t.get('entry_delta')]
        delta_in_range = sum(1 for d in deltas if abs(d - target_delta) <= delta_tolerance)
        
        # Analyze DTEs
        dtes = [t.get('dte_at_entry', 0) for t in completed_trades if t.get('dte_at_entry')]
        dte_in_range = sum(1 for d in dtes if dte_min <= d <= dte_max)
        
        metrics = {
            'target_delta': target_delta,
            'delta_tolerance': delta_tolerance,
            'actual_deltas': deltas,
            'delta_compliance_rate': delta_in_range / len(deltas) if deltas else 0,
            'target_dte': target_dte,
            'dte_range': [dte_min, dte_max],
            'actual_dtes': dtes,
            'dte_compliance_rate': dte_in_range / len(dtes) if dtes else 0,
            'status': 'CALCULATED'
        }
        
        # Store in metadata
        if 'metadata' not in self.backtest_data:
            self.backtest_data['metadata'] = {}
        self.backtest_data['metadata']['implementation_metrics'] = metrics
    
    def generate_adequacy_report(self) -> str:
        """Generate the implementation adequacy assessment"""
        if not self.backtest_data:
            return "No backtest loaded. Please load a backtest first."
        
        metadata = self.backtest_data.get('metadata', {})
        trades = self.backtest_data.get('trades', [])
        implementation_metrics = metadata.get('implementation_metrics', {})
        
        # Prepare comprehensive prompt for AI
        prompt = f"""
You are an expert financial programmer and options trader analyzing a backtest implementation.
Your task is to assess how well the code implements the strategy specified in the YAML file.

BACKTEST INFORMATION:
- Name: {metadata.get('memorable_name', 'Unknown')}
- Strategy: {metadata.get('strategy', 'Unknown')}
- Date Range: {metadata.get('start_date', 'N/A')} to {metadata.get('end_date', 'N/A')}
- Total Trades: {len(trades)}
- Performance: {metadata.get('total_return', 0):.2%}

STRATEGY YAML SPECIFICATION:
```yaml
{yaml.dump(self.strategy_yaml, default_flow_style=False) if self.strategy_yaml else 'Not available'}
```

IMPLEMENTATION METRICS:
{json.dumps(implementation_metrics, indent=2)}

SAMPLE TRADES (First 5):
"""
        # Add sample trades
        for i, trade in enumerate(trades[:5]):
            prompt += f"""
Trade {i+1}:
- Entry Delta: {trade.get('entry_delta', 'N/A')}
- DTE at Entry: {trade.get('dte_at_entry', 'N/A')}
- Strike: ${trade.get('strike', 0)}
- Entry Price: ${trade.get('option_price', 0)}
- Exit Reason: {trade.get('exit_reason', 'N/A')}
- P&L: ${trade.get('pnl', 0):.2f} ({trade.get('pnl_pct', 0):.1f}%)
- Selection Process: {json.dumps(trade.get('selection_process', {}), indent=2)}
"""

        prompt += f"""

SOURCE CODE CONTEXT:
Option Selection Function:
```python
{self.source_code.get('find_suitable_options_advanced', 'Not loaded')[:1000]}...
```

Please provide a comprehensive IMPLEMENTATION ADEQUACY ASSESSMENT following this exact structure:

=== STRATEGY IMPLEMENTATION ADEQUACY REPORT ===
Backtest: {metadata.get('memorable_name', 'Unknown')}
Strategy File: {metadata.get('strategy', 'unknown')}.yaml

📋 YAML SPECIFICATION vs ACTUAL IMPLEMENTATION:

1. DELTA TARGETING ADEQUACY: [EXCELLENT/GOOD/MODERATE/POOR] [✅/⚠️/❌]
   YAML specifies: [target] ± [tolerance] (Range: [min]-[max])
   Code achieved: 
   - Average: [calculated average]
   - Distribution: [min] to [max]
   - In-range: [X]/[total] trades ([percentage]%)
   
   WHY IT [SUCCEEDED/FAILED]:
   - [Specific reason based on code analysis]
   - [Another reason if applicable]

2. DTE TARGETING ADEQUACY: [EXCELLENT/GOOD/MODERATE/POOR] [✅/⚠️/❌]
   YAML specifies: [target] days (Range: [min]-[max])
   Code achieved:
   - Average: [calculated average] days
   - Distribution: [min] to [max] days
   - In-range: [X]/[total] trades ([percentage]%)
   
   WHY IT [SUCCEEDED/MISSED]:
   - [Specific reason based on code analysis]

3. EXIT RULES ADEQUACY: [EXCELLENT/GOOD/MODERATE/POOR] [✅/⚠️/❌]
   YAML specifies: [list exit rules from YAML]
   Code achieved:
   - Profit targets: [accuracy assessment]
   - Stop losses: [accuracy assessment]
   - Time stops: [accuracy assessment]

4. POSITION SIZING ADEQUACY: [EXCELLENT/GOOD/MODERATE/POOR] [✅/⚠️/❌]
   YAML specifies: [position size from YAML]
   Code achieved: [actual range]

=== IMPLEMENTATION SCORE: [X]/100 ===

CRITICAL ISSUES:
[List 1-3 most critical implementation problems]

IMPACT ON RESULTS:
- Your backtest tested a [description] strategy instead of intended [description]
- This likely [increased/decreased] returns by approximately [X]%

RECOMMENDATIONS:
1. [Most important fix with specific code location]
2. [Second priority fix]
3. [Third priority fix]

VERDICT: [VALID/INVALID] - This backtest [IS/IS NOT] testing your intended strategy.

[If INVALID]: Your results do not reflect the strategy specified in the YAML.
[If VALID]: Your implementation correctly follows the strategy specification.
"""
        
        try:
            response = self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            return f"Error generating assessment: {str(e)}"
    
    def start_expert_session(self):
        """Start an interactive expert session"""
        print("\n" + "="*60)
        print("🎯 BACKTEST IMPLEMENTATION EXPERT")
        print("="*60)
        
        # Generate and display initial assessment
        print("\nAnalyzing your backtest implementation...\n")
        assessment = self.generate_adequacy_report()
        print(assessment)
        
        # Interactive loop
        print("\n" + "-"*60)
        print("I can help you understand and fix implementation issues.")
        print("Ask me about specific trades, code problems, or improvements.")
        print("Type 'exit' to end the session.")
        print("-"*60)
        
        while True:
            user_input = input("\n🤖 Expert > ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("\n✅ Expert session ended. Good luck with your trading!")
                break
            
            if not user_input:
                continue
            
            # Process user query with context
            response = self.answer_question(user_input)
            print(f"\n{response}")
    
    def answer_question(self, question: str) -> str:
        """Answer a specific question about the implementation"""
        # Add context to the question
        context = f"""
Based on the backtest we analyzed ({self.backtest_data.get('metadata', {}).get('memorable_name', 'Unknown')}),
answer this question as an expert financial programmer and options trader:

Question: {question}

You have access to:
- The full backtest data with {len(self.backtest_data.get('trades', []))} trades
- The strategy YAML configuration
- The source code implementation
- Implementation metrics showing targeting accuracy

Provide specific, actionable answers. Reference actual trade numbers, code line numbers, or specific values when relevant.
"""
        
        try:
            response = self.chat_session.send_message(context)
            return response.text
        except Exception as e:
            return f"Error processing question: {str(e)}"


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Expert for Backtest Implementation Assessment")
    parser.add_argument('--backtest', type=str, help='Path to backtest JSON file')
    parser.add_argument('--list', action='store_true', help='List available backtests')
    
    args = parser.parse_args()
    
    expert = ImplementationExpert()
    
    if args.list:
        # List available backtests
        trade_logs_dir = Path(__file__).parent / "trade_logs"
        if trade_logs_dir.exists():
            json_files = list(trade_logs_dir.glob("*.json"))
            if json_files:
                print("\nAvailable backtests:")
                for i, f in enumerate(sorted(json_files, reverse=True)[:10]):
                    print(f"{i+1}. {f.stem}")
            else:
                print("No backtests found")
        return
    
    # Load backtest
    if args.backtest:
        backtest_path = args.backtest
    else:
        # Use most recent backtest
        trade_logs_dir = Path(__file__).parent / "trade_logs"
        json_files = sorted(trade_logs_dir.glob("*.json"), reverse=True)
        if json_files:
            backtest_path = str(json_files[0])
            print(f"Using most recent backtest: {json_files[0].stem}")
        else:
            print("No backtests found. Please run a backtest first.")
            return
    
    # Load and analyze
    if expert.load_backtest(backtest_path):
        expert.start_expert_session()


if __name__ == "__main__":
    main()