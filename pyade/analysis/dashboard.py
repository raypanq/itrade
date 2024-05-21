from ..model.candle import Candle, STRTIME_FMT
from ..model.signal import Signal
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from decimal import Decimal
import pandas as pd
from . import get_rsis, get_emas, get_atrs
from .. import utc_date, trunc
from ..model import SymbolStr
from functools import reduce
from . import FeeCalculable, Analyzable

class _Transaction:
    def __init__(self,
                 from_candle_open_sec: float,
                 to_candle_open_sec: float,
                 is_buy: bool,
                 price: Decimal,
                 tp: Decimal,
                 sl: Decimal,
                 symstr: SymbolStr):
        self.from_candle_open_sec = from_candle_open_sec
        self.to_candle_open_sec = to_candle_open_sec
        self.is_buy = is_buy
        self.is_tp = False
        self.price = price
        self.tp = tp
        self.sl = sl
        self.unit = Decimal(0)
        self.used_margin_usd = Decimal(0)
        self.symstr = symstr
        self.risk_amt_usd = Decimal(0)
        self.order_amt_usd = Decimal(0)

    @property
    def is_sell(self) ->bool:
        return not self.is_buy

    @property
    def is_sl(self) -> bool:
        return not self.is_tp

class Dashboard:
    '''
    现实中的交易过程是， 同时监听 eurusd h12 h4 的数据， symbol 不一样的情况不需要去重，就不用考虑了
    这样第一种需要去重的情况是，eurusd h4 同时适用于2种以上的策略，那么不同的策略可能会在同样的 candle 产生重复的交易信号，所以相同symbol相同period存在两种以上策略的话，就要去重，
    简单起见，无论是不是2种，只要是相同symbol相同period我都去重
    因为是相同period相同candle，重复的条件是 symbol,period,price,tp,sl,open_time,is_buy 都对应想等

    第二种需要去重的情况是，eurusd h12 的最后一个h4，两个period都产生了交易信号，那么price都是收盘价，难说tp 和 sl不会重复，所以相同symbol不同period也需要去重,
    这种情况下的重复， candle 的 open_time 是不一样的，显然 h12 的 open_time 要比最后一个 h4 早8个小时，
    这种情况重复的条件是 symbol, price, tp, sl, is_buy 都对应想等
    '''
    @staticmethod
    def draw_paral_trade_asset(data_list:list, spread:Decimal, risk_perc:Decimal, init_balance_usd:Decimal, leverage:Decimal, fee_calc:FeeCalculable):
        """
        只画资产走势图
        """
        #只保留有信号的组合
        data_list = [data for data in data_list if data[1]]
        if not data_list:
            return 
        print('start draw paral trade asset')
        # 资产图加上usedmargin图，其他的蜡烛图
        fig = make_subplots(rows=2, cols=1)
        print('start add traces to fig')
        all_tran_list:list[_Transaction] = []
        for data in data_list:
            candle_list, signal_list, peak_set, valley_set = data
            tran_list = Dashboard._get_trans(candle_list, signal_list, spread)
            all_tran_list.extend(tran_list)
        
        tp_cnt, sl_cnt, time_balance_usedmargin_list = Dashboard._summarize_paral_trade_asset_with_alltrans(all_tran_list, risk_perc, init_balance_usd, leverage, fee_calc)
        _, balance_start, _ = time_balance_usedmargin_list[0]
        _, balance_end, _ = time_balance_usedmargin_list[-1]
        date_list = [utc_date(t_sec) for t_sec,_,_ in time_balance_usedmargin_list]
        strtime_list = [date.strftime(STRTIME_FMT) for date in date_list]
        Dashboard._print_paral_trade_asset(tp_cnt, sl_cnt, balance_start, balance_end, strtime_list[0], strtime_list[-1])
        # balance
        print('start draw balance')
        balance_trace = go.Scatter(
            x=strtime_list,
            y=[b for _,b,_ in time_balance_usedmargin_list],
            line=dict(width=1, color='#2962FF')
        )
        # used margin
        print('start draw usermargin')
        used_margin_trace = go.Scatter(
            x=strtime_list,
            y=[um for _,_,um in time_balance_usedmargin_list],
            line=dict(width=1, color='rgba(8, 153, 129, 1)')
        )
        fig.add_trace(balance_trace, row=1, col=1)
        fig.add_trace(used_margin_trace, row=2, col=1)
        layout_update_dict = {
            'plot_bgcolor':'#151924',
            'paper_bgcolor':'#151924',
            'xaxis':{'showgrid':False, 'rangeslider': {'visible': False}, 'showticklabels': False},
            'yaxis':{'showgrid':False, 'domain':[0.2, 1], 'zeroline':False},
            'xaxis2':{'showgrid':False, 'rangeslider': {'visible': False}, 'showticklabels': False},
            'yaxis2':{'showgrid':False, 'domain':[0, 0.2], 'zeroline':False}
        }
        fig.update_layout(**layout_update_dict)
        fig.show()

    @staticmethod
    def draw_paral_trade_symbolperiod_asset(data_list: list, 
                                                  spread:Decimal, 
                                                  risk_perc:Decimal, 
                                                  init_balance_usd:Decimal, 
                                                  leverage:Decimal, 
                                                  fee_calc:FeeCalculable):
        """
        画所有交易对的图, 以及资产走势图
        """
        #只保留有信号的组合
        data_list = [data for data in data_list if data[1]]
        if not data_list:
            return 
        print('start draw paral trade asset')
        # 资产图加上usedmargin图，其他的蜡烛图
        trace_num = len(data_list) + 2
        trace_y_perc = 1.0/trace_num
        trace_title_list = [
            f'{candle_list[0].symstr} {candle_list[0].period}' 
            for candle_list,_,_,_ in data_list
        ]
        trace_title_list.extend(['balance', 'used margin'])
        fig = make_subplots(rows=trace_num, cols=1, subplot_titles=trace_title_list, vertical_spacing=0)
        print('start add traces to fig')
        all_tran_list:list[_Transaction] = []
        for idx, data in enumerate(data_list):
            candle_list, signal_list, peak_set, valley_set = data
            tran_list = Dashboard._get_trans(candle_list, signal_list, spread)
            all_tran_list.extend(tran_list)
            trace_tuple = Dashboard._get_traces(candle_list, signal_list, peak_set, valley_set)
            trace_y_end = min(1.0, 1-idx*trace_y_perc)
            trace_y_start = max(0.0, trace_y_end-trace_y_perc)
            trace_y_domain = [trace_y_start, trace_y_end]
            shape_list = Dashboard._get_shapes(tran_list)
            candle_trace, trend_trace, ema_trace, atr_trace, rsi_trace, buy_trace, sell_trace = trace_tuple
            row = idx+1
            fig.add_traces([candle_trace, trend_trace, ema_trace, buy_trace, sell_trace], rows=row, cols=1)
            layout_update_dict = {
                f'xaxis{idx+1}': {'showgrid':False, 'rangeslider':{'visible':False}, 'showticklabels':False},
                f'yaxis{idx+1}': {'showgrid':False, 'domain':trace_y_domain, 'zeroline':False}
            }
            fig.update_layout(**layout_update_dict)
            [fig.add_shape(shape, row=row, col=1) for shape in shape_list]
        
        tp_cnt, sl_cnt, time_balance_usedmargin_list = Dashboard._summarize_paral_trade_asset_with_alltrans(all_tran_list, risk_perc, init_balance_usd, leverage, fee_calc)
        _, balance_start, _ = time_balance_usedmargin_list[0]
        _, balance_end, _ = time_balance_usedmargin_list[-1]
        date_list = [utc_date(t_sec) for t_sec,_,_ in time_balance_usedmargin_list]
        strtime_list = [date.strftime(STRTIME_FMT) for date in date_list]
        Dashboard._print_paral_trade_asset(tp_cnt, sl_cnt, balance_start, balance_end, strtime_list[0], strtime_list[-1])
        # balance
        print('start draw balance')
        balance_trace = go.Scatter(
            x=strtime_list,
            y=[b for _,b,_ in time_balance_usedmargin_list],
            line=dict(width=1, color='#2962FF')
        )
        # used margin
        print('start draw usermargin')
        used_margin_trace = go.Scatter(
            x=strtime_list,
            y=[um for _,_,um in time_balance_usedmargin_list],
            line=dict(width=1, color='rgba(8, 153, 129, 1)')
        )
        fig.add_trace(balance_trace, row=len(data_list) + 1, col=1)
        fig.add_trace(used_margin_trace, row=len(data_list) + 2, col=1)
        balance_trace_y_end = 1-len(data_list)*trace_y_perc
        balance_trace_y_start = balance_trace_y_end - trace_y_perc
        browser_portrait_height = 2391
        browser_landscape_height = 1255
        trace_height = max(browser_landscape_height/trace_num, 300)
        layout_update_dict = {
            'plot_bgcolor':'#151924',
            'paper_bgcolor':'#151924',
            'height':trace_num*trace_height,
            f'xaxis{len(data_list) + 1}':{'showgrid':False, 'rangeslider': {'visible': False}, 'showticklabels': False},
            f'yaxis{len(data_list) + 1}':{'showgrid':False, 'domain':[balance_trace_y_start, balance_trace_y_end], 'zeroline':False},
            f'xaxis{len(data_list) + 2}':{'showgrid':False, 'rangeslider': {'visible': False}, 'showticklabels': False},
            f'yaxis{len(data_list) + 2}':{'showgrid':False, 'domain':[0, balance_trace_y_start], 'zeroline':False}
        }
        fig.update_layout(**layout_update_dict)
        # Fix subplot's title overlay next subplot
        for idx in range(len(fig.layout.annotations)):
            fig.layout.annotations[idx].update(y=1-idx*trace_y_perc)
        fig.show()

    @staticmethod
    def _print_paral_trade_asset(tp_cnt:int, 
                                 sl_cnt:int, 
                                 balance_start:Decimal, 
                                 balance_end:Decimal,
                                 from_str:str,
                                 to_str:str):
        print(f'\n-------------- paral trade ---------------')
        print(f'{from_str}  {to_str}')
        print(f'tot {tp_cnt + sl_cnt} tp {tp_cnt} sl {sl_cnt}')
        profit_perc = balance_end / balance_start
        print(f"balance from {trunc(balance_start)} to {trunc(balance_end)}, x{trunc(profit_perc)}")
        print(f"net profit {trunc(balance_end - balance_start)}, x{trunc(profit_perc-1)}\n")
        # print(f"balance from {trunc(balance_start)} to {trunc(balance_end)}, {trunc(100 * profit_perc)}%")
        # print(f"net profit {trunc(balance_end - balance_start)}, {trunc(100 * (profit_perc-1))}%\n")
    
    @staticmethod
    def _summarize_paral_trade_asset(data_list: list, spread:Decimal, risk_perc:Decimal, init_balance_usd:Decimal, leverage:Decimal, fee_calc:FeeCalculable) -> tuple:
        #只保留有信号的组合
        data_list = [data for data in data_list if data[1]]
        if not data_list:
            return 
        all_tran_list:list[_Transaction] = [
            tran
            for candle_list, signal_list,_,_ in data_list
            for tran in Dashboard._get_trans(candle_list, signal_list, spread)
        ]
        return Dashboard._summarize_paral_trade_asset_with_alltrans(all_tran_list, risk_perc, init_balance_usd, leverage, fee_calc)

    @staticmethod
    def _summarize_paral_trade_asset_with_alltrans(all_tran_list: list[_Transaction], 
                                                         risk_perc:Decimal, 
                                                         init_balance_usd:Decimal, 
                                                         leverage:Decimal,
                                                         fee_calc:FeeCalculable) -> tuple:
        balance_usd = init_balance_usd
        used_margin_usd = Decimal(0)
        min_risk_amt_usd = init_balance_usd * risk_perc
        time_balance_usedmargin_list:list[tuple] = [] # for drawing line chart
        tp_cnt = 0
        sl_cnt = 0
        pending_tran_list:list[_Transaction] = [] # 去除同 symstr 不同 period 之间，重复下单

        # 相同symbolstr不同period，比如h4和h12，一根h12就是三根h4, 因为是open sec, 如果在第一个h4，都出现了信号，那就是同样的opensec，不同的period，其他的price，tp sl 也可能一样，这种情况会被合并掉了，没问题
        # 但是如果是 第三根 h4, 虽然open_sec 不一样，其他的price，tp sl 也可能一样， 这种情况并不会合并， 那么实际上会是重复的订单
        all_tran_list = sorted(all_tran_list, key=lambda x: x.from_candle_open_sec)
        time_set_list:list[set] = [
            {tran.from_candle_open_sec, tran.to_candle_open_sec}
            for tran in all_tran_list
        ]
        time_set: set[int] = reduce(lambda a,b: a.union(b), time_set_list)
        time_list = sorted(list(time_set))

        def is_tran_pending(tran:_Transaction, pending_tran_list:list[_Transaction]) -> bool:
            for ptran in pending_tran_list:
                if (ptran.price == tran.price and
                    ptran.sl == tran.sl and
                    ptran.tp == tran.tp and
                    ptran.symstr == tran.symstr):
                    return True
            return False


        for t_sec in time_list:
            for tran in all_tran_list:
                # 先平仓释放 used margin
                if tran.to_candle_open_sec == t_sec and tran in pending_tran_list:
                    # 平仓
                    fill_price = tran.sl if tran.is_sl else tran.tp
                    diff_order_amt_quote = tran.unit * abs(fill_price - tran.price)
                    diff_order_amt_usd = diff_order_amt_quote if tran.symstr.quote == 'usd' else diff_order_amt_quote / fill_price
                    # profit or loss
                    balance_usd += (diff_order_amt_usd if tran.is_tp else -diff_order_amt_usd)
                    # commission fee
                    balance_usd += fee_calc.get_commission_fee(tran.order_amt_usd)
                    # swap fee
                    balance_usd += fee_calc.get_swap_fee(tran.symstr, 
                                                               tran.unit/pow(10,5),
                                                               tran.from_candle_open_sec, 
                                                               tran.to_candle_open_sec, 
                                                               tran.is_buy)
                    used_margin_usd = max(0, used_margin_usd - tran.used_margin_usd)
                    time_balance_usedmargin_list.append((t_sec, balance_usd, used_margin_usd))
                    tp_cnt += 1 if tran.is_tp else 0
                    sl_cnt += 1 if tran.is_sl else 0
                    pending_tran_list.remove(tran)
                    print("    <-- closing position")

                elif tran.from_candle_open_sec == t_sec:
                    risk_amt_usd = max(balance_usd * risk_perc, min_risk_amt_usd)
                    free_margin_usd = balance_usd - used_margin_usd
                    tot_risk_amt_usd = reduce(lambda a,b: a+b, [t.risk_amt_usd for t in pending_tran_list]) if pending_tran_list else 0
                    margin_to_risk_usd = free_margin_usd - tot_risk_amt_usd
                    if margin_to_risk_usd >= risk_amt_usd:
                        if is_tran_pending(tran, pending_tran_list):
                            print('pending tran exist')
                        else:
                            # 下单
                            risk_amt_quote = risk_amt_usd if tran.symstr.quote == 'usd' else risk_amt_usd * tran.price
                            unit = risk_amt_quote / abs(tran.sl - tran.price)
                            order_amt_quote = unit * tran.price
                            order_amt_usd = order_amt_quote if tran.symstr.quote == 'usd' else order_amt_quote / tran.price
                            order_used_margin_usd = order_amt_usd / leverage
                            tran.unit = unit
                            tran.risk_amt_usd = risk_amt_usd
                            tran.order_amt_usd = order_amt_usd
                            tran.used_margin_usd = order_used_margin_usd
                            used_margin_usd += order_used_margin_usd
                            time_balance_usedmargin_list.append((t_sec, balance_usd, used_margin_usd))
                            balance_usd += fee_calc.get_commission_fee(order_amt_usd)
                            pending_tran_list.append(tran)
                            print("--> opening position")
                    else:
                        print("no enough free margin to place order")
        return tp_cnt, sl_cnt, time_balance_usedmargin_list
    
    @staticmethod
    def draw_candle_chart(candle_list: list[Candle], 
                          analyst: Analyzable, 
                          peak_set:set[Candle], 
                          valley_set:set[Candle], 
                          spread:Decimal, 
                          draw_signal: bool = True):
        signal_list = analyst.analyze(candle_list, peak_set, valley_set)
        tran_list = Dashboard._get_trans(candle_list, signal_list, spread)
        shape_list = Dashboard._get_shapes(tran_list)
        candle_trace, trend_trace, ema_trace, atr_trace, rsi_trace, buy_trace, sell_trace = Dashboard._get_traces(candle_list, signal_list, peak_set, valley_set)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)

        # row 1
        fig.add_traces([candle_trace, trend_trace, ema_trace], rows=1, cols=1)
        fig.update_layout(
            xaxis=dict(showgrid=False, rangeslider=dict(visible=False)),
            yaxis=dict(showgrid=False, domain=[0.4, 1]),
            plot_bgcolor='#151924',
            paper_bgcolor='#151924'
        )
        if draw_signal:
            fig.add_traces([buy_trace, sell_trace], rows=1, cols=1)
            fig.update_layout(shapes=shape_list)

        # row 2
        fig.add_trace(atr_trace, row=2, col=1)
        fig.update_layout(
            xaxis2=dict(showgrid=False),
            yaxis2=dict(showgrid=False, domain=[0.2, 0.4]),
        )
        # row 3
        fig.add_trace(rsi_trace, row=3, col=1)
        fig.update_layout(
            xaxis3=dict(showgrid=False),
            yaxis3=dict(showgrid=False, domain=[0, 0.2]),
        )
        fig.show()
        tp_cnt, sl_cnt = Dashboard.summarize(candle_list, signal_list)
        tot_cnt = tp_cnt+sl_cnt
        tp_perc = tp_cnt / tot_cnt
        sl_perc = sl_cnt / tot_cnt
        tp_perc_str = f"{(100 * tp_perc):.2f}%"
        sl_perc_str = f"{(100 * sl_perc):.2f}%"
        symstr = candle_list[0].symstr
        period = candle_list[0].period
        from_date = utc_date(candle_list[0].open_sec)
        to_date = utc_date(candle_list[-1].open_sec)
        formatter = "%Y%m%d"
        summ_str = f"{symstr} {period} {analyst.__name__} {from_date.strftime(formatter)} {to_date.strftime(formatter)} total({tot_cnt}) tp({tp_cnt})({tp_perc_str}) sl({sl_cnt})({sl_perc_str})"
        print(f'\n{summ_str}')

    @staticmethod
    def _get_traces(candle_list: list[Candle],
                    signal_list: list[Signal],
                    peak_set:set[Candle],
                    valley_set:set[Candle]) -> tuple:
        df = pd.DataFrame(dict(
            st=[c.strtime for c in candle_list],
            o=[c.o for c in candle_list],
            h=[c.h for c in candle_list],
            l=[c.l for c in candle_list],
            c=[c.c for c in candle_list]
        ))
        green = '#089981'
        red = '#F23645'
        candle_trace = go.Candlestick(
            x=df.st,
            open=df.o,
            high=df.h,
            low=df.l,
            close=df.c,
            increasing=dict(line=dict(color=green, width=1), fillcolor=green),
            decreasing=dict(line=dict(color=red, width=1), fillcolor=red)
        )
        #draw ema
        blue = '#2962FF'
        emas = get_emas(list(df.c), win=60)
        ema_trace = go.Scatter(
            x=df.st,
            y=emas,
            line=dict(width=1, color=blue)
        )
        #draw atr
        atr_list = get_atrs(list(df.h), list(df.l), list(df.c), win=14)
        atr_trace = go.Scatter(
            x=df.st,
            y=atr_list,
            line=dict(width=1, color='rgba(8, 153, 129, 1)')
        )
        #draw rsi
        rsi_list = get_rsis(list(df.c), win=7)
        rsi_trace = go.Scatter(
            x=df.st,
            y=rsi_list,
            line=dict(width=1, color='rgba(8, 153, 129, 1)')
        )

        #draw trends
        peak_valley_set = {*peak_set, *valley_set}
        trend_trace = go.Scatter(
            x=[c.strtime for c in candle_list if c in peak_valley_set],
            y=[c.c for c in candle_list if c in peak_valley_set],
            line=dict(width=1, color='rgba(41, 98, 255, 0.5)')
        )
        # draw buy signals
        yellow = '#ffff3f'
        buy_sec_set = set([s.candle_sec for s in signal_list if s.is_buy])
        buy_candle_list = [c for c in candle_list if c.open_sec in buy_sec_set]
        buy_trace = go.Scatter(
            x=[c.strtime for c in buy_candle_list],
            y=[c.c for c in buy_candle_list],
            mode='markers',
            marker=dict(size=10, color=yellow, symbol='triangle-up')
        )
        # draw sell signals
        sell_sec_set = set([s.candle_sec for s in signal_list if not s.is_buy])
        sell_candle_list = [c for c in candle_list if c.open_sec in sell_sec_set]
        sell_trace = go.Scatter(
            x=[c.strtime for c in sell_candle_list],
            y=[c.c for c in sell_candle_list],
            mode='markers',
            marker=dict(size=10, color=yellow, symbol='triangle-down')
        )
        # draw signals's tp and sl transactions
        return candle_trace, trend_trace, ema_trace, atr_trace, rsi_trace, buy_trace, sell_trace

    @staticmethod
    def summarize(candle_list: list[Candle],
                  signal_list: list[Signal],
                  spread:Decimal,
                  min_perc: Decimal = None) -> tuple:
        if candle_list and signal_list:
            tran_list = Dashboard._get_trans(candle_list, signal_list, spread)
            buy_tp_cnt = len([tran for tran in tran_list if tran.is_buy and tran.is_tp])
            buy_sl_cnt = len([tran for tran in tran_list if tran.is_buy and tran.is_sl])
            sell_tp_cnt = len([tran for tran in tran_list if tran.is_sell and tran.is_tp])
            sell_sl_cnt = len([tran for tran in tran_list if tran.is_sell and tran.is_sl])
            total_buy_cnt = buy_tp_cnt + buy_sl_cnt
            total_sell_cnt = sell_tp_cnt + sell_sl_cnt
            total_fill_cnt = total_buy_cnt + total_sell_cnt
            total_tp_cnt = buy_tp_cnt + sell_tp_cnt
            total_sl_cnt = buy_sl_cnt + sell_sl_cnt
            if total_fill_cnt:
                total_tp_perc = total_tp_cnt / total_fill_cnt
                if ((min_perc is not None and total_tp_perc >= min_perc) or min_perc is None):
                    return total_tp_cnt, total_sl_cnt

    @staticmethod
    def _get_shapes(tran_list:list[_Transaction]) -> list[dict]:
        green = '#089981'
        red = '#F23645'
        shape_list = []
        for tran in tran_list:
            from_date = utc_date(tran.from_candle_open_sec)
            to_date = utc_date(tran.to_candle_open_sec)
            x0 = from_date.strftime(STRTIME_FMT)
            y0 = tran.price
            x1 = to_date.strftime(STRTIME_FMT)
            tp_opacity = 0.5 if tran.is_tp else 0.1
            sl_opacity = 0.5 if tran.is_sl else 0.1
            # drawing take-profit transactions
            tp_shape = {
                'type': 'rect',
                'xref': 'x',
                'yref': 'y',
                'x0': x0,
                'y0': y0,
                'x1': x1,
                'y1': tran.tp,
                'fillcolor': green,
                'line_color': green,
                'line_width': 1,
                'opacity': tp_opacity
            }
            sl_shape = {
                'type': 'rect',
                'xref': 'x',
                'yref': 'y',
                'x0': x0,
                'y0': y0,
                'x1': x1,
                'y1': tran.sl,
                'fillcolor': red,
                'line_color': red,
                'line_width': 1,
                'opacity': sl_opacity
            }
            shape_list.extend([tp_shape, sl_shape])
        return shape_list

    @staticmethod
    def _get_trans(candle_list: list[Candle],
                   signal_list: list[Signal],
                   spread:Decimal) -> list[_Transaction]:
        # 同一个 symbol period 的一根蜡烛，不会同时 buy 和 sell 信号出现， 一个 open_sec 确实只应该出现一个信号
        signal_dict = {signal.candle_sec: signal for signal in signal_list}
        pending_signal_set = set()
        tran_list: list[_Transaction] = []
        symstr = candle_list[0].symstr
        spread_price = spread/(100 if symstr.quote == 'jpy' else pow(10, 4))
        # candle's price actually is middle of ask/bid. so use half spread to calc
        half_spread_price = spread_price/2
        for candle in candle_list:
            rm_list = []
            for ps in pending_signal_set:
                tran = _Transaction(from_candle_open_sec=ps.candle_sec,
                                 is_buy=ps.is_buy,
                                 sl=ps.sl,
                                 tp=ps.tp,
                                 price=ps.price,
                                 to_candle_open_sec=candle.open_sec,
                                 symstr=ps.symstr)
                # so consider spread, it's easier to stop-loss, harder to take-profit
                if ps.is_buy:
                    if candle.l-half_spread_price <= ps.sl:
                        tran.is_tp = False
                    elif candle.h-half_spread_price >= ps.tp:
                        tran.is_tp = True
                    else:
                        tran = None
                else:
                    if candle.h+half_spread_price >= ps.sl:
                        tran.is_tp = False
                    elif candle.l+half_spread_price <= ps.tp:
                        tran.is_tp = True
                    else:
                        tran = None
                if tran is not None:
                    tran_list.append(tran)
                    rm_list.append(ps)
            [pending_signal_set.remove(ps) for ps in rm_list]
            signal = signal_dict.get(candle.open_sec)
            if signal:
                pending_signal_set.add(signal)
        return tran_list

