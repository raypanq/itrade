from enum import StrEnum, unique, auto

@unique
class SymbolStr(StrEnum):
    EURUSD = auto()
    USDJPY = auto()
    GBPUSD = auto()
    AUDUSD = auto()
    USDCHF = auto()
    USDCAD = auto()
    NZDUSD = auto()
    BTCUSD = auto()
    ETHUSD = auto()
    XAUUSD = auto()
    XAGUSD = auto()
    XBRUSD = auto() # Brent Oil
    XNGUSD = auto() # Natural Gas
    XTIUSD = auto() # West Texas Intermediate Crude Oil
    XPTUSD = auto()

    @property
    def base(self) -> str:
        return str(self)[:3]

    @property 
    def quote(self) -> str:
        return str(self)[3:]
    

@unique
class CandlePeriod(StrEnum):
    S1 = auto()
    S5 = auto()
    S10 = auto()
    S15 = auto()
    S30 = auto()
    
    M1 = auto()
    M2 = auto()
    M3 = auto()
    M4 = auto()
    M5 = auto()
    M10 = auto()
    M15 = auto()
    M30 = auto()
    M45 = auto()
    
    H1 = auto()
    H2 = auto()
    H3 = auto()
    H4 = auto()
    H12 = auto()
    
    D1 = auto()
    W1 = auto()
    MO1 = auto()
    MO3 = auto()
    MO6 = auto()
    Y1 = auto()
