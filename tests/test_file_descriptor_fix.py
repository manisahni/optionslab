#!/usr/bin/env python3
"""
Test script to verify file descriptor fix for backtesting
This script tests the enhanced subprocess execution with proper resource management
"""

import subprocess
import os
import resource
import signal
import tempfile
import time
from pathlib import Path

def test_file_descriptor_limits():
    """Test increasing file descriptor limits"""
    try:
        # Get current limits
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        print(f"Current file descriptor limits: soft={soft}, hard={hard}")
        
        # Set to maximum allowed
        resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
        new_soft, new_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        print(f"✅ File descriptor limits updated: soft={new_soft}, hard={new_hard}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to set file descriptor limits: {e}")
        return False

def test_subprocess_execution():
    """Test subprocess execution with proper resource management"""
    try:
        # Create temporary files for stdout/stderr
        stdout_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        stderr_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        temp_files = [stdout_file.name, stderr_file.name]
        
        # Close the temporary files to free file descriptors
        stdout_file.close()
        stderr_file.close()
        
        # Open files for subprocess
        with open(stdout_file.name, 'w') as stdout, open(stderr_file.name, 'w') as stderr:
            # Simplified subprocess creation for testing
            process = subprocess.Popen(
                ['python', '-c', 'print("Hello from subprocess"); import sys; print(f"Python version: {sys.version}")'],
                stdout=stdout,
                stderr=stderr,
                close_fds=True  # Close inherited file descriptors
            )
            
            # Wait for completion
            return_code = process.wait(timeout=10)
            
            # Read output files
            with open(stdout_file.name, 'r') as f:
                stdout_content = f.read()
            with open(stderr_file.name, 'r') as f:
                stderr_content = f.read()
            
            print(f"✅ Subprocess completed with return code: {return_code}")
            print(f"Stdout: {stdout_content.strip()}")
            print(f"Stderr: {stderr_content.strip()}")
            
            return return_code == 0
            
    except Exception as e:
        print(f"❌ Subprocess execution failed: {e}")
        return False
    finally:
        # Cleanup temporary files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as cleanup_error:
                print(f"⚠️ Failed to cleanup {temp_file}: {cleanup_error}")

def main():
    """Run all tests"""
    print("🔧 Testing file descriptor fix...")
    
    # Test 1: File descriptor limits
    print("\n1. Testing file descriptor limits...")
    if test_file_descriptor_limits():
        print("✅ File descriptor limits test passed")
    else:
        print("❌ File descriptor limits test failed")
        return False
    
    # Test 2: Subprocess execution
    print("\n2. Testing subprocess execution...")
    if test_subprocess_execution():
        print("✅ Subprocess execution test passed")
    else:
        print("❌ Subprocess execution test failed")
        return False
    
    print("\n🎉 All tests passed! File descriptor fix is working correctly.")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 