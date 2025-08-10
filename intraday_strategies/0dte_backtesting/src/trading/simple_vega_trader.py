#!/usr/bin/env python3
"""
Simplified Vega-Aware 0DTE Trading System
Executes immediately without async complexity
"""

import os
import sys
from pathlib import Path
from datetime import datetime, time, timedelta
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
import pytz
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from config directory
project_root = Path(__file__).parent.parent.parent
config_path = project_root / 'config' / '.env'
load_dotenv(config_path)

class SimpleVegaTrader:
    def __init__(self):
        """Initialize the trader"""
        
        # Get credentials
        api_key = os.getenv('ALPACA_PAPER_API_KEY')
        secret_key = os.getenv('ALPACA_PAPER_SECRET_KEY')
        
        if not api_key or not secret_key:
            raise ValueError("Missing API credentials in .env file")
        
        # Initialize clients
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=True
        )
        
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )
        
        # Strategy parameters
        self.min_iv_percentile = 30
        self.max_vega_ratio = 0.02
        self.profit_target = 0.50  # 50% of premium
        self.stop_loss = 2.0  # 200% of premium
        
        logger.info("Simple Vega Trader initialized")
    
    def get_market_status(self):
        """Check if market is open"""
        try:
            clock = self.trading_client.get_clock()
            return clock.is_open, clock
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return False, None
    
    def get_spy_price(self):
        """Get current SPY price"""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols="SPY")
            quote = self.data_client.get_stock_latest_quote(request)
            spy_quote = quote["SPY"]
            
            mid_price = (spy_quote.bid_price + spy_quote.ask_price) / 2
            
            return {
                'bid': spy_quote.bid_price,
                'ask': spy_quote.ask_price,
                'mid': mid_price,
                'spread': spy_quote.ask_price - spy_quote.bid_price
            }
        except Exception as e:
            logger.error(f"Error getting SPY price: {e}")
            return None
    
    def check_entry_conditions(self):
        """Check if we should enter a trade"""
        
        # Get Eastern Time
        et_tz = pytz.timezone('America/New_York')
        now_et = datetime.now(et_tz)
        current_time = now_et.time()
        
        logger.info(f"Current time: {now_et.strftime('%I:%M:%S %p ET')}")
        
        # Check time window (3:00-3:50 PM ET for testing)
        entry_start = time(15, 0)  # 3:00 PM
        entry_end = time(15, 50)   # 3:50 PM (extended for testing)
        
        if not (entry_start <= current_time <= entry_end):
            logger.info(f"Outside trading window (3:00-3:45 PM ET)")
            return False, "Outside trading window"
        
        # Check market is open
        is_open, clock = self.get_market_status()
        if not is_open:
            logger.info("Market is closed")
            return False, "Market closed"
        
        # Get SPY price
        spy_data = self.get_spy_price()
        if not spy_data:
            return False, "Could not get SPY price"
        
        logger.info(f"SPY Price: ${spy_data['mid']:.2f} (spread: ${spy_data['spread']:.2f})")
        
        # Simulate Greeks and IV check
        # In production, you'd calculate real Greeks here
        simulated_iv_percentile = 45  # Simulated
        simulated_vega_ratio = 0.015  # Simulated
        
        logger.info(f"IV Percentile: {simulated_iv_percentile}%")
        logger.info(f"Vega Ratio: {simulated_vega_ratio:.3f}")
        
        # Check IV percentile
        if simulated_iv_percentile < self.min_iv_percentile:
            return False, f"IV percentile too low: {simulated_iv_percentile}%"
        
        # Check vega ratio
        if simulated_vega_ratio > self.max_vega_ratio:
            return False, f"Vega ratio too high: {simulated_vega_ratio:.3f}"
        
        # Check account
        try:
            account = self.trading_client.get_account()
            buying_power = float(account.buying_power)
            
            if buying_power < 10000:
                return False, f"Insufficient buying power: ${buying_power:.2f}"
            
            logger.info(f"Account buying power: ${buying_power:,.2f}")
            
        except Exception as e:
            logger.error(f"Error checking account: {e}")
            return False, "Could not check account"
        
        # All conditions met
        return True, "All conditions met"
    
    def execute_trade(self):
        """Execute the strangle trade"""
        
        logger.info("="*50)
        logger.info("TRADE EXECUTION")
        logger.info("="*50)
        
        # Get SPY price
        spy_data = self.get_spy_price()
        if not spy_data:
            logger.error("Could not get SPY price")
            return False
        
        spy_price = spy_data['mid']
        
        # Calculate strikes for strangle
        # Typically 3-5 points OTM for 30 delta
        call_strike = round(spy_price + 3)
        put_strike = round(spy_price - 3)
        
        logger.info(f"SPY Price: ${spy_price:.2f}")
        logger.info(f"Strangle strikes:")
        logger.info(f"  Call: ${call_strike}")
        logger.info(f"  Put: ${put_strike}")
        
        # Calculate position size (simplified)
        account = self.trading_client.get_account()
        buying_power = float(account.buying_power)
        position_size = min(1, int(buying_power * 0.01 / 1000))  # 1% risk
        
        logger.info(f"Position size: {position_size} contracts per leg")
        
        # In a real implementation, you would:
        # 1. Find the actual option symbols
        # 2. Get real-time quotes
        # 3. Place limit orders
        # 4. Monitor fills
        
        logger.info("\n📊 SIMULATED TRADE:")
        logger.info(f"  SELL {position_size} SPY Call @ ${call_strike}")
        logger.info(f"  SELL {position_size} SPY Put @ ${put_strike}")
        logger.info(f"  Est. Premium: $200 per strangle")
        logger.info(f"  Max Risk: $400 per strangle")
        logger.info(f"  Target: 50% of premium ($100)")
        logger.info(f"  Stop: 200% of premium ($400)")
        logger.info(f"  Exit: 3:59 PM or target/stop")
        
        # Log the trade
        self.log_trade({
            'timestamp': datetime.now(),
            'spy_price': spy_price,
            'call_strike': call_strike,
            'put_strike': put_strike,
            'position_size': position_size,
            'status': 'SIMULATED'
        })
        
        return True
    
    def log_trade(self, trade_info):
        """Log trade to file"""
        try:
            import json
            
            log_file = 'trades_log.json'
            
            # Read existing logs
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
            
            # Add new trade
            trade_info['timestamp'] = str(trade_info['timestamp'])
            logs.append(trade_info)
            
            # Write back
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
            
            logger.info(f"Trade logged to {log_file}")
            
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    def run(self):
        """Main execution"""
        
        print("\n" + "="*60)
        print("🚀 SIMPLE VEGA TRADER - STARTING")
        print("="*60)
        
        # Check entry conditions
        should_trade, reason = self.check_entry_conditions()
        
        if should_trade:
            logger.info("✅ Entry conditions met!")
            
            # Execute trade
            success = self.execute_trade()
            
            if success:
                print("\n✅ TRADE EXECUTED (SIMULATED)")
                print("   Check trades_log.json for details")
                print("   In production, this would place real orders")
            else:
                print("\n❌ Trade execution failed")
        else:
            print(f"\n❌ No trade: {reason}")
            print("\n📋 Entry Requirements:")
            print("   - Time: 3:00-3:45 PM ET")
            print("   - Market: Open")
            print("   - IV Percentile: > 30%")
            print("   - Vega Ratio: < 0.02")
            print("   - Buying Power: > $10,000")
        
        # Show current positions
        try:
            positions = self.trading_client.get_all_positions()
            if positions:
                print(f"\n📊 Current Positions: {len(positions)}")
                for pos in positions[:3]:
                    print(f"   {pos.symbol}: {pos.qty} @ ${pos.avg_entry_price}")
            else:
                print("\n📊 No open positions")
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
        
        print("\n" + "="*60)
        print("EXECUTION COMPLETE")
        print("="*60)

def main():
    """Main entry point"""
    try:
        trader = SimpleVegaTrader()
        trader.run()
    except KeyboardInterrupt:
        print("\nShutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()