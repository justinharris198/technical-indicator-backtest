#Python Based Technical Indicator Backtest

I. Introduction

Most backtest solutions focus primarily on the entry signal without enough attention paid to the holding period and exit signal. Other backtests will have the user either long or short without a choice of neutral. For a backtest to be truly adequate, it must incorporate a trade signal, holding that trade until an exit is signaled, and incorporating a sizing methodology into the analysis. Most backtests don't allow for this and measure on a daily basis. This software measures for trades regardless of the time frame.

This backtest measures true trade profitability by generating an open price, an intial stop loss, sizes the position based open price and initial stop.
