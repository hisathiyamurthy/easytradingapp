"""Strategy schemas."""
from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field
from enum import Enum


class StrategyType(str, Enum):
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    BREAKOUT = "BREAKOUT"
    GRID = "GRID"
    DCA = "DCA"


class StrategyStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "validated"
    BACKTESTED = "backtested"
    PAPER_TRADING = "paper_trading"
    LIVE = "live"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    strategy_type: StrategyType
    parameters: dict = Field(default_factory=dict)
    is_paper_trading: bool = True


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StrategyStatus] = None
    parameters: Optional[dict] = None
    is_paper_trading: Optional[bool] = None


class StrategyResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    strategy_type: StrategyType
    status: StrategyStatus
    parameters: dict
    is_paper_trading: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    strategies: List[StrategyResponse]
    total: int


class StrategyParameterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    value: Any
    param_type: str = "string"


class StrategyParameterUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[Any] = None
    param_type: Optional[str] = None


class StrategyParameterResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    name: str
    value: Any
    param_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class StrategyLogResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    log_level: str
    message: str
    data: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class StrategyBacktestRequest(BaseModel):
    strategy_id: UUID
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000
    symbols: List[str]


class StrategyBacktestResponse(BaseModel):
    strategy_id: UUID
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float


class StrategyLogListResponse(BaseModel):
    logs: List[StrategyLogResponse]
    total: int


class StrategyActivateRequest(BaseModel):
    broker_id: Optional[UUID] = None


class StrategyDeactivateRequest(BaseModel):
    reason: Optional[str] = None


class StrategyCloneRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    copy_parameters: bool = True


class StrategyParseRequest(BaseModel):
    strategy_text: str = Field(..., min_length=1)


class StrategyParseResponse(BaseModel):
    name: str
    description: str
    strategy_type: str
    parameters: dict
    entry_conditions: List[Any]
    exit_conditions: List[Any]
    validation_errors: List[str]
    is_valid: bool


# Strategy Instance Schemas

class InstanceStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class InstanceMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class InstanceCreate(BaseModel):
    strategy_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    capital: float = 100000.0
    mode: InstanceMode = InstanceMode.PAPER
    symbols: List[str] = ["NIFTY"]


class InstanceResponse(BaseModel):
    id: UUID
    user_id: UUID
    strategy_id: UUID
    name: str
    capital: float
    allocated_capital: float
    status: InstanceStatus
    mode: InstanceMode
    current_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    trades_count: int
    winning_trades: int
    losing_trades: int
    max_drawdown: float
    started_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class InstanceListResponse(BaseModel):
    instances: List[InstanceResponse]
    total: int


class InstanceTradeResponse(BaseModel):
    id: UUID
    instance_id: UUID
    symbol: str
    exchange: str
    side: str
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_percent: Optional[float]
    commission: float
    exit_reason: Optional[str]
    entry_time: datetime
    exit_time: Optional[datetime]

    class Config:
        from_attributes = True


class InstanceTradesResponse(BaseModel):
    trades: List[InstanceTradeResponse]
    total: int


class InstancePerformanceResponse(BaseModel):
    instance_id: UUID
    name: str
    status: str
    mode: str
    capital: float
    allocated_capital: float
    current_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    trades_count: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    max_profit: float
    return_percent: float
    recent_trades: List[dict]


class InstanceStartRequest(BaseModel):
    initial_balance: Optional[float] = None


class InstanceClosePositionRequest(BaseModel):
    symbol: str
    reason: str = "manual"


# Strategy Lifecycle Schemas

class StrategyLifecycleStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    BACKTESTED = "backtested"
    PAPER_TRADING = "paper_trading"
    LIVE = "live"
    PAUSED = "paused"
    STOPPED = "stopped"


class StrategyValidationRequest(BaseModel):
    strategy_id: UUID


class StrategyValidationResponse(BaseModel):
    strategy_id: UUID
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    can_run_backtest: bool
    can_start_paper_trading: bool
    can_start_live: bool


class StrategyFullBacktestRequest(BaseModel):
    strategy_text: str = Field(..., min_length=10)
    symbol: str = "NIFTY"
    exchange: str = "NSE"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timeframe: str = "1d"
    initial_capital: float = 100000


class StrategyFullBacktestResponse(BaseModel):
    strategy_text: str
    parsed_strategy: dict
    validation: dict
    backtest: Optional[dict]
    lifecycle_state: str
    allowed_transitions: List[str]


class StrategyLifecycleTransitionRequest(BaseModel):
    target_state: StrategyLifecycleStatus
    reason: Optional[str] = None


class StrategyLifecycleTransitionResponse(BaseModel):
    success: bool
    from_state: str
    to_state: str
    message: str
    requirements_met: List[str]
    requirements_missing: List[str]


class StrategyApprovalRequest(BaseModel):
    strategy_id: UUID
    approved: bool
    reason: Optional[str] = None


class StrategyApprovalResponse(BaseModel):
    strategy_id: UUID
    approved_by: UUID
    approved_at: datetime
    status: str
