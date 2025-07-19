#!/usr/bin/env python3
"""
Debug version of the auditable Gradio app
"""

import gradio as gr
import traceback

def debug_backtest(data_file, strategy_file, start_date, end_date, initial_capital):
    """Debug test function"""
    return f"""
## 🐛 Debug Test Results

**Data File:** {data_file}
**Strategy:** {strategy_file}
**Date Range:** {start_date} to {end_date}
**Initial Capital:** ${initial_capital:,.2f}

### 📊 Debug Results
- **Status:** Working
- **Test:** Successful
"""

def create_debug_interface():
    """Create a debug interface"""
    
    print("🔍 Creating debug interface...")
    
    try:
        with gr.Blocks(title="OptionsLab - Debug Interface") as app:
            
            print("✅ Blocks created")
            
            gr.Markdown("# 🐛 OptionsLab - Debug Interface")
            
            with gr.Row():
                with gr.Column():
                    data_file = gr.Textbox(
                        label="Data File",
                        value="test_data.parquet"
                    )
                    
                    strategy_file = gr.Textbox(
                        label="Strategy File", 
                        value="test_strategy.yaml"
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
                    
                    run_btn = gr.Button("🐛 Run Debug Test")
                
                with gr.Column():
                    results = gr.Markdown("**Debug results will appear here...**")
            
            print("✅ Interface components created")
            
            run_btn.click(
                fn=debug_backtest,
                inputs=[data_file, strategy_file, start_date, end_date, initial_capital],
                outputs=[results]
            )
            
            print("✅ Event handlers created")
        
        print("✅ Interface creation complete")
        return app
        
    except Exception as e:
        print(f"❌ Error creating interface: {e}")
        print(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        print("🚀 Starting debug app...")
        app = create_debug_interface()
        print("✅ Interface created, launching...")
        app.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True
        )
    except Exception as e:
        print(f"❌ Error launching app: {e}")
        print(traceback.format_exc()) 