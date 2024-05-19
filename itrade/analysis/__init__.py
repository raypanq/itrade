import pandas as pd
from ..model.candle import Candle
from ..model.signal import Signal
from typing import Protocol
from ..model import SymbolStr
from decimal import Decimal

class Analyzable(Protocol):
    @staticmethod
    def analyze(candle_list: list[Candle], peak_set:set[Candle], valley_set:set[Candle]) -> list[Signal]:
        pass

class ChiefAnalyzable(Protocol):
    @staticmethod
    def analyze(candle_list: list[Candle], peak_set:set[Candle], valley_set:set[Candle], analyst_list:list[Analyzable]) -> list[Signal]:
        pass

class IFeeCalculable(Protocol):
    def get_commission_fee(self, order_amt_usd: Decimal) -> Decimal:
        pass
        
    def get_swap_fee(self, symstr:SymbolStr, lot:Decimal, from_sec:float, to_sec:float, is_buy:bool) -> Decimal:
        pass

def get_emas(num_list: list[Decimal], win:int) -> list[Decimal]:
    ema_series = pd.Series(num_list).ewm(span=win, adjust=False).mean()
    return list(ema_series)

def get_atrs(h_list: list[Decimal], l_list: list[Decimal], c_list: list[Decimal], win=int) -> list[Decimal]:
    df = pd.DataFrame(dict(
        h=h_list,
        l=l_list,
        c=c_list
    ))
    df['h-l'] = abs(df.h - df.l)
    df['h-prev_c'] = abs(df.h - df.c.shift())
    df['l-prev_c'] = abs(df.l - df.c.shift())
    df['tr'] = df[['h-l', 'h-prev_c', 'l-prev_c']].max(axis=1)
    return list(df.tr.ewm(span=win, adjust=False).mean())

def get_rsis(num_list:list[Decimal], win:int) -> list[Decimal]:
    series = pd.Series(num_list)
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=win).mean()
    avg_loss = loss.rolling(window=win).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return list(rsi)


def get_peaks_valleys(candle_list: list[Candle]) -> tuple[set[Candle], set[Candle]]:
    # peaks and valleys
    peak_set = set()
    valley_set = set()
    for i in range(1,len(candle_list)-1):
        candle = candle_list[i]
        prev_candle = candle_list[i - 1]
        next_candle = candle_list[i + 1]
        if candle.c > max(prev_candle.c, next_candle.c):
            peak_set.add(candle)
        elif candle.c < min(prev_candle.c, next_candle.c):
            valley_set.add(candle)

    # calc retracement
    peak_valley_list = [c for c in candle_list if c in {*peak_set, *valley_set}]
    for i in range(3, len(peak_valley_list)):
        candle = peak_valley_list[i]
        prev_candle = peak_valley_list[i - 1]
        prev_prev_candle = peak_valley_list[i - 2]
        retracement = candle.c - prev_candle.c
        prev_retracement = prev_candle.c - prev_prev_candle.c
        retracement_perc = retracement / prev_retracement if prev_retracement != 0 else None
        if (not retracement_perc) or retracement_perc < -0.382:
            continue
        else:
            try:
                peak_set.remove(candle)
            except:
                valley_set.remove(candle)
    return peak_set, valley_set

def get_signals(candle_list: list[Candle],
                buy_set: set[Candle],
                sell_set: set[Candle]) -> list['Signal']:
    '''
    因为sl和tp的逻辑，对策略的成功率也是有很大影响，所以构造 signal的方法，每个策略都应该独立，放在对应策略的内部
    '''
    # compose signals
    atr_list = get_atrs([c.h for c in candle_list],
                         [c.l for c in candle_list],
                         [c.c for c in candle_list],
                         win=14)
    atr_dict = {c: atr_list[i] for i, c in enumerate(candle_list)}

    signal_list = []
    for i, candle in enumerate(candle_list):
        prev_candle = candle_list[i - 1] if (i - 1) >= 0 else None
        if not prev_candle:
            continue
        if not (candle in {*buy_set, *sell_set}):
            continue
        price = candle.c
        atr = atr_dict[candle]
        if candle in buy_set:
            min_l = min(candle.l, prev_candle.l)
            sl = min_l - atr
            is_buy = True
        else:
            max_h = max(candle.h, prev_candle.h)
            sl = max_h + atr
            is_buy = False

        diff_price = price - sl
        tp = price + diff_price
        signal = Signal(is_buy=is_buy,
                        price=price,
                        candle_sec=candle.open_sec,
                        sl=sl,
                        tp=tp,
                        symstr=candle.symstr)
        signal_list.append(signal)
    return signal_list

def get_me_to_prev_valley(candle_list: list[Candle],
                      me_idx: int,
                      valley_set:set[Candle]) -> list[Candle]:
    me = candle_list[me_idx]
    up_trend_list = [me]
    i = me_idx - 1
    while i >= 0:
        candle = candle_list[i]
        up_trend_list.append(candle)
        if candle in valley_set:
            break
        i -= 1
    return up_trend_list

def get_me_to_prev_peak(candle_list: list[Candle],
                    me_idx: int,
                    peak_set:set[Candle]) -> list[Candle]:
    me = candle_list[me_idx]
    down_trend_list = [me] #not put me inside loop to check peak, it me is peak already, will break instantly
    i = me_idx - 1
    while i >= 0:
        candle = candle_list[i]
        down_trend_list.append(candle)
        if candle in peak_set:
            break
        i -= 1
    return down_trend_list
