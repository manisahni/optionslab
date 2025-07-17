"""
CLI utilities for enhanced user experience
"""
import sys
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback color class
    class _Color:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    Fore = Back = Style = _Color()


class Colors:
    """Color constants that work with or without colorama"""
    
    @staticmethod
    def red(text: str) -> str:
        return f"{Fore.RED}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text
    
    @staticmethod
    def green(text: str) -> str:
        return f"{Fore.GREEN}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text
    
    @staticmethod
    def yellow(text: str) -> str:
        return f"{Fore.YELLOW}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text
    
    @staticmethod
    def blue(text: str) -> str:
        return f"{Fore.BLUE}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text
    
    @staticmethod
    def magenta(text: str) -> str:
        return f"{Fore.MAGENTA}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text
    
    @staticmethod
    def cyan(text: str) -> str:
        return f"{Fore.CYAN}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text
    
    @staticmethod
    def bold(text: str) -> str:
        return f"{Style.BRIGHT}{text}{Style.RESET_ALL}" if COLORS_AVAILABLE else text


def is_interactive() -> bool:
    """Check if running in an interactive terminal"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def print_banner():
    """Print welcome banner"""
    banner = f"""
{Colors.cyan('='*70)}
{Colors.bold('🚀 SPY OPTIONS BACKTESTER')}
{Colors.cyan('='*70)}

Professional options strategy backtesting with 5 years of SPY data
• Test strategies: Long Calls, Long Puts, Straddles, Covered Calls
• Full portfolio management with Greeks tracking
• Comprehensive risk analysis and reporting

