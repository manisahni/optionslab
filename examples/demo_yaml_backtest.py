#!/usr/bin/env python3
"""
YAML Integration Demo
Demonstrates how to use YAML-configured strategies with advanced features
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import yaml

# Add paths
sys.path.append(str(Path(__file__).parent / "optionslab-core"))
sys.path.append(str(Path(__file__).parent / "optionslab-ui"))

def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")


def demo_yaml_cli():
    """Demonstrate YAML usage with CLI"""
    print_section("DEMO: YAML Configuration with CLI")
    
    # Show available YAML files
    print("\n1️⃣ Available YAML configurations:")
    
    config_dirs = [
        Path("optionslab-core/config/strategies"),
        Path("optionslab-ui/config/strategies"),
        Path("optionslab-ui/strategy_templates")
    ]
    
    yaml_files = []
    for config_dir in config_dirs:
        if config_dir.exists():
            for yaml_file in config_dir.glob("*.yaml"):
                yaml_files.append(yaml_file)
                print(f"   📄 {yaml_file}")
    
    if not yaml_files:
        print("   ⚠️  No YAML files found. Creating example...")
        create_example_yaml()
        return
    
    # Demo: List available configs
    print("\n2️⃣ List YAML configurations using CLI:")
    cmd = ["python", "optionslab-core/backtester_enhanced.py", "--list-yaml"]
    print(f"   Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print("   Output:")
        for line in result.stdout.split('\n')[:10]:  # Show first 10 lines
            if line.strip():
                print(f"   {line}")
    
    # Demo: Run backtest with YAML
    print("\n3️⃣ Run backtest with YAML configuration:")
    
    # Use the first available YAML file
    yaml_file = yaml_files[0].name
    
    # Set dates
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    
    cmd = [
        "python", "optionslab-core/backtester_enhanced.py",
        "--yaml-config", yaml_file,
        "--start-date", start_date.strftime("%Y%m%d"),
        "--end-date", end_date.strftime("%Y%m%d")
    ]
    
    print(f"   Command: {' '.join(cmd)}")
    print("\n   ⏳ Running backtest...")
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
    
    if result.returncode == 0:
        print("   ✅ Backtest completed successfully!")
        
        # Show key results
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if any(keyword in line for keyword in ['Total Return:', 'Sharpe Ratio:', 'Max Drawdown:']):
                print(f"   {line.strip()}")
    else:
        print(f"   ❌ Backtest failed: {result.stderr}")
    
    # Demo: Override parameters
    print("\n4️⃣ Run with parameter overrides:")
    
    cmd_override = cmd + [
        "--override", "exit_rules.profit_target_pct=1.0",
        "--override", "exit_rules.stop_loss_pct=0.30"
    ]
    
    print(f"   Command: {' '.join(cmd_override)}")
    print("   📝 This overrides the profit target to 100% and stop loss to 30%")


def demo_streamlit_yaml():
    """Demonstrate YAML usage in Streamlit"""
    print_section("DEMO: YAML in Streamlit UI")
    
    print("\n📱 Streamlit UI Features:")
    print("   1. Configuration Mode selector (Traditional vs YAML)")
    print("   2. YAML file dropdown selector")
    print("   3. Configuration details display")
    print("   4. Parameter override section")
    print("   5. Advanced features indicators")
    
    print("\n🚀 To launch Streamlit with YAML support:")
    print("   cd optionslab-ui")
    print("   streamlit run streamlit_app.py")
    
    print("\n📋 In the Streamlit UI:")
    print("   1. Select 'YAML Config' mode in the sidebar")
    print("   2. Choose a YAML file from the dropdown")
    print("   3. Review the configuration details")
    print("   4. Optionally override parameters")
    print("   5. Run the backtest")


def demo_advanced_features():
    """Demonstrate advanced exit features"""
    print_section("DEMO: Advanced Exit Features")
    
    # Load and display an advanced YAML config
    yaml_path = Path("optionslab-core/config/strategies/long_put_dynamic_stops.yaml")
    
    if yaml_path.exists():
        print(f"\n📄 Loading: {yaml_path}")
        
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"\n🎯 Strategy: {config.get('name', 'Unknown')}")
        print(f"📝 Description: {config.get('description', 'No description')}")
        
        # Show advanced features
        print("\n🔧 Advanced Features:")
        
        if config.get('dynamic_stops', {}).get('enabled'):
            print("\n   🛡️ Dynamic Volatility Stops:")
            atr_settings = config['dynamic_stops'].get('atr_settings', {})
            print(f"      • ATR Period: {atr_settings.get('period', 14)}")
            print(f"      • Volatility Lookback: {atr_settings.get('volatility_lookback', 30)}")
            weights = config['dynamic_stops'].get('component_weights', {})
            print(f"      • Component Weights: ATR={weights.get('atr_weight', 0.4)}, "
                  f"Vega={weights.get('vega_weight', 0.35)}, "
                  f"Theta={weights.get('theta_weight', 0.25)}")
        
        if config.get('greeks_exits', {}).get('enabled'):
            print("\n   📊 Greeks-Based Exits:")
            if config['greeks_exits'].get('delta_threshold_exit', {}).get('enabled'):
                threshold = config['greeks_exits']['delta_threshold_exit'].get('threshold', 0.15)
                print(f"      • Delta Threshold Exit: {threshold}")
            if config['greeks_exits'].get('theta_acceleration_exit', {}).get('enabled'):
                threshold = config['greeks_exits']['theta_acceleration_exit'].get('threshold', 2.0)
                print(f"      • Theta Acceleration Exit: {threshold}x")
            if config['greeks_exits'].get('vega_crush_exit', {}).get('enabled'):
                threshold = config['greeks_exits']['vega_crush_exit'].get('threshold', -25)
                print(f"      • Vega Crush Exit: {threshold}%")
        
        if config.get('iv_exits', {}).get('enabled'):
            print("\n   📈 IV-Based Exits:")
            if config['iv_exits'].get('iv_rank_exit', {}).get('enabled'):
                threshold = config['iv_exits']['iv_rank_exit'].get('threshold', 15)
                print(f"      • IV Rank Exit: {threshold}")
    else:
        print(f"   ⚠️  Advanced YAML not found: {yaml_path}")


def create_example_yaml():
    """Create an example YAML configuration"""
    print_section("Creating Example YAML Configuration")
    
    example_yaml = {
        'name': 'Example Long Put with Advanced Exits',
        'description': 'Demonstration of YAML configuration with dynamic stops and Greeks exits',
        'category': 'directional',
        'version': '1.0',
        
        'legs': [{
            'type': 'put',
            'direction': 'long',
            'quantity': 1,
            'delta_target': -0.40,
            'delta_tolerance': 0.10
        }],
        
        'entry_rules': {
            'dte': 30,
            'dte_tolerance': 5,
            'dte_range': [25, 35],
            'target_delta': -0.40,
            'delta_tolerance': 0.10,
            'volume_min': 100,
            'open_interest_min': 500,
            'bid_ask_spread_max_pct': 0.05
        },
        
        'exit_rules': {
            'profit_target_pct': 0.75,
            'stop_loss_pct': 0.40,
            'exit_on_dte': 5,
            'max_hold_days': 30
        },
        
        'dynamic_stops': {
            'enabled': True,
            'atr_settings': {
                'period': 14,
                'volatility_lookback': 30,
                'multiplier': 2.0
            },
            'component_weights': {
                'atr_weight': 0.4,
                'vega_weight': 0.35,
                'theta_weight': 0.25
            },
            'confidence_threshold': 0.7
        },
        
        'greeks_exits': {
            'enabled': True,
            'delta_threshold_exit': {
                'enabled': True,
                'threshold': 0.15,
                'signal_strength': 'moderate'
            },
            'theta_acceleration_exit': {
                'enabled': True,
                'threshold': 2.0,
                'dte_acceleration_zone': 10
            },
            'vega_crush_exit': {
                'enabled': True,
                'threshold': -25.0,
                'time_window': 2
            }
        },
        
        'risk_management': {
            'max_positions': 3,
            'position_sizing': {
                'method': 'fixed',
                'max_position_size_pct': 0.05
            }
        }
    }
    
    # Save example YAML
    output_dir = Path("optionslab-core/config/strategies")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "example_advanced_strategy.yaml"
    
    with open(output_file, 'w') as f:
        yaml.dump(example_yaml, f, default_flow_style=False, indent=2, sort_keys=False)
    
    print(f"✅ Created example YAML: {output_file}")
    print("\n📋 Example configuration includes:")
    print("   • Basic strategy parameters (Long Put)")
    print("   • Dynamic volatility-based stops")
    print("   • Greeks-based exit conditions")
    print("   • Risk management settings")


def main():
    """Run all demonstrations"""
    print("\n" + "🚀 "*20)
    print("YAML INTEGRATION DEMONSTRATION")
    print("🚀 "*20)
    
    # Run demos
    demo_yaml_cli()
    demo_streamlit_yaml()
    demo_advanced_features()
    
    print("\n" + "="*60)
    print("📚 YAML Integration Benefits:")
    print("   • Reusable strategy configurations")
    print("   • Version control for strategies")
    print("   • Easy parameter experimentation")
    print("   • Support for advanced exit strategies")
    print("   • Consistent configuration across CLI and UI")
    
    print("\n✨ Get started by:")
    print("   1. Creating YAML files in config/strategies/")
    print("   2. Using --yaml-config flag with CLI")
    print("   3. Selecting YAML Config mode in Streamlit")
    
    print("\n🎉 Happy backtesting with YAML!")


if __name__ == "__main__":
    main()