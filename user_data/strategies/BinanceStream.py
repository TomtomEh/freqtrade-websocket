import time
from talipp.indicators.Indicator import Indicator
from binance import Client
from binance import ThreadedWebsocketManager, ThreadedDepthCacheManager
from datetime import datetime, timedelta
from freqtrade.strategy.interface import IStrategy, SellCheckTuple, SellType
from freqtrade.persistence import Trade
from pandas import DataFrame

time_map={
    "1m":60,
    "5m":5*60,
    "15m":15*60,
    "30m":30*60,
    "1h":60*60,
}
keys_map={
    "o":1,
    "h": 2,
    "l":3,
    "c":4,
    "v":5
}
_register = {}
class BasePairInfo: 
    ft= None
    _data={}
    last_check = None

    def __init__(self,pair):
        self.buy_signal=0
        self.pair=pair
        self.sell_signal=0
        self.should_buy=False
        self.should_sell=False
        self.last_check = datetime.now()

    @classmethod
    def get(cls,pair):
        key=pair.replace("/","")
        res = cls._data.get(key,None)
        return res  
    @classmethod
    def set(cls,pair,val):
        key=pair.replace("/","")
        cls._data[key]=val
     
    @classmethod
    def heartbeat(cls):
        now = datetime.now()
        if cls.last_check is None:
            cls.last_check = now
            return
        if(now - cls.last_check)>timedelta(minutes=5):
            for key,val in cls._data.items():
                if(now - val.last_check)>timedelta(minutes=5):
                    if BaseIndicator.twm is not None:
                        BaseIndicator.twm.stop()
                    if OrderBook.dcm is not None:
                        OrderBook.dcm.stop()
                    exit(0)   

            cls.last_check = now
            
         
                        
                    
    def open_trade(self,pair):
        trade_filter = []
        trade_filter.append(Trade.is_open.is_(True))
        query = Trade.get_trades()
        
        _open_trades = query.populate_existing().filter(*trade_filter).all()
        found_trade = None
        for trade in _open_trades :
            if trade.pair.replace("/","") == pair.replace("/",""):
                found_trade = trade
        return found_trade
    
    def execute_sell(self, price, reason):
        sell_reason=SellCheckTuple(sell_type=reason)
      
        with self.ft._sell_lock:
            trade=self.open_trade(self.pair)
            

            if not trade:
                return
            if price is None:
                price = self.ft.get_sell_rate(trade.pair, True)    
            for a in trade.orders:
                if a.status == 'open':
                    return
            if trade and  trade.is_open: 
    
                self.ft.execute_sell(trade,price,sell_reason)
                try:
                    pass
                except Exception as e:
                    print(e)  
    def execute_buy(self,price):
        found_trade = self.open_trade(self.pair) 
        if found_trade:
            return

        stake_amount = self.ft.wallets.get_trade_stake_amount(self.pair)

        try:
            self.ft.execute_buy(self.pair,stake_amount,price)
        except Exception as e:
            print(e)  
                            
    def buy(self,price=None):
        if self.ft:
            self.execute_buy(price)
        else:
            self.should_buy=True   
    def check_buy(self):
        res=self.should_buy
        self.should_buy=False
        return res    
    def sell(self,price=None,reason = SellType.SELL_SIGNAL):
        if self.ft:
            self.execute_sell(price,reason)
        else:
            self.should_sell=True   
    
   
     
    def check_sell(self):
        res=self.should_sell
        self.should_sell=False
        return res    
    
    @classmethod
    def set_ft(cls,ft):
        cls.ft=ft    

class BinanceStream(IStrategy):
    _pair_info={}
    _init=False
    @classmethod
    def set_instance(cls,inst):
        cls.instance=inst    
    def new_ob(self,pair_info,ob):
        pass   
    def new_candle(self,pair_info):
        pass
    def init(self):
        if self._init:
            return 
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
    def set_ft(self,ft):
        self.ft=ft  
        BasePairInfo.set_ft(ft)
    
    def heartbeat(self):
        BasePairInfo.heartbeat()
    
    def bot_loop_start(self, **kwargs) -> None:
        self.init()

        self.heartbeat()
    
    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair=metadata["pair"]    
        shoud_buy=self.get_pair(pair).check_buy()
        if shoud_buy:
            self.unlock_pair(pair)
            dataframe.loc[dataframe.index.max(),"buy"]=1 
        else:
            dataframe.loc[dataframe.index.max(),"buy"]=0
        return dataframe
    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair=metadata["pair"]
        shoud_sell=self.get_pair(pair).check_sell()
        if shoud_sell:
            dataframe.loc[dataframe.index.max(),"sell"]=1 
        else:
            dataframe.loc[dataframe.index.max(),"sell"]=0
        return dataframe


    def get_pair(self,pair):
        res = BasePairInfo.get(pair)
        if res is None:
            BinanceStream.set_instance(self)
            BasePairInfo.set(pair,BasePairInfo(pair))

            self.init_pair_info(BasePairInfo.get(pair))
        return res  
    def init_pair_info(self,pair_info):
        pass      
    def check_buy(self,pair):
        return BasePairInfo.get(pair).check_buy()
    def check_sell(self,pair):
        return BasePairInfo.get(pair).check_sell()
    def sell(self,pair,price=None,reason = SellType.SELL_SIGNAL):
        BasePairInfo.get(pair).sell(price,reason)
     
     
    def new_ticker(self,pair_info,ticker):
        
        """
        Message format:
        {
        "e": "kline",     // Event type
        "E": 123456789,   // Event time
        "s": "BNBBTC",    // Symbol
        "k": {
            "t": 123400000, // Kline start time
            "T": 123460000, // Kline close time
            "s": "BNBBTC",  // Symbol
            "i": "1m",      // Interval
            "f": 100,       // First trade ID
            "L": 200,       // Last trade ID
            "o": "0.0010",  // Open price
            "c": "0.0020",  // Close price
            "h": "0.0025",  // High price
            "l": "0.0015",  // Low price
            "v": "1000",    // Base asset volume
            "n": 100,       // Number of trades
            "x": false,     // Is this kline closed?
            "q": "1.0000",  // Quote asset volume
            "V": "500",     // Taker buy base asset volume
            "Q": "0.500",   // Taker buy quote asset volume
            "B": "123456"   // Ignore
        }
        }
        """       
        pass         
   
