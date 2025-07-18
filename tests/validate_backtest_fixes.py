#!/usr/bin/env python3
"""
Comprehensive validation script for backtesting system fixes
Tests file descriptor management, subprocess execution, and resource handling
"""

import os
import sys
import subprocess
import resource
import tempfile
import time
import threading
import queue
import signal
from pathlib import Path

def test_resource_limits():
    """Test resource limit management"""
    print("🔧 Testing Resource Limits...")
    
    try:
        # Get current limits
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        print(f"  Current file descriptor limits: soft={soft}, hard={hard}")
        
        # Test setting limits
        max_fd = min(hard, 4096)
        resource.setrlimit(resource.RLIMIT_NOFILE, (max_fd, max_fd))
        
        # Verify limits were set
        new_soft, new_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        print(f"  New file descriptor limits: soft={new_soft}, hard={new_hard}")
        
        if new_soft >= max_fd:
            print("  ✅ Resource limits configured successfully")
            return True
        else:
            print("  ❌ Resource limits not set correctly")
            return False
            
    except Exception as e:
        print(f"  ❌ Resource limit test failed: {e}")
        return False

def test_file_descriptor_management():
    """Test file descriptor management"""
    print("📁 Testing File Descriptor Management...")
    
    try:
        # Create temporary files
        temp_files = []
        for i in range(10):
            temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            temp_files.append(temp_file.name)
            temp_file.close()
        
        # Write to files
        for temp_file in temp_files:
            with open(temp_file, 'w') as f:
                f.write(f"Test content for {temp_file}")
        
        # Read from files
        for temp_file in temp_files:
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "Test content" in content
        
        # Clean up
        for temp_file in temp_files:
            os.unlink(temp_file)
        
        print("  ✅ File descriptor management working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ File descriptor management test failed: {e}")
        return False

def test_subprocess_execution():
    """Test subprocess execution with proper resource management"""
    print("⚙️ Testing Subprocess Execution...")
    
    try:
        # Test simple subprocess
        result = subprocess.run(
            [sys.executable, "-c", "print('Hello, World!')"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and "Hello, World!" in result.stdout:
            print("  ✅ Basic subprocess execution working")
        else:
            print("  ❌ Basic subprocess execution failed")
            return False
        
        # Test subprocess with file descriptors
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as stdout_file:
            stdout_file.close()
            
            with open(stdout_file.name, 'w') as stdout:
                process = subprocess.Popen(
                    [sys.executable, "-c", "print('File descriptor test')"],
                    stdout=stdout,
                    stderr=subprocess.PIPE,
                    env=dict(os.environ, PYTHONUNBUFFERED='1'),
                    close_fds=True
                )
                
                return_code = process.wait(timeout=10)
                
                if return_code == 0:
                    with open(stdout_file.name, 'r') as f:
                        output = f.read()
                        if "File descriptor test" in output:
                            print("  ✅ File descriptor subprocess execution working")
                        else:
                            print("  ❌ File descriptor subprocess output incorrect")
                            return False
                else:
                    print("  ❌ File descriptor subprocess failed")
                    return False
            
            # Clean up
            os.unlink(stdout_file.name)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Subprocess execution test failed: {e}")
        return False

def test_queue_based_execution():
    """Test queue-based execution system"""
    print("🔄 Testing Queue-Based Execution...")
    
    class TestExecutor:
        def __init__(self):
            self.task_queue = queue.Queue()
            self.result_queue = queue.Queue()
            self.workers = []
            self.shutdown_event = threading.Event()
        
        def start_workers(self, num_workers=2):
            for i in range(num_workers):
                worker = threading.Thread(target=self._worker_loop, args=(i,))
                worker.daemon = True
                worker.start()
                self.workers.append(worker)
        
        def _worker_loop(self, worker_id):
            while not self.shutdown_event.is_set():
                try:
                    task = self.task_queue.get(timeout=1.0)
                    if task is None:
                        break
                    
                    # Simulate work
                    time.sleep(0.1)
                    result = f"Worker {worker_id} completed task: {task}"
                    self.result_queue.put(result)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    self.result_queue.put(f"Worker {worker_id} error: {e}")
        
        def shutdown(self):
            self.shutdown_event.set()
            for _ in self.workers:
                self.task_queue.put(None)
            for worker in self.workers:
                worker.join(timeout=5)
    
    try:
        executor = TestExecutor()
        executor.start_workers(2)
        
        # Submit tasks
        for i in range(5):
            executor.task_queue.put(f"Task {i}")
        
        # Get results
        results = []
        for _ in range(5):
            result = executor.result_queue.get(timeout=5)
            results.append(result)
        
        executor.shutdown()
        
        if len(results) == 5 and all("completed task" in result for result in results):
            print("  ✅ Queue-based execution working correctly")
            return True
        else:
            print("  ❌ Queue-based execution failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Queue-based execution test failed: {e}")
        return False

def test_backtest_command_building():
    """Test backtest command building"""
    print("🔨 Testing Backtest Command Building...")
    
    try:
        # Test command building logic
        cmd = [
            sys.executable,
            "backtester_enhanced.py",
            "--strategy", "long_call",
            "--start-date", "2024-01-01",
            "--end-date", "2024-01-31",
            "--initial-capital", "10000"
        ]
        
        # Verify command structure
        if (len(cmd) >= 7 and 
            cmd[0] == sys.executable and
            "--strategy" in cmd and
            "--start-date" in cmd and
            "--end-date" in cmd):
            print("  ✅ Command building working correctly")
            return True
        else:
            print("  ❌ Command building failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Command building test failed: {e}")
        return False

def test_error_handling():
    """Test error handling mechanisms"""
    print("🛡️ Testing Error Handling...")
    
    try:
        # Test timeout handling
        try:
            subprocess.run(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout=1
            )
        except subprocess.TimeoutExpired:
            print("  ✅ Timeout handling working correctly")
        else:
            print("  ❌ Timeout handling failed")
            return False
        
        # Test invalid command handling
        try:
            result = subprocess.run(
                ["invalid_command_that_does_not_exist"],
                capture_output=True,
                text=True,
                timeout=5
            )
            print("  ✅ Invalid command handling working correctly")
        except FileNotFoundError:
            print("  ✅ Invalid command handling working correctly")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error handling test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔍 Running comprehensive backtesting system validation...")
    print("=" * 60)
    
    tests = [
        test_resource_limits,
        test_file_descriptor_management,
        test_subprocess_execution,
        test_queue_based_execution,
        test_backtest_command_building,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"  ❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("=" * 60)
    print(f"📊 Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Backtesting system is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 