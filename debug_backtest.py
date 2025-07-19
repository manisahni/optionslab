#!/usr/bin/env python3
"""
Simple Backtest Debug Runner
Runs backtests and captures all errors to help with debugging
"""

import sys
import traceback
from datetime import datetime
from pathlib import Path
import subprocess
import argparse

def run_backtest_debug(config_path):
    """Run backtest and capture all output and errors"""
    
    # Create debug log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("debug_logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"backtest_debug_{timestamp}.log"
    
    print(f"🔍 Starting backtest debug for: {config_path}")
    print(f"📝 Log file: {log_file}")
    print("-" * 50)
    
    # Run the backtest and capture output
    try:
        # Run the actual backtest with proper Python import
        # Create a small runner script to properly import and run the backtest
        runner_code = f"""
import sys
sys.path.insert(0, 'optionslab')
from auditable_backtest import run_auditable_backtest

# Run the backtest
data_dir = "spy_options_downloader/spy_options_parquet"
config_file = "{config_path}"
start_date = "2022-01-01"
end_date = "2022-12-31"

print(f"Running backtest with config: {config_path}")
results = run_auditable_backtest(data_dir, config_file, start_date, end_date)

if results:
    print(f"\\n✅ Backtest completed! Return: {{results['total_return']:.2%}}")
else:
    print("\\n❌ Backtest failed!")
    sys.exit(1)
"""
        
        # Use venv Python if available, otherwise system Python
        venv_python = Path(__file__).parent / "venv" / "bin" / "python"
        python_exe = str(venv_python) if venv_python.exists() else sys.executable
        
        result = subprocess.run(
            [python_exe, "-c", runner_code],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent  # Run from project root
        )
        
        # Write to log file
        with open(log_file, 'w') as f:
            f.write(f"Backtest Debug Log - {datetime.now()}\n")
            f.write(f"Config: {config_path}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("STDOUT:\n")
            f.write("-" * 40 + "\n")
            f.write(result.stdout)
            f.write("\n\n")
            
            f.write("STDERR:\n")
            f.write("-" * 40 + "\n")
            f.write(result.stderr)
            f.write("\n\n")
            
            f.write("Return Code: " + str(result.returncode) + "\n")
        
        # Print summary to console
        if result.returncode == 0:
            print("✅ Backtest completed successfully!")
            print(f"\nLast few lines of output:")
            print("-" * 40)
            lines = result.stdout.strip().split('\n')
            for line in lines[-10:]:
                print(line)
        else:
            print("❌ Backtest failed with errors!")
            print(f"\nError output:")
            print("-" * 40)
            print(result.stderr)
            
            # Try to extract the specific error
            stderr_lines = result.stderr.strip().split('\n')
            for line in stderr_lines:
                if "Error" in line or "error" in line or "KeyError" in line:
                    print(f"\n🔴 Main Error: {line}")
            
            # Also check stdout for errors
            if "AUDIT: Failed" in result.stdout:
                failed_lines = [l for l in result.stdout.split('\n') if "Failed" in l]
                print(f"\n🔴 Audit Failures:")
                for line in failed_lines[-5:]:
                    print(f"   {line}")
        
        print(f"\n📁 Full log saved to: {log_file}")
        return result.returncode == 0
        
    except Exception as e:
        error_msg = f"Failed to run backtest: {str(e)}\n{traceback.format_exc()}"
        print(f"❌ {error_msg}")
        
        with open(log_file, 'w') as f:
            f.write(f"Backtest Debug Log - {datetime.now()}\n")
            f.write(f"Config: {config_path}\n")
            f.write("=" * 80 + "\n\n")
            f.write("EXCEPTION:\n")
            f.write(error_msg)
        
        return False

def main():
    parser = argparse.ArgumentParser(description='Debug backtest runs')
    parser.add_argument('config', help='Path to strategy config YAML file')
    parser.add_argument('--loop', action='store_true', 
                       help='Keep running until successful (press Ctrl+C to stop)')
    
    args = parser.parse_args()
    
    if args.loop:
        attempt = 1
        while True:
            print(f"\n🔄 Attempt #{attempt}")
            success = run_backtest_debug(args.config)
            if success:
                print("\n🎉 Backtest succeeded! Stopping loop.")
                break
            else:
                print(f"\n⏳ Waiting 5 seconds before retry...")
                print("   (Press Ctrl+C to stop)")
                try:
                    import time
                    time.sleep(5)
                except KeyboardInterrupt:
                    print("\n👋 Stopped by user")
                    break
            attempt += 1
    else:
        run_backtest_debug(args.config)

if __name__ == "__main__":
    main()