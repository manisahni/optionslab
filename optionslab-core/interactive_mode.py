"""
Interactive mode for the SPY Options Backtester
"""
import sys
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from cli_utils import (
    Colors, print_banner, print_strategy_descriptions, 
    prompt_user, prompt_choice, validate_date, validate_positive_number,
    validate_percentage, confirm_action, print_error, print_info,
    print_success, is_interactive
)
from data_loader import SPYDataLoader


class InteractiveSession:
    """Handles interactive backtester configuration"""
    
    def __init__(self):
        self.data_loader = SPYDataLoader()
        self.available_dates = None
        self.config = {}
        
    def run(self) -> Dict[str, Any]:
        """Run interactive session and return configuration"""
        if not is_interactive():
            print_error("Interactive mode requires a terminal")
            sys.exit(1)
        
        print_banner()
        print(f"{Colors.bold('🎮 INTERACTIVE MODE')}")
        print("Let's configure your options backtest step by step...\n")
        
        # Load available data
        print_info("Loading available data...")
        try:
            self.available_dates = self.data_loader.get_available_dates()
            print_success(f"Found {len(self.available_dates)} trading days of data")
            print(f"   Data range: {self.available_dates[0]} to {self.available_dates[-1]}")
        except Exception as e:
            print_error(f"Could not load data: {e}")
            sys.exit(1)
        
        # Step-by-step configuration
        self._choose_strategy()
        self._choose_date_range()
        self._configure_parameters()
        self._configure_risk_management()
        self._configure_output()
        
        # Review and confirm
        self._review_configuration()
        
        return self.config
    
    def _choose_strategy(self):
        """Strategy selection with descriptions"""
        print(f"\n{Colors.bold('📊 STEP 1: Choose Strategy')}")
        
        strategies = ['long_call', 'long_put', 'straddle', 'covered_call']
        descriptions = [
            'Buy calls (bullish)',
            'Buy puts (bearish)', 
            'Buy calls + puts (volatility play)',
            'Sell calls against stock (income)'
        ]
        
        print("\nStrategy details:")
        strategy_info = {
            'long_call': "Best for: Bull markets, moderate volatility\nRisk: Premium paid | Reward: Unlimited upside",
            'long_put': "Best for: Bear markets, high volatility\nRisk: Premium paid | Reward: High downside profit",
            'straddle': "Best for: High volatility, uncertain direction\nRisk: Total premium | Reward: Large moves either way",
            'covered_call': "Best for: Sideways/slightly bullish markets\nRisk: Stock downside | Reward: Premium income"
        }
        
        for i, (strategy, desc) in enumerate(zip(strategies, descriptions), 1):
            print(f"\n{Colors.cyan(f'{i}. {strategy.replace('_', ' ').title()}')}")
            print(f"   {desc}")
            print(f"   {strategy_info[strategy]}")
        
        choice = prompt_choice("Select your strategy:", strategies, descriptions)
        self.config['strategy'] = choice
        print_success(f"Selected strategy: {choice.replace('_', ' ').title()}")
    
    def _choose_date_range(self):
        """Date range selection with data validation"""
        print(f"\n{Colors.bold('📅 STEP 2: Choose Date Range')}")
        
        print(f"\nAvailable data: {Colors.cyan(self.available_dates[0])} to {Colors.cyan(self.available_dates[-1])}")
        
        # Suggest some common ranges
        today = datetime.now()
        suggestions = [
            ("Last 6 months", self._get_recent_date(180), self.available_dates[-1]),
            ("2022 (Bear market)", "20220101", "20221231"),
            ("2021 (Bull market)", "20210101", "20211231"), 
            ("COVID period (High vol)", "20200301", "20200630"),
            ("Custom range", None, None)
        ]
        
        print(f"\n{Colors.cyan('Suggested date ranges:')}")
        for i, (desc, start, end) in enumerate(suggestions, 1):
            if start and end:
                print(f"  {i}. {desc}: {start} to {end}")
            else:
                print(f"  {i}. {desc}")
        
        choice = prompt_choice("Choose date range:", [s[0] for s in suggestions])
        
        # Get the selected suggestion
        selected = next(s for s in suggestions if s[0] == choice)
        
        if selected[1] and selected[2]:  # Pre-defined range
            start_date = selected[1]
            end_date = selected[2]
        else:  # Custom range
            start_date = prompt_user(
                "Start date (YYYYMMDD)", 
                default=self._get_recent_date(365),
                validation_func=lambda d: self._validate_date_in_range(d)
            )
            end_date = prompt_user(
                "End date (YYYYMMDD)",
                default=self.available_dates[-1],
                validation_func=lambda d: self._validate_date_in_range(d, start_date)
            )
        
        self.config['start_date'] = start_date
        self.config['end_date'] = end_date
        
        # Calculate trading days in range
        trading_days = [d for d in self.available_dates if start_date <= d <= end_date]
        print_success(f"Date range: {start_date} to {end_date} ({len(trading_days)} trading days)")
    
    def _configure_parameters(self):
        """Configure strategy-specific parameters"""
        print(f"\n{Colors.bold('⚙️  STEP 3: Configure Parameters')}")
        
        strategy = self.config['strategy']
        
        # Initial capital
        capital = prompt_user(
            "Initial capital",
            default="100000",
            validation_func=validate_positive_number
        )
        self.config['initial_capital'] = float(capital)
        
        # Strategy-specific parameters
        if strategy in ['long_call', 'long_put']:
            delta = prompt_user(
                f"Delta threshold (0.20-0.40 typical for {strategy.split('_')[1]}s)",
                default="0.30",
                validation_func=lambda x: self._validate_delta(x, strategy)
            )
            self.config['delta_threshold'] = float(delta)
            
        elif strategy == 'straddle':
            delta = prompt_user(
                "Delta threshold (0.50 for ATM straddles)",
                default="0.50", 
                validation_func=lambda x: self._validate_delta(x, strategy)
            )
            self.config['delta_threshold'] = float(delta)
            
        elif strategy == 'covered_call':
            delta = prompt_user(
                "Delta threshold for short calls (0.20-0.30 typical)",
                default="0.25",
                validation_func=lambda x: self._validate_delta(x, strategy)
            )
            self.config['delta_threshold'] = float(delta)
        
        # Days to expiration
        min_dte = prompt_user(
            "Minimum days to expiration",
            default="10",
            validation_func=lambda x: self._validate_dte(x, min_val=1, max_val=30)
        )
        max_dte = prompt_user(
            "Maximum days to expiration", 
            default="60",
            validation_func=lambda x: self._validate_dte(x, min_val=int(min_dte), max_val=365)
        )
        
        self.config['min_dte'] = int(min_dte)
        self.config['max_dte'] = int(max_dte)
        
        print_success("Parameters configured")
    
    def _configure_risk_management(self):
        """Configure risk management settings"""
        print(f"\n{Colors.bold('🛡️  STEP 4: Risk Management')}")
        
        # Position sizing
        position_size = prompt_user(
            "Maximum position size (% of capital, e.g., 5 for 5%)",
            default="5",
            validation_func=lambda x: self._validate_position_size(x)
        )
        # Convert percentage to decimal
        self.config['position_size'] = float(position_size) / 100
        
        # Stop loss
        stop_loss = prompt_user(
            "Stop loss (% loss to close position, e.g., 50 for 50%)",
            default="50",
            validation_func=validate_percentage
        )
        self.config['stop_loss'] = float(stop_loss) / 100
        
        # Profit target
        profit_target = prompt_user(
            "Profit target (% gain to close position, e.g., 100 for 100%)",
            default="100", 
            validation_func=validate_percentage
        )
        self.config['profit_target'] = float(profit_target) / 100
        
        print_success("Risk management configured")
    
    def _configure_output(self):
        """Configure output options"""
        print(f"\n{Colors.bold('💾 STEP 5: Output Options')}")
        
        save_results = confirm_action("Save detailed results to files?", default=True)
        
        if save_results:
            default_name = f"{self.config['strategy']}_{self.config['start_date']}_{self.config['end_date']}"
            output_name = prompt_user(
                "Output filename (without extension)",
                default=default_name
            )
            
            # Create results directory if it doesn't exist
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            
            self.config['output'] = str(results_dir / output_name)
            print_success(f"Results will be saved to: {self.config['output']}")
        else:
            self.config['output'] = None
    
    def _review_configuration(self):
        """Review final configuration and confirm"""
        print(f"\n{Colors.bold('📋 CONFIGURATION REVIEW')}")
        print("=" * 50)
        
        print(f"{Colors.cyan('Strategy:')} {self.config['strategy'].replace('_', ' ').title()}")
        print(f"{Colors.cyan('Date Range:')} {self.config['start_date']} to {self.config['end_date']}")
        print(f"{Colors.cyan('Initial Capital:')} ${self.config['initial_capital']:,.2f}")
        print(f"{Colors.cyan('Delta Threshold:')} {self.config['delta_threshold']:.2f}")
        print(f"{Colors.cyan('Days to Expiration:')} {self.config['min_dte']} to {self.config['max_dte']}")
        print(f"{Colors.cyan('Position Size:')} {self.config['position_size']:.1%}")
        print(f"{Colors.cyan('Stop Loss:')} {self.config['stop_loss']:.1%}")
        print(f"{Colors.cyan('Profit Target:')} {self.config['profit_target']:.1%}")
        
        if self.config.get('output'):
            print(f"{Colors.cyan('Output:')} {self.config['output']}")
        else:
            print(f"{Colors.cyan('Output:')} Console only")
        
        print("\n" + "=" * 50)
        
        if not confirm_action(f"{Colors.bold('Run backtest with these settings?')}", default=True):
            print(f"{Colors.yellow('Backtest cancelled by user')}")
            sys.exit(0)
    
    def _get_recent_date(self, days_ago: int) -> str:
        """Get date N days ago in YYYYMMDD format"""
        target_date = datetime.now() - timedelta(days=days_ago)
        date_str = target_date.strftime('%Y%m%d')
        
        # Find closest available date
        for date in self.available_dates:
            if date >= date_str:
                return date
        
        return self.available_dates[0]
    
    def _validate_date_in_range(self, date_str: str, start_date: str = None) -> bool:
        """Validate date is in available range"""
        date_validation = validate_date(date_str)
        if date_validation is not True:
            return date_validation
        
        if date_str < self.available_dates[0]:
            return f"Date too early. Available from {self.available_dates[0]}"
        
        if date_str > self.available_dates[-1]:
            return f"Date too late. Available until {self.available_dates[-1]}"
        
        if start_date and date_str <= start_date:
            return "End date must be after start date"
        
        return True
    
    def _validate_delta(self, delta_str: str, strategy: str) -> bool:
        """Validate delta threshold for strategy"""
        try:
            delta = float(delta_str)
            if strategy in ['long_call', 'covered_call']:
                if 0.1 <= delta <= 0.9:
                    return True
                return "Delta should be between 0.1 and 0.9 for calls"
            elif strategy == 'long_put':
                if 0.1 <= delta <= 0.9:  # Will be made negative later
                    return True
                return "Delta should be between 0.1 and 0.9 for puts"
            elif strategy == 'straddle':
                if 0.3 <= delta <= 0.7:
                    return True
                return "Delta should be between 0.3 and 0.7 for straddles (0.5 = ATM)"
        except ValueError:
            return "Please enter a valid number"
    
    def _validate_dte(self, dte_str: str, min_val: int = 1, max_val: int = 365) -> bool:
        """Validate days to expiration"""
        try:
            dte = int(dte_str)
            if min_val <= dte <= max_val:
                return True
            return f"DTE should be between {min_val} and {max_val}"
        except ValueError:
            return "Please enter a valid number"
    
    def _validate_position_size(self, size_str: str) -> bool:
        """Validate position size percentage"""
        try:
            size = float(size_str)
            if 0.1 <= size <= 50:  # 0.1% to 50%
                return True
            return "Position size should be between 0.1% and 50%"
        except ValueError:
            return "Please enter a valid percentage"


def run_interactive_mode() -> Dict[str, Any]:
    """Main entry point for interactive mode"""
    session = InteractiveSession()
    return session.run()