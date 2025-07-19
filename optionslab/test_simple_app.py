#!/usr/bin/env python3
"""
Simple test version of the auditable Gradio app
"""

import gradio as gr

def simple_backtest(data_file, strategy_file, start_date, end_date, initial_capital):
    """Simple test function"""
    return f"""
## 🧪 Test Backtest Results

**Data File:** {data_file}
**Strategy:** {strategy_file}
**Date Range:** {start_date} to {end_date}
**Initial Capital:** ${initial_capital:,.2f}

### 📊 Test Results
- **Final Value:** $10,500.00
- **Total Return:** 5.00%
- **Total Trades:** 3
- **Win Rate:** 66.67%

### 🔍 Test Audit Log
This is a test run to verify the interface is working.
"""

def create_simple_interface():
    """Create a simple test interface"""
    
    with gr.Blocks(title="OptionsLab - Test Interface") as app:
        
        gr.Markdown("# 🧪 OptionsLab - Test Interface")
        
        with gr.Row():
            with gr.Column():
                data_file = gr.Textbox(
                    label="Data File",
                    value="test_data.parquet",
                    placeholder="Enter data file path"
                )
                
                strategy_file = gr.Textbox(
                    label="Strategy File", 
                    value="test_strategy.yaml",
                    placeholder="Enter strategy file path"
                )
                
                start_date = gr.Textbox(
                    label="Start Date",
                    value="2023-01-01"
                )
                
                end_date = gr.Textbox(
                    label="End Date",
                    value="2023-12-31"
                )
                
                initial_capital = gr.Number(
                    label="Initial Capital",
                    value=10000
                )
                
                run_btn = gr.Button("🧪 Run Test Backtest")
            
            with gr.Column():
                results = gr.Markdown("**Results will appear here...**")
        
        run_btn.click(
            fn=simple_backtest,
            inputs=[data_file, strategy_file, start_date, end_date, initial_capital],
            outputs=[results]
        )
    
    return app

if __name__ == "__main__":
    print("🚀 Starting simple test app...")
    app = create_simple_interface()
    print("✅ Interface created, launching...")
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    ) 