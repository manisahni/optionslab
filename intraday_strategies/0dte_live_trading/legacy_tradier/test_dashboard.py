#!/usr/bin/env python3
"""Test the Gradio dashboard with data loading"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradier.dashboard.gradio_dashboard import state, create_dashboard

print("Testing dashboard initialization...")
success, msg = state.initialize()
print(f"Initialization: {msg}")

if success:
    print(f"Price history: {len(state.price_history)} points")
    print(f"Greeks history: {len(state.greeks_history)} points")
    
    if state.price_history:
        print(f"Latest price: ${state.price_history[-1]['price']:.2f}")
    
    if state.greeks_history:
        latest = state.greeks_history[-1]
        print(f"Latest Greeks: Delta={latest['delta']:.3f}, Vega={latest['vega']:.3f}")

print("\nStarting dashboard on port 7870...")
print("Visit http://localhost:7870 to view the dashboard")

# Create and launch dashboard
app = create_dashboard()
app.launch(server_name="0.0.0.0", server_port=7870, share=False)