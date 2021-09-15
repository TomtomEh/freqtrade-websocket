# Websocket for Freqtrade Strategy
The goal of this project is to provide an alternative way to get realtime data from Binance and use it in freqtrade despite the exchange used.
It also uses talipp for computing 
## Features
- Live Ticker
- Live Order Book Data
- Live Candles
## Requirements
- python-binance
- talipp
## Advantages over using standard freqtrade data
Freqtrade data is obtained using requests: it asks for new data and then it will receive the results. Using websockets you will get the pair information pushed from binance servers as soon as they are computed. For instance, while testing using about 100 pairs, freqtrade took almost one minute to start computing the new candle, while using this approach in 3s all pairs were already processed.

Using talipp reduce the computation power required, since data are update by only adding the contribution of the new candle to the already computed data. While freqtrade computes the indicators on their integrity and by default for 1000 timeframes.

With a minimal change (see bellow) one can trigger a buy or sell directly from the function that computes the signal, reducing even more the time between taking decision and executing a trade. Also this option allow to choose the buy and sell prices inside the strategy (for instance using the orderbook information).

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
## Callback data
###  new_ticker
New ticker data is exactly as provided by the Binance API:
```json
   
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
           
```

## How to keep it running in case of failure
Websockets can get closed, or connection can be lost, managing it indivudually can be a source of problems and error prone. The solution employed is simply exit freqtrade as soon as there is a problem, so you can use a shell script that will restart it automatically:
```bash
while :
do
  freqtrade  trade       --config config.json --config config_obonly_dr.json    --db-url sqlite:///tradesv3_wild.sqlite
  sleep 10
done

```
## Hints
- Use a large timeframe on freqtrade (1h) to avoid it fetching data too often, and get the desired timeframe from BaseIndicator 
