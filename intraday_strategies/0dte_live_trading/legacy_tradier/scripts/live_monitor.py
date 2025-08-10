#!/usr/bin/env python3
"""
Live Monitor with Greeks and Risk Tracking
Enhanced monitoring with real-time Greeks calculation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TradierClient, OrderManager
from core.risk_monitor import RiskMonitor
from datetime import datetime
import time
import json
from colorama import init, Fore, Back, Style

# Initialize colorama for colored output
init()

def format_greek(value: float, threshold: float = None) -> str:
    """Format Greek value with color coding"""
    formatted = f"{value:+.3f}"
    if threshold and abs(value) > threshold:
        return Fore.RED + formatted + Style.RESET_ALL
    elif abs(value) > 0.1:
        return Fore.YELLOW + formatted + Style.RESET_ALL
    else:
        return Fore.GREEN + formatted + Style.RESET_ALL

def format_risk_level(level: str) -> str:
    """Format risk level with color"""
    colors = {
        'LOW': Fore.GREEN,
        'MEDIUM': Fore.YELLOW,
        'HIGH': Fore.RED + Style.BRIGHT,
        'CRITICAL': Back.RED + Fore.WHITE + Style.BRIGHT,
        'SAFE': Fore.GREEN,
        'NEUTRAL': Fore.CYAN,
        'WATCH': Fore.YELLOW,
        'WARNING': Fore.RED,
        'DANGER': Back.RED + Fore.WHITE
    }
    return colors.get(level, '') + level + Style.RESET_ALL

def live_monitor():
    """Enhanced live monitoring with Greeks"""
    
    print("="*80)
    print(Fore.CYAN + Style.BRIGHT + "🚀 LIVE STRANGLE MONITOR WITH GREEKS" + Style.RESET_ALL)
    print("="*80)
    
    try:
        # Initialize components
        client = TradierClient(env="sandbox")
        order_mgr = OrderManager(client)
        risk_monitor = RiskMonitor(client, vega_limit=2.0, delta_limit=0.20)
        
        # Get current time
        now = datetime.now()
        print(f"\n📅 Time: {now.strftime('%I:%M:%S %p ET')}")
        
        # Check market status
        if client.is_market_open():
            print(Fore.GREEN + "✅ Market is OPEN" + Style.RESET_ALL)
        else:
            print(Fore.RED + "⚠️  Market is CLOSED" + Style.RESET_ALL)
        
        # Calculate risk metrics
        print("\n" + Fore.YELLOW + "Calculating risk metrics..." + Style.RESET_ALL)
        metrics = risk_monitor.calculate_risk_metrics()
        
        if not metrics:
            print(Fore.RED + "❌ No strangle position found" + Style.RESET_ALL)
            return False
        
        # Display SPY price
        spy_price = metrics['spy_price']
        print(f"\n" + "="*40)
        print(f"📈 SPY PRICE: " + Fore.WHITE + Style.BRIGHT + f"${spy_price:.2f}" + Style.RESET_ALL)
        print("="*40)
        
        # Display positions
        print("\n📊 STRANGLE POSITIONS:")
        print("-"*40)
        
        if 'call' in metrics['positions']:
            call = metrics['positions']['call']
            print(f"\n📈 CALL: {call['symbol']}")
            print(f"   Strike: ${call['strike']:.0f}")
            print(f"   Price: ${call['price']:.2f}")
            print(f"   IV: {call['iv']:.1%}")
            print(f"   Distance: {format_greek(call['distance'])}")
        
        if 'put' in metrics['positions']:
            put = metrics['positions']['put']
            print(f"\n📉 PUT: {put['symbol']}")
            print(f"   Strike: ${put['strike']:.0f}")
            print(f"   Price: ${put['price']:.2f}")
            print(f"   IV: {put['iv']:.1%}")
            print(f"   Distance: {format_greek(put['distance'])}")
        
        # Display Greeks
        print("\n🎯 GREEKS:")
        print("-"*40)
        
        greeks = metrics['greeks']
        print(f"   Delta: {format_greek(greeks['delta'], 0.20)}")
        print(f"   Gamma: {format_greek(greeks['gamma'], 0.05)}")
        print(f"   Theta: {format_greek(greeks['theta'] * 100)} ($/day)")
        print(f"   Vega: {format_greek(greeks['vega'], 2.0)}")
        print(f"   Rho: {format_greek(greeks['rho'])}")
        
        # Individual leg Greeks
        print(f"\n   Call Delta: {format_greek(greeks['call_delta'])}")
        print(f"   Put Delta: {format_greek(greeks['put_delta'])}")
        print(f"   Call Vega: {format_greek(greeks['call_vega'])}")
        print(f"   Put Vega: {format_greek(greeks['put_vega'])}")
        
        # Display risk levels
        print("\n⚠️  RISK ASSESSMENT:")
        print("-"*40)
        
        risk_levels = metrics['risk_levels']
        print(f"   Vega Risk: {format_risk_level(risk_levels['vega'])}")
        print(f"   Delta Risk: {format_risk_level(risk_levels['delta'])}")
        print(f"   Strike Risk: {format_risk_level(risk_levels['strike'])}")
        print(f"   Gamma Risk: {format_risk_level(risk_levels['gamma'])}")
        print(f"\n   OVERALL: {format_risk_level(risk_levels['overall'])}")
        
        # Display warnings
        if metrics['warnings']:
            print("\n🚨 WARNINGS:")
            print("-"*40)
            for warning in metrics['warnings']:
                print(f"   {warning}")
        else:
            print("\n" + Fore.GREEN + "✅ No warnings" + Style.RESET_ALL)
        
        # Check exit conditions
        should_exit, reason = risk_monitor.should_exit(metrics)
        
        print("\n📤 EXIT STRATEGY:")
        print("-"*40)
        
        if should_exit:
            print(Back.RED + Fore.WHITE + Style.BRIGHT + 
                  f"   🚨 EXIT SIGNAL: {reason}" + Style.RESET_ALL)
            print("\n   " + Fore.YELLOW + "Recommended Action: CLOSE POSITION NOW" + Style.RESET_ALL)
        else:
            print(Fore.GREEN + f"   ✅ Hold position: {reason}" + Style.RESET_ALL)
        
        # Time management
        close_time = now.replace(hour=15, minute=59, second=0)
        time_remaining = close_time - now
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        
        print(f"\n⏰ TIME TO CLOSE: {hours}h {minutes}m")
        
        # Strike visualization
        print("\n" + "="*60)
        print("STRIKE MAP:")
        
        # Create visual representation
        put_strike = metrics['positions'].get('put', {}).get('strike', 0)
        call_strike = metrics['positions'].get('call', {}).get('strike', 0)
        
        if put_strike and call_strike:
            # Calculate position on scale
            strike_range = call_strike - put_strike
            spy_position = (spy_price - put_strike) / strike_range
            
            # Create visual bar (30 characters wide)
            bar_width = 30
            spy_pos_char = int(spy_position * bar_width)
            spy_pos_char = max(0, min(bar_width - 1, spy_pos_char))
            
            # Build the bar
            bar = ['-'] * bar_width
            bar[spy_pos_char] = '●'
            
            # Color the bar based on position
            colored_bar = ''
            for i, char in enumerate(bar):
                if i < 5 or i >= bar_width - 5:
                    colored_bar += Fore.RED + char + Style.RESET_ALL
                elif i < 10 or i >= bar_width - 10:
                    colored_bar += Fore.YELLOW + char + Style.RESET_ALL
                else:
                    colored_bar += Fore.GREEN + char + Style.RESET_ALL
            
            print(f"PUT ${put_strike:.0f} |{colored_bar}| CALL ${call_strike:.0f}")
            print(f"            SPY @ ${spy_price:.2f}")
        
        print("="*60)
        
        # Export metrics
        risk_monitor.export_metrics('tradier_risk_metrics.json')
        print(f"\n📁 Metrics saved to: tradier_risk_metrics.json")
        
        return True
        
    except Exception as e:
        print(f"\n" + Fore.RED + f"❌ Error: {e}" + Style.RESET_ALL)
        import traceback
        traceback.print_exc()
        return False

def continuous_monitor(interval: int = 30):
    """Run continuous monitoring"""
    
    print(f"🔄 Starting continuous monitoring (updates every {interval}s)")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Clear screen (optional - comment out if you want to see history)
            os.system('clear' if os.name == 'posix' else 'cls')
            
            live_monitor()
            
            print(f"\n⏳ Next update in {interval} seconds...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n" + Fore.YELLOW + "✋ Monitoring stopped by user" + Style.RESET_ALL)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Live strangle monitor with Greeks')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=30, help='Update interval in seconds')
    args = parser.parse_args()
    
    if args.once:
        live_monitor()
    else:
        continuous_monitor(args.interval)