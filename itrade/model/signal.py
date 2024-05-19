from . import SymbolStr

class Signal:
    def __init__(self, is_buy:bool,
                 price:float,
                 candle_sec:int,
                 sl:float,
                 tp:float,
                 symstr:SymbolStr) -> None:
        self.is_buy = is_buy
        self.price = price
        self.candle_sec = candle_sec
        self.sl = sl
        self.tp = tp
        self.symstr = symstr

    # def __eq__(self, other):
    #     if not isinstance(other, Signal):
    #         raise TypeError(f'{type(other)} is not Signal instance')
    #     # 必须把 candle_sec 考虑进去，否则比如10天前如果出现过同样价格的信号，那么今天的信号就会被合并
    #     return (self.is_buy, self.price, self.candle_sec, self.sl, self.tp, self.symstr) == (other.is_buy, other.price, other.candle_sec, other.sl, other.tp, other.symstr)

    # def __hash__(self):
    #     return hash((self.is_buy, self.price, self.candle_sec, self.sl, self.tp, self.symstr))