#!/usr/bin/env python3
"""
Comprehensive Test Suite for Tradier Trading System
"""

import sys
import os
import json
from datetime import datetime, date
import traceback

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test results collector
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "warnings": 0
    }
}

def log_test(name, status, message="", details=None):
    """Log test result"""
    test_results["tests"].append({
        "name": name,
        "status": status,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    test_results["summary"]["total"] += 1
    if status == "PASS":
        test_results["summary"]["passed"] += 1
        print(f"✅ {name}: {message}")
    elif status == "FAIL":
        test_results["summary"]["failed"] += 1
        print(f"❌ {name}: {message}")
    elif status == "WARN":
        test_results["summary"]["warnings"] += 1
        print(f"⚠️  {name}: {message}")

def test_tradier_connection():
    """Test Tradier API connection"""
    try:
        from core import TradierClient
        client = TradierClient(env="sandbox")
        
        # Test profile
        profile = client.get_profile()
        if profile:
            log_test("Tradier Connection", "PASS", f"Connected to account {profile.get('account', 'Unknown')}")
        else:
            log_test("Tradier Connection", "FAIL", "Could not get profile")
            
        # Test market status
        is_open = client.is_market_open()
        log_test("Market Status", "PASS", f"Market is {'OPEN' if is_open else 'CLOSED'}")
        
        # Test balances
        balances = client.get_balances()
        if balances and 'balances' in balances:
            bal = balances['balances']
            margin = bal.get('margin', {})
            bp = margin.get('option_buying_power', 0)
            log_test("Account Balance", "PASS", f"Option BP: ${bp:,.2f}")
        else:
            log_test("Account Balance", "WARN", "Could not get balances")
            
    except Exception as e:
        log_test("Tradier Connection", "FAIL", str(e))
        traceback.print_exc()

def test_options_chain():
    """Test options chain retrieval"""
    try:
        from core import TradierClient, OptionsManager
        
        client = TradierClient(env="sandbox")
        options_mgr = OptionsManager(client)
        
        # Get 0DTE options
        chain = options_mgr.get_0dte_options("SPY")
        if chain and 'options' in chain:
            options = chain['options'].get('option', [])
            log_test("Options Chain", "PASS", f"Found {len(options)} 0DTE options")
            
            # Test strike finding
            strikes = options_mgr.find_strangle_strikes("SPY", target_delta=0.15, dte=0)
            if strikes:
                call, put = strikes
                log_test("Strike Selection", "PASS", 
                        f"Call: ${call['strike']}, Put: ${put['strike']}")
            else:
                log_test("Strike Selection", "WARN", "No suitable strikes found")
        else:
            log_test("Options Chain", "FAIL", "Could not retrieve options")
            
    except Exception as e:
        log_test("Options Chain", "FAIL", str(e))
        traceback.print_exc()

def test_greeks_calculator():
    """Test Greeks calculations"""
    try:
        from core.greeks_calculator import GreeksCalculator
        
        calc = GreeksCalculator()
        
        # Test basic Greeks calculation
        spot = 637.0
        strike = 640.0
        time_to_expiry = 0.01  # Small time for 0DTE
        volatility = 0.15
        
        greeks = calc.calculate_greeks(spot, strike, time_to_expiry, volatility, 'call')
        
        if greeks and 'delta' in greeks:
            log_test("Greeks Calculator", "PASS", 
                    f"Delta: {greeks['delta']:.3f}, Gamma: {greeks['gamma']:.3f}, "
                    f"Vega: {greeks['vega']:.2f}, Theta: {greeks['theta']:.2f}")
        else:
            log_test("Greeks Calculator", "FAIL", "Could not calculate Greeks")
            
        # Test IV calculation
        option_price = 1.50
        iv = calc.calculate_iv_from_price(option_price, spot, strike, time_to_expiry, 'call')
        if iv:
            log_test("IV Calculation", "PASS", f"Calculated IV: {iv:.2%}")
        else:
            log_test("IV Calculation", "WARN", "Could not calculate IV")
            
    except Exception as e:
        log_test("Greeks Calculator", "FAIL", str(e))
        traceback.print_exc()

def test_order_management():
    """Test order management functions"""
    try:
        from core import TradierClient, OrderManager
        
        client = TradierClient(env="sandbox")
        order_mgr = OrderManager(client)
        
        # Get open orders
        open_orders = order_mgr.get_open_orders()
        log_test("Open Orders", "PASS", f"Found {len(open_orders)} open orders")
        
        # Get positions
        positions = order_mgr.get_strangle_positions()
        if positions:
            calls = len(positions.get('calls', []))
            puts = len(positions.get('puts', []))
            log_test("Positions", "PASS", f"{calls} calls, {puts} puts")
        else:
            log_test("Positions", "PASS", "No open positions")
            
    except Exception as e:
        log_test("Order Management", "FAIL", str(e))
        traceback.print_exc()

def test_trade_logger():
    """Test trade logging functionality"""
    try:
        from core.trade_logger import TradeLogger
        
        logger = TradeLogger()
        
        # Get statistics
        stats = logger.get_statistics()
        if stats:
            log_test("Trade Logger", "PASS", 
                    f"Total P&L: ${stats.get('total_pnl', 0):.2f}, "
                    f"Win Rate: {stats.get('win_rate', 0):.1f}%")
        else:
            log_test("Trade Logger", "PASS", "No trade history")
            
    except Exception as e:
        log_test("Trade Logger", "FAIL", str(e))
        traceback.print_exc()

def test_spy_quotes():
    """Test SPY quote retrieval"""
    try:
        from core import TradierClient
        
        client = TradierClient(env="sandbox")
        quotes = client.get_quotes(['SPY'])
        
        if quotes and 'quotes' in quotes:
            quote = quotes['quotes'].get('quote', {})
            if isinstance(quote, list):
                quote = quote[0]
            
            bid = quote.get('bid', 0)
            ask = quote.get('ask', 0)
            last = quote.get('last', 0)
            
            log_test("SPY Quotes", "PASS", 
                    f"Bid: ${bid:.2f}, Ask: ${ask:.2f}, Last: ${last:.2f}")
        else:
            log_test("SPY Quotes", "FAIL", "Could not get SPY quote")
            
    except Exception as e:
        log_test("SPY Quotes", "FAIL", str(e))
        traceback.print_exc()

def test_database():
    """Test database connectivity"""
    try:
        from database import get_db_manager
        
        db = get_db_manager()
        conn = db.get_connection()
        
        # Test SPY prices table
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM spy_prices WHERE date(timestamp) = ?", 
                      (date.today().strftime('%Y-%m-%d'),))
        count = cursor.fetchone()[0]
        
        log_test("Database", "PASS", f"Found {count} SPY records for today")
        
    except Exception as e:
        log_test("Database", "FAIL", str(e))
        traceback.print_exc()

def generate_report():
    """Generate test report"""
    print("\n" + "="*60)
    print("TEST REPORT SUMMARY")
    print("="*60)
    print(f"Timestamp: {test_results['timestamp']}")
    print(f"Total Tests: {test_results['summary']['total']}")
    print(f"✅ Passed: {test_results['summary']['passed']}")
    print(f"❌ Failed: {test_results['summary']['failed']}")
    print(f"⚠️  Warnings: {test_results['summary']['warnings']}")
    
    # Calculate success rate
    if test_results['summary']['total'] > 0:
        success_rate = (test_results['summary']['passed'] / test_results['summary']['total']) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    
    # Save report to JSON
    with open('test_report.json', 'w') as f:
        json.dump(test_results, f, indent=2)
    print(f"\nDetailed report saved to: test_report.json")
    
    # Create markdown report
    with open('TEST_REPORT.md', 'w') as f:
        f.write("# Tradier Trading System Test Report\n\n")
        f.write(f"**Generated:** {test_results['timestamp']}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total Tests: {test_results['summary']['total']}\n")
        f.write(f"- Passed: {test_results['summary']['passed']}\n")
        f.write(f"- Failed: {test_results['summary']['failed']}\n")
        f.write(f"- Warnings: {test_results['summary']['warnings']}\n")
        if test_results['summary']['total'] > 0:
            f.write(f"- Success Rate: {success_rate:.1f}%\n\n")
        
        f.write("## Test Results\n\n")
        f.write("| Test | Status | Message |\n")
        f.write("|------|--------|----------|\n")
        for test in test_results['tests']:
            status_emoji = "✅" if test['status'] == "PASS" else "❌" if test['status'] == "FAIL" else "⚠️"
            f.write(f"| {test['name']} | {status_emoji} {test['status']} | {test['message']} |\n")
        
        f.write("\n## System Status\n\n")
        f.write("### Components Tested\n\n")
        f.write("1. **Tradier API Connection** - Communication with broker\n")
        f.write("2. **Options Chain Retrieval** - 0DTE options data\n")
        f.write("3. **Greeks Calculator** - Risk metrics computation\n")
        f.write("4. **Order Management** - Position and order handling\n")
        f.write("5. **Trade Logger** - Trade history and statistics\n")
        f.write("6. **Market Data** - Real-time quotes\n")
        f.write("7. **Database** - Data persistence\n\n")
        
        if test_results['summary']['failed'] > 0:
            f.write("### ⚠️ Issues Found\n\n")
            for test in test_results['tests']:
                if test['status'] == "FAIL":
                    f.write(f"- **{test['name']}**: {test['message']}\n")
    
    print("Markdown report saved to: TEST_REPORT.md")

def main():
    print("="*60)
    print("RUNNING COMPREHENSIVE SYSTEM TESTS")
    print("="*60)
    
    # Run all tests
    print("\n1. Testing Tradier Connection...")
    test_tradier_connection()
    
    print("\n2. Testing Options Chain...")
    test_options_chain()
    
    print("\n3. Testing Greeks Calculator...")
    test_greeks_calculator()
    
    print("\n4. Testing Order Management...")
    test_order_management()
    
    print("\n5. Testing Trade Logger...")
    test_trade_logger()
    
    print("\n6. Testing SPY Quotes...")
    test_spy_quotes()
    
    print("\n7. Testing Database...")
    test_database()
    
    # Generate report
    generate_report()

if __name__ == "__main__":
    main()