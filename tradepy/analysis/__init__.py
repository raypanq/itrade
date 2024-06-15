import pandas as pd
from ..model.candle import Candle
from ..model.signal import Signal
from typing import Protocol
from ..model import SymbolStr
from decimal import Decimal

class Analyzable(Protocol):
    @staticmethod
    def analyze(candles: list[Candle], peaks:set[Candle], valleys:set[Candle]) -> list[Signal]:
        raise NotImplementedError()

class ChiefAnalyzable(Protocol):
    @staticmethod
    def analyze(candles: list[Candle], peaks:set[Candle], valleys:set[Candle], analysts:list[Analyzable]) -> list[Signal]:
        raise NotImplementedError()

class FeeCalculable(Protocol):
    #TODO order_amt_usd
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
    ema_floats = list(ema_series)
    ema_decimals = [Decimal(ema) for ema in ema_floats]
    return ema_decimals

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
    atr_flts = list(df.tr.ewm(span=win, adjust=False).mean())
    atr_decs = [Decimal(atr) for atr in atr_flts]
    return atr_decs

def get_rsis(nums:list[Decimal], win:int) -> list[Decimal]:
    if not nums:
        return []
    close_delta = pd.Series(nums).diff()
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)

    ma_up = up.ewm(com=win - 1, adjust=True, min_periods=win).mean()
    ma_down = down.ewm(com=win - 1, adjust=True, min_periods=win).mean()
    rsi_series = 100 - (100 / (1 + ma_up / ma_down))
    rsi_flts = list(rsi_series)
    rsi_decs = [Decimal(rsi) for rsi in rsi_flts]
    return rsi_decs

def get_peaks_valleys(candles: list[Candle]) -> tuple[set[Candle], set[Candle]]:
    if not candles:
        return set(), set()
    # peaks and valleys
    peaks = set()
    valleys = set()
    for i in range(1,len(candles)-1):
        candle = candles[i]
        prev_candle = candles[i - 1]
        next_candle = candles[i + 1]
        if candle.c > max(prev_candle.c, next_candle.c):
            peaks.add(candle)
        elif candle.c < min(prev_candle.c, next_candle.c):
            valleys.add(candle)

    # calc retracement
    peak_valleys = [c for c in candles if c in {*peaks, *valleys}]
    for i in range(3, len(peak_valleys)):
        candle = peak_valleys[i]
        prev_candle = peak_valleys[i - 1]
        prev_prev_candle = peak_valleys[i - 2]
        retracement = candle.c - prev_candle.c
        prev_retracement = prev_candle.c - prev_prev_candle.c
        retracement_perc = retracement / prev_retracement if prev_retracement != 0 else None
        if (not retracement_perc) or retracement_perc < -0.382:
            continue
        else:
            try:
                peaks.remove(candle)
            except:
                valleys.remove(candle)
    return peaks, valleys

def get_signals(candles: list[Candle],
                buys: set[Candle],
                sells: set[Candle]) -> list['Signal']:
    if not candles or not buys or not sells:
        return []
    '''
    因为sl和tp的逻辑，对策略的成功率也是有很大影响，所以构造 signal的方法，每个策略都应该独立，放在对应策略的内部
    '''
    # compose signals
    atrs = get_atrs([c.h for c in candles],
                         [c.l for c in candles],
                         [c.c for c in candles],
                         win=14)
    atrs = {c: atrs[i] for i, c in enumerate(candles)}

    signals = []
    for i, candle in enumerate(candles):
        prev_candle = candles[i - 1] if (i - 1) >= 0 else None
        if not prev_candle:
            continue
        if not (candle in {*buys, *sells}):
            continue
        price = candle.c
        atr = atrs[candle]
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
        signals.append(signal)
    return signals

def get_me_to_prev_valley(candles: list[Candle],
                            me_idx: int,
                            valleys:set[Candle]) -> list[Candle]:
    
    me = candles[me_idx]
    up_trends = [me]
    i = me_idx - 1
    while i >= 0:
        candle = candles[i]
        up_trends.append(candle)
        if candle in valleys:
            break
        i -= 1
    return up_trends

def get_me_to_prev_peak(candles: list[Candle],
                    me_idx: int,
                    peaks:set[Candle]) -> list[Candle]:
    me = candles[me_idx]
    down_trends = [me] #not put me inside loop to check peak, it me is peak already, will break instantly
    i = me_idx - 1
    while i >= 0:
        candle = candles[i]
        down_trends.append(candle)
        if candle in peaks:
            break
        i -= 1
    return down_trends