{Colors.yellow('💡 New user? Try:')} {Colors.green('python backtester.py --interactive')}
{Colors.yellow('📚 Need help?')} {Colors.green('python backtester.py --help')}
{Colors.yellow('🎯 Quick start:')} {Colors.green('python backtester.py --examples')}
"""
    print(banner)


def print_strategy_descriptions():
    """Print detailed strategy descriptions"""
    strategies = {
        'long_call': {
            'name': 'Long Call',
            'description': 'Buy call options betting on upward price movement',
            'best_for': 'Bullish outlook, moderate volatility',
            'risk': 'Limited to premium paid',
            'reward': 'Unlimited upside potential',
            'example_params': '--delta-threshold 0.30 --min-dte 15 --max-dte 45'
        },
        'long_put': {
            'name': 'Long Put',
            'description': 'Buy put options betting on downward price movement',
            'best_for': 'Bearish outlook, moderate to high volatility',
            'risk': 'Limited to premium paid',
            'reward': 'High profit potential on downward moves',
            'example_params': '--delta-threshold 0.30 --min-dte 15 --max-dte 45'
        },
        'straddle': {
            'name': 'Long Straddle',
            'description': 'Buy call and put at same strike (volatility play)',
            'best_for': 'High volatility, uncertain direction',
            'risk': 'Limited to total premium paid',
            'reward': 'Profit from large moves in either direction',
            'example_params': '--delta-threshold 0.50 --min-dte 20 --max-dte 60'
        },
        'covered_call': {
            'name': 'Covered Call',
            'description': 'Sell calls against stock position (income strategy)',
            'best_for': 'Neutral to slightly bullish outlook',
            'risk': 'Unlimited downside from stock, capped upside',
            'reward': 'Premium income, modest capital appreciation',
            'example_params': '--delta-threshold 0.25 --min-dte 20 --max-dte 45'
        }
    }
    
    print(f"\n{Colors.bold('📊 AVAILABLE STRATEGIES')}")
    print("=" * 60)
    
    for strategy_key, info in strategies.items():
        print(f"\n{Colors.bold(Colors.blue(info['name'].upper()))} ({strategy_key})")
        print(f"  {Colors.cyan('Description:')} {info['description']}")
        print(f"  {Colors.cyan('Best for:')} {info['best_for']}")
        print(f"  {Colors.cyan('Risk:')} {info['risk']}")
        print(f"  {Colors.cyan('Reward:')} {info['reward']}")
        print(f"  {Colors.cyan('Example:')} python backtester.py --strategy {strategy_key} {info['example_params']}")


def print_examples():
    """Print usage examples"""
    examples = [
        {
            'title': 'Quick Test (1 month)',
            'description': 'Test a strategy quickly with recent data',
            'command': 'python backtester.py --strategy long_call --start-date 20240601 --end-date 20240630'
        },
        {
            'title': 'Bull Market Backtest',
            'description': 'Test long calls during 2021 bull run',
            'command': 'python backtester.py --strategy long_call --start-date 20210101 --end-date 20211231 --delta-threshold 0.30'
        },
        {
            'title': 'COVID Volatility Test',
            'description': 'Test straddles during high volatility period',
            'command': 'python backtester.py --strategy straddle --start-date 20200301 --end-date 20200630 --delta-threshold 0.50'
        },
        {
            'title': 'Conservative Strategy',
            'description': 'Test covered calls with conservative parameters',
            'command': 'python backtester.py --strategy covered_call --start-date 20220101 --end-date 20221231 --stop-loss 0.25'
        },
        {
            'title': 'Save Results',
            'description': 'Run backtest and save detailed results',
            'command': 'python backtester.py --strategy long_put --start-date 20220101 --end-date 20220630 --output results/bear_market_puts'
        }
    ]
    
    print(f"\n{Colors.bold('🎯 USAGE EXAMPLES')}")
    print("=" * 60)
    
    for i, example in enumerate(examples, 1):
        print(f"\n{Colors.bold(f'{i}. {example['title']}')}")
        print(f"   {example['description']}")
        print(f"   {Colors.green(example['command'])}")


def prompt_user(prompt: str, default: Optional[str] = None, 
                validation_func: Optional[callable] = None) -> str:
    """Prompt user with validation"""
    if not is_interactive():
        if default is not None:
            return default
        raise ValueError(f"Non-interactive mode requires default value for: {prompt}")
    
    display_prompt = prompt
    if default:
        display_prompt += f" [{Colors.yellow(default)}]"
    display_prompt += ": "
    
    while True:
        try:
            response = input(display_prompt).strip()
            if not response and default:
                response = default
            
            if validation_func:
                validation_result = validation_func(response)
                if validation_result is True:
                    return response
                else:
                    print(f"{Colors.red('Error:')} {validation_result}")
                    continue
            
            return response
            
        except KeyboardInterrupt:
            print(f"\n{Colors.yellow('Cancelled by user')}")
            sys.exit(0)
        except EOFError:
            print(f"\n{Colors.yellow('End of input')}")
            sys.exit(0)


def prompt_choice(prompt: str, choices: List[str], 
                 descriptions: Optional[List[str]] = None) -> str:
    """Prompt user to choose from a list"""
    if not is_interactive():
        raise ValueError("Choice prompts require interactive mode")
    
    print(f"\n{Colors.bold(prompt)}")
    
    for i, choice in enumerate(choices, 1):
        desc = f" - {descriptions[i-1]}" if descriptions and len(descriptions) >= i else ""
        print(f"  {Colors.cyan(f'{i}.')} {choice}{desc}")
    
    while True:
        try:
            response = input(f"\nEnter choice (1-{len(choices)}): ").strip()
            
            try:
                choice_num = int(response)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                else:
                    print(f"{Colors.red('Error:')} Please enter a number between 1 and {len(choices)}")
            except ValueError:
                # Check if they typed the choice name directly
                response_lower = response.lower()
                for choice in choices:
                    if choice.lower() == response_lower:
                        return choice
                print(f"{Colors.red('Error:')} Please enter a number between 1 and {len(choices)}")
                
        except KeyboardInterrupt:
            print(f"\n{Colors.yellow('Cancelled by user')}")
            sys.exit(0)


def validate_date(date_str: str) -> bool:
    """Validate date format"""
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return "Please use YYYYMMDD format (e.g., 20220101)"


def validate_positive_number(value_str: str) -> bool:
    """Validate positive number"""
    try:
        num = float(value_str)
        if num > 0:
            return True
        else:
            return "Value must be positive"
    except ValueError:
        return "Please enter a valid number"


def validate_percentage(value_str: str) -> bool:
    """Validate percentage (0-1 or 0-100)"""
    try:
        num = float(value_str)
        if 0 <= num <= 1:
            return True
        elif 1 < num <= 100:
            return True  # Will convert 0-100 to 0-1 later
        else:
            return "Percentage must be between 0 and 1 (or 0 and 100)"
    except ValueError:
        return "Please enter a valid percentage"


def format_currency(amount: float) -> str:
    """Format currency with color coding"""
    formatted = f"${amount:,.2f}"
    if amount > 0:
        return Colors.green(formatted)
    elif amount < 0:
        return Colors.red(formatted)
    else:
        return formatted


def format_percentage(pct: float) -> str:
    """Format percentage with color coding"""
    formatted = f"{pct:.2%}"
    if pct > 0:
        return Colors.green(formatted)
    elif pct < 0:
        return Colors.red(formatted)
    else:
        return formatted


def print_progress_bar(current: int, total: int, prefix: str = "", 
                      suffix: str = "", length: int = 50):
    """Print a progress bar"""
    if total == 0:
        return
    
    percent = current / total
    filled_length = int(length * percent)
    bar = '█' * filled_length + '-' * (length - filled_length)
    
    print(f'\r{prefix} |{Colors.cyan(bar)}| {percent:.1%} {suffix}', end='', flush=True)
    
    if current == total:
        print()  # New line when complete


def confirm_action(message: str, default: bool = False) -> bool:
    """Confirm a potentially destructive action"""
    if not is_interactive():
        return default
    
    default_text = "Y/n" if default else "y/N"
    response = input(f"{message} [{default_text}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes', 'true', '1']


def print_error(message: str, suggestion: Optional[str] = None):
    """Print formatted error message"""
    print(f"\n{Colors.red('❌ ERROR:')} {message}")
    if suggestion:
        print(f"{Colors.yellow('💡 Suggestion:')} {suggestion}")


def print_warning(message: str):
    """Print formatted warning message"""
    print(f"{Colors.yellow('⚠️  WARNING:')} {message}")


def print_success(message: str):
    """Print formatted success message"""
    print(f"{Colors.green('✅ SUCCESS:')} {message}")


def print_info(message: str):
    """Print formatted info message"""
    print(f"{Colors.blue('ℹ️  INFO:')} {message}")


def suggest_similar_command(input_cmd: str, valid_commands: List[str]) -> Optional[str]:
    """Suggest similar command for typos"""
    input_lower = input_cmd.lower()
    
    # Simple string similarity check
    for cmd in valid_commands:
        cmd_lower = cmd.lower()
        
        # Exact substring match
        if input_lower in cmd_lower or cmd_lower in input_lower:
            return cmd
        
        # Simple edit distance for short strings
        if len(input_cmd) > 2 and _simple_similarity(input_lower, cmd_lower) > 0.6:
            return cmd
    
    return None


def _simple_similarity(s1: str, s2: str) -> float:
    """Simple string similarity calculation"""
    if not s1 or not s2:
        return 0.0
    
    # Calculate character overlap
    s1_chars = set(s1)
    s2_chars = set(s2)
    overlap = len(s1_chars.intersection(s2_chars))
    total = len(s1_chars.union(s2_chars))
    
    return overlap / total if total > 0 else 0.0