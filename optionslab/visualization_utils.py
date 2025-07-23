#!/usr/bin/env python3
"""
Utilities for visualization and AI integration
"""

import plotly.graph_objects as go
import base64
from io import BytesIO
from typing import Optional, Union, List, Dict
import traceback


def plotly_to_base64(fig: go.Figure, format: str = 'png', width: int = 1200, height: int = 800) -> Optional[str]:
    """Convert a Plotly figure to base64 encoded image
    
    Args:
        fig: Plotly figure object
        format: Image format ('png', 'jpeg', 'svg')
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        Base64 encoded image string or None if failed
    """
    try:
        # Convert to image bytes
        img_bytes = fig.to_image(format=format, width=width, height=height)
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return img_base64
        
    except Exception as e:
        # Check if it's a Chrome/Kaleido issue
        if "Chrome" in str(e) or "kaleido" in str(e).lower():
            print(f"Note: Chrome not available for image export. AI will analyze code instead.")
            # Return a placeholder or None
            return None
        else:
            print(f"Error converting Plotly figure to base64: {e}")
            traceback.print_exc()
            return None


def get_visualization_code(function_name: str) -> Optional[str]:
    """Get the source code of a visualization function for AI analysis
    
    Args:
        function_name: Name of the visualization function or chart type
        
    Returns:
        Source code as string or None if not found
    """
    try:
        import inspect
        from . import visualization
        
        # Map chart types to function names
        function_map = {
            'pnl_curve': 'plot_pnl_curve',
            'trade_markers': 'plot_trade_markers',
            'win_loss': 'plot_win_loss_distribution',
            'heatmap': 'plot_strategy_heatmap',
            'dashboard': 'create_summary_dashboard',
            'delta_histogram': 'plot_delta_histogram',
            'dte_histogram': 'plot_dte_histogram',
            'compliance_scorecard': 'plot_compliance_scorecard',
            'coverage_heatmap': 'plot_option_coverage_heatmap',
            'delta_timeline': 'plot_delta_coverage_time_series',
            'dte_timeline': 'plot_dte_coverage_time_series',
            'exit_distribution': 'plot_exit_reason_distribution',
            'exit_efficiency': 'plot_exit_efficiency_heatmap',
            'greeks_evolution': 'plot_greeks_evolution',
            'technical_indicators': 'plot_technical_indicators_dashboard'
        }
        
        # Convert chart type to function name if needed
        actual_function_name = function_map.get(function_name, function_name)
        
        # Get the function object
        func = getattr(visualization, actual_function_name, None)
        if func is None:
            return f"# Function '{actual_function_name}' not found in visualization module"
            
        # Get source code
        source = inspect.getsource(func)
        return source
        
    except Exception as e:
        print(f"Error getting visualization code: {e}")
        return f"# Error retrieving source code: {str(e)}"


def prepare_visualization_context(
    fig: go.Figure, 
    function_name: str,
    trades_sample: List[Dict],
    error_description: Optional[str] = None
) -> Dict:
    """Prepare complete context for AI visualization debugging
    
    Args:
        fig: The Plotly figure (potentially broken)
        function_name: Name of the function that created it
        trades_sample: Sample of trade data used
        error_description: Description of what's wrong
        
    Returns:
        Dictionary with all context for AI analysis
    """
    context = {
        'function_name': function_name,
        'error_description': error_description or "Please analyze this visualization for issues",
        'image_base64': plotly_to_base64(fig) if fig else None,
        'source_code': get_visualization_code(function_name),
        'trades_sample': trades_sample[:5] if trades_sample else [],  # First 5 trades
        'data_structure': {
            'columns': list(trades_sample[0].keys()) if trades_sample else [],
            'total_trades': len(trades_sample) if trades_sample else 0
        }
    }
    
    return context


def create_ai_visualization_prompt(context: Dict) -> str:
    """Create a structured prompt for AI visualization analysis
    
    Args:
        context: Context dictionary from prepare_visualization_context
        
    Returns:
        Formatted prompt string
    """
    image_note = ""
    if not context.get('image_base64'):
        image_note = "\n**Note**: Visual preview not available. Please analyze the code and data structure to identify issues.\n"
    
    prompt = f"""
Please analyze this visualization and provide improvements:

**Function**: {context['function_name']}
**Issue**: {context['error_description']}
{image_note}
**Current Implementation**:
```python
{context['source_code']}
```

**Sample Trade Data Structure**:
Columns: {context['data_structure']['columns']}
Total Trades: {context['data_structure']['total_trades']}

**Sample Trades**:
{context['trades_sample']}

Please provide:
1. Analysis of what's wrong with the current visualization based on the code and data
2. Complete corrected Python code for the function
3. Explanation of the fixes applied
"""
    
    return prompt