#!/usr/bin/env python3
"""
Daily Zero DTE Update Script
Automatically downloads new 0DTE options data each trading day
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import subprocess
import json
import time
import requests

# Add the market_data directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zero_dte_spy_options_database import ZeroDTESPYOptionsDatabase

# Configure logging
log_dir = os.path.expanduser("~/0dte/logs")
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f"zero_dte_update_{datetime.now().strftime('%Y%m')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ZeroDTEUpdater')


class ZeroDTEDailyUpdater:
    """Handles daily updates of Zero DTE database"""
    
    def __init__(self):
        self.db = ZeroDTESPYOptionsDatabase()
        self.notification_file = os.path.expanduser("~/0dte/logs/update_status.json")
        
    def is_trading_day(self, date=None):
        """Check if today is a trading day"""
        if date is None:
            date = datetime.now()
        
        # Skip weekends
        if date.weekday() >= 5:
            return False
        
        # List of US market holidays for 2025-2026
        holidays = [
            "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
            "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01",
            "2025-11-27", "2025-12-25",
            "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
            "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
            "2026-11-26", "2026-12-25"
        ]
        
        date_str = date.strftime("%Y-%m-%d")
        return date_str not in holidays
    
    def check_thetadata_running(self):
        """Check if ThetaData Terminal is running"""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            return 'ThetaTerminal' in result.stdout
        except:
            return False
    
    def start_thetadata(self):
        """Attempt to start ThetaData Terminal"""
        logger.info("Attempting to start ThetaData Terminal...")
        
        # Path to ThetaData
        thetadata_path = os.path.expanduser("~/Desktop/ThetaDataTerminalV2")
        
        if os.path.exists(thetadata_path):
            try:
                # Start ThetaData in background
                subprocess.Popen(
                    ['java', '-jar', 'ThetaTerminalV3.jar'],
                    cwd=thetadata_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                
                # Wait for it to start
                time.sleep(10)
                
                # Check if it's running
                if self.check_thetadata_running():
                    logger.info("✅ ThetaData Terminal started successfully")
                    return True
                else:
                    logger.error("❌ Failed to start ThetaData Terminal")
                    return False
                    
            except Exception as e:
                logger.error(f"Error starting ThetaData: {e}")
                return False
        else:
            logger.error(f"ThetaData not found at {thetadata_path}")
            return False
    
    def test_api_connection(self):
        """Test if ThetaData API is responding"""
        try:
            response = requests.get("http://localhost:25503/v3/", timeout=5)
            return True
        except:
            return False
    
    def get_today_date(self):
        """Get today's date in YYYYMMDD format"""
        return datetime.now().strftime("%Y%m%d")
    
    def update_today(self):
        """Download today's 0DTE data"""
        today = self.get_today_date()
        logger.info(f"Updating Zero DTE data for {today}")
        
        try:
            # Download today's data
            records = self.db.download_zero_dte_options_for_date(today)
            
            if records > 0:
                logger.info(f"✅ Successfully downloaded {records:,} records for {today}")
                return True, records
            else:
                logger.warning(f"No 0DTE data found for {today}")
                return False, 0
                
        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            return False, 0
    
    def save_status(self, success, records=0, error=None):
        """Save update status for monitoring"""
        status = {
            "last_update": datetime.now().isoformat(),
            "date": self.get_today_date(),
            "success": success,
            "records": records,
            "error": str(error) if error else None,
            "database_stats": {
                "total_days": self.db.metadata['total_days'],
                "total_records": self.db.metadata['total_records']
            }
        }
        
        with open(self.notification_file, 'w') as f:
            json.dump(status, f, indent=2)
    
    def run_update(self):
        """Main update process"""
        logger.info("="*60)
        logger.info("ZERO DTE DAILY UPDATE")
        logger.info("="*60)
        
        # Check if it's a trading day
        if not self.is_trading_day():
            logger.info("Not a trading day, skipping update")
            self.save_status(True, 0, "Not a trading day")
            return
        
        # Check if already updated today
        today = self.get_today_date()
        today_file = os.path.join(self.db.data_dir, today, f"zero_dte_spy_{today}.parquet")
        
        if os.path.exists(today_file):
            logger.info(f"Data for {today} already exists, skipping")
            self.save_status(True, 0, "Already updated")
            return
        
        # Check ThetaData
        if not self.check_thetadata_running():
            logger.warning("ThetaData Terminal not running")
            if not self.start_thetadata():
                self.save_status(False, 0, "Could not start ThetaData")
                return
        
        # Wait for API to be ready
        max_attempts = 30
        for i in range(max_attempts):
            if self.test_api_connection():
                logger.info("✅ API connection established")
                break
            time.sleep(2)
        else:
            logger.error("API not responding after 60 seconds")
            self.save_status(False, 0, "API not responding")
            return
        
        # Perform update
        success, records = self.update_today()
        
        if success:
            self.save_status(True, records)
            logger.info("✅ Daily update completed successfully")
            
            # Show summary
            logger.info(f"\nDatabase Summary:")
            logger.info(f"  Total days: {self.db.metadata['total_days']}")
            logger.info(f"  Total records: {self.db.metadata['total_records']:,}")
        else:
            self.save_status(False, 0, "Download failed")
            logger.error("❌ Daily update failed")
        
        logger.info("="*60)


def main():
    """Run the daily update"""
    updater = ZeroDTEDailyUpdater()
    
    try:
        updater.run_update()
    except Exception as e:
        logger.error(f"Update failed with error: {e}")
        updater.save_status(False, 0, str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()