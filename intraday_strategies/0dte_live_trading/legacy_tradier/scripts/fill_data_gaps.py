#!/usr/bin/env python3
"""
Fill data gaps and generate Greeks for dashboard
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import logging
from core import TradierClient
from core.cache_manager import TradierCacheManager
from core.greeks_calculator import GreeksCalculator
from database import get_db_manager
import json
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fill_spy_gaps():
    """Fill gaps in SPY data for today"""
    client = TradierClient(env="sandbox")
    cache_mgr = TradierCacheManager(client)
    db = get_db_manager()
    
    # Get today's date
    today = datetime.now().date()
    market_open = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=30)
    market_close = datetime.combine(today, datetime.min.time()).replace(hour=16, minute=0)
    
    logger.info(f"Filling gaps for {today} from {market_open} to {market_close}")
    
    # Check existing data
    query = """
        SELECT timestamp FROM spy_prices 
        WHERE date(timestamp) = ? 
        AND time(timestamp) >= '09:30:00' 
        AND time(timestamp) <= '16:00:00'
        ORDER BY timestamp
    """
    existing = db.execute_query(query, (str(today),))
    existing_times = set(row['timestamp'] for row in existing)
    
    logger.info(f"Found {len(existing_times)} existing regular hours records")
    
    # Generate all expected timestamps (1-minute bars)
    expected_times = []
    current = market_open
    while current <= market_close:
        expected_times.append(current)
        current += timedelta(minutes=1)
    
    # Find missing timestamps
    missing_times = []
    for ts in expected_times:
        ts_str = ts.strftime('%Y-%m-%d %H:%M:00')
        if ts_str not in existing_times:
            missing_times.append(ts)
    
    logger.info(f"Found {len(missing_times)} missing timestamps")
    
    if missing_times:
        # Group missing times into ranges for efficient API calls
        ranges = []
        start = missing_times[0]
        end = missing_times[0]
        
        for ts in missing_times[1:]:
            if (ts - end).total_seconds() <= 120:  # Within 2 minutes
                end = ts
            else:
                ranges.append((start, end))
                start = ts
                end = ts
        ranges.append((start, end))
        
        logger.info(f"Fetching data in {len(ranges)} ranges")
        
        # Fetch missing data
        for start, end in ranges:
            start_str = start.strftime("%Y-%m-%d %H:%M")
            end_str = end.strftime("%Y-%m-%d %H:%M")
            logger.info(f"Fetching {start_str} to {end_str}")
            
            response = client.get_timesales(
                symbol="SPY",
                interval="1min",
                start=start_str,
                end=end_str,
                session_filter="all"
            )
            
            if response and isinstance(response, dict) and 'series' in response:
                if isinstance(response['series'], dict) and 'data' in response['series']:
                    api_data = response['series']['data']
                    records = []
                    
                    for item in api_data:
                        if not isinstance(item, dict):
                            logger.warning(f"Skipping non-dict item: {type(item)}")
                            continue
                            
                        time_str = item.get('time', '')
                        if not time_str:
                            continue
                            
                        timestamp = datetime.fromisoformat(time_str.replace('T', ' ').replace('Z', ''))
                        hour = timestamp.hour
                        minute = timestamp.minute
                        session_type = 'regular' if (9 <= hour < 16 or (hour == 9 and minute >= 30)) else 'extended'
                        
                        records.append((
                            timestamp,
                            item.get('open', 0),
                            item.get('high', 0),
                            item.get('low', 0),
                            item.get('close', 0),
                            item.get('volume', 0),
                            item.get('vwap'),
                            session_type
                        ))
                    
                    if records:
                        query = """
                            INSERT OR IGNORE INTO spy_prices 
                            (timestamp, open, high, low, close, volume, vwap, session_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        db.execute_many(query, records)
                        logger.info(f"Added {len(records)} records")
                else:
                    logger.warning(f"No data in response for {start_str} to {end_str}")
            else:
                logger.warning(f"Invalid or empty response for {start_str} to {end_str}")
    
    # Verify final count
    count_query = """
        SELECT COUNT(*) as count FROM spy_prices 
        WHERE date(timestamp) = ? 
        AND time(timestamp) >= '09:30:00' 
        AND time(timestamp) <= '16:00:00'
    """
    final_count = db.execute_query(count_query, (str(today),))
    logger.info(f"Final regular hours record count: {final_count[0]['count']}")
    
    return len(missing_times)

def generate_greeks_data():
    """Generate Greeks data for simulated positions"""
    client = TradierClient(env="sandbox")
    calc = GreeksCalculator()
    db = get_db_manager()
    
    # Get recent SPY prices
    query = """
        SELECT timestamp, close FROM spy_prices 
        WHERE date(timestamp) = date('now') 
        AND time(timestamp) >= '09:30:00'
        AND time(timestamp) <= '16:00:00'
        ORDER BY timestamp
    """
    prices = db.execute_query(query)
    
    if not prices:
        logger.warning("No SPY prices found for today")
        return
    
    logger.info(f"Generating Greeks for {len(prices)} price points")
    
    # Simulate a strangle position
    current_price = prices[-1]['close'] if prices else 630
    
    # Define strikes (slightly OTM)
    call_strike = round(current_price + 2)  # $2 OTM call
    put_strike = round(current_price - 2)   # $2 OTM put
    
    greeks_history = []
    
    for price_data in prices:
        timestamp = datetime.fromisoformat(price_data['timestamp'])
        spot = price_data['close']
        
        # Time to expiration (0DTE)
        expiry = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)
        tte = max((expiry - timestamp).total_seconds() / (365 * 24 * 3600), 1e-6)
        
        # Calculate IV based on time of day (higher in morning, lower in afternoon)
        hour = timestamp.hour
        base_iv = 0.15  # 15% base IV
        if hour < 10:
            iv = base_iv * 1.3
        elif hour < 12:
            iv = base_iv * 1.1
        else:
            iv = base_iv * 0.9
        
        # Calculate Greeks for call
        call_greeks = calc.calculate_greeks(
            spot=spot,
            strike=call_strike,
            time_to_expiry=tte,
            volatility=iv,
            option_type='call'
        )
        
        # Calculate Greeks for put
        put_greeks = calc.calculate_greeks(
            spot=spot,
            strike=put_strike,
            time_to_expiry=tte,
            volatility=iv,
            option_type='put'
        )
        
        # Combined position Greeks (long strangle)
        combined_greeks = {
            'delta': call_greeks['delta'] + put_greeks['delta'],
            'gamma': call_greeks['gamma'] + put_greeks['gamma'],
            'vega': call_greeks['vega'] + put_greeks['vega'],
            'theta': call_greeks['theta'] + put_greeks['theta'],
            'timestamp': timestamp.isoformat()
        }
        
        greeks_history.append(combined_greeks)
        
        # Also store in database
        for option_type, greeks, strike in [('call', call_greeks, call_strike), ('put', put_greeks, put_strike)]:
            symbol = f"SPY{expiry.strftime('%y%m%d')}{'C' if option_type == 'call' else 'P'}{strike:05d}000"
            
            query = """
                INSERT OR REPLACE INTO options_data 
                (timestamp, symbol, underlying, strike, option_type, expiry, 
                 bid, ask, last, volume, open_interest, iv, 
                 delta, gamma, theta, vega, rho)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # Simulate bid/ask
            option_value = greeks['price'] if 'price' in greeks else 1.0
            spread = 0.05
            
            values = (
                timestamp,
                symbol,
                'SPY',
                strike,
                option_type,
                expiry.date(),
                max(0, option_value - spread/2),  # bid
                option_value + spread/2,  # ask
                option_value,  # last
                np.random.randint(100, 10000),  # volume
                np.random.randint(1000, 50000),  # open_interest
                iv,
                greeks['delta'],
                greeks['gamma'],
                greeks['theta'],
                greeks['vega'],
                greeks.get('rho', 0)
            )
            
            db.execute_query(query, values)
    
    # Save Greeks history to JSON for dashboard
    json_path = os.path.join(os.path.dirname(__file__), '..', 'tradier_risk_metrics.json')
    
    # Load existing data if any
    existing_data = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                existing_data = json.load(f)
        except:
            existing_data = {}
    
    # Update with new history
    existing_data['history'] = [
        {
            'timestamp': item['timestamp'],
            'greeks': {
                'delta': item['delta'],
                'gamma': item['gamma'],
                'vega': item['vega'],
                'theta': item['theta']
            }
        }
        for item in greeks_history
    ]
    
    # Save updated data
    with open(json_path, 'w') as f:
        json.dump(existing_data, f, indent=2)
    
    logger.info(f"Generated {len(greeks_history)} Greeks data points")
    
    # Verify options data
    count = db.execute_query("SELECT COUNT(*) as count FROM options_data")[0]['count']
    logger.info(f"Total options records in database: {count}")

def main():
    """Main function"""
    logger.info("Starting data gap filling and Greeks generation")
    
    # Fill SPY data gaps
    gaps_filled = fill_spy_gaps()
    logger.info(f"Filled {gaps_filled} gaps in SPY data")
    
    # Generate Greeks data
    generate_greeks_data()
    
    # Print summary
    db = get_db_manager()
    stats = db.execute_query("SELECT * FROM cache_stats")[0]
    
    logger.info("\n" + "="*50)
    logger.info("Data Update Complete!")
    logger.info(f"Total SPY records: {stats['total_spy_records']}")
    logger.info(f"Total options records: {stats['total_options_records']}")
    logger.info(f"Trading days cached: {stats['trading_days_cached']}")
    logger.info(f"Latest data: {stats['latest_spy_data']}")
    logger.info("="*50)

if __name__ == "__main__":
    main()