#!/usr/bin/env python3
"""Debug script to test imports and basic functionality"""

import sys
import traceback

print("=== Debugging OptionsLab App ===")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")
print("")

# Test imports
modules_to_test = [
    "gradio",
    "pandas",
    "numpy",
    "yaml",
    "matplotlib",
    "seaborn",
    "plotly"
]

print("Testing imports:")
for module in modules_to_test:
    try:
        __import__(module)
        print(f"✅ {module} - OK")
    except ImportError as e:
        print(f"❌ {module} - FAILED: {e}")

print("\nTesting local imports:")
try:
    from auditable_backtest import run_auditable_backtest
    print("✅ auditable_backtest - OK")
except Exception as e:
    print(f"❌ auditable_backtest - FAILED: {e}")
    traceback.print_exc()

try:
    from ai_assistant import AIAssistant
    print("✅ ai_assistant - OK")
except Exception as e:
    print(f"❌ ai_assistant - FAILED: {e}")
    traceback.print_exc()

try:
    from visualization import plot_pnl_curve
    print("✅ visualization - OK")
except Exception as e:
    print(f"❌ visualization - FAILED: {e}")
    traceback.print_exc()

# Test basic Gradio app
print("\nTesting basic Gradio app:")
try:
    import gradio as gr
    
    def greet(name):
        return f"Hello {name}!"
    
    demo = gr.Interface(fn=greet, inputs="text", outputs="text")
    print("✅ Gradio interface created successfully")
    
    # Try to launch on a test port
    print("\nAttempting to launch on port 7777...")
    demo.launch(server_port=7777, share=False, prevent_thread_lock=True)
    print("✅ Gradio launch successful!")
    demo.close()
    
except Exception as e:
    print(f"❌ Gradio test failed: {e}")
    traceback.print_exc()

print("\n=== Debug complete ===")