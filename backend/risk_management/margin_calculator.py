"""Margin Calculator for Indian stock markets.

Calculates margin requirements for different order types and segments.
"""
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class MarginRequirement:
    """Margin requirement for an order."""
    order_value: float
    margin_required: float
    exposure: float
    margin_percentage: float
    segment: str  # NSE_EQ, NSE_FO, BSE_EQ, BSE_FO, MCX
    order_type: str  # CASH, MARGIN, DELIVERY, INTRADAY


class MarginCalculator:
    """Calculator for margin requirements in Indian markets."""
    
    # Standard margin percentages (as of 2024)
    MARGIN_RATES = {
        # Equity Cash
        "NSE_EQ_CASH": 0.20,  # 20% for cash delivery
        "NSE_EQ_INTRADAY": 0.05,  # 5% for intraday
        "BSE_EQ_CASH": 0.20,
        "BSE_EQ_INTRADAY": 0.05,
        
        # Equity Futures (NSE F&O)
        "NSE_FO": 0.12,  # 12% for futures
        
        # Options
        "NSE_OPT": 0.10,  # 10% for options (premium)
        "NSE_OPT_SELL": 0.10,  # 10% for option selling
        
        # Commodity (MCX)
        "MCX": 0.05,  # 5% for commodities
        
        # Currency (NSE)
        "NSE_CUR": 0.05,  # 5% for currency
    }
    
    # Exposure multipliers
    EXPOSURE_MULTIPLIERS = {
        "NSE_EQ_INTRADAY": 20.0,  # 5% margin = 20x exposure
        "NSE_EQ_CASH": 1.0,
        "NSE_FO": 8.33,  # 12% margin
        "NSE_OPT": 10.0,
        "MCX": 20.0,
        "NSE_CUR": 20.0,
    }
    
    def __init__(self, segment: str = "NSE_EQ"):
        self.segment = segment
    
    def calculate_margin(
        self,
        symbol: str,
        quantity: int,
        price: float,
        order_type: str = "INTRADAY",
        segment: Optional[str] = None,
    ) -> MarginRequirement:
        """Calculate margin requirement for an order.
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares/contracts
            price: Order price
            order_type: Type of order (CASH, MARGIN, DELIVERY, INTRADAY)
            segment: Market segment (NSE_EQ, NSE_FO, BSE_EQ, MCX, NSE_CUR)
        
        Returns:
            MarginRequirement with margin calculations
        """
        segment = segment or self.segment
        order_value = price * quantity
        
        # Get margin rate
        margin_key = f"{segment}_{order_type}"
        margin_rate = self.MARGIN_RATES.get(margin_key, 0.20)
        
        # Calculate margin
        margin_required = order_value * margin_rate
        
        # Calculate exposure (leverage)
        exposure_multiplier = self.EXPOSURE_MULTIPLIERS.get(segment, 1.0)
        exposure = order_value * exposure_multiplier if margin_required > 0 else 0
        
        return MarginRequirement(
            order_value=order_value,
            margin_required=margin_required,
            exposure=exposure,
            margin_percentage=margin_rate * 100,
            segment=segment,
            order_type=order_type,
        )
    
    def calculate_margin_for_bracket_order(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        segment: str = "NSE_EQ",
    ) -> dict:
        """Calculate total margin for a bracket order (entry + target + stop loss).
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares
            entry_price: Entry price
            target_price: Target profit price
            stop_loss: Stop loss price
            segment: Market segment
        
        Returns:
            Dictionary with margin breakdown
        """
        entry_margin = self.calculate_margin(symbol, quantity, entry_price, "INTRADAY", segment)
        
        # For bracket orders, additional margin may be needed for worst case
        price_diff = abs(target_price - stop_loss)
        worst_case_loss = price_diff * quantity
        worst_case_margin = worst_case_loss * 0.5  # 50% of worst case as additional margin
        
        total_margin = entry_margin.margin_required + worst_case_margin
        
        return {
            "entry_margin": entry_margin.margin_required,
            "worst_case_margin": worst_case_margin,
            "total_margin_required": total_margin,
            "order_value": entry_margin.order_value,
            "leverage": entry_margin.order_value / total_margin if total_margin > 0 else 1.0,
        }
    
    def calculate_intraday_margin(
        self,
        symbol: str,
        quantity: int,
        price: float,
        segment: str = "NSE_EQ",
    ) -> MarginRequirement:
        """Calculate intraday margin (MIS - Margin Intraday Square-off).
        
        Intraday trading in India typically requires 5% margin (20x leverage).
        """
        return self.calculate_margin(symbol, quantity, price, "INTRADAY", segment)
    
    def calculate_delivery_margin(
        self,
        symbol: str,
        quantity: int,
        price: float,
        segment: str = "NSE_EQ",
    ) -> MarginRequirement:
        """Calculate delivery/cash margin (CNC - Cash n Carry).
        
        Delivery trading requires full value (20% for delivery).
        """
        return self.calculate_margin(symbol, quantity, price, "CASH", segment)
    
    def calculate_futures_margin(
        self,
        symbol: str,
        quantity: int,
        price: float,
        segment: str = "NSE_FO",
    ) -> MarginRequirement:
        """Calculate margin for futures contracts."""
        return self.calculate_margin(symbol, quantity, price, "MARGIN", segment)
    
    def check_sufficient_margin(
        self,
        available_margin: float,
        required_margin: float,
    ) -> tuple[bool, float]:
        """Check if user has sufficient margin for an order.
        
        Args:
            available_margin: User's available margin balance
            required_margin: Required margin for the order
        
        Returns:
            Tuple of (is_sufficient, shortfall)
        """
        if available_margin >= required_margin:
            return True, 0.0
        return False, required_margin - available_margin
    
    def get_margin_utilization(
        self,
        used_margin: float,
        available_margin: float,
    ) -> float:
        """Calculate margin utilization percentage."""
        total = used_margin + available_margin
        if total == 0:
            return 0.0
        return (used_margin / total) * 100


