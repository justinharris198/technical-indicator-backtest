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
2. 