ohlcv=["o","h","l","c","v"]

class OrderBook:
    dcm=None
    _class_init= False 
    _backtesting=False
    @classmethod
    def class_init(cls):
        cls._class_init=True
        if not cls._backtesting:
          cls.dcm = ThreadedDepthCacheManager()
          cls.dcm.setDaemon(True)
          cls.dcm.start()
    def __init__(self,symbol,max_depth=500,currency=None):
        self.strat=BinanceStream.instance
        if(OrderBook._class_init == False):
            OrderBook.class_init() 
        self.symbol=symbol.replace("/","")     
        if currency is not None:
           self.data_symbol=symbol.split("/")[0]+currency
        else:
            self.data_symbol=self.symbol
        
        while True:
            try:
                self.dcm.start_depth_cache(callback=self.handle_dcm_message, symbol=self.data_symbol,limit=max_depth)
                break
            except :
                print(f"Starting order book for {symbol}.")        
                time.sleep(0.5)
                 
    def handle_dcm_message(self,depth_cache):
        t=datetime.fromtimestamp(depth_cache.update_time/1e3)
        if datetime.now()>(t+timedelta(seconds=1)):
                return
        self.cache=depth_cache
        
        self.strat.new_ob(self.strat.get_pair(self.symbol),depth_cache)


class SimpleIndicator(Indicator):
     
     def _calculate_new_value(self):
        if len(self.input_values) > 0:
            return self.input_values
        return None 
class BaseIndicator:
    _class_init=False
    registered={}
    _backtesting=False
    not_initialized=True  
    twm=None         
    @classmethod
    def class_init(cls):
        cls._class_init=True
        if not cls._backtesting:
            cls.twm = ThreadedWebsocketManager()
            cls.twm.setDaemon(True)
            cls.twm.start()
    def _calculate_new_value(self):
        if len(self.input_values) > 0:
            return self.input_values
        return None
    def __init__(self,symbol,prefetch=True,timeframe="1m",min_hist=100,currency=None): 
 
        if(BaseIndicator._class_init == False):
            BaseIndicator.class_init() 
        self.strat=BinanceStream.instance
    
        self.symbol=symbol.replace("/","")     
        if currency is not None:
           self.data_symbol=symbol.split("/")[0]+currency
        else:
            self.data_symbol=self.symbol
        
        self.prefetch=prefetch
        self.timeframe =timeframe
        self.min_hist=min_hist
        self.path = BaseIndicator.get_path(symbol, timeframe)
        for f in ohlcv:
            setattr(self, f, SimpleIndicator())
       
        if not self._backtesting:
            self.sock=self.twm.start_kline_socket(callback=self.process_message, symbol=self.data_symbol,interval=timeframe)
            time.sleep(0.5)
        
    def process_message(self, msg):

        if msg['e'] == 'error':
            print("socket error!!!")
        else:
            k=msg["k"]
            pi=self.strat.get_pair(self.symbol)
            pi.last_check=datetime.now()
            if self.not_initialized and self.prefetch:
                client = Client()
                tf=time_map[self.timeframe]*1000 
                end=int(k["t"])+2*tf
                start=end-tf*self.min_hist
                res=client.get_klines(symbol=self.data_symbol, interval=self.timeframe,startTime=start,endTime=end) 
                
                
                for a in res:
                    for f in ohlcv:
                        val = a[keys_map[f]]
                        getattr(self, f).add_input_value(float(val))
                self.strat.new_candle(pi)
                self.not_initialized = False
            else:   
                if k["x"]:
                    for f in ohlcv:
                        indicator=getattr(self, f)
                        indicator.add_input_value(float(k[f]))
                        if(len(indicator)>2*self.min_hist):
                            indicator.purge_oldest(self.min_hist)
                    self.strat.new_candle(pi)
                else:
                    t=datetime.fromtimestamp(int(msg["E"])/1e3)
                    if datetime.now()>(t+timedelta(seconds=1)):
                        return
                    self.strat.new_ticker(pi,k)    
    @staticmethod
    def get_path(symbol, interval):
        return f'{symbol.lower()}@kline_{interval}'

