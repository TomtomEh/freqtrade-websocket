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
