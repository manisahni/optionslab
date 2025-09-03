"""
Gradio UI Component for Backtest Results Viewer
Integrates with the existing OptionsLab Gradio interface
"""

import gradio as gr
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import sys
sys.path.append('/Users/nish_macbook/trading/daily-optionslab')

from backtests.backtest_manager import BacktestManager


class BacktestResultsViewer:
    """Gradio component for viewing and managing backtest results"""
    
    def __init__(self):
        self.manager = BacktestManager()
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface for backtest results"""
        
        with gr.Blocks(title="Backtest Results Manager") as interface:
            gr.Markdown("# 📊 Backtest Results Manager")
            gr.Markdown("View, compare, and analyze your backtest results")
            
            with gr.Tabs():
                # Tab 1: View Results
                with gr.Tab("View Results"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            # Results list
                            refresh_btn = gr.Button("🔄 Refresh List", scale=0)
                            results_dropdown = gr.Dropdown(
                                label="Select Backtest",
                                choices=self._get_backtest_choices(),
                                value=None,
                                interactive=True
                            )
                            
                            # Filter options
                            gr.Markdown("### Filters")
                            strategy_filter = gr.Dropdown(
                                label="Strategy Type",
                                choices=["All"] + self._get_strategy_types(),
                                value="All",
                                interactive=True
                            )
                            
                        with gr.Column(scale=2):
                            # Results display
                            result_display = gr.Markdown("Select a backtest to view details")
                            metrics_display = gr.JSON(label="Metrics")
                            audit_log_display = gr.Textbox(
                                label="Audit Log (Last 50 Lines)",
                                lines=20,
                                max_lines=30,
                                interactive=False
                            )
                
                # Tab 2: Compare Results
                with gr.Tab("Compare Results"):
                    with gr.Row():
                        with gr.Column():
                            compare_selector = gr.CheckboxGroup(
                                label="Select Backtests to Compare",
                                choices=self._get_backtest_choices(),
                                value=[]
                            )
                            compare_btn = gr.Button("📊 Generate Comparison", variant="primary")
                        
                        with gr.Column():
                            comparison_table = gr.Dataframe(
                                label="Comparison Table",
                                interactive=False
                            )
                            comparison_chart = gr.Plot(label="Comparison Chart")
                
                # Tab 3: Run New Backtest
                with gr.Tab("Run New Backtest"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### Backtest Configuration")
                            
                            config_file = gr.Dropdown(
                                label="Strategy Config",
                                choices=self._get_config_files(),
                                value=None
                            )
                            
                            start_date = gr.Textbox(
                                label="Start Date (YYYY-MM-DD)",
                                value="2024-01-01"
                            )
                            
                            end_date = gr.Textbox(
                                label="End Date (YYYY-MM-DD)",
                                value="2024-03-31"
                            )
                            
                            description = gr.Textbox(
                                label="Description (Optional)",
                                placeholder="Enter a description for this backtest run"
                            )
                            
                            run_btn = gr.Button("🚀 Run Backtest", variant="primary")
                            
                        with gr.Column():
                            run_status = gr.Markdown("### Status\nReady to run backtest")
                            run_output = gr.Textbox(
                                label="Execution Log",
                                lines=20,
                                max_lines=30,
                                interactive=False
                            )
                
                # Tab 4: Summary Statistics
                with gr.Tab("Summary Statistics"):
                    summary_btn = gr.Button("📈 Update Summary", variant="primary")
                    summary_display = gr.JSON(label="System Statistics")
                    
                    with gr.Row():
                        total_backtests = gr.Number(label="Total Backtests", interactive=False)
                        avg_return = gr.Number(label="Average Return (%)", interactive=False)
                        best_return = gr.Number(label="Best Return (%)", interactive=False)
                        worst_return = gr.Number(label="Worst Return (%)", interactive=False)
            
            # Event handlers
            refresh_btn.click(
                fn=self._refresh_dropdown,
                outputs=[results_dropdown, compare_selector]
            )
            
            results_dropdown.change(
                fn=self._display_result,
                inputs=[results_dropdown],
                outputs=[result_display, metrics_display, audit_log_display]
            )
            
            strategy_filter.change(
                fn=self._filter_by_strategy,
                inputs=[strategy_filter],
                outputs=[results_dropdown]
            )
            
            compare_btn.click(
                fn=self._compare_results,
                inputs=[compare_selector],
                outputs=[comparison_table, comparison_chart]
            )
            
            run_btn.click(
                fn=self._run_backtest,
                inputs=[config_file, start_date, end_date, description],
                outputs=[run_status, run_output, results_dropdown]
            )
            
            summary_btn.click(
                fn=self._update_summary,
                outputs=[summary_display, total_backtests, avg_return, best_return, worst_return]
            )
        
        return interface
    
    def _get_backtest_choices(self) -> List[str]:
        """Get list of backtest choices for dropdown"""
        backtests = self.manager.list_backtests()
        choices = []
        for bt in backtests:
            label = f"{bt['result_id']} - {bt['strategy_name']} ({bt['start_date']} to {bt['end_date']})"
            if 'total_return' in bt.get('metrics', {}):
                label += f" [{bt['metrics']['total_return']:.1f}%]"
            choices.append(label)
        return choices
    
    def _get_strategy_types(self) -> List[str]:
        """Get unique strategy types"""
        backtests = self.manager.list_backtests()
        types = list(set(bt['strategy_type'] for bt in backtests))
        return sorted(types)
    
    def _get_config_files(self) -> List[str]:
        """Get available config files"""
        import os
        config_dir = "config"
        if os.path.exists(config_dir):
            configs = [f"config/{f}" for f in os.listdir(config_dir) if f.endswith('.yaml')]
            return sorted(configs)
        return []
    
    def _refresh_dropdown(self):
        """Refresh the dropdown choices"""
        choices = self._get_backtest_choices()
        return gr.Dropdown(choices=choices), gr.CheckboxGroup(choices=choices)
    
    def _display_result(self, selection: str) -> tuple:
        """Display selected backtest result"""
        if not selection:
            return "Select a backtest to view details", {}, ""
        
        # Extract result_id from selection
        result_id = selection.split(" - ")[0]
        
        backtest = self.manager.get_backtest(result_id)
        if not backtest:
            return "Backtest not found", {}, ""
        
        # Format display
        metadata = backtest['metadata']
        metrics = backtest['results']['metrics']
        
        display_text = f"""
