from src.model.candle import Candle
from src.model.signal import Signal
from . import IChiefAnalyzable, IAnalyzable

class ChiefAnalyst(IChiefAnalyzable):

    @staticmethod
    def analyze(candle_list: list[Candle], peak_set:set[Candle], valley_set:set[Candle], analyst_list:list[IAnalyzable]) -> list[Signal]:
        if (not candle_list) or (not analyst_list):
            return []
        symstr = candle_list[0].symstr
        period = candle_list[0].period
        assert symstr.quote == 'usd' or symstr.base == 'usd', "other currency need to convert riskamt from usd into quote"
        
        signal_list = [
            signal  # The signal to include in the final list
            for analyst in analyst_list  # For each analyst in the list of analysts
            for signal in analyst.analyze(candle_list, peak_set, valley_set)  # For each signal returned by the analyze method
        ]
        # 虽然在 _Transaction 生成过程中会去重，但是 live 并不会走到 dashboard 中，所以这里去重很必要
        signal_list = _sort(_rm_repeat(signal_list))
        return signal_list


def _sort(signal_list:list[Signal]) -> list[Signal]:
    return sorted(signal_list, key=lambda x: x.candle_sec)

def _rm_repeat(signal_list:list[Signal]) -> list[Signal]:
    # 这是同一个 symbol period 的不同策略，生产的所有信号
    # 同一个 symbol period 的一根蜡烛，一个 open_sec 确实只应该出现一个信号
    signal_dict = {signal.candle_sec:signal for signal in signal_list}
    uniq_signal_list = [
        signal
        for _,signal in signal_dict.items()
    ]
    return uniq_signal_list