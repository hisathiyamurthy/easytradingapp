"""Backtest export API endpoints."""
from enum import Enum
from uuid import UUID
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from core.security import get_current_user, TokenData, require_trader
from services.export_service import BacktestExporter

router = APIRouter(prefix="/backtest", tags=["Backtesting"])
exporter = BacktestExporter()


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    HTML = "html"
    PDF = "pdf"


class BacktestConfig(BaseModel):
    strategy_id: Optional[str] = None
    symbol: str
    exchange: str = "NSE"
    from_date: str
    to_date: str
    initial_capital: float = 100000
    strategy_type: str = "momentum"
    parameters: Optional[dict] = None


class BacktestResponse(BaseModel):
    backtest_id: str
    status: str
    message: str


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(
    config: BacktestConfig,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Run a new backtest."""
    import asyncio
    from backtesting.engine import BacktestEngine
    
    # Create backtest ID
    backtest_id = str(UUID())
    
    # Run backtest in background (simplified - in production use Celery)
    try:
        engine = BacktestEngine(
            symbol=config.symbol,
            exchange=config.exchange,
            initial_capital=config.initial_capital,
            from_date=config.from_date,
            to_date=config.to_date,
            strategy_type=config.strategy_type,
            parameters=config.parameters or {},
        )
        
        results = await engine.run()
        
        return BacktestResponse(
            backtest_id=backtest_id,
            status="completed",
            message="Backtest completed successfully",
        )
    except Exception as e:
        return BacktestResponse(
            backtest_id=backtest_id,
            status="error",
            message=str(e),
        )


@router.get("/{backtest_id}/export")
async def export_backtest_results(
    backtest_id: UUID,
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format: csv, json, html, pdf"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Export backtest results in various formats."""
    from sqlalchemy import select
    from models.backtest_models import BacktestResult
    
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.id == backtest_id,
            BacktestResult.user_id == current_user.user_id,
        )
    )
    backtest = result.scalar_one_or_none()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest result not found",
        )
    
    results = backtest.results or {}
    
    if format == ExportFormat.CSV:
        csv_content = exporter.export_to_csv(results)
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=backtest_{backtest_id}.csv",
            },
        )
    
    elif format == ExportFormat.JSON:
        json_content = exporter.export_to_json(results)
        return StreamingResponse(
            iter([json_content]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=backtest_{backtest_id}.json",
            },
        )
    
    elif format == ExportFormat.HTML:
        html_content = exporter.generate_pdf_html(results)
        return StreamingResponse(
            iter([html_content]),
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename=backtest_{backtest_id}.html",
            },
        )
    
    elif format == ExportFormat.PDF:
        pdf_bytes = await exporter.export_to_pdf(results)
        
        if not pdf_bytes:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PDF generation not available. Install weasyprint: pip install weasyprint",
            )
        
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=backtest_{backtest_id}.pdf",
            },
        )


@router.get("/{backtest_id}/equity-curve")
async def get_equity_curve(
    backtest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get equity curve data for charting."""
    from sqlalchemy import select
    from models.backtest_models import BacktestResult
    
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.id == backtest_id,
            BacktestResult.user_id == current_user.user_id,
        )
    )
    backtest = result.scalar_one_or_none()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest result not found",
        )
    
    results = backtest.results or {}
    equity_curve = exporter.export_equity_curve(results)
    
    return {
        "backtest_id": str(backtest_id),
        "equity_curve": equity_curve,
    }


@router.get("/{backtest_id}/summary")
async def get_backtest_summary(
    backtest_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_trader()),
):
    """Get backtest summary metrics."""
    from sqlalchemy import select
    from models.backtest_models import BacktestResult
    
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.id == backtest_id,
            BacktestResult.user_id == current_user.user_id,
        )
    )
    backtest = result.scalar_one_or_none()
    
    if not backtest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backtest result not found",
        )
    
    results = backtest.results or {}
    summary = results.get("summary", {})
    
    return {
        "id": str(backtest.id),
        "strategy_id": str(backtest.strategy_id),
        "strategy_name": backtest.strategy_name,
        "created_at": backtest.created_at.isoformat(),
        "summary": summary,
    }