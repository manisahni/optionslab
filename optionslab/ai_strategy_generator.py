#!/usr/bin/env python3
"""
AI Strategy Generator for OptionsLab
Generates trading strategy YAML files using OpenAI
"""

import yaml
import json
from pathlib import Path
from datetime import datetime
import uuid
from typing import Dict, Optional, Tuple, List
import re
from .ai_openai import get_openai_assistant

class AIStrategyGenerator:
    """Generate trading strategies using AI"""
    
    def __init__(self):
        self.ai_assistant = get_openai_assistant()
        self.strategies_dir = Path(__file__).parent / "ai_strategies"
        self.strategies_dir.mkdir(exist_ok=True)
        
    def generate_strategy(self, 
                         strategy_type: str,
                         risk_level: str,
                         target_dte_range: Tuple[int, int],
                         target_delta_range: Tuple[float, float],
                         max_positions: int,
                         position_size: float,
                         special_instructions: str = "") -> Tuple[str, Dict]:
        """Generate a complete strategy YAML file"""
        
        prompt = f"""
Generate a complete options trading strategy YAML configuration with the following requirements:

Strategy Type: {strategy_type}
Risk Level: {risk_level}
Target DTE Range: {target_dte_range[0]} to {target_dte_range[1]} days
Target Delta Range: {target_delta_range[0]} to {target_delta_range[1]}
Max Positions: {max_positions}
Position Size: {position_size * 100}% of capital per trade
Special Instructions: {special_instructions}

Create a YAML configuration that includes:
1. A descriptive name and description
2. Entry rules with the specified parameters
3. Exit rules appropriate for the risk level
4. Market filters for risk management
5. Risk management parameters

The YAML should follow this exact structure:

```yaml
name: "Strategy Name"
description: "Detailed description"
type: {strategy_type}
version: "1.0"

parameters:
  initial_capital: 10000
  position_size: {position_size}
  max_positions: {max_positions}
  entry_frequency: 3  # days between entries

entry_rules:
  min_dte: {target_dte_range[0]}
  max_dte: {target_dte_range[1]}
  min_delta: {target_delta_range[0]}
  max_delta: {target_delta_range[1]}
  min_volume: 100
  min_open_interest: 500
  min_bid_ask_spread: 0.1
  max_bid_ask_spread: 0.5

exit_rules:
  profit_target: 0.5
  stop_loss: -0.5
  dte_threshold: 7
  delta_threshold: 0.8
  trailing_stop:
    enabled: true
    activation_profit: 0.25
    trail_percent: 0.15

market_filters:
  min_underlying_price: 100
  max_underlying_price: 1000
  min_iv_rank: 0.2
  max_iv_rank: 0.8
  avoid_earnings_days: 5
  required_market_hours: true

risk_management:
  max_daily_loss: -0.02
  max_weekly_loss: -0.05
  max_position_risk: 0.02
```

Make the strategy realistic and practical. Adjust all parameters based on the strategy type and risk level.
"""
        
        try:
            response = self.ai_assistant.chat(prompt, {})
            
            # Extract YAML from response
            yaml_start = response.find("```yaml")
            yaml_end = response.find("```", yaml_start + 7)
            
            if yaml_start != -1 and yaml_end != -1:
                yaml_content = response[yaml_start + 7:yaml_end].strip()
            else:
                # If no code block, assume entire response is YAML
                yaml_content = response.strip()
            
            # Parse and validate YAML
            strategy_config = yaml.safe_load(yaml_content)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"ai_strategy_{timestamp}_{unique_id}.yaml"
            filepath = self.strategies_dir / filename
            
            # Save YAML file
            with open(filepath, 'w') as f:
                yaml.dump(strategy_config, f, default_flow_style=False, sort_keys=False)
            
            # Return YAML content (not filepath) and config
            return yaml_content, strategy_config
            
        except Exception as e:
            raise Exception(f"Failed to generate strategy: {str(e)}")
    
    def analyze_backtest_for_improvements(self, backtest_data: Dict) -> Dict:
        """Analyze backtest results and suggest strategy improvements"""
        
        metadata = backtest_data.get('metadata', {})
        trades = backtest_data.get('trades', [])
        
        prompt = f"""
Analyze this backtest and suggest specific parameter improvements:

Backtest Results:
- Total Return: {metadata.get('total_return', 0):.2%}
- Win Rate: {metadata.get('win_rate', 0):.1%}
- Total Trades: {len(trades)}
- Sharpe Ratio: {metadata.get('sharpe_ratio', 0):.2f}

Sample Trades (first 5):
{json.dumps(trades[:5], indent=2, default=str)}

Based on the trade patterns, suggest specific improvements to:
1. Entry parameters (DTE, delta ranges)
2. Exit rules (profit targets, stop losses)
3. Position sizing
4. Market filters

Provide specific numeric recommendations.
"""
        
        try:
            response = self.ai_assistant.chat(prompt, backtest_data)
            
            # Parse recommendations
            recommendations = {
                'analysis': response,
                'suggested_changes': self._extract_numeric_suggestions(response)
            }
            
            return recommendations
            
        except Exception as e:
            return {'error': str(e)}
    
    def _extract_numeric_suggestions(self, text: str) -> Dict:
        """Extract numeric parameter suggestions from AI response"""
        suggestions = {}
        
        # Look for common parameter patterns
        import re
        
        # DTE suggestions
        dte_match = re.search(r'DTE.*?(\d+)\s*to\s*(\d+)', text, re.IGNORECASE)
        if dte_match:
            suggestions['min_dte'] = int(dte_match.group(1))
            suggestions['max_dte'] = int(dte_match.group(2))
        
        # Delta suggestions
        delta_match = re.search(r'delta.*?(0\.\d+)\s*to\s*(0\.\d+)', text, re.IGNORECASE)
        if delta_match:
            suggestions['min_delta'] = float(delta_match.group(1))
            suggestions['max_delta'] = float(delta_match.group(2))
        
        # Profit target
        profit_match = re.search(r'profit target.*?(\d+)%', text, re.IGNORECASE)
        if profit_match:
            suggestions['profit_target'] = float(profit_match.group(1)) / 100
        
        # Stop loss
        stop_match = re.search(r'stop loss.*?(\d+)%', text, re.IGNORECASE)
        if stop_match:
            suggestions['stop_loss'] = -float(stop_match.group(1)) / 100
        
        return suggestions
    
    def process_conversation(self, message: str, chat_history: List[Dict], 
                           context: Dict, current_yaml: str) -> Tuple[str, Dict, str, str]:
        """Process conversational input and generate/update strategy"""
        
        # Build conversation context for AI
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in chat_history[-10:]  # Last 10 messages for context
        ])
        
        # Check if we have enough information to generate a strategy
        if self._should_generate_strategy(message, context):
            # Extract parameters from conversation
            params = self._extract_params_from_conversation(conversation_text, context)
            
            # Generate strategy YAML
            yaml_content, strategy_name = self._generate_conversational_strategy(params, conversation_text)
            
            # Update context
            context['generated'] = True
            context['params'] = params
            
            response = f"""Great! Based on our conversation, I've created your strategy:

**{strategy_name}**

Key features:
- Strategy Type: {params.get('strategy_type', 'custom').replace('_', ' ').title()}
- Risk Level: {params.get('risk_level', 'moderate').title()}
- DTE Range: {params.get('min_dte', 30)}-{params.get('max_dte', 45)} days
- Position Size: {params.get('position_size', 0.05) * 100}% per trade
- Max Positions: {params.get('max_positions', 3)}

The strategy YAML has been generated. You can review it, make any adjustments, and save it when ready.

Would you like me to explain any part of the strategy or make any adjustments?"""
            
            return response, context, yaml_content, strategy_name
        
        elif context.get('generated') and 'adjust' in message.lower():
            # User wants to modify existing strategy
            params = context.get('params', {})
            adjustments = self._extract_adjustments(message)
            params.update(adjustments)
            
            # Regenerate with new params
            yaml_content, strategy_name = self._generate_conversational_strategy(params, conversation_text)
            context['params'] = params
            
            response = f"I've updated your strategy based on your feedback. The changes have been applied to the YAML."
            
            return response, context, yaml_content, strategy_name
        
        else:
            # Continue gathering information
            response, updated_context = self._get_next_question(message, context)
            return response, updated_context, current_yaml, ""
    
    def _should_generate_strategy(self, message: str, context: Dict) -> bool:
        """Determine if we have enough info to generate a strategy"""
        # Keywords that indicate readiness
        ready_keywords = ['generate', 'create', 'build', 'make', 'yes', 'sounds good', 'perfect', "let's do it"]
        
        # Check if user is confirming
        if any(keyword in message.lower() for keyword in ready_keywords):
            # Check if we have minimum required info
            if context.get('stage') in ['confirmed', 'ready']:
                return True
        
        # Check if we've gathered enough through conversation
        required_info = ['strategy_type', 'risk_level']
        if all(key in context for key in required_info):
            return True
        
        return False
    
    def _extract_params_from_conversation(self, conversation: str, context: Dict) -> Dict:
        """Extract strategy parameters from conversation"""
        params = {
            'strategy_type': 'short_put',
            'risk_level': 'moderate',
            'min_dte': 30,
            'max_dte': 45,
            'min_delta': -0.30,
            'max_delta': -0.10,
            'max_positions': 3,
            'position_size': 0.05,
            'special_instructions': ''
        }
        
        # Update with context info
        if 'template' in context:
            template_params = self._get_template_defaults(context['template'])
            params.update(template_params)
        
        # Extract strategy type
        strategy_patterns = {
            'put selling|sell puts|cash secured puts': 'short_put',
            'call buying|buy calls|long calls': 'long_call',
            'put buying|buy puts|long puts': 'long_put',
            'iron condor|condor': 'iron_condor',
            'call spread|bull call': 'call_spread',
            'put spread|bull put': 'put_spread'
        }
        
        for pattern, strategy_type in strategy_patterns.items():
            if re.search(pattern, conversation, re.IGNORECASE):
                params['strategy_type'] = strategy_type
                break
        
        # Extract risk level
        if re.search(r'conservative|safe|low risk', conversation, re.IGNORECASE):
            params['risk_level'] = 'conservative'
        elif re.search(r'aggressive|high risk|growth', conversation, re.IGNORECASE):
            params['risk_level'] = 'aggressive'
        
        # Extract DTE preferences
        dte_match = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)\s*(?:days|dte)', conversation, re.IGNORECASE)
        if dte_match:
            params['min_dte'] = int(dte_match.group(1))
            params['max_dte'] = int(dte_match.group(2))
        elif 'weekly' in conversation.lower():
            params['min_dte'] = 7
            params['max_dte'] = 14
        elif 'monthly' in conversation.lower():
            params['min_dte'] = 25
            params['max_dte'] = 35
        
        # Extract position info
        pos_match = re.search(r'(\d+)\s*positions?\s*(?:at once|max|maximum)?', conversation, re.IGNORECASE)
        if pos_match:
            params['max_positions'] = int(pos_match.group(1))
        
        # Extract account size for position sizing
        account_match = re.search(r'\$?([\d,]+k?)\s*(?:account|capital|portfolio)', conversation, re.IGNORECASE)
        if account_match:
            size_str = account_match.group(1).replace(',', '')
            if 'k' in size_str.lower():
                account_size = float(size_str.replace('k', '')) * 1000
            else:
                account_size = float(size_str)
            
            # Adjust position size based on account size
            if account_size < 10000:
                params['position_size'] = 0.10  # 10% for small accounts
            elif account_size < 50000:
                params['position_size'] = 0.05  # 5% for medium accounts
            else:
                params['position_size'] = 0.02  # 2% for large accounts
        
        # Update from context
        params.update(context.get('params', {}))
        
        return params
    
    def _generate_conversational_strategy(self, params: Dict, conversation: str) -> Tuple[str, str]:
        """Generate strategy YAML from conversational parameters"""
        
        # Adjust parameters based on risk level
        risk_adjustments = {
            'conservative': {
                'profit_target': 0.25,
                'stop_loss': -1.0,
                'min_iv_rank': 0.3,
                'delta_multiplier': 0.5
            },
            'moderate': {
                'profit_target': 0.5,
                'stop_loss': -1.5,
                'min_iv_rank': 0.2,
                'delta_multiplier': 1.0
            },
            'aggressive': {
                'profit_target': 0.75,
                'stop_loss': -2.0,
                'min_iv_rank': 0.1,
                'delta_multiplier': 1.5
            }
        }
        
        risk_settings = risk_adjustments.get(params['risk_level'], risk_adjustments['moderate'])
        
        # Create strategy name
        strategy_name = f"{params['risk_level'].title()} {params['strategy_type'].replace('_', ' ').title()} Strategy"
        
        # Build strategy config
        strategy_config = {
            'name': strategy_name,
            'description': f"AI-generated {params['risk_level']} {params['strategy_type'].replace('_', ' ')} strategy based on user conversation",
            'type': params['strategy_type'],
            'version': '1.0',
            'created_date': datetime.now().isoformat(),
            
            'parameters': {
                'initial_capital': 10000,
                'position_size': params['position_size'],
                'max_positions': params['max_positions'],
                'entry_frequency': 3
            },
            
            'entry_rules': {
                'min_dte': params['min_dte'],
                'max_dte': params['max_dte'],
                'min_delta': params['min_delta'] * risk_settings['delta_multiplier'],
                'max_delta': params['max_delta'] * risk_settings['delta_multiplier'],
                'min_volume': 100,
                'min_open_interest': 500,
                'min_bid_ask_spread': 0.05,
                'max_bid_ask_spread': 0.30
            },
            
            'exit_rules': {
                'profit_target': risk_settings['profit_target'],
                'stop_loss': risk_settings['stop_loss'],
                'dte_threshold': 7,
                'delta_threshold': 0.7,
                'trailing_stop': {
                    'enabled': params['risk_level'] != 'conservative',
                    'activation_profit': risk_settings['profit_target'] * 0.5,
                    'trail_percent': 0.15
                }
            },
            
            'market_filters': {
                'min_underlying_price': 50,
                'max_underlying_price': 500,
                'min_iv_rank': risk_settings['min_iv_rank'],
                'max_iv_rank': 0.8,
                'avoid_earnings_days': 5,
                'required_market_hours': True
            },
            
            'risk_management': {
                'max_daily_loss': -0.02,
                'max_weekly_loss': -0.05,
                'max_position_risk': params['position_size'] * 2
            }
        }
        
        # Format as YAML
        yaml_content = yaml.dump(strategy_config, default_flow_style=False, sort_keys=False)
        
        return yaml_content, strategy_name
    
    def _get_next_question(self, message: str, context: Dict) -> Tuple[str, Dict]:
        """Determine next question based on conversation state"""
        
        # Initial stage - gathering basic info
        if context.get('stage') == 'initial':
            # Check what info we have from the message
            if 'income' in message.lower() or 'monthly' in message.lower():
                context['goal'] = 'income'
                context['strategy_type'] = 'short_put'
                context['stage'] = 'risk_assessment'
                
                return ("""I understand you're looking for income generation. For monthly income, selling cash-secured puts is often a great choice.

Now, let's talk about risk. Would you describe yourself as:
- **Conservative**: Prioritize capital preservation, willing to accept lower returns
- **Moderate**: Balance between growth and safety
- **Aggressive**: Willing to take more risk for higher potential returns

Also, what's your approximate account size? This helps me recommend appropriate position sizing.""", context)
            
            elif 'growth' in message.lower() or 'capital appreciation' in message.lower():
                context['goal'] = 'growth'
                context['strategy_type'] = 'long_call'
                context['stage'] = 'risk_assessment'
                
                return ("""Got it! You're focused on capital growth. Buying calls can be a great strategy for this.

What's your risk tolerance?
- **Conservative**: Longer-dated options, smaller positions
- **Moderate**: Balanced approach
- **Aggressive**: Shorter-term trades, larger positions

And roughly how much capital are you working with?""", context)
        
        # Risk assessment stage
        elif context.get('stage') == 'risk_assessment':
            # Extract risk level
            if 'conservative' in message.lower():
                context['risk_level'] = 'conservative'
            elif 'aggressive' in message.lower():
                context['risk_level'] = 'aggressive'
            else:
                context['risk_level'] = 'moderate'
            
            context['stage'] = 'position_details'
            
            return (f"""Perfect! A {context['risk_level']} approach it is.

Now for position management:
1. How many positions do you want to manage at once? (typically 1-5)
2. Do you have any preferred stocks or ETFs? (e.g., SPY, QQQ, AAPL)
3. Any specific requirements? (avoid earnings, focus on high IV, etc.)""", context)
        
        # Position details stage
        elif context.get('stage') == 'position_details':
            context['stage'] = 'confirmed'
            
            # Summarize what we'll create
            strategy_type = context.get('strategy_type', 'short_put').replace('_', ' ').title()
            risk_level = context.get('risk_level', 'moderate').title()
            
            return (f"""Excellent! I have everything I need. Let me summarize what I'll create for you:

📋 **Strategy Summary:**
- Type: {strategy_type}
- Risk Level: {risk_level}
- Goal: {context.get('goal', 'income').title()} Generation
- Position Management: Based on your preferences

I'll generate a complete strategy configuration with:
- Entry rules optimized for your risk level
- Exit rules with profit targets and stop losses
- Risk management parameters
- Market filters to avoid problematic trades

Ready to generate your strategy? Just say "yes" or "generate"!""", context)
        
        # Default - ask for more info
        return ("""I need a bit more information. Could you tell me:
1. What's your main trading goal? (income, growth, hedging)
2. What's your risk tolerance? (conservative, moderate, aggressive)
3. Do you have a preferred strategy type in mind?""", context)
    
    def _extract_adjustments(self, message: str) -> Dict:
        """Extract parameter adjustments from user message"""
        adjustments = {}
        
        # Check for DTE changes
        dte_match = re.search(r'(?:change|make|set).*?(\d+)\s*(?:to|-)\s*(\d+)\s*(?:days|dte)', message, re.IGNORECASE)
        if dte_match:
            adjustments['min_dte'] = int(dte_match.group(1))
            adjustments['max_dte'] = int(dte_match.group(2))
        
        # Check for position changes
        pos_match = re.search(r'(?:change|make|set).*?(\d+)\s*positions?', message, re.IGNORECASE)
        if pos_match:
            adjustments['max_positions'] = int(pos_match.group(1))
        
        # Check for risk level changes
        if 'more conservative' in message.lower():
            adjustments['risk_level'] = 'conservative'
        elif 'more aggressive' in message.lower():
            adjustments['risk_level'] = 'aggressive'
        
        return adjustments
    
    def _get_template_defaults(self, template_name: str) -> Dict:
        """Get default parameters for a template"""
        templates = {
            'conservative_put_selling': {
                'strategy_type': 'short_put',
                'risk_level': 'conservative',
                'min_dte': 30,
                'max_dte': 60,
                'min_delta': -0.20,
                'max_delta': -0.10,
                'position_size': 0.05,
                'max_positions': 3
            },
            'aggressive_call_buying': {
                'strategy_type': 'long_call',
                'risk_level': 'aggressive',
                'min_dte': 20,
                'max_dte': 45,
                'min_delta': 0.40,
                'max_delta': 0.60,
                'position_size': 0.02,
                'max_positions': 5
            },
            'iron_condor': {
                'strategy_type': 'iron_condor',
                'risk_level': 'moderate',
                'min_dte': 30,
                'max_dte': 45,
                'min_delta': -0.20,
                'max_delta': -0.10,
                'position_size': 0.10,
                'max_positions': 2
            }
        }
        
        return templates.get(template_name, {})
    
    def create_strategy_from_template(self, template_name: str, modifications: Dict) -> Tuple[str, Dict]:
        """Create a new strategy based on a template with modifications"""
        
        templates = {
            'conservative_put_selling': {
                'name': 'Conservative Put Selling',
                'type': 'short_put',
                'parameters': {
                    'position_size': 0.05,
                    'max_positions': 3
                },
                'entry_rules': {
                    'min_dte': 30,
                    'max_dte': 60,
                    'min_delta': -0.20,
                    'max_delta': -0.10
                },
                'exit_rules': {
                    'profit_target': 0.5,
                    'stop_loss': -2.0,
                    'dte_threshold': 7
                }
            },
            'aggressive_call_buying': {
                'name': 'Aggressive Call Buying',
                'type': 'long_call',
                'parameters': {
                    'position_size': 0.02,
                    'max_positions': 5
                },
                'entry_rules': {
                    'min_dte': 20,
                    'max_dte': 45,
                    'min_delta': 0.40,
                    'max_delta': 0.60
                },
                'exit_rules': {
                    'profit_target': 1.0,
                    'stop_loss': -0.5,
                    'dte_threshold': 5
                }
            },
            'iron_condor': {
                'name': 'Iron Condor',
                'type': 'iron_condor',
                'parameters': {
                    'position_size': 0.10,
                    'max_positions': 2
                },
                'entry_rules': {
                    'min_dte': 30,
                    'max_dte': 45,
                    'min_delta': -0.20,
                    'max_delta': -0.10,
                    'call_delta': 0.20
                },
                'exit_rules': {
                    'profit_target': 0.5,
                    'stop_loss': -2.0,
                    'dte_threshold': 10
                }
            }
        }
        
        if template_name not in templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        # Start with template
        strategy = templates[template_name].copy()
        
        # Apply modifications
        for key, value in modifications.items():
            if '.' in key:
                # Handle nested keys like 'entry_rules.min_dte'
                parts = key.split('.')
                target = strategy
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                target[parts[-1]] = value
            else:
                strategy[key] = value
        
        # Add metadata
        strategy['version'] = '1.0'
        strategy['created_date'] = datetime.now().isoformat()
        strategy['template_base'] = template_name
        
        # Generate filename and save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"ai_strategy_{timestamp}_{unique_id}.yaml"
        filepath = self.strategies_dir / filename
        
        with open(filepath, 'w') as f:
            yaml.dump(strategy, f, default_flow_style=False, sort_keys=False)
        
        return str(filepath), strategy
    
    def get_generated_strategies(self) -> List[Dict]:
        """Get list of all AI-generated strategies"""
        strategies = []
        
        for yaml_file in self.strategies_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)
                    strategies.append({
                        'filename': yaml_file.name,
                        'filepath': str(yaml_file),
                        'name': config.get('name', 'Unknown'),
                        'type': config.get('type', 'Unknown'),
                        'created': yaml_file.stat().st_mtime
                    })
            except:
                continue
        
        # Sort by creation time (newest first)
        strategies.sort(key=lambda x: x['created'], reverse=True)
        return strategies

# Singleton instance
_generator_instance = None

def get_strategy_generator() -> AIStrategyGenerator:
    """Get singleton instance of strategy generator"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = AIStrategyGenerator()
    return _generator_instance