"""
Data loading utilities for backtesting
Handles parquet data loading and strategy configuration
"""

import pandas as pd
import yaml
from pathlib import Path
from typing import Optional, Union


def load_data(data_source: Union[str, Path], start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Unified data loading function for files or directories
    
    Args:
        data_source: Path to data file or directory
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        DataFrame with options data or None if loading fails
    """
    print(f"🔍 AUDIT: Loading data from {data_source}")
    
    data_path = Path(data_source)
    
    # Detect if it's a directory or file
    if data_path.is_dir():
        print(f"📅 AUDIT: Multi-day mode - loading from {start_date} to {end_date}")
        return _load_multi_day_data(data_path, start_date, end_date)
    else:
        print(f"📄 AUDIT: Single-file mode")
        return _load_single_file(data_path, start_date, end_date)


def _load_single_file(file_path: Path, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Load and filter single parquet file
    
    Args:
        file_path: Path to parquet file
        start_date: Start date for filtering
        end_date: End date for filtering
        
    Returns:
        Filtered DataFrame or None if loading fails
    """
    try:
        df = pd.read_parquet(file_path)
        print(f"✅ AUDIT: Loaded {len(df)} records")
    except Exception as e:
        try:
            print(f"⚠️ AUDIT: Default parser failed, trying fastparquet...")
            df = pd.read_parquet(file_path, engine='fastparquet')
            print(f"✅ AUDIT: Loaded {len(df)} records with fastparquet")
        except Exception as e2:
            print(f"❌ AUDIT: Failed to load data: {e2}")
            return None
    
    # Audit the data
    print(f"📊 AUDIT: Columns: {list(df.columns)}")
    print(f"📅 AUDIT: Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Filter to date range
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    if df['date'].dtype == 'object':
        df['date'] = pd.to_datetime(df['date'])
    
    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
    print(f"✅ AUDIT: Filtered to {len(df)} rows in date range")
    
    return df


def _load_multi_day_data(data_dir: Path, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Load multiple days of parquet data from directory
    
    Args:
        data_dir: Directory containing parquet files
        start_date: Start date for loading
        end_date: End date for loading
        
    Returns:
        Combined DataFrame or None if no data found
    """
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    all_data = []
    files_loaded = 0
    
    # Search both main and repaired directories
    for subdir in ['', 'repaired']:
        search_path = data_dir / subdir if subdir else data_dir
        if not search_path.exists():
            continue
            
        for file in sorted(search_path.glob("spy_options_eod_*.parquet")):
            # Extract date from filename
            date_str = file.stem.split('_')[-1]
            try:
                file_date = pd.to_datetime(date_str, format='%Y%m%d')
                
                if start_dt <= file_date <= end_dt:
                    print(f"\n📁 AUDIT: Loading {file_date.strftime('%Y-%m-%d')}")
                    
                    try:
                        df = pd.read_parquet(file)
                        print(f"✅ AUDIT: Loaded {len(df)} records")
                    except Exception:
                        try:
                            print(f"⚠️ AUDIT: Trying fastparquet...")
                            df = pd.read_parquet(file, engine='fastparquet')
                            print(f"✅ AUDIT: Loaded {len(df)} records")
                        except Exception as e:
                            print(f"❌ AUDIT: Failed to load {file.name}: {e}")
                            continue
                    
                    all_data.append(df)
                    files_loaded += 1
                    
            except Exception as e:
                print(f"⚠️ AUDIT: Skipping {file.name}: {e}")
    
    if not all_data:
        print(f"❌ AUDIT: No data files found for date range")
        return None
    
    # Combine all dataframes
    print(f"\n🔄 AUDIT: Combining {files_loaded} files...")
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values('date').reset_index(drop=True)
    
    print(f"✅ AUDIT: Combined: {len(combined_df)} records")
    print(f"📅 AUDIT: Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    
    return combined_df


def load_strategy_config(config_path: Union[str, Path]) -> Optional[dict]:
    """Load and validate strategy configuration from YAML file
    
    Args:
        config_path: Path to strategy YAML file
        
    Returns:
        Strategy configuration dict or None if loading fails
    """
    print(f"🔍 AUDIT: Loading strategy config from {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"✅ AUDIT: Strategy: {config['name']}")
        print(f"📝 AUDIT: Type: {config['strategy_type']}")
        print(f"💰 AUDIT: Capital: ${config['parameters']['initial_capital']:,.2f}")
        
        # Validate required fields
        required_fields = ['name', 'strategy_type', 'parameters', 'option_selection']
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            print(f"❌ AUDIT: Missing required fields: {missing_fields}")
            return None
            
        # Validate option_selection has mandatory delta/DTE criteria
        option_selection = config.get('option_selection', {})
        if 'delta_criteria' not in option_selection or 'dte_criteria' not in option_selection:
            print(f"❌ AUDIT: Strategy must have delta_criteria and dte_criteria in option_selection")
            return None
        
        return config
    except Exception as e:
        print(f"❌ AUDIT: Failed to load config: {e}")
        return None