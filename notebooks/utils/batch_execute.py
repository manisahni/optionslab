#!/usr/bin/env python3
"""
Batch Notebook Execution with Papermill
========================================
Run notebooks with parameter sweeps for backtesting and analysis
"""

import papermill as pm
from pathlib import Path
from datetime import datetime
import pandas as pd
import json
import yaml
from typing import List, Dict, Any
import concurrent.futures
import time


def run_single_execution(
    notebook_path: str,
    parameters: dict,
    output_dir: str,
    execution_id: str
) -> Dict[str, Any]:
    """
    Execute a single notebook with given parameters
    
    Args:
        notebook_path: Path to notebook
        parameters: Parameters to inject
        output_dir: Directory for outputs
        execution_id: Unique ID for this execution
    
    Returns:
        Dictionary with execution results
    """
    notebook_path = Path(notebook_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create unique output filename
    output_file = output_dir / f"{notebook_path.stem}_{execution_id}.ipynb"
    
    start_time = time.time()
    
    try:
        # Execute notebook
        pm.execute_notebook(
            input_path=str(notebook_path),
            output_path=str(output_file),
            parameters=parameters,
            kernel_name="python3"
        )
        
        execution_time = time.time() - start_time
        
        return {
            "execution_id": execution_id,
            "status": "success",
            "parameters": parameters,
            "output_path": str(output_file),
            "execution_time": execution_time
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        return {
            "execution_id": execution_id,
            "status": "failed",
            "parameters": parameters,
            "error": str(e),
            "execution_time": execution_time
        }


def run_parameter_sweep(
    notebook_path: str,
    parameter_sets: List[Dict],
    output_dir: str = None,
    parallel: bool = False,
    max_workers: int = 4
) -> pd.DataFrame:
    """
    Run notebook with multiple parameter sets
    
    Args:
        notebook_path: Path to notebook
        parameter_sets: List of parameter dictionaries
        output_dir: Directory for outputs
        parallel: Run executions in parallel
        max_workers: Maximum parallel workers
    
    Returns:
        DataFrame with execution results
    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"results/sweep_{timestamp}"
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Starting parameter sweep")
    print(f"📓 Notebook: {notebook_path}")
    print(f"📊 Parameter sets: {len(parameter_sets)}")
    print(f"📁 Output directory: {output_dir}")
    
    results = []
    
    if parallel and len(parameter_sets) > 1:
        print(f"⚡ Running in parallel with {max_workers} workers")
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for i, params in enumerate(parameter_sets):
                execution_id = f"run_{i:04d}"
                future = executor.submit(
                    run_single_execution,
                    notebook_path,
                    params,
                    output_dir,
                    execution_id
                )
                futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                
                if result["status"] == "success":
                    print(f"✅ {result['execution_id']}: Success ({result['execution_time']:.1f}s)")
                else:
                    print(f"❌ {result['execution_id']}: Failed - {result.get('error', 'Unknown error')}")
    
    else:
        print(f"🔄 Running sequentially")
        
        for i, params in enumerate(parameter_sets):
            execution_id = f"run_{i:04d}"
            print(f"\n📝 Executing {execution_id}/{len(parameter_sets):04d}")
            print(f"   Parameters: {params}")
            
            result = run_single_execution(
                notebook_path,
                params,
                output_dir,
                execution_id
            )
            
            results.append(result)
            
            if result["status"] == "success":
                print(f"   ✅ Success ({result['execution_time']:.1f}s)")
            else:
                print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Save results summary
    summary_file = output_dir / "sweep_summary.csv"
    results_df.to_csv(summary_file, index=False)
    print(f"\n📊 Results saved to: {summary_file}")
    
    # Print summary
    success_count = len(results_df[results_df["status"] == "success"])
    fail_count = len(results_df[results_df["status"] == "failed"])
    total_time = results_df["execution_time"].sum()
    
    print(f"\n📈 Summary:")
    print(f"   Total executions: {len(results_df)}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {fail_count}")
    print(f"   Total time: {total_time:.1f}s")
    print(f"   Average time: {total_time/len(results_df):.1f}s")
    
    return results_df


def load_sweep_config(config_file: str) -> Dict[str, Any]:
    """
    Load parameter sweep configuration from YAML or JSON file
    
    Args:
        config_file: Path to configuration file
    
    Returns:
        Configuration dictionary
    """
    config_path = Path(config_file)
    
    if config_path.suffix in [".yaml", ".yml"]:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    elif config_path.suffix == ".json":
        with open(config_path) as f:
            config = json.load(f)
    else:
        raise ValueError(f"Unsupported config format: {config_path.suffix}")
    
    return config


def generate_date_ranges(
    start_year: int,
    end_year: int,
    period: str = "yearly"
) -> List[Dict[str, str]]:
    """
    Generate date range parameters for backtesting
    
    Args:
        start_year: Starting year
        end_year: Ending year
        period: Period type (yearly, quarterly, monthly)
    
    Returns:
        List of parameter dictionaries
    """
    parameter_sets = []
    
    if period == "yearly":
        for year in range(start_year, end_year + 1):
            parameter_sets.append({
                "START_DATE": f"{year}-01-01",
                "END_DATE": f"{year}-12-31",
                "PERIOD_LABEL": f"Year_{year}"
            })
    
    elif period == "quarterly":
        quarters = [
            ("Q1", "01-01", "03-31"),
            ("Q2", "04-01", "06-30"),
            ("Q3", "07-01", "09-30"),
            ("Q4", "10-01", "12-31")
        ]
        
        for year in range(start_year, end_year + 1):
            for quarter_name, start_month, end_month in quarters:
                parameter_sets.append({
                    "START_DATE": f"{year}-{start_month}",
                    "END_DATE": f"{year}-{end_month}",
                    "PERIOD_LABEL": f"{year}_{quarter_name}"
                })
    
    elif period == "monthly":
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                # Get last day of month
                if month == 12:
                    next_month = 1
                    next_year = year + 1
                else:
                    next_month = month + 1
                    next_year = year
                
                last_day = (pd.Timestamp(f"{next_year}-{next_month:02d}-01") - pd.Timedelta(days=1)).day
                
                parameter_sets.append({
                    "START_DATE": f"{year}-{month:02d}-01",
                    "END_DATE": f"{year}-{month:02d}-{last_day:02d}",
                    "PERIOD_LABEL": f"{year}_{month:02d}"
                })
    
    return parameter_sets


if __name__ == "__main__":
    # Example usage
    print("📓 Papermill Batch Execution Utility")
    print("=" * 50)
    
    # Example 1: Date range sweep
    print("\nExample 1: Date Range Sweep")
    date_params = generate_date_ranges(2022, 2024, period="yearly")
    
    for params in date_params:
        print(f"  {params['PERIOD_LABEL']}: {params['START_DATE']} to {params['END_DATE']}")
    
    # Example 2: Strategy parameter sweep
    print("\nExample 2: Strategy Parameter Sweep")
    strategy_params = [
        {"STRATEGY": "pmcc", "INITIAL_CAPITAL": 10000, "LEAP_DELTA": 0.70},
        {"STRATEGY": "pmcc", "INITIAL_CAPITAL": 10000, "LEAP_DELTA": 0.80},
        {"STRATEGY": "pmcc", "INITIAL_CAPITAL": 25000, "LEAP_DELTA": 0.75},
    ]
    
    for i, params in enumerate(strategy_params):
        print(f"  Run {i+1}: {params}")
    
    print("\nTo execute a sweep, use:")
    print("  from notebooks.utils.batch_execute import run_parameter_sweep")
    print("  results = run_parameter_sweep('notebook.py', parameter_sets)")