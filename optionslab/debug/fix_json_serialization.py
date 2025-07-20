#!/usr/bin/env python3
"""
Fix for JSON serialization issue with Timestamp objects
"""

import json
import pandas as pd
from datetime import datetime, date
import numpy as np

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles pandas Timestamp and numpy types"""
    def default(self, obj):
        if isinstance(obj, (pd.Timestamp, datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return super().default(obj)

def convert_timestamps_in_dict(data):
    """Recursively convert timestamps in a dictionary to strings"""
    if isinstance(data, dict):
        return {k: convert_timestamps_in_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_timestamps_in_dict(item) for item in data]
    elif isinstance(data, (pd.Timestamp, datetime, date)):
        return data.isoformat() if not pd.isna(data) else None
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.floating):
        return float(data)
    elif pd.isna(data):
        return None
    else:
        return data

# Test the fix
if __name__ == "__main__":
    # Create test data with timestamps
    test_data = {
        'date': pd.Timestamp('2024-01-01'),
        'value': np.int64(100),
        'float_val': np.float64(10.5),
        'nan_val': np.nan,
        'nested': {
            'timestamp': datetime.now(),
            'array': np.array([1, 2, 3])
        }
    }
    
    print("Original data types:")
    for k, v in test_data.items():
        print(f"{k}: {type(v)}")
    
    # Convert
    converted = convert_timestamps_in_dict(test_data)
    
    # Try to serialize
    try:
        json_str = json.dumps(converted, indent=2)
        print("\nSuccessfully serialized!")
        print(json_str)
    except Exception as e:
        print(f"\nError: {e}")