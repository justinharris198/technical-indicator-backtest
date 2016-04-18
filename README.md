#Python Based Technical Indicator Backtest

#I. Introduction

I introduced this software because I found other programs lacking. Problems I've found while looking for backtesting solutions include:

1. Easily pulling time series data from a source for an aggregated analysis (only allowing for analysis on one instrument at a time)
2. Missing a stop loss methodology completely
3. Not incorporating sizing decisions into the software
4. Handling entry as a daily decision, not entry as initiation of a trade that persists until an exit condition is triggered, regardless of the time frame
5. Missing the important metrics to judge the profitability of the system over time
6. Not incorporating enough history to judge if profitability is increasing or decreasing over time
7. Ease of implementation

So I created this software that takes these things into account:

1. Pulls from Quandl and can run an aggregated analysis on any number of securities
2. Incorporates a stop loss methodology as technical time series that dynamically change for trailing stop methodologies as well as event driven stop losses that can trigger if an event occurs, such as an adx min/plus crossover
3. The percent of portfolio risked on each trade is defined at the beginning of the script. The size is calculated as dollar risked on trade divided by the distanct from open to the stop, so that if the stop is hit and the exit price is the stop price, than the loss to the account will equal the percent risked on the trade.
4. Trades are initiated with a trade signal produced by an event or a time series crossing another time series. Once the trade is initiated, the trade remains in place until a stop is realized, regardless of the time frame.
5. The important metrics, for me at least, are win percent, win to loss ratio, average time frame of each trade, max drawdown, volatility, average profit to amount risked on each trade. With these numbers, you can run risk analytics to judge one methodology over another. I also include graphs that show the profitability over time analyze if strategies lose eficacy over time.
6. Using Quandl data, especially time series with data going back to 1950, we can truly guage if our model works or if we found a short run anomaly.
7. Changing 3 items in the analysis will render a custom analysis. Essentially, this software is supposed to be easy enough where the only items that need to be edited are the initial user defined inputs (initial portfolio level, time frame, etc), the entry condition, and the exit condition. No more no less, and no need to have to learn a programming language to start running strategy analyses.

#II. Specifying the entry condition (with example)

1. Scroll to entry_model()
2. Create a pandas dataframe time series that will act as the condition. For example, if testing a moving average model, you could use ta-lib or pandas mean(). When I tested, I used pandas mean() to find the price average over a certain number of days. The script will input the data pulled from quandl into this function for the analysis, so when defining the function you want to test, use either security_time_series['Settle'],security_time_series['Open'],security_time_series['High'] or security_time_series['Low'] as the price series input.
3. Name your data.
4. Concatenate the time series onto security_time_series.
5. Define the signal in trade_trigger()

Case study: Enter long into a security when price closes above the 200 day moving average. Enter short into a security when price closes above the 200 day moving average.
1. Find entry_model()
2. Pandas has a mean function which outputs a Series. We need to have a Dataframe, so this will be a 2 step process. Defining the mean, we have ma = pd.rolling_mean(security_time_series['Settle'],200), which gives the 200 day moving average. Translating into the right format we have ma = pd.DataFrame(ma,index=security_time_series.index). The 'index = security_time_series.index' just verifies that we use the same dates for both series, so when we join them together, we'll have the correct average on the right dates.
3. Name the column, ma.columns = ['moving_average_two_hundred_days']
4. Add the time series ma to the list in h = pd.concat([security_time_series,...,])
5. Define the trade trigger criteria. In this case, the trigger needs to be when the settle price is > than the moving average for a long and < moving average for a short. Long: h['Settle'] > h['moving_average_two_hundred_days']. Long: h['Settle'] < h['moving_average_two_hundred_days'].

That's it! The entry has been set!

#III. Specifying the exit signal.

1. Find exit_model()
2. Create pandas dataframe time series which will serve as the exit condition.
3. Name the new time series.
4. Define an exit condition that overrides the initial stop.
5. Concatenate the time series.
6. Update short() and long() for complex stops (ie adx min/plus crossover). If there is no complex logic, set return in short and long to slp and ssp respectively. The script is set up to follow the simple stop, or to equal the close if the complex logic is hit.

#IV. Run the model.

The model will output into an excel spreadsheet labeled strategy_analysis.xlsx in the same folder as the python script.
