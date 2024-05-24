import pandas as pd
from ..model.candle import Candle
from ..model.signal import Signal
from typing import Protocol
from ..model import SymbolStr
from decimal import Decimal

class Analyzable(Protocol):
    @staticmethod
    def analyze(candle_list: list[Candle], peak_set:set[Candle], valley_set:set[Candle]) -> list[Signal]:
        raise NotImplementedError()

class ChiefAnalyzable(Protocol):
    @staticmethod
    def analyze(candle_list: list[Candle], peak_set:set[Candle], valley_set:set[Candle], analyst_list:list[Analyzable]) -> list[Signal]:
        raise NotImplementedError()

class FeeCalculable(Protocol):
    @staticmethod
    def get_commission_fee(order_amt_usd: Decimal) -> Decimal:
        raise NotImplementedError()
        
    @staticmethod
    def get_swap_fee(symstr:SymbolStr, lot:Decimal, from_sec:float, to_sec:float, is_buy:bool) -> Decimal:
        raise NotImplementedError()

def get_emas(nums: list[Decimal], win:int) -> list[Decimal]:
    if not nums:
        return []
    ema_series = pd.Series(nums).ewm(span=win, adjust=False).mean()
    ema_float_list = list(ema_series)
    ema_decimal_list = [Decimal(ema) for ema in ema_float_list]
    return ema_decimal_list

def get_atrs(highs: list[Decimal], lows: list[Decimal], closes: list[Decimal], win=int) -> list[Decimal]:
    if not highs or not lows or not closes:
        return []
    df = pd.DataFrame(dict(
        h=highs,
        l=lows,
        c=closes
    ))
    df['h-l'] = abs(df.h - df.l)
    df['h-prev_c'] = abs(df.h - df.c.shift())
    df['l-prev_c'] = abs(df.l - df.c.shift())
    df['tr'] = df[['h-l', 'h-prev_c', 'l-prev_c']].max(axis=1)
    atr_float_list = list(df.tr.ewm(span=win, adjust=False).mean())
    atr_decimal_list = [Decimal(atr) for atr in atr_float_list]
    return atr_decimal_list

def get_rsis(nums:list[Decimal], win:int) -> list[Decimal]:
    if not nums:
        return []
    close_delta = pd.Series(nums).diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)

    ma_up = up.ewm(com=win - 1, adjust=True, min_periods=win).mean()
    ma_down = down.ewm(com=win - 1, adjust=True, min_periods=win).mean()
    rsi_series = 100 - (100 / (1 + ma_up / ma_down))
    rsi_float_list = list(rsi_series)
    rsi_decimal_list = [Decimal(rsi) for rsi in rsi_float_list]
    return rsi_decimal_list

def get_peaks_valleys(candles: list[Candle]) -> tuple[set[Candle], set[Candle]]:
    if not candles:
        return set(), set()
    # peaks and valleys
    peak_set = set()
    valley_set = set()
    for i in range(1,len(candles)-1):
        candle = candles[i]
        prev_candle = candles[i - 1]
        next_candle = candles[i + 1]
        if candle.c > max(prev_candle.c, next_candle.c):
            peak_set.add(candle)
        elif candle.c < min(prev_candle.c, next_candle.c):
            valley_set.add(candle)

    # calc retracement
    peak_valley_list = [c for c in candles if c in {*peak_set, *valley_set}]
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

def get_signals(candles: list[Candle],
                buys: set[Candle],
                sells: set[Candle]) -> list['Signal']:
    if not candles or not buys or not sells:
        return []
    '''
    因为sl和tp的逻辑，对策略的成功率也是有很大影响，所以构造 signal的方法，每个策略都应该独立，放在对应策略的内部
    '''
    # compose signals
    atr_list = get_atrs([c.h for c in candles],
                         [c.l for c in candles],
                         [c.c for c in candles],
                         win=14)
    atr_dict = {c: atr_list[i] for i, c in enumerate(candles)}

    signal_list = []
    for i, candle in enumerate(candles):
        prev_candle = candles[i - 1] if (i - 1) >= 0 else None
        if not prev_candle:
            continue
        if not (candle in {*buys, *sells}):
            continue
        price = candle.c
        atr = atr_dict[candle]
        if candle in buys:
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

def get_me_to_prev_valley(candles: list[Candle],
                            me_idx: int,
                            valleys:set[Candle]) -> list[Candle]:
    
    me = candles[me_idx]
    up_trend_list = [me]
    i = me_idx - 1
    while i >= 0:
        candle = candles[i]
        up_trend_list.append(candle)
        if candle in valleys:
            break
        i -= 1
    return up_trend_list

def get_me_to_prev_peak(candles: list[Candle],
                    me_idx: int,
                    peaks:set[Candle]) -> list[Candle]:
    me = candles[me_idx]
    down_trend_list = [me] #not put me inside loop to check peak, it me is peak already, will break instantly
    i = me_idx - 1
    while i >= 0:
        candle = candles[i]
        down_trend_list.append(candle)
        if candle in peaks:
            break
        i -= 1
    return down_trend_list
