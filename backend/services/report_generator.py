"""PDF Report Generator for trading analytics.

Generates PDF reports for backtest results, performance analytics, and daily summaries.
"""
import io
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not available, PDF generation will be limited")


class PDFReportGenerator:
    """Generate PDF reports for trading analytics."""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            logger.warning("PDF generation requires reportlab. Install with: pip install reportlab")
        
        self.styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles."""
        if not self.styles:
            return
        
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=30,
            alignment=TA_CENTER,
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#16213e'),
            spaceBefore=20,
            spaceAfter=10,
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a1a2e'),
            fontName='Helvetica-Bold',
        ))
    
    def generate_backtest_report(
        self,
        metrics: dict,
        strategy_name: str,
        start_date: str,
        end_date: str,
    ) -> bytes:
        """Generate PDF report for backtest results.
        
        Args:
            metrics: Backtest metrics dictionary
            strategy_name: Name of the strategy
            start_date: Backtest start date
            end_date: Backtest end date
        
        Returns:
            PDF bytes
        """
        if not REPORTLAB_AVAILABLE:
            return self._generate_fallback_pdf()
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        story = []
        
        # Title
        story.append(Paragraph("Backtest Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Strategy info
        story.append(Paragraph(f"<b>Strategy:</b> {strategy_name}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Period:</b> {start_date} to {end_date}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Performance Summary
        story.append(Paragraph("Performance Summary", self.styles['SectionHeader']))
        
        perf_data = [
            ['Metric', 'Value'],
            ['Total Return', f"{metrics.get('total_return_pct', 0):.2f}%"],
            ['Annualized Return', f"{metrics.get('annualized_return', 0):.2f}%"],
            ['Sharpe Ratio', f"{metrics.get('sharpe_ratio', 0):.2f}"],
            ['Sortino Ratio', f"{metrics.get('sortino_ratio', 0):.2f}"],
            ['Max Drawdown', f"{metrics.get('max_drawdown_pct', 0):.2f}%"],
            ['Calmar Ratio', f"{metrics.get('calmar_ratio', 0):.2f}"],
        ]
        
        table = Table(perf_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Trade Statistics
        story.append(Paragraph("Trade Statistics", self.styles['SectionHeader']))
        
        trade_data = [
            ['Metric', 'Value'],
            ['Total Trades', str(metrics.get('total_trades', 0))],
            ['Winning Trades', str(metrics.get('winning_trades', 0))],
            ['Losing Trades', str(metrics.get('losing_trades', 0))],
            ['Win Rate', f"{metrics.get('win_rate', 0):.2f}%"],
            ['Gross Profit', f"₹{metrics.get('gross_profit', 0):,.2f}"],
            ['Gross Loss', f"₹{metrics.get('gross_loss', 0):,.2f}"],
            ['Profit Factor', f"{metrics.get('profit_factor', 0):.2f}"],
            ['Total Commission', f"₹{metrics.get('total_commission', 0):,.2f}"],
        ]
        
        table = Table(trade_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        story.append(table)
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "Generated by EasyTradingApp",
            ParagraphStyle('Footer', parent=self.styles['Normal'], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
        ))
        
        doc.build(story)
        return buffer.getvalue()
    
    def generate_performance_report(
        self,
        analytics: dict,
        period: str,
    ) -> bytes:
        """Generate PDF report for performance analytics.
        
        Args:
            analytics: Performance analytics dictionary
            period: Reporting period (daily/monthly/yearly)
        
        Returns:
            PDF bytes
        """
        if not REPORTLAB_AVAILABLE:
            return self._generate_fallback_pdf()
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        story = []
        
        # Title
        title = f"{period.capitalize()} Performance Report"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Period info
        story.append(Paragraph(
            f"<b>Period:</b> {analytics.get('start_date', 'N/A')} to {analytics.get('end_date', 'N/A')}",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 30))
        
        # Portfolio Value
        story.append(Paragraph("Portfolio Overview", self.styles['SectionHeader']))
        
        portfolio_data = [
            ['Metric', 'Value'],
            ['Starting Value', f"₹{analytics.get('starting_value', 0):,.2f}"],
            ['Ending Value', f"₹{analytics.get('ending_value', 0):,.2f}"],
            ['Total P&L', f"₹{analytics.get('total_pnl', 0):,.2f}"],
            ['Return', f"{analytics.get('return_pct', 0):.2f}%"],
        ]
        
        table = Table(portfolio_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Risk Metrics
        story.append(Paragraph("Risk Metrics", self.styles['SectionHeader']))
        
        risk_data = [
            ['Metric', 'Value'],
            ['Sharpe Ratio', f"{analytics.get('sharpe_ratio', 0):.2f}"],
            ['Sortino Ratio', f"{analytics.get('sortino_ratio', 0):.2f}"],
            ['Max Drawdown', f"{analytics.get('max_drawdown', 0):.2f}%"],
            ['Volatility', f"{analytics.get('volatility', 0):.2f}%"],
        ]
        
        table = Table(risk_data, colWidths=[3*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
        
        doc.build(story)
        return buffer.getvalue()
    
    def generate_trade_history_report(
        self,
        trades: list[dict],
        user_name: str,
    ) -> bytes:
        """Generate PDF report for trade history.
        
        Args:
            trades: List of trade dictionaries
            user_name: User name
        
        Returns:
            PDF bytes
        """
        if not REPORTLAB_AVAILABLE:
            return self._generate_fallback_pdf()
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        story = []
        
        # Title
        story.append(Paragraph("Trade History Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph(f"<b>User:</b> {user_name}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Total Trades:</b> {len(trades)}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        if not trades:
            story.append(Paragraph("No trades to display.", self.styles['Normal']))
        else:
            # Trades table
            story.append(Paragraph("Trades", self.styles['SectionHeader']))
            
            table_data = [['Date', 'Symbol', 'Side', 'Qty', 'Entry', 'Exit', 'P&L']]
            
            for trade in trades[:50]:  # Limit to 50 trades per page
                table_data.append([
                    trade.get('entry_timestamp', '')[:10],
                    trade.get('symbol', ''),
                    trade.get('side', '').upper(),
                    str(trade.get('quantity', 0)),
                    f"₹{trade.get('entry_price', 0):.2f}",
                    f"₹{trade.get('exit_price', 0):.2f}" if trade.get('exit_price') else 'Open',
                    f"₹{trade.get('pnl', 0):.2f}",
                ])
            
            table = Table(table_data, colWidths=[0.9*inch, 0.8*inch, 0.5*inch, 0.4*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            story.append(table)
        
        doc.build(story)
        return buffer.getvalue()
    
    def _generate_fallback_pdf(self) -> bytes:
        """Generate a simple fallback PDF when reportlab is not available."""
        if not REPORTLAB_AVAILABLE:
            logger.warning("Creating text fallback instead of PDF")
            content = "PDF generation requires reportlab. Please install: pip install reportlab"
            return content.encode('utf-8')
        return b""


class ReportService:
    """Service for generating various trading reports."""
    
    def __init__(self):
        self.pdf_generator = PDFReportGenerator()
    
    async def generate_backtest_pdf(
        self,
        metrics: dict,
        strategy_name: str,
        start_date: str,
        end_date: str,
    ) -> bytes:
        """Generate backtest report as PDF."""
        return self.pdf_generator.generate_backtest_report(
            metrics=metrics,
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
        )
    
    async def generate_performance_pdf(
        self,
        analytics: dict,
        period: str,
    ) -> bytes:
        """Generate performance report as PDF."""
        return self.pdf_generator.generate_performance_report(
            analytics=analytics,
            period=period,
        )
    
    async def generate_trade_history_pdf(
        self,
        trades: list[dict],
        user_name: str,
    ) -> bytes:
        """Generate trade history report as PDF."""
        return self.pdf_generator.generate_trade_history_report(
            trades=trades,
            user_name=user_name,
        )


_report_service: Optional[ReportService] = None


def get_report_service() -> ReportService:
    """Get report service singleton."""
    global _report_service
    if _report_service is None:
        _report_service = ReportService()
    return _report_service


if __name__ == "__main__":
    # Test PDF generation
    generator = PDFReportGenerator()
    
    # Test backtest report
    metrics = {
        'total_return_pct': 15.5,
        'annualized_return': 18.2,
        'sharpe_ratio': 1.45,
        'sortino_ratio': 1.82,
        'max_drawdown_pct': 8.5,
        'calmar_ratio': 2.14,
        'total_trades': 45,
        'winning_trades': 28,
        'losing_trades': 17,
        'win_rate': 62.22,
        'gross_profit': 25000,
        'gross_loss': 12000,
        'profit_factor': 2.08,
        'total_commission': 450,
    }
    
    pdf = generator.generate_backtest_report(
        metrics=metrics,
        strategy_name="EMA Crossover",
        start_date="2025-01-01",
        end_date="2025-12-31",
    )
    
    print(f"Generated PDF: {len(pdf)} bytes")
