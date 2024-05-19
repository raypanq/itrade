from . import SymbolStr
from decimal import Decimal

class Signal:
    def __init__(self, is_buy:bool,
                 price:Decimal,
                 candle_sec:float,
                 sl:Decimal,
                 tp:Decimal,
                 symstr:SymbolStr) -> None:
        self.is_buy = is_buy
        self.price = price
        self.candle_sec = candle_sec
        self.sl = sl
        self.tp = tp
        self.symstr = symstr
