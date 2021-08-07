import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy 
from freqtrade.strategy import timeframe_to_prev_date
import os
from pandas import DataFrame
from datetime import datetime, timedelta
from freqtrade.data.converter import order_book_to_dataframe
from talipp.indicators import EMA, SMA ,BB,RSI

from user_data.strategies.BinanceStream import BaseIndicator, BasePairInfo, OrderBook



class PairInfo(BasePairInfo):
    def __init__(self,pair):
        super().__init__(pair)
        self.bi=BaseIndicator(pair,timeframe="5m",currency="USDT")
        self.bb_40=BB(40,2.0,input_indicator=self.bi.c) #Attach BB to the base close indicator
        self.bb20=BB(20,2.0,input_indicator=self.bi.c) 
        self.ema_slow=EMA(50,input_indicator=self.bi.c)
        self.volume_mean_slow=SMA(30,input_indicator=self.bi.v)
        self.rsi=RSI(9,input_indicator=self.bi.c)
        self.ob=OrderBook(pair,currency="USDT")
        self.indicators_buy = False
        self.ticker_buy =False
    def new_ticker(self, candle):
        last_price = float(candle["c"]) 
        if last_price > self.bi.c[-1][-1]:
            self.ticker_buy = True
        else:
            self.ticker_buy = False
            
    delta_bid = 0.002
    delta_ask = 0.002
    ob_ratio = 1.3    
    def new_ob(self,depth_cache):
        if  not self.ticker_buy or not self.indicators_buy:
            return 
        bids=np.array(depth_cache.get_bids())
        asks=np.array(depth_cache.get_asks())
        mid_price=(0.5*bids[0][0]+0.5*asks[0][0])
        bid_cut = mid_price - mid_price*delta_bid
        ask_cut = mid_price + mid_price*delta_ask
        bid_side=bids[bids[:,0]>bid_cut]
        ask_side=asks[asks[:,0]<ask_cut]
        wall_side=bid_side
        asum=ask_side[:,1].sum() 
        bsum=bid_side[:,1].sum() 
        if bsum > ob_ratio*asum:
            self.buy()    
    
    def new_candle(self):
        bbdelta = self.bb_40[-1].cb - self.bb_40[-1].lb
        close = self.bi.c[-1][-1]
        close_prev=self.bi.c[-2][-1]
        closedelta = abs(close - close_prev)
        tail = abs(self.bi.c[-1][-1] - self.bi.l[-1][-1]) 
        volume = self.bi.v[-1][-1]
        
        buy_condition = ((  
            self.bi.l[-2][0] > 0 
            and  bbdelta > (close* 0.0084)
            and  closedelta>(close * 0.0175) 
            and  tail < (bbdelta * 0.25) 
            and  close<self.bb_40[-2].lb 
            and  close<self.bi.c[-2][0] 
        )
        |
        (   close < self.ema_slow[-1] 
            and  close < 0.985 * self.bb20[-1].lb 
            and  volume < self.volume_mean_slow[-2] * 20 
           
        ))
       
        if buy_condition:
           self.indicators_buy = True
        else:
           self.indicators_buy = False
            

        sell_condition=(
            close > self.bb20[-1].ub and
            close_prev > self.bb20[-2].ub and
            volume > 0 
        )

        if sell_condition:
            self.sell()
        
class CombinedBinHAndClucV4WS(IStrategy):
    INTERFACE_VERSION = 2

    minimal_roi = {
        "0": 0.018
    }

    stoploss = -0.9 # effectively disabled.

    timeframe = '1h'
    compute_original=False
    # Sell signal
    use_sell_signal = True
    sell_profit_only = True
    sell_profit_offset = 0.001 # it doesn't meant anything, just to guarantee there is a minimal profit.
    ignore_roi_if_buy_signal = True

    # Trailing stoploss
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.007
    trailing_stop_positive_offset = 0.018

    # Custom stoploss
    use_custom_stoploss = False

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 50

    
   
   
    def bot_loop_start(self, **kwargs) -> None:
        PairInfo.heartbeat()
    def set_ft(self,ft):
        PairInfo.set_ft(ft)
    def confirm_trade_exit(self, pair: str, trade: 'Trade', order_type: str, amount: float,
                           rate: float, time_in_force: str, sell_reason: str,
                           current_time: 'datetime', **kwargs) -> bool:
        if rate < trade.open_rate:
            return False
        return True
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair=metadata["pair"]    
        shoud_buy=PairInfo.get(pair).check_buy()
        if shoud_buy:
            self.unlock_pair(pair)
            dataframe.loc[dataframe.index.max(),"buy"]=1 
        else:
            dataframe.loc[dataframe.index.max(),"buy"]=0
        return dataframe
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair=metadata["pair"]
        shoud_sell=PairInfo.get(pair).check_sell()
        if shoud_sell:
            dataframe.loc[dataframe.index.max(),"sell"]=1 
        else:
            dataframe.loc[dataframe.index.max(),"sell"]=0
        return dataframe
