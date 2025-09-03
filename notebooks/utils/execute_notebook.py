#!/usr/bin/env python3
"""
Papermill Notebook Execution Utility
=====================================
Execute parameterized notebooks with Papermill
"""

import papermill as pm
import argparse
import json
from pathlib import Path
from datetime import datetime
import sys


def execute_notebook(
    input_path: str,
    output_path: str = None,
    parameters: dict = None,
    kernel_name: str = None
):
    """
    Execute a notebook with Papermill
    
    Args:
        input_path: Path to input notebook (.py or .ipynb)
        output_path: Path for executed notebook (optional)
        parameters: Dictionary of parameters to inject
        kernel_name: Jupyter kernel to use (default: python3)
    
    Returns:
        Path to executed notebook
    """
    input_path = Path(input_path)
    
    # Generate output path if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"{input_path.stem}_executed_{timestamp}.ipynb"
        output_path = input_path.parent / output_name
    else:
        output_path = Path(output_path)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📓 Executing notebook: {input_path}")
    print(f"📝 Output: {output_path}")
    
    if parameters:
        print(f"⚙️ Parameters:")
        for key, value in parameters.items():
            print(f"   {key}: {value}")
    
    try:
        # Execute with Papermill
        pm.execute_notebook(
            input_path=str(input_path),
            output_path=str(output_path),
            parameters=parameters or {},
            kernel_name=kernel_name or "python3",
            progress_bar=True
        )
        
        print(f"✅ Execution complete: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        raise


def main():
    """Command-line interface for notebook execution"""
    parser = argparse.ArgumentParser(
        description="Execute notebooks with Papermill"
    )
    
    parser.add_argument(
        "input",
        help="Input notebook path (.py or .ipynb)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output notebook path (default: auto-generated)"
    )
    
    parser.add_argument(
        "-p", "--parameters",
        action="append",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Parameter key-value pairs"
    )
    
    parser.add_argument(
        "-f", "--param-file",
        help="JSON file with parameters"
    )
    
    parser.add_argument(
        "-k", "--kernel",
        default="python3",
        help="Jupyter kernel name (default: python3)"
    )
    
    args = parser.parse_args()
    
    # Build parameters dictionary
    parameters = {}
    
    # Add parameters from command line
    if args.parameters:
        for key, value in args.parameters:
            # Try to parse as JSON for complex types
            try:
                parameters[key] = json.loads(value)
            except json.JSONDecodeError:
                # Keep as string if not valid JSON
                parameters[key] = value
    
    # Add parameters from file
    if args.param_file:
        with open(args.param_file) as f:
            file_params = json.load(f)
            parameters.update(file_params)
    
    # Execute notebook
    try:
        output_path = execute_notebook(
            input_path=args.input,
            output_path=args.output,
            parameters=parameters,
            kernel_name=args.kernel
        )
        
        print(f"\n🎉 Success! Output saved to: {output_path}")
        return 0
        
    except Exception as e:
        print(f"\n💥 Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())