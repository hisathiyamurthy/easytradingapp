"""Options trading utilities - lot sizes and strike selection."""
from typing import Optional, Dict, List, Tuple


# Indian options lot sizes (2024)
OPTIONS_LOT_SIZES = {
    # Indices
    "NIFTY": 25,
    "BANKNIFTY": 15,
    "FINNIFTY": 25,
    "MIDCAPNIFTY": 50,
    "SENSEX": 10,
    
    # Common stocks (approximate - should be updated from broker)
    "RELIANCE": 250,
    "TCS": 250,
    "HDFCBANK": 250,
    "INFY": 250,
    "SBIN": 500,
    "BAJFINANCE": 250,
    "ITC": 400,
    "MARUTI": 250,
    "SUNPHARMA": 500,
    "TITAN": 250,
    "ADANIPORTS": 500,
    "ASIANPAINT": 250,
    "AXISBANK": 250,
    "COALINDIA": 500,
    "HINDUNILVR": 250,
    "KOTAKBANK": 250,
    "LT": 250,
    "M&M": 250,
    "NTPC": 500,
    "ONGC": 500,
    "POWERGRID": 500,
    "TATASTEEL": 500,
    "ULTRACEMCO": 250,
}


def get_lot_size(symbol: str) -> int:
    """Get the lot size for a symbol. Returns default 1 if unknown."""
    return OPTIONS_LOT_SIZES.get(symbol.upper(), 1)


def get_all_lot_sizes() -> Dict[str, int]:
    """Return all known lot sizes."""
    return OPTIONS_LOT_SIZES.copy()


def calculate_atm_strike(current_price: float, base: int = 100) -> int:
    """Calculate the ATM (At The Money) strike price."""
    return round(current_price / base) * base


def calculate_strike_distance(base_price: float, distance: int, option_type: str) -> Tuple[int, int]:
    """
    Calculate ITM/OTM strike based on distance from ATM.
    
    Args:
        base_price: Current underlying price
        distance: Points away from ATM
        option_type: 'CE' for calls (ITM = lower), 'PE' for puts (ITM = higher)
    
    Returns:
        (strike_price, strike_type) where strike_type is 'ITM', 'OTM', or 'ATM'
    """
    atm = calculate_atm_strike(base_price)
    
    if option_type.upper() == "CE":
        # For CE: ITM = below ATM, OTM = above ATM
        itm_strike = atm - distance
        return (itm_strike, "ITM" if distance > 0 else "ATM")
    else:  # PE
        # For PE: ITM = above ATM, OTM = below ATM  
        itm_strike = atm + distance
        return (itm_strike, "ITM" if distance > 0 else "ATM")


def get_option_symbol(
    underlying: str,
    strike: int,
    option_type: str,
    exchange: str = "NSE"
) -> str:
    """
    Generate the broker-specific option symbol.
    
    Example: NIFTY 22000 CE -> NIFTY22200CE
    """
    return f"{underlying.upper()}{strike}{option_type.upper()}"


def get_closest_strike(current_price: float, target_distance: int, option_type: str) -> int:
    """Get the closest strike to target distance from current price."""
    atm = calculate_atm_strike(current_price)
    
    if option_type.upper() == "CE":
        return atm - target_distance
    else:
        return atm + target_distance


class OptionsStrikeSelector:
    """Service to select appropriate strike prices for options."""
    
    def __init__(self, lot_size: int = 25):
        self.lot_size = lot_size
    
    def select_strike(
        self,
        current_price: float,
        selection_type: str,  # ATM, ITM, OTM
        distance: int = 0,  # Points for ITM/OTM
        option_type: str = "CE"
    ) -> Dict[str, any]:
        """
        Select appropriate strike based on criteria.
        
        Returns dict with:
        - strike: The selected strike price
        - type: ATM/ITM/OTM
        - symbol: Full option symbol
        - lot_size: Number of lots
        """
        atm = calculate_atm_strike(current_price)
        
        if selection_type.upper() == "ATM":
            strike = atm
            strike_type = "ATM"
        elif selection_type.upper() == "ITM":
            if option_type.upper() == "CE":
                strike = atm - distance
            else:
                strike = atm + distance
            strike_type = "ITM"
        elif selection_type.upper() == "OTM":
            if option_type.upper() == "CE":
                strike = atm + distance
            else:
                strike = atm - distance
            strike_type = "OTM"
        else:
            # Default to ATM
            strike = atm
            strike_type = "ATM"
        
        return {
            "strike": strike,
            "type": strike_type,
            "symbol": get_option_symbol("NIFTY" if not hasattr(self, 'underlying') else self.underlying, strike, option_type),
            "lot_size": self.lot_size,
            "quantity": self.lot_size,  # 1 lot
        }
    
    def set_underlying(self, symbol: str):
        """Set underlying and update lot size."""
        self.underlying = symbol.upper()
        self.lot_size = get_lot_size(self.underlying)