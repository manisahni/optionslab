#!/usr/bin/env python3
import gradio as gr

def test_function(x):
    return f"Hello {x}!"

print("🚀 Creating test interface...")
iface = gr.Interface(fn=test_function, inputs="text", outputs="text")
print("✅ Interface created, launching on port 7861...")
iface.launch(server_port=7861, show_error=True) 