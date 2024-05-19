from datetime import datetime,timezone
from src import del_float_tail, utc_date
from . import SymbolStr,CandlePeriod

STRTIME_FMT = "%Y-%m-%d_%H'%M\"%S"


class Candle:
    def __init__(self, o:float, h:float, l:float, c:float, open_sec:int, symstr:SymbolStr, period:CandlePeriod) -> None:
        self.o = o
        self.h = h
        self.l = l
        self.c = c
        self.open_sec = open_sec
        self.symstr = symstr
        self.period = period

    @property
    def c_4f(self):
        return del_float_tail(self.c, 4)
    
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
    def o_4f(self):
        return del_float_tail(self.o, 4)

    @property
    def strtime(self) -> str:
        return utc_date(self.open_sec).strftime(STRTIME_FMT)

    @property
    def is_up(self):
        return self.c > self.o

    @property
    def is_down(self):
        return self.c < self.o
