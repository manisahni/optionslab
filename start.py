#!/usr/bin/env python3
"""
Simple OptionsLab Startup Script
Launches all services automatically with proper error handling
"""

import subprocess
import time
import sys
import os
import signal
import requests
from pathlib import Path

class OptionsLabStarter:
    def __init__(self):
        self.processes = []
        self.ports = {
            'backend': 8000,
            'ai_service': 8001,
            'gradio': 7860
        }
        
    def check_port_available(self, port):
        """Check if a port is available"""
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=1)
            return response.status_code == 200
        except:
            return False
    
    def kill_process_on_port(self, port):
        """Kill any process using the specified port"""
        try:
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(['kill', '-9', pid])
                        print(f"✅ Killed process {pid} on port {port}")
        except Exception as e:
            print(f"⚠️ Could not kill process on port {port}: {e}")
    
    def start_backend(self):
        """Start the FastAPI backend server"""
        print("🚀 Starting Backend Server...")
        try:
            process = subprocess.Popen(
                [sys.executable, "backend.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes.append(('backend', process))
            
            # Wait for backend to start
            for i in range(10):
                time.sleep(1)
                if self.check_port_available(self.ports['backend']):
                    print("✅ Backend server is running on http://localhost:8000")
                    return True
                print(f"⏳ Waiting for backend... ({i+1}/10)")
            
            print("❌ Backend failed to start")
            return False
            
        except Exception as e:
            print(f"❌ Error starting backend: {e}")
            return False
    
    def start_ai_service(self):
        """Start the AI service"""
        print("🤖 Starting AI Service...")
        try:
            process = subprocess.Popen(
                [sys.executable, "ai_service.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes.append(('ai_service', process))
            
            # Wait for AI service to start
            for i in range(10):
                time.sleep(1)
                try:
                    response = requests.get(f"http://localhost:{self.ports['ai_service']}/status", timeout=2)
                    if response.status_code == 200:
                        print("✅ AI service is running on http://localhost:8001")
                        return True
                except:
                    pass
                print(f"⏳ Waiting for AI service... ({i+1}/10)")
            
            print("❌ AI service failed to start")
            return False
            
        except Exception as e:
            print(f"❌ Error starting AI service: {e}")
            return False
    
    def start_gradio(self):
        """Start the Gradio frontend"""
        print("📊 Starting Gradio Frontend...")
        try:
            process = subprocess.Popen(
                [sys.executable, "simple_gradio_app.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes.append(('gradio', process))
            
            # Wait for Gradio to start
            for i in range(15):
                time.sleep(1)
                try:
                    response = requests.get(f"http://localhost:{self.ports['gradio']}", timeout=2)
                    if response.status_code == 200:
                        print("✅ Gradio frontend is running on http://localhost:7860")
                        return True
                except:
                    pass
                print(f"⏳ Waiting for Gradio... ({i+1}/15)")
            
            print("❌ Gradio failed to start")
            return False
            
        except Exception as e:
            print(f"❌ Error starting Gradio: {e}")
            return False
    
    def check_dependencies(self):
        """Check if required files exist"""
        required_files = [
            "backend.py",
            "ai_service.py", 
            "simple_gradio_app.py",
            "simple_ai_system.py",
            "backtest_engine.py"
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
        
        if missing_files:
            print(f"❌ Missing required files: {', '.join(missing_files)}")
            return False
        
        print("✅ All required files found")
        return True
    
    def cleanup_ports(self):
        """Clean up any processes using our ports"""
        print("🧹 Cleaning up ports...")
        for service, port in self.ports.items():
            self.kill_process_on_port(port)
    
    def start_all(self):
        """Start all services"""
        print("🎯 Starting OptionsLab...")
        print("=" * 50)
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Clean up ports
        self.cleanup_ports()
        
        # Start services in order
        services = [
            ('Backend', self.start_backend),
            ('AI Service', self.start_ai_service),
            ('Gradio', self.start_gradio)
        ]
        
        for name, start_func in services:
            if not start_func():
                print(f"❌ Failed to start {name}")
                self.cleanup()
                return False
        
        print("=" * 50)
        print("🎉 OptionsLab is ready!")
        print("📊 Frontend: http://localhost:7860")
        print("🔧 Backend API: http://localhost:8000")
        print("🤖 AI Service: http://localhost:8001")
        print("\nPress Ctrl+C to stop all services")
        
        return True
    
    def cleanup(self):
        """Clean up all processes"""
        print("\n🛑 Stopping all services...")
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ Stopped {name}")
            except:
                try:
                    process.kill()
                    print(f"🔪 Force killed {name}")
                except:
                    pass
        
        self.cleanup_ports()
        print("✅ Cleanup complete")

def signal_handler(signum, frame):
    """Handle Ctrl+C"""
    print("\n🛑 Received interrupt signal")
    if hasattr(signal_handler, 'starter'):
        signal_handler.starter.cleanup()
    sys.exit(0)

def main():
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create starter
    starter = OptionsLabStarter()
    signal_handler.starter = starter
    
    # Start all services
    if starter.start_all():
        try:
            # Keep running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print("❌ Failed to start OptionsLab")
        sys.exit(1)

if __name__ == "__main__":
    main() 