"""Backtest export service for PDF and CSV."""
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID


class BacktestExporter:
    """Export backtest results to PDF and CSV formats."""

    def export_to_csv(self, results: Dict[str, Any]) -> str:
        """Export backtest results to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["EasyTradingApp - Backtest Report"])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow([])

        summary = results.get("summary", {})
        writer.writerow(["Summary Metrics"])
        writer.writerow(["Metric", "Value"])
        
        metrics = [
            ("Total Trades", summary.get("total_trades", 0)),
            ("Winning Trades", summary.get("winning_trades", 0)),
            ("Losing Trades", summary.get("losing_trades", 0)),
            ("Win Rate", f"{summary.get('win_rate', 0):.2f}%"),
            ("Total Return", f"₹{summary.get('total_return', 0):.2f}"),
            ("Total Return %", f"{summary.get('total_return_pct', 0):.2f}%"),
            ("Sharpe Ratio", f"{summary.get('sharpe_ratio', 0):.2f}"),
            ("Max Drawdown", f"₹{summary.get('max_drawdown', 0):.2f}"),
            ("Max Drawdown %", f"{summary.get('max_drawdown_pct', 0):.2f}%"),
            ("Profit Factor", f"{summary.get('profit_factor', 0):.2f}"),
            ("Average Win", f"₹{summary.get('avg_win', 0):.2f}"),
            ("Average Loss", f"₹{summary.get('avg_loss', 0):.2f}"),
            ("Avg Trade Duration", f"{summary.get('avg_trade_duration', 'N/A')}"),
        ]
        
        for metric, value in metrics:
            writer.writerow([metric, value])

        writer.writerow([])

        trades = results.get("trades", [])
        if trades:
            writer.writerow(["Trade Details"])
            writer.writerow([
                "Entry Time", "Exit Time", "Symbol", "Side", "Quantity",
                "Entry Price", "Exit Price", "P&L", "P&L %", "Duration"
            ])
            
            for trade in trades:
                writer.writerow([
                    trade.get("entry_time", ""),
                    trade.get("exit_time", ""),
                    trade.get("symbol", ""),
                    trade.get("side", ""),
                    trade.get("quantity", 0),
                    f"₹{trade.get('entry_price', 0):.2f}",
                    f"₹{trade.get('exit_price', 0):.2f}",
                    f"₹{trade.get('pnl', 0):.2f}",
                    f"{trade.get('pnl_pct', 0):.2f}%",
                    trade.get("duration", ""),
                ])

        return output.getvalue()

    def export_to_json(self, results: Dict[str, Any]) -> str:
        """Export backtest results to JSON format."""
        import json
        return json.dumps(results, indent=2, default=str)

    def export_equity_curve(self, results: Dict[str, Any]) -> List[Dict]:
        """Get equity curve data for charting."""
        equity_curve = results.get("equity_curve", [])
        return [
            {
                "timestamp": point.get("timestamp"),
                "equity": point.get("equity"),
                "drawdown": point.get("drawdown", 0),
            }
            for point in equity_curve
        ]

    def generate_pdf_html(self, results: Dict[str, Any]) -> str:
        """Generate HTML report that can be converted to PDF."""
        summary = results.get("summary", {})
        trades = results.get("trades", [])
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>EasyTradingApp - Backtest Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #1a1a2e; }}
        h2 {{ color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #0f3460; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .metric-label {{ font-weight: bold; color: #666; }}
        .metric-value {{ font-size: 24px; color: #1a1a2e; }}
        .positive {{ color: #00c853; }}
        .negative {{ color: #d50000; }}
        .summary-box {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>EasyTradingApp - Backtest Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary-box">
        <h2>Performance Summary</h2>
        <div class="metric">
            <div class="metric-label">Total Trades</div>
            <div class="metric-value">{summary.get('total_trades', 0)}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Win Rate</div>
            <div class="metric-value">{summary.get('win_rate', 0):.2f}%</div>
        </div>
        <div class="metric">
            <div class="metric-label">Total Return</div>
            <div class="metric-value {'positive' if summary.get('total_return', 0) >= 0 else 'negative'}">
                ₹{summary.get('total_return', 0):.2f}
            </div>
        </div>
        <div class="metric">
            <div class="metric-label">Sharpe Ratio</div>
            <div class="metric-value">{summary.get('sharpe_ratio', 0):.2f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Max Drawdown</div>
            <div class="metric-value negative">₹{summary.get('max_drawdown', 0):.2f}</div>
        </div>
    </div>
    
    <h2>Detailed Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Winning Trades</td><td>{summary.get('winning_trades', 0)}</td></tr>
        <tr><td>Losing Trades</td><td>{summary.get('losing_trades', 0)}</td></tr>
        <tr><td>Profit Factor</td><td>{summary.get('profit_factor', 0):.2f}</td></tr>
        <tr><td>Average Win</td><td>₹{summary.get('avg_win', 0):.2f}</td></tr>
        <tr><td>Average Loss</td><td>₹{summary.get('avg_loss', 0):.2f}</td></tr>
        <tr><td>Average Trade Duration</td><td>{summary.get('avg_trade_duration', 'N/A')}</td></tr>
    </table>
    
    <h2>Trade History</h2>
    <table>
        <tr>
            <th>Entry Time</th>
            <th>Symbol</th>
            <th>Side</th>
            <th>Quantity</th>
            <th>Entry Price</th>
            <th>Exit Price</th>
            <th>P&L</th>
        </tr>
"""
        
        for trade in trades[:50]:
            pnl = trade.get("pnl", 0)
            pnl_class = "positive" if pnl >= 0 else "negative"
            html += f"""
        <tr>
            <td>{trade.get('entry_time', '')}</td>
            <td>{trade.get('symbol', '')}</td>
            <td>{trade.get('side', '')}</td>
            <td>{trade.get('quantity', 0)}</td>
            <td>₹{trade.get('entry_price', 0):.2f}</td>
            <td>₹{trade.get('exit_price', 0):.2f}</td>
            <td class="{pnl_class}">₹{pnl:.2f}</td>
        </tr>
"""
        
        html += """
    </table>
</body>
</html>
"""
        return html

    async def export_to_pdf(self, results: Dict[str, Any]) -> Optional[bytes]:
        """Export backtest results to PDF using WeasyPrint or similar."""
        try:
            from weasyprint import HTML
            html_content = self.generate_pdf_html(results)
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes
        except ImportError:
            return None
        except Exception:
            return None

    async def export_to_pdf_fallback(self, results: Dict[str, Any]) -> Optional[bytes]:
        """Fallback PDF generation using pdfkit or similar."""
        try:
            import pdfkit
            html_content = self.generate_pdf_html(results)
            pdf_bytes = pdfkit.from_string(html_content, False)
            return pdf_bytes
        except ImportError:
            return None
        except Exception:
            return None
