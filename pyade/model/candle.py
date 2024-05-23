from .. import utc_date
from decimal import Decimal
from . import SymbolStr,CandlePeriod

STRTIME_FMT = "%Y-%m-%d_%H'%M\"%S"


class Candle:
    def __init__(self, o:Decimal, h:Decimal, l:Decimal, c:Decimal, open_sec:float, symstr:SymbolStr, period:CandlePeriod) -> None:
        self.o = o
        self.h = h
        self.l = l
        self.c = c
        self.open_sec = open_sec
        self.symstr = symstr
        self.period = period

    
    @property
    def body(self):
        return abs(self.c - self.o)
    
    @property
    def h_wick(self):
        return self.h - max(self.c, self.o)
    
    @property
    def l_wick(self):
        return min(self.c, self.o) - self.l
    
    @property
    def len(self):
        return self.h - self.l


    @property
    def strtime(self) -> str:
        return utc_date(self.open_sec).strftime(STRTIME_FMT)

    @property
    def is_up(self):
        return self.c > self.o

    @property
    def is_down(self):
        return self.c < self.o
    
    def __str__(self) -> str:
        return f"C(op{utc_date(self.open_sec)} sym{str(self.symstr).upper()} period{self.period} ohlc{self.o}, {self.h}, {self.l}, {self.c})"
