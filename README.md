# Freqtrade Websocket Strategy
The goal of this project is to provide an alternative way to get realtime data from Binance and use it in freqtrade despite the exchange used.
It also uses talipp for computing 
## Features
- Live Ticker
- Live Order Book Data
- Live Candles
## Advantages over using standard freqtrade data
Freqtrade data is obtained using requests, so that it asks for new data and then it will receive the results. Using websockets you will get the pair information pushed from binance servers as soon as they are computed. For instance, while testing using about 100 pairs, freqtrade took almost one minute to start computing the new candle, while using this approcach in 3s all pairs were already processed.

Using talipp reduce the computation power required, since data are update by only adding the contribution of the new candle to the already computed data. While freqtrade computes the indicators on their integrity and by default for 1000 timeframes.

With a minimal change (see bellow) one can trigger a buy directly from the signal reducing even more the time between taking decision and buying. Also this option allow to choose the buy and sell prices in the strategy (for instance using the orderbook information)

## How to use it 
CombinedBinHAndClucV4WS is an example of using this interface to code a strategy. In a few words what you need is:
- Inherit from BinanceStream class
- Implement init_indicators method to initialize the websocket stream and setup the indicators
- Implement new_candle, new_ob or new_ticker to process new data (be carefull with the amount of computation, you will usually have a call every second)
- Call pair_info.buy() and pair_info.sell() to trigger a buy or a sell
# How to directly trigger a buy and sell and choose the price.
To directly trigger a buy or sell, BinanceStream must have a refernce to the freqtradebot class. 
It requires adding the following line into freqtradebot.py:
```python       
self.strategy.set_ft(self)
```

around line 66
```python
        # Cache values for 1800 to avoid frequent polling of the exchange for prices
        # Caching only applies to RPC methods, so prices for open trades are still
        # refreshed once every iteration.
        self._sell_rate_cache: TTLCache = TTLCache(maxsize=100, ttl=1800)
        self._buy_rate_cache: TTLCache = TTLCache(maxsize=100, ttl=1800)

        self.strategy: IStrategy = StrategyResolver.load_strategy(self.config)
        self.strategy.set_ft(self) 

        # Check config consistency here since strategies can set certain options
        validate_config_consistency(config)
        ```
