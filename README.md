#Python Based Technical Indicator Backtest

#I. Introduction

I introduced this software because I found other programs lacking. Problems I've found while looking for backtesting solutions include:

1. Easily pulling time series data from a source for an aggregated analysis (only allowing for analysis on one instrument at a time)
2. Missing a stop loss methodology completely
3. Not incorporating sizing decisions into the software
4. Handling entry as a daily decision, not entry as initiation of a trade that persists until an exit condition is triggered, regardless of the time frame
5. Missing the important metrics to judge the profitability of the system over time
6. Not incorporating enough history to judge if profitability is increasing or decreasing over time

So I created this software that takes these things into account:
1. Pulls from Quandl and can run an aggregated analysis on any number of securities
2. Incorporates a stop loss methodology as technical time series that dynamically change for trailing stop methodologies as well as event driven stop losses that can trigger if an event occurs, such as an adx min/plus crossover
3. The percent of portfolio risked on each trade is defined at the beginning of the script. The size is calculated as dollar risked on trade divided by the distanct from open to the stop, so that if the stop is hit and the exit price is the stop price, than the loss to the account will equal the percent risked on the trade.
4. Trades are initiated with a trade signal produced by an event or a time series crossing another time series. Once the trade is initiated, the trade remains in place until a stop is realized, regardless of the time frame.
5. The important metrics, for me at least, are win percent, win to loss ratio, average time frame of each trade, max drawdown, volatility, average profit to amount risked on each trade. With these numbers, you can run risk analytics to judge one methodology over another. I also include graphs that show the profitability over time analyze if strategies lose eficacy over time.
6. Using Quandl data, especially time series with data going back to 1950, we can truly guage if our model works or if we found a short run anomaly.
