#!/usr/bin/env python3
"""
Enhanced CSV format for complete backtest data storage
Stores all backtest data in a single Excel-compatible CSV file
"""

import pandas as pd
import numpy as np
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import io


def save_comprehensive_csv(
    backtest_id: str,
    trades_df: pd.DataFrame,
    results: Dict,
    strategy_config: Dict,
    strategy_file_path: str,
    audit_log: Optional[str] = None
) -> str:
    """
    Save all backtest data in a single comprehensive CSV file
    
    Args:
        backtest_id: Unique identifier for the backtest
        trades_df: DataFrame containing all trade data
        results: Dictionary with backtest results
        strategy_config: Strategy configuration dictionary
        strategy_file_path: Path to the original strategy YAML file
        audit_log: Optional audit log text
        
    Returns:
        Path to the saved CSV file
    """
    # Create output directory
    logs_dir = Path(__file__).parent / "trade_logs"
    now = datetime.now()
    year_dir = logs_dir / str(now.year)
    month_dir = year_dir / f"{now.month:02d}"
    month_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename with backtest ID and memorable name
    memorable_name = results.get('memorable_name', 'backtest')
    filename = f"{backtest_id}_{memorable_name}_{now.strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = month_dir / filename
    
    # Prepare the CSV content
    csv_buffer = io.StringIO()
    
    # Write metadata header section
    csv_buffer.write("# BACKTEST METADATA\n")
    csv_buffer.write(f"# BACKTEST_ID,{backtest_id}\n")
    csv_buffer.write(f"# MEMORABLE_NAME,{memorable_name}\n")
    csv_buffer.write(f"# STRATEGY,{results.get('strategy', 'Unknown')}\n")
    csv_buffer.write(f"# STRATEGY_FILE,{strategy_file_path}\n")
    csv_buffer.write(f"# START_DATE,{results.get('start_date', '')}\n")
    csv_buffer.write(f"# END_DATE,{results.get('end_date', '')}\n")
    csv_buffer.write(f"# BACKTEST_DATE,{now.isoformat()}\n")
    csv_buffer.write(f"# INITIAL_CAPITAL,{results.get('initial_capital', 10000)}\n")
    csv_buffer.write(f"# FINAL_VALUE,{results.get('final_value', 0)}\n")
    csv_buffer.write(f"# TOTAL_RETURN,{results.get('total_return', 0):.4f}\n")
    csv_buffer.write(f"# SHARPE_RATIO,{results.get('sharpe_ratio', 0):.4f}\n")
    csv_buffer.write(f"# MAX_DRAWDOWN,{results.get('max_drawdown', 0):.4f}\n")
    csv_buffer.write(f"# WIN_RATE,{results.get('win_rate', 0):.4f}\n")
    csv_buffer.write(f"# TOTAL_TRADES,{len(trades_df)}\n")
    
    # Write compliance scorecard
    compliance = results.get('compliance_scorecard', {})
    if compliance:
        csv_buffer.write("# \n")
        csv_buffer.write("# COMPLIANCE SCORECARD\n")
        csv_buffer.write(f"# OVERALL_COMPLIANCE,{compliance.get('overall_score', 0):.2f}\n")
        csv_buffer.write(f"# DELTA_COMPLIANCE,{compliance.get('delta_compliance', 0):.2f}\n")
        csv_buffer.write(f"# DTE_COMPLIANCE,{compliance.get('dte_compliance', 0):.2f}\n")
        csv_buffer.write(f"# COMPLIANT_TRADES,{compliance.get('compliant_trades', 0)}\n")
        csv_buffer.write(f"# NON_COMPLIANT_TRADES,{compliance.get('non_compliant_trades', 0)}\n")
    
    # Write strategy configuration as key-value pairs
    csv_buffer.write("# \n")
    csv_buffer.write("# STRATEGY CONFIGURATION\n")
    _write_yaml_as_csv_rows(csv_buffer, strategy_config, "# STRATEGY_CONFIG")
    
    # Write audit log if provided
    if audit_log:
        csv_buffer.write("# \n")
        csv_buffer.write("# AUDIT LOG (Last 100 lines)\n")
        audit_lines = audit_log.strip().split('\n')[-100:]  # Last 100 lines
        for line in audit_lines:
            # Escape commas and quotes in audit log
            escaped_line = line.replace('"', '""').replace(',', ';')
            csv_buffer.write(f'# AUDIT,"{escaped_line}"\n')
    
    # Write separator before trade data
    csv_buffer.write("# \n")
    csv_buffer.write("# ===== TRADE DATA BEGINS BELOW =====\n")
    csv_buffer.write("# \n")
    
    # Prepare trade data with all necessary columns
    if not trades_df.empty:
        # Ensure all required columns exist
        trades_df = _ensure_trade_columns(trades_df)
        
        # Add backtest ID to each trade
        trades_df['backtest_id'] = backtest_id
        
        # Convert date/timestamp columns to strings
        date_columns = ['entry_date', 'exit_date', 'expiration']
        for col in date_columns:
            if col in trades_df.columns:
                trades_df[col] = trades_df[col].apply(
                    lambda x: x.isoformat() if isinstance(x, pd.Timestamp) else str(x) if pd.notna(x) else ''
                )
        
        # Convert Greeks history to JSON strings if present
        if 'greeks_history' in trades_df.columns:
            def serialize_greeks_history(x):
                if isinstance(x, (list, dict)):
                    # Convert Timestamps to strings in the data structure
                    def convert_timestamps(obj):
                        if isinstance(obj, pd.Timestamp):
                            return obj.isoformat()
                        elif isinstance(obj, dict):
                            return {k: convert_timestamps(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_timestamps(item) for item in obj]
                        else:
                            return obj
                    
                    converted = convert_timestamps(x)
                    return json.dumps(converted)
                else:
                    return str(x)
            
            trades_df['greeks_history'] = trades_df['greeks_history'].apply(serialize_greeks_history)
        
        # Write trade data
        trades_df.to_csv(csv_buffer, index=False)
    
    # Write to file
    with open(filepath, 'w') as f:
        f.write(csv_buffer.getvalue())
    
    print(f"✅ Saved comprehensive CSV: {filepath}")
    return str(filepath)


def _write_yaml_as_csv_rows(buffer: io.StringIO, data: Dict, prefix: str, level: int = 0):
    """Recursively write YAML data as CSV rows"""
    indent = "." * level
    
    for key, value in data.items():
        if isinstance(value, dict):
            buffer.write(f'{prefix},{indent}{key},<section>\n')
            _write_yaml_as_csv_rows(buffer, value, prefix, level + 1)
        elif isinstance(value, list):
            buffer.write(f'{prefix},{indent}{key},[{",".join(str(v) for v in value)}]\n')
        else:
            # Escape values that might contain commas or quotes
            str_value = str(value).replace('"', '""')
            if ',' in str_value:
                str_value = f'"{str_value}"'
            buffer.write(f'{prefix},{indent}{key},{str_value}\n')


def _ensure_trade_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all required columns exist in the trades DataFrame"""
    required_columns = [
        'trade_id', 'entry_date', 'exit_date', 'option_type', 'strike',
        'expiration', 'contracts', 'entry_price', 'exit_price',
        'entry_underlying', 'exit_underlying', 'pnl', 'pnl_pct',
        'days_held', 'exit_reason', 'entry_delta', 'exit_delta',
        'entry_iv', 'exit_iv', 'compliance_score'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            # Try to find alternative column names
            if col == 'entry_price' and 'option_price' in df.columns:
                df['entry_price'] = df['option_price']
            elif col == 'entry_underlying' and 'underlying_at_entry' in df.columns:
                df['entry_underlying'] = df['underlying_at_entry']
            elif col == 'exit_underlying' and 'underlying_at_exit' in df.columns:
                df['exit_underlying'] = df['underlying_at_exit']
            else:
                df[col] = np.nan
    
    return df


def load_comprehensive_csv(filepath: str) -> Dict:
    """
    Load a comprehensive CSV file and parse all sections
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        Dictionary containing metadata, strategy config, and trades
    """
    metadata = {}
    strategy_config = {}
    audit_log = []
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Find where trade data begins
    trade_data_start = 0
    for i, line in enumerate(lines):
        if '===== TRADE DATA BEGINS BELOW =====' in line:
            trade_data_start = i + 2  # Skip separator and empty line
            break
    
    # Parse metadata and other sections
    current_section = None
    for line in lines[:trade_data_start]:
        line = line.strip()
        if not line or line == '#':
            continue
            
        if line.startswith('# '):
            # Parse header lines
            parts = line[2:].split(',', 1)
            if len(parts) == 2:
                key, value = parts
                key = key.strip()
                value = value.strip()
                
                if key in ['BACKTEST_ID', 'MEMORABLE_NAME', 'STRATEGY', 'STRATEGY_FILE',
                          'START_DATE', 'END_DATE', 'BACKTEST_DATE']:
                    metadata[key.lower()] = value
                elif key in ['INITIAL_CAPITAL', 'FINAL_VALUE']:
                    metadata[key.lower()] = float(value)
                elif key in ['TOTAL_RETURN', 'SHARPE_RATIO', 'MAX_DRAWDOWN', 'WIN_RATE']:
                    metadata[key.lower()] = float(value)
                elif key == 'TOTAL_TRADES':
                    metadata[key.lower()] = int(value)
                elif key == 'STRATEGY_CONFIG':
                    # Parse strategy config lines
                    _parse_strategy_config_line(value, strategy_config)
                elif key == 'AUDIT':
                    audit_log.append(value.strip('"').replace('""', '"').replace(';', ','))
    
    # Load trade data
    trade_lines = ''.join(lines[trade_data_start:])
    if trade_lines.strip():
        try:
            trades_df = pd.read_csv(io.StringIO(trade_lines))
        except pd.errors.ParserError as e:
            # If there's a parsing error, try to clean up the data
            print(f"Warning: CSV parsing error, attempting to fix: {e}")
            # Remove any remaining comment lines
            clean_lines = [line for line in lines[trade_data_start:] if not line.strip().startswith('#')]
            trade_lines = ''.join(clean_lines)
            trades_df = pd.read_csv(io.StringIO(trade_lines))
        
        # Parse JSON columns
        if 'greeks_history' in trades_df.columns:
            trades_df['greeks_history'] = trades_df['greeks_history'].apply(
                lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else x
            )
    else:
        trades_df = pd.DataFrame()
    
    return {
        'metadata': metadata,
        'strategy_config': strategy_config,
        'audit_log': '\n'.join(audit_log),
        'trades': trades_df
    }


def _parse_strategy_config_line(line: str, config: Dict):
    """Parse a strategy config line into the config dictionary"""
    parts = line.split(',', 1)
    if len(parts) == 2:
        key_path, value = parts
        keys = key_path.split('.')
        
        # Navigate to the correct nested dictionary
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the value
        final_key = keys[-1]
        if value == '<section>':
            current[final_key] = {}
        elif value.startswith('[') and value.endswith(']'):
            # Parse list
            list_str = value[1:-1]
            current[final_key] = [v.strip() for v in list_str.split(',') if v.strip()]
        else:
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1].replace('""', '"')
            # Try to parse as number
            try:
                if '.' in value:
                    current[final_key] = float(value)
                else:
                    current[final_key] = int(value)
            except ValueError:
                current[final_key] = value