### {metadata['strategy_name']}
- **Type**: {metadata['strategy_type']}
- **Period**: {metadata['start_date']} to {metadata['end_date']}
- **Run Date**: {metadata['timestamp']}
- **Description**: {metadata.get('description', 'N/A')}
"""
        
        # Get last 50 lines of audit log
        audit_lines = backtest['audit_log'].split('\n')
        audit_snippet = '\n'.join(audit_lines[-50:])
        
        return display_text, metrics, audit_snippet
    
    def _filter_by_strategy(self, strategy_type: str):
        """Filter results by strategy type"""
        if strategy_type == "All":
            backtests = self.manager.list_backtests()
        else:
            backtests = self.manager.list_backtests(strategy_type=strategy_type)
        
        choices = []
        for bt in backtests:
            label = f"{bt['result_id']} - {bt['strategy_name']} ({bt['start_date']} to {bt['end_date']})"
            if 'total_return' in bt.get('metrics', {}):
                label += f" [{bt['metrics']['total_return']:.1f}%]"
            choices.append(label)
        
        return gr.Dropdown(choices=choices)
    
    def _compare_results(self, selections: List[str]):
        """Compare selected backtests"""
        if not selections or len(selections) < 2:
            return pd.DataFrame({"Message": ["Select at least 2 backtests to compare"]}), go.Figure()
        
        # Extract result IDs
        result_ids = [s.split(" - ")[0] for s in selections]
        
        # Get comparison data
        comparison_df = self.manager.compare_backtests(result_ids)
        comparison_chart = self.manager.create_comparison_chart(result_ids)
        
        return comparison_df, comparison_chart
    
    def _run_backtest(self, config_file: str, start_date: str, end_date: str, description: str):
        """Run a new backtest"""
        if not config_file:
            return "### ❌ Error\nPlease select a configuration file", "", gr.Dropdown()
        
        status_text = f"### 🔄 Running Backtest\nStrategy: {config_file}\nPeriod: {start_date} to {end_date}"
        
        try:
            # Capture output
            import io
            from contextlib import redirect_stdout
            
            output_capture = io.StringIO()
            
            with redirect_stdout(output_capture):
                result = self.manager.run_backtest(
                    config_file=config_file,
                    start_date=start_date,
                    end_date=end_date,
                    description=description
                )
            
            output_text = output_capture.getvalue()
            
            if result['success']:
                status_text = f"### ✅ Backtest Complete\nResult ID: {result['result_id']}"
                if result.get('metrics'):
                    status_text += f"\nTotal Return: {result['metrics'].get('total_return', 'N/A')}%"
            else:
                status_text = f"### ❌ Backtest Failed\nError: {result.get('error', 'Unknown error')}"
            
            # Refresh dropdown
            new_choices = self._get_backtest_choices()
            
            return status_text, output_text, gr.Dropdown(choices=new_choices)
            
        except Exception as e:
            return f"### ❌ Error\n{str(e)}", str(e), gr.Dropdown()
    
    def _update_summary(self):
        """Update summary statistics"""
        stats = self.manager.get_summary_stats()
        
        total = stats.get('total_backtests', 0)
        avg_return = stats.get('average_return', 0)
        
        best_return = 0
        if stats.get('best_performing'):
            best_return = stats['best_performing']['return']
        
        worst_return = 0
        if stats.get('worst_performing'):
            worst_return = stats['worst_performing']['return']
        
        return stats, total, avg_return, best_return, worst_return


def create_standalone_app():
    """Create a standalone Gradio app for testing"""
    viewer = BacktestResultsViewer()
    interface = viewer.create_interface()
    return interface


if __name__ == "__main__":
    # Launch standalone for testing
    app = create_standalone_app()
    app.launch(server_name="0.0.0.0", server_port=7863, share=False)