#!/usr/bin/env python3
"""
Alpaca Position Monitor
Real-time monitoring of options positions and P&L
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.alpaca_client import AlpacaClient
from core.greeks_calculator import GreeksCalculator
import time
from datetime import datetime
import pytz
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

class AlpacaMonitor:
    """Real-time position monitor for Alpaca"""
    
    def __init__(self, paper: bool = True):
        """Initialize monitor"""
        self.client = AlpacaClient(paper=paper)
        self.greeks_calc = GreeksCalculator()
        self.console = Console()
        self.ET = pytz.timezone('US/Eastern')
    
    def get_account_summary(self) -> Table:
        """Get account summary table"""
        account = self.client.get_account()
        
        table = Table(title="Account Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        if account:
            table.add_row("Account Number", account.get('account_number', 'N/A'))
            table.add_row("Buying Power", f"${float(account.get('buying_power', 0)):,.2f}")
            table.add_row("Portfolio Value", f"${float(account.get('portfolio_value', 0)):,.2f}")
            table.add_row("Cash", f"${float(account.get('cash', 0)):,.2f}")
            table.add_row("Day Trade Count", str(account.get('daytrade_count', 0)))
            table.add_row("Pattern Day Trader", "Yes" if account.get('pattern_day_trader') else "No")
        
        return table
    
    def get_positions_table(self) -> Table:
        """Get positions table"""
        positions = self.client.get_positions()
        
        table = Table(title="Open Positions", show_header=True)
        table.add_column("Symbol", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Qty", style="white")
        table.add_column("Entry", style="white")
        table.add_column("Current", style="white")
        table.add_column("P&L", style="green")
        table.add_column("P&L %", style="green")
        
        total_pnl = 0
        
        for pos in positions:
            symbol = pos.get('symbol', '')
            qty = int(pos.get('qty', 0))
            side = pos.get('side', '')
            avg_entry = float(pos.get('avg_entry_price', 0))
            current_price = float(pos.get('current_price', 0))
            
            # Calculate P&L
            if side == 'short':
                pnl = (avg_entry - current_price) * abs(qty) * 100  # Options are 100 shares
                pnl_pct = ((avg_entry - current_price) / avg_entry) * 100 if avg_entry > 0 else 0
            else:
                pnl = (current_price - avg_entry) * qty * 100
                pnl_pct = ((current_price - avg_entry) / avg_entry) * 100 if avg_entry > 0 else 0
            
            total_pnl += pnl
            
            # Determine type
            if len(symbol) > 10:  # Option
                pos_type = "Option"
            else:
                pos_type = "Stock"
            
            # Color code P&L
            pnl_color = "green" if pnl >= 0 else "red"
            
            table.add_row(
                symbol,
                pos_type,
                f"{qty:+d}",
                f"${avg_entry:.2f}",
                f"${current_price:.2f}",
                f"[{pnl_color}]${pnl:+.2f}[/{pnl_color}]",
                f"[{pnl_color}]{pnl_pct:+.1f}%[/{pnl_color}]"
            )
        
        if positions:
            table.add_row("", "", "", "", "", "─" * 10, "─" * 8)
            pnl_color = "green" if total_pnl >= 0 else "red"
            table.add_row(
                "TOTAL", "", "", "", "",
                f"[bold {pnl_color}]${total_pnl:+.2f}[/bold {pnl_color}]",
                ""
            )
        
        return table
    
    def get_orders_table(self) -> Table:
        """Get open orders table"""
        orders = self.client.get_orders(status="open")
        
        table = Table(title="Open Orders", show_header=True)
        table.add_column("Symbol", style="cyan")
        table.add_column("Side", style="white")
        table.add_column("Qty", style="white")
        table.add_column("Type", style="white")
        table.add_column("Limit", style="white")
        table.add_column("Status", style="yellow")
        
        for order in orders:
            table.add_row(
                order.get('symbol', ''),
                order.get('side', '').upper(),
                str(order.get('qty', 0)),
                order.get('order_type', '').upper(),
                f"${float(order.get('limit_price', 0)):.2f}" if order.get('limit_price') else "N/A",
                order.get('status', '').upper()
            )
        
        return table
    
    def get_market_status(self) -> str:
        """Get market status"""
        clock = self.client.get_market_hours()
        
        if clock:
            is_open = clock.get('is_open', False)
            next_open = clock.get('next_open', '')
            next_close = clock.get('next_close', '')
            
            if is_open:
                # Parse and format close time
                try:
                    close_time = datetime.fromisoformat(next_close.replace('Z', '+00:00'))
                    close_et = close_time.astimezone(self.ET)
                    time_to_close = (close_et - datetime.now(self.ET)).total_seconds() / 60
                    
                    return f"🟢 MARKET OPEN (Closes in {time_to_close:.0f} min at {close_et.strftime('%I:%M %p ET')})"
                except:
                    return "🟢 MARKET OPEN"
            else:
                # Parse and format open time
                try:
                    open_time = datetime.fromisoformat(next_open.replace('Z', '+00:00'))
                    open_et = open_time.astimezone(self.ET)
                    return f"🔴 MARKET CLOSED (Opens {open_et.strftime('%m/%d %I:%M %p ET')})"
                except:
                    return "🔴 MARKET CLOSED"
        
        return "⚠️ MARKET STATUS UNKNOWN"
    
    def get_spy_quote(self) -> str:
        """Get SPY quote"""
        quote = self.client.get_stock_quote("SPY")
        
        if quote:
            bid = quote.get('bp', 0)
            ask = quote.get('ap', 0)
            mid = (bid + ask) / 2
            return f"SPY: ${mid:.2f} (Bid: ${bid:.2f}, Ask: ${ask:.2f})"
        
        return "SPY: N/A"
    
    def create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()
        
        # Get current time
        now = datetime.now(self.ET)
        time_str = now.strftime('%Y-%m-%d %H:%M:%S ET')
        
        # Create panels
        header = Panel(
            f"[bold cyan]Alpaca Live Monitor[/bold cyan]\n"
            f"[white]{time_str}[/white]\n"
            f"{self.get_market_status()}\n"
            f"{self.get_spy_quote()}",
            title="System Status",
            border_style="cyan"
        )
        
        # Split layout
        layout.split_column(
            Layout(header, size=7),
            Layout(name="main")
        )
        
        # Add tables to main section
        layout["main"].split_row(
            Layout(self.get_account_summary()),
            Layout(name="right")
        )
        
        layout["right"].split_column(
            Layout(self.get_positions_table()),
            Layout(self.get_orders_table())
        )
        
        return layout
    
    def run(self):
        """Run the monitor"""
        self.console.print("[bold cyan]Starting Alpaca Monitor...[/bold cyan]")
        self.console.print(f"Mode: [yellow]{'PAPER' if self.client.paper else 'LIVE'}[/yellow] Trading\n")
        
        with Live(self.create_layout(), refresh_per_second=0.5, console=self.console) as live:
            try:
                while True:
                    live.update(self.create_layout())
                    time.sleep(2)
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Monitor stopped.[/yellow]")

if __name__ == "__main__":
    # Check if rich is installed
    try:
        from rich import print
    except ImportError:
        print("Installing required package: rich")
        os.system("/opt/homebrew/bin/python3.11 -m pip install rich")
    
    # Run monitor
    monitor = AlpacaMonitor(paper=True)
    monitor.run()