class PortfolioMarginCalculator:
    """Calculate portfolio-level margin requirements."""
    
    def __init__(self):
        self.calculator = MarginCalculator()
    
    def calculate_total_margin(
        self,
        positions: list[dict],
        pending_orders: list[dict],
    ) -> dict:
        """Calculate total margin requirement for portfolio.
        
        Args:
            positions: List of current positions
            pending_orders: List of pending orders
        
        Returns:
            Dictionary with margin breakdown
        """
        total_used_margin = 0.0
        total_order_margin = 0.0
        total_exposure = 0.0
        
        # Calculate margin for positions
        for pos in positions:
            margin = self.calculator.calculate_margin(
                symbol=pos.get("symbol", ""),
                quantity=pos.get("quantity", 0),
                price=pos.get("current_price", pos.get("entry_price", 0)),
                order_type=pos.get("order_type", "INTRADAY"),
                segment=pos.get("segment", "NSE_EQ"),
            )
            total_used_margin += margin.margin_required
            total_exposure += margin.exposure
        
        # Calculate margin for pending orders
        for order in pending_orders:
            margin = self.calculator.calculate_margin(
                symbol=order.get("symbol", ""),
                quantity=order.get("quantity", 0),
                price=order.get("price", 0),
                order_type=order.get("order_type", "INTRADAY"),
                segment=order.get("segment", "NSE_EQ"),
            )
            total_order_margin += margin.margin_required
        
        total_required = total_used_margin + total_order_margin
        
        return {
            "used_margin": total_used_margin,
            "pending_order_margin": total_order_margin,
            "total_required_margin": total_required,
            "total_exposure": total_exposure,
            "position_count": len(positions),
            "pending_order_count": len(pending_orders),
        }
    
    def check_margin_sufficient(
        self,
        available_margin: float,
        positions: list[dict],
        pending_orders: list[dict],
    ) -> dict:
        """Check if margin is sufficient for all positions and orders."""
        margin_info = self.calculate_total_margin(positions, pending_orders)
        required = margin_info["total_required_margin"]
        
        is_sufficient = available_margin >= required
        shortfall = max(0, required - available_margin)
        
        return {
            "is_sufficient": is_sufficient,
            "shortfall": shortfall,
            "available_margin": available_margin,
            "required_margin": required,
            "utilization_percent": (required / available_margin * 100) if available_margin > 0 else 0,
        }


# Singleton instance
_margin_calculator: Optional[MarginCalculator] = None
_portfolio_margin_calculator: Optional[PortfolioMarginCalculator] = None


def get_margin_calculator() -> MarginCalculator:
    """Get margin calculator singleton."""
    global _margin_calculator
    if _margin_calculator is None:
        _margin_calculator = MarginCalculator()
    return _margin_calculator


def get_portfolio_margin_calculator() -> PortfolioMarginCalculator:
    """Get portfolio margin calculator singleton."""
    global _portfolio_margin_calculator
    if _portfolio_margin_calculator is None:
        _portfolio_margin_calculator = PortfolioMarginCalculator()
    return _portfolio_margin_calculator


if __name__ == "__main__":
    calc = MarginCalculator()
    
    # Example: Intraday order
    margin = calc.calculate_intraday_margin(
        symbol="RELIANCE",
        quantity=100,
        price=2500,
        segment="NSE_EQ",
    )
    print(f"Intraday Order:")
    print(f"  Order Value: ₹{margin.order_value:,.2f}")
    print(f"  Margin Required: ₹{margin.margin_required:,.2f} ({margin.margin_percentage}%)")
    print(f"  Exposure: ₹{margin.exposure:,.2f}")
    
    # Example: Delivery order
    margin = calc.calculate_delivery_margin(
        symbol="RELIANCE",
        quantity=100,
        price=2500,
    )
    print(f"\nDelivery Order:")
    print(f"  Order Value: ₹{margin.order_value:,.2f}")
    print(f"  Margin Required: ₹{margin.margin_required:,.2f} ({margin.margin_percentage}%)")
    
    # Example: Futures
    margin = calc.calculate_futures_margin(
        symbol="NIFTY",
        quantity=50,
        price=22000,
    )
    print(f"\nFutures Order:")
    print(f"  Order Value: ₹{margin.order_value:,.2f}")
    print(f"  Margin Required: ₹{margin.margin_required:,.2f} ({margin.margin_percentage}%)")
    print(f"  Exposure: ₹{margin.exposure:,.2f}")
