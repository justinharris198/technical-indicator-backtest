# -*- coding: utf-8 -*-
"""
Created on Mon Nov 02 16:46:02 2015

@author: jharris
"""
import Quandl
import datetime as d
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import sys as sys
import pandas.io.sql as pds
import psycopg2
import datetime as d
import math
import talib
pd.options.mode.chained_assignment = None
#user defined inputs
quandl_authtoken = ''
tested_securities = ['CURRFX/AUDUSD','CURRFX/EURUSD']
start_date = d.date(1960,01,01)
end_date = d.date(2015,12,01)

### Part I ###
'''
In this section, we define a series of functions that pulls the data from quandl, 
transforms that into a standardized data frame, performs the analysis, and then 
calculates a hypothetical portfolio based on the trades signaled
'''
#this pulls the quandl data and standardizes for the analytics process
def get_quandl_data_and_standardize(security,start_date,end_date):
    start_date = start_date
    end_date = end_date
    quandl_data = Quandl.get(security, authtoken = quandl_authtoken, collapse = 'daily', trim_start=start_date, trim_end=end_date)
    if 'CURRFX' in security:
        quandl_data = pd.concat([quandl_data['Rate'],quandl_data['Rate'],quandl_data['Rate'],quandl_data['Rate']],axis = 1, join='inner')
        quandl_data.columns = ['Open','High','Low','Settle']
    elif 'SCF' in security:
        quandl_data = quandl_data.drop(['Volume','Prev. Day Open Interest'], axis=1)
    else:
        sys.exit('Unsupported Dataset')
    quandl_data = quandl_data.fillna(0)
    quandl_data = quandl_data[quandl_data.Settle != 0]
    return quandl_data
#some algorithm that outputs
def risk_metrics(stst_risk):
    margin = 0
    quote = 0
    dollar_per_quote = 0
    def set_values(h,value):
        h[0] = value        
        return value
    marginpd = pd.DataFrame(np.zeros(len(stst_risk.index)),columns=['margin'],index = stst_risk.index)
    quotepd = pd.DataFrame(np.zeros(len(stst_risk.index)),columns=['quote'],index = stst_risk.index)
    dollar_per_quotepd = pd.DataFrame(np.zeros(len(stst_risk.index)),columns=['dollar_per_quote'],index = stst_risk.index)
    stst_risk = pd.concat([stst_risk,marginpd,quotepd,dollar_per_quotepd],axis=1)
    stst_risk['margin'] = margin
    stst_risk['quote'] = quote
    stst_risk['dollar_per_quote'] = dollar_per_quote
    return stst_risk
def trade_tracker(stst_stop,dollar_risk):
    trade_tracker = pd.DataFrame(pd.Series(np.zeros(len(stst_stop.index)),index=stst_stop.index),columns=['trade_tracker'])
    trade_open = pd.DataFrame(pd.Series(np.zeros(len(stst_stop.index)),index=stst_stop.index),columns=['trade_open'])
    adx_trade = pd.DataFrame(pd.Series(np.zeros(len(stst_stop.index)),index=stst_stop.index),columns=['adx_trade'])
    adx_dm15_trade = pd.DataFrame(pd.Series(np.zeros(len(stst_stop.index)),index=stst_stop.index),columns=['mar_trade'])
    trade_close = pd.DataFrame(pd.Series(np.zeros(len(stst_stop.index)),index=stst_stop.index),columns=['trade_close'])
    running_profit = pd.DataFrame(pd.Series(np.zeros(len(stst_stop.index)),index=stst_stop.index),columns=['running_profit'])
    days_in_trade = pd.DataFrame(pd.Series(np.zeros(len(stst_stop.index)),index=stst_stop.index),columns=['days_in_trade'])
    stop_methodology = pd.DataFrame(pd.Series(np.zeros(len(stst_stop.index)),index=stst_stop.index),columns=['stop_methodology'])
    stst_stop = pd.concat([stst_stop,trade_tracker,trade_open,running_profit,days_in_trade,trade_close,stop_methodology,adx_trade,adx_dm15_trade],axis=1)
        #sift through and construct daily portfolios
        #start with beginning positions, add, end with 
        #portfolio value daily to plot at end of analysis
#need to add logic for running stop. Stop resets daily right now.
    for i in range(2,len(stst_stop.index)):
#in trade logic long
        if stst_stop['trade_tracker'][i-1] == 1 and stst_stop['trade_close'][i-1] == 0:
            if stst_stop['days_in_trade'][i-1] < 0:
                stst_stop['stop_long'][i] = stst_stop['stop_long'][i-1]
            elif stst_stop['stop_methodology'][i-1] == 0:
                if stst_stop['stop_long_post'][i-1] > stst_stop['stop_long'][i-1]:
                    stst_stop['stop_methodology'][i] = 1
                    stst_stop['stop_long'][i-1] = stst_stop['stop_long_post'][i-1]
                else:
                    stst_stop['stop_long'][i] = stst_stop['stop_long'][i-1]
            elif stst_stop['stop_methodology'][i-1] == 1:
                if stst_stop['stop_long_post'][i-1] > stst_stop['stop_long'][i-2]:
                    stst_stop['stop_long'][i-1] = stst_stop['stop_long_post'][i-1]
                else:
                    stst_stop['stop_long'][i-1] = stst_stop['stop_long'][i-2]
                stst_stop['stop_methodology'][i] = 1
            stst_stop['trade_tracker'][i] = 1
            stst_stop['trade_open'][i] = stst_stop['trade_open'][i-1]
            stst_stop['adx_trade'][i] = stst_stop['adx_trade'][i-1]
            stst_stop['mar_trade'][i] = stst_stop['mar_trade'][i-1]
            if stst_stop['Open'][i] < stst_stop['stop_long'][i-1]:
                stst_stop['trade_close'][i] = stst_stop['stop_long'][i-1]            
            elif stst_stop['Low'][i] < stst_stop['stop_long'][i-1]:
                stst_stop['trade_close'][i] = stst_stop['stop_long'][i-1]
#in trade logic short
        elif stst_stop['trade_tracker'][i-1] == -1 and stst_stop['trade_close'][i-1] == 0:
            if stst_stop['days_in_trade'][i-1] < 0:
                stst_stop['stop_short'][i] = stst_stop['stop_short'][i-1]            
            elif stst_stop['stop_methodology'][i-1] == 0:
                if stst_stop['stop_short_post'][i-1] < stst_stop['stop_short'][i-1]:
                    stst_stop['stop_methodology'][i] = 1
                    stst_stop['stop_short'][i-1] = stst_stop['stop_short_post'][i-1]
                else:
                    stst_stop['stop_short'][i] = stst_stop['stop_short'][i-1]
            elif stst_stop['stop_methodology'][i-1] == 1:
                if stst_stop['stop_short_post'][i-1] < stst_stop['stop_short'][i-2]:
                    stst_stop['stop_short'][i-1] = stst_stop['stop_short_post'][i-1]
                else:
                    stst_stop['stop_short'][i-1] = stst_stop['stop_short'][i-2]
                stst_stop['stop_methodology'][i] = 1
            stst_stop['trade_tracker'][i] = -1
            stst_stop['trade_open'][i] = stst_stop['trade_open'][i-1]
            stst_stop['adx_trade'][i] = stst_stop['adx_trade'][i-1]
            stst_stop['mar_trade'][i] = stst_stop['mar_trade'][i-1]            
            if stst_stop['Open'][i] > stst_stop['stop_short'][i-1]:
                stst_stop['trade_close'][i] = stst_stop['stop_short'][i-1]            
            elif stst_stop['High'][i] > stst_stop['stop_short'][i-1]:
                stst_stop['trade_close'][i] = stst_stop['stop_short'][i-1]
#long first trade logic
        elif stst_stop['Trade'][i-2] == 0 and stst_stop['Trade'][i-1] == 1 and stst_stop['trade_tracker'][i-1] == 0:
            if stst_stop['stop_long'][i-1] < stst_stop['stop_long_post'][i-1]:
                stst_stop['stop_methodology'][i] = 1
                stst_stop['stop_long'][i-1] = stst_stop['stop_long_post'][i-1]
            if stst_stop['Open'][i] > stst_stop['stop_long'][i-1]:
                if stst_stop['Low'][i] < stst_stop['stop_long'][i-1]:
                    stst_stop['trade_close'][i] = stst_stop['stop_long'][i-1]
                stst_stop['trade_tracker'][i] = 1
                stst_stop['adx_trade'][i] = stst_stop['adx'][i]
                stst_stop['mar_trade'][i] = stst_stop['mar'][i]                
                stst_stop['trade_open'][i] = stst_stop['Open'][i]
                stst_stop['stop_long'][i] = stst_stop['stop_long'][i-1]
        elif stst_stop['Trade'][i-2] == 0 and stst_stop['Trade'][i-1] == -1 and stst_stop['trade_tracker'][i-1] == 0:
            if stst_stop['stop_short'][i-1] > stst_stop['stop_short_post'][i-1]:
                stst_stop['stop_methodology'][i] = 1
                stst_stop['stop_short'][i-1] = stst_stop['stop_short_post'][i-1]
            if stst_stop['Open'][i] < stst_stop['stop_short'][i-1]:
                if stst_stop['High'][i] > stst_stop['stop_short'][i-1]:
                    stst_stop['trade_close'][i] = stst_stop['stop_short'][i-1]
                stst_stop['trade_tracker'][i] = -1
                stst_stop['adx_trade'][i] = stst_stop['adx'][i]
                stst_stop['mar_trade'][i] = stst_stop['mar'][i]
                stst_stop['trade_open'][i] = stst_stop['Open'][i]
                stst_stop['stop_short'][i] = stst_stop['stop_short'][i-1]
#or (stst_stop['Trade'][i-1] == -1 and stst_stop['Open'][i] < stst_stop['stop_short'][i-1])
#portfolio summation logic
        if stst_stop['trade_open'][i] != 0:
            if stst_stop['trade_open'][i-1] == 0 and stst_stop['trade_tracker'][i] == -1:
                stst_stop['days_in_trade'][i] == 1
                stst_stop['quote'][i] = dollar_risk / ( stst_stop['stop_short'][i-1] - stst_stop['trade_open'][i])
            elif stst_stop['trade_open'][i-1] == 0 and stst_stop['trade_tracker'][i] == 1:
                stst_stop['days_in_trade'][i] == 1
                stst_stop['quote'][i] = dollar_risk / (stst_stop['trade_open'][i] - stst_stop['stop_long'][i-1])
            else:
                stst_stop['days_in_trade'][i] = stst_stop['days_in_trade'][i-1]+1
                stst_stop['quote'][i] = stst_stop['quote'][i-1]
        if stst_stop['trade_open'][i] != 0:
            if stst_stop['trade_close'][i] == 0:
                stst_stop['running_profit'][i] = ((stst_stop['Settle'][i] - stst_stop['trade_open'][i]) * stst_stop['quote'][i]) * stst_stop['trade_tracker'][i]
            else:
                stst_stop['running_profit'][i] = ((stst_stop['trade_close'][i] - stst_stop['trade_open'][i]) * stst_stop['quote'][i]) * stst_stop['trade_tracker'][i]
    return stst_stop
def portfolio_daily(ststs_trade,starting_value):
    portfolio_tracker = pd.DataFrame(pd.Series(np.zeros(len(ststs_trade.index)),index=ststs_trade.index),columns=['portfolio_tracker'])
    ststs_trade = pd.concat([ststs_trade,portfolio_tracker],axis=1)
    for i in range(len(ststs_trade.index)):
        if ststs_trade['trade_open'][i] != 0:
            ststs_trade['portfolio_tracker'][i] = ststs_trade['running_profit'][i] - ststs_trade['running_profit'][i-1] + ststs_trade['portfolio_tracker'][i-1]
        else:
            ststs_trade['portfolio_tracker'][i] = ststs_trade['portfolio_tracker'][i-1]
    return ststs_trade
#for the portfolio object. Initializing datetime index over the period of investigation
def initialize_portfolio(start_date,end_date,portfolio_value): 
    portfolio_test_period = (end_date - start_date).days
    dates = pd.date_range(start_date,periods = portfolio_test_period)
    portfolio = pd.DataFrame(pd.Series(np.zeros(portfolio_test_period),index=dates),columns=['running_portfolio'])
    portfolio['running_portfolio'] = portfolio_value
    return portfolio
def sql_script_read(query_file):
    with open(query_file,"r") as my_file:
        data = my_file.read()
    return data
def trade_stats(tsa,stats,security):
    tsa = tsa[['trade_open','trade_close','trade_tracker','quote','running_profit','days_in_trade','adx','rsi','adx_min','adx_plus','adx_trade','mar_trade','Settle']]
    portfolio_tracker = pd.DataFrame(pd.Series(np.zeros(len(tsa.index)),index=tsa.index),columns=['security'])
    portfolio_tracker['security'] = security    
    tsa = pd.concat([portfolio_tracker,tsa],axis=1)
    stats = stats.append(tsa)
    stats = stats[stats.trade_close != 0]
    return stats
def strategy_stats(strat_stats,entry_high_low,adx_back,ma_slope,stop_one,stop_two,win_percentage,win_to_loss,average_trade_length):
    holder = pd.DataFrame(index=np.arange(0, 1), columns=('entry_high_low','adx_back','ma_slope','stop_one','stop_two','win_percentage','win_to_loss','average_trade_length'))
    holder['entry_high_low'][0] = entry_high_low
    holder['adx_back'][0] = adx_back
    holder['ma_slope'][0] = ma_slope
    holder['stop_one'][0] = stop_one
    holder['stop_two'][0] = stop_two
    holder['win_percentage'][0] = win_percentage
    holder['win_to_loss'][0] = win_to_loss
    holder['average_trade_length'][0] = average_trade_length
    strat_stats = strat_stats.append(holder)
    return strat_stats
def portfolio_additions(h):
    h['portfolio_tracker'][0] = 0
    for i in range(len(h.index)):
        if math.isnan(h['portfolio_tracker'][i]):
            h['portfolio_tracker'][i] = h['portfolio_tracker'][i-1]
        h['running_portfolio'][i] =  h['portfolio_tracker'][i] + h['running_portfolio'][i]
    return h
#trade methodology
#trade methodology #1: win to loss 3.42. Win percentage: .446. (daily). win to loss 4.36 win percentage .47919 (weekly).
#macd_slow = 12
#macd_fast = 26
#macd_ma = 9
#adx_days = 14
#rsi_days = 14
#adx_avg_days = 45
#diff_min_plus = 10
#adx_trend_strength = 0
def macd_test(security_time_series,macd_slow,macd_fast,macd_ma,adx_days,rsi_days,adx_avg_days,adx_trend_strength,std,ma_days):
    macd = talib.MACD(np.array(security_time_series['Settle']),macd_slow,macd_fast,macd_ma)
    macd = pd.DataFrame({'macd_slow':pd.Series(macd[0],index=security_time_series.index),'macd_fast':pd.Series(macd[1],index=security_time_series.index),'macd_dist':pd.Series(macd[2],index=security_time_series.index).shift(5)})    
    macd_shift = talib.MACD(np.array(security_time_series.shift(1)['Settle']),macd_slow,macd_fast,macd_ma)
    macd_shift = pd.DataFrame({'macd_slow_prev':pd.Series(macd_shift[0],index=security_time_series.index),'macd_fast_prev':pd.Series(macd_shift[1],index=security_time_series.index),'macd_dist_prev':pd.Series(macd_shift[2],index=security_time_series.index)})
    bbands = talib.BBANDS(np.array(security_time_series['Settle']),timeperiod = 14,nbdevup=std,nbdevdn=std)
    bbands = pd.DataFrame({'settleprev':security_time_series.shift(1)['Settle'],'up':pd.Series(bbands[0],index=security_time_series.index),'down':pd.Series(bbands[2],index=security_time_series.index),'ma':pd.Series(bbands[1],index=security_time_series.index)})    
    bbands_shift = talib.BBANDS(np.array(security_time_series['Settle']),timeperiod = 14)
    bbands_shift = pd.DataFrame({'up_shift':pd.Series(bbands_shift[0],index=security_time_series.index),'downup_shift':pd.Series(bbands_shift[2],index=security_time_series.index),'maup_shift':pd.Series(bbands_shift[1],index=security_time_series.index)})
    adx_min =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx_min'],index=security_time_series.index)
    adx_plus =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx_plus'],index=security_time_series.index)
    adx =  pd.DataFrame(talib.ADX(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx'],index=security_time_series.index)
    adx_dm15 =  pd.DataFrame(talib.ADX(np.array(security_time_series.shift(14)['High']),np.array(security_time_series.shift(14)['Low']),np.array(security_time_series.shift(14)['Settle']),timeperiod = adx_days),columns=['adx_dm15'],index=security_time_series.index)
    adx_min_average = pd.rolling_mean(adx_min,adx_avg_days)
    adx_plus_average = pd.rolling_mean(adx_plus,adx_avg_days)
    adx_min_shift =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series.shift(1)['High']),np.array(security_time_series.shift(1)['Low']),np.array(security_time_series.shift(1)['Settle']),timeperiod = adx_days),columns=['adx_minprev'],index=security_time_series.index)
    adx_plus_shift =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series.shift(1)['High']),np.array(security_time_series.shift(1)['Low']),np.array(security_time_series.shift(1)['Settle']),timeperiod = adx_days),columns=['adx_plusprev'],index=security_time_series.index)    
    adx_min_shift_two =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series.shift(2)['High']),np.array(security_time_series.shift(2)['Low']),np.array(security_time_series.shift(2)['Settle']),timeperiod = adx_days),columns=['adx_minprev_two'],index=security_time_series.index)
    adx_plus_shift_two =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series.shift(2)['High']),np.array(security_time_series.shift(2)['Low']),np.array(security_time_series.shift(2)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_two'],index=security_time_series.index)    
    adx_min_shift_three =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series.shift(3)['High']),np.array(security_time_series.shift(3)['Low']),np.array(security_time_series.shift(3)['Settle']),timeperiod = adx_days),columns=['adx_minprev_three'],index=security_time_series.index)
    adx_plus_shift_three =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series.shift(3)['High']),np.array(security_time_series.shift(3)['Low']),np.array(security_time_series.shift(3)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_three'],index=security_time_series.index)   
    adx_min_shift_four =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series.shift(4)['High']),np.array(security_time_series.shift(4)['Low']),np.array(security_time_series.shift(4)['Settle']),timeperiod = adx_days),columns=['adx_minprev_four'],index=security_time_series.index)
    adx_plus_shift_four =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series.shift(4)['High']),np.array(security_time_series.shift(4)['Low']),np.array(security_time_series.shift(4)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_four'],index=security_time_series.index)   
    adx_min_shift_five =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series.shift(5)['High']),np.array(security_time_series.shift(5)['Low']),np.array(security_time_series.shift(5)['Settle']),timeperiod = adx_days),columns=['adx_minprev_five'],index=security_time_series.index)
    adx_plus_shift_five =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series.shift(5)['High']),np.array(security_time_series.shift(5)['Low']),np.array(security_time_series.shift(5)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_five'],index=security_time_series.index)   
    adx_min_shift_six =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series.shift(6)['High']),np.array(security_time_series.shift(6)['Low']),np.array(security_time_series.shift(6)['Settle']),timeperiod = adx_days),columns=['adx_minprev_six'],index=security_time_series.index)
    adx_plus_shift_six =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series.shift(6)['High']),np.array(security_time_series.shift(6)['Low']),np.array(security_time_series.shift(6)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_six'],index=security_time_series.index)
    adx_average = pd.rolling_mean(adx,adx_avg_days)
    adx_min_average.columns = ['adx_min_avg']
    adx_plus_average.columns = ['adx_plus_avg']
    adx_average.columns = ['adx_avg']
    ma = pd.rolling_mean(security_time_series['Settle'],ma_days)
    ma = pd.DataFrame(ma,index=security_time_series.index)    
    ma.columns = ['mar']
    mini = pd.rolling_min(security_time_series.shift(1)['Settle'],ma_days)
    mini = pd.DataFrame(mini,index=security_time_series.index)    
    mini.columns = ['mini']
    maxi = pd.rolling_max(security_time_series.shift(1)['Settle'],ma_days)
    maxi = pd.DataFrame(maxi,index=security_time_series.index)    
    maxi.columns = ['maxi']
    sar = pd.DataFrame(talib.SAR(np.array(security_time_series['High']),np.array(security_time_series['Low']),increment,max_amount),index=security_time_series.index,columns=['sar'])
    sar_prev = pd.DataFrame(talib.SAR(np.array(security_time_series.shift(1)['High']),np.array(security_time_series.shift(1)['Low']),increment,max_amount),index=security_time_series.index,columns=['sarprev'])
    rsi = talib.RSI(np.array(security_time_series['Settle']),timeperiod = rsi_days)
    rsi = pd.DataFrame({'rsi':pd.Series(rsi,index=security_time_series.index)})
    h = pd.concat([security_time_series,adx_dm15,ma,mini,maxi,macd,adx_min_shift,adx_plus_shift,adx_min_shift_two,adx_plus_shift_two,adx_min_shift_three,adx_plus_shift_three,adx_min_shift_four,adx_plus_shift_four,adx_min_shift_five,adx_plus_shift_five,adx_min_shift_six,adx_plus_shift_six,macd_shift,rsi,adx_min,adx_plus,adx,adx_min_average,adx_plus_average,adx_average,bbands,bbands_shift,sar,sar_prev],axis=1)  
    def trade_trigger(h):
        if h['adx_min'] < h['adx_plus'] and h['adx_minprev'] > h['adx_plusprev']:
            return 1
        elif h['adx_min'] > h['adx_plus'] and h['adx_minprev'] < h['adx_plusprev']:
            return -1
        else:
            return 0
    trade = pd.DataFrame(h.apply(trade_trigger,axis=1),columns=['Trade'])
    security_time_series = pd.concat([security_time_series[['Open','High','Low','Settle']],trade,rsi,adx,adx_dm15,ma],axis=1)
    return security_time_series
def adx(security_time_series,macd_slow,macd_fast,macd_ma,adx_days,rsi_days,adx_avg_days,adx_trend_strength,std,ma_days):
    adx_min =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx_min'],index=security_time_series.index)
    adx_plus =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx_plus'],index=security_time_series.index)
    adx =  pd.DataFrame(talib.ADXR(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx'],index=security_time_series.index)
    adx_min_shift =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series.shift(1)['High']),np.array(security_time_series.shift(1)['Low']),np.array(security_time_series.shift(1)['Settle']),timeperiod = adx_days),columns=['adx_minprev'],index=security_time_series.index)
    adx_plus_shift =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series.shift(1)['High']),np.array(security_time_series.shift(1)['Low']),np.array(security_time_series.shift(1)['Settle']),timeperiod = adx_days),columns=['adx_plusprev'],index=security_time_series.index)
    adx_shift =  pd.DataFrame(talib.ADX(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adxprev'],index=security_time_series.index)    
    adx_min_average = pd.rolling_mean(adx_min,adx_avg_days)
    adx_plus_average = pd.rolling_mean(adx_plus,adx_avg_days)
    adx_average = pd.rolling_mean(adx,adx_avg_days)
    ma = pd.rolling_mean(security_time_series['Settle'],ma_days)
    ma = pd.DataFrame(ma)    
    ma.columns = ['ma']
    adx_min_average.columns = ['adx_min_avg']
    adx_plus_average.columns = ['adx_plus_avg']
    adx_average.columns = ['adx_avg']
    rsi = talib.RSI(np.array(security_time_series['Settle']),timeperiod = rsi_days)
    rsi = pd.DataFrame({'rsi':pd.Series(rsi,index=security_time_series.index)})
    h = pd.concat([security_time_series,rsi,adx_min_shift,adx_min,adx_plus_shift,adx_plus,adx_shift,adx,adx_min_average,adx_plus_average,adx_average,ma],axis=1)  
    def trade_trigger(h):
        if h['adx_min'] > h['adx_plus'] and h['adx_minprev'] < h['adx_plusprev'] and h['adx'] > 25 and h['Settle'] > h['ma']:
            return 1
        elif h['adx_min'] < h['adx_plus'] and h['adx_minprev'] > h['adx_plusprev'] and h['adx'] > 25 and h['Settle'] < h['ma']:
            return -1
        else:
            return 0
    trade = pd.DataFrame(h.apply(trade_trigger,axis=1),columns=['Trade'])
    security_time_series = pd.concat([security_time_series[['Open','High','Low','Settle']],trade],axis=1)
    return security_time_series
def bbands(security_time_series,std,bbands_days,adx_days,rsi_days,adx_avg_days):
    bbands = talib.BBANDS(np.array(security_time_series['Settle']),timeperiod = 14,nbdevup=std,nbdevdn=std)
    bbands = pd.DataFrame({'settleprev':security_time_series.shift(1)['Settle'],'up':pd.Series(bbands[0],index=security_time_series.index),'down':pd.Series(bbands[2],index=security_time_series.index),'ma':pd.Series(bbands[1],index=security_time_series.index)})    
    bbands_shift = talib.BBANDS(np.array(security_time_series['Settle']),timeperiod = 14)
    bbands_shift = pd.DataFrame({'up_shift':pd.Series(bbands_shift[0],index=security_time_series.index),'downup_shift':pd.Series(bbands_shift[2],index=security_time_series.index),'maup_shift':pd.Series(bbands_shift[1],index=security_time_series.index)})
    adx_min =  pd.DataFrame(talib.MINUS_DI(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx_min'],index=security_time_series.index)
    adx_plus =  pd.DataFrame(talib.PLUS_DI(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx_plus'],index=security_time_series.index)
    adx =  pd.DataFrame(talib.ADX(np.array(security_time_series['High']),np.array(security_time_series['Low']),np.array(security_time_series['Settle']),timeperiod = adx_days),columns=['adx'],index=security_time_series.index)
    adx_min_average = pd.rolling_mean(adx_min,adx_avg_days)
    adx_plus_average = pd.rolling_mean(adx_plus,adx_avg_days)
    adx_average = pd.rolling_mean(adx,adx_avg_days)
    adx_min_average.columns = ['adx_min_avg']
    adx_plus_average.columns = ['adx_plus_avg']
    adx_average.columns = ['adx_avg']
    rsi = talib.RSI(np.array(security_time_series['Settle']),timeperiod = rsi_days)
    rsi = pd.DataFrame({'rsi':pd.Series(rsi,index=security_time_series.index)})
    h = pd.concat([security_time_series,bbands,bbands_shift,rsi,adx_min,adx_plus,adx,adx_min_average,adx_plus_average,adx_average],axis=1)  
    def trade_trigger(h):
        if h['Settle'] > h['up'] and h['settleprev'] < h['up'] and h['adx_plus_avg'] > h['adx_min_avg'] + 5 and h['rsi'] < 70:
            return 1
        elif h['Settle'] < h['down'] and h['settleprev'] > h['down'] and h['adx_min_avg'] > h['adx_plus_avg'] + 5 and h['rsi'] > 30:
            return -1
        else:
            return 0
    trade = pd.DataFrame(h.apply(trade_trigger,axis=1),columns=['Trade'])
    security_time_series = pd.concat([security_time_series[['Open','High','Low','Settle']],trade],axis=1)
    return security_time_series
def stop_loss_methodology_macd(sts_trade,days,atr_multiplier):
    roll_max = pd.DataFrame(pd.rolling_max(sts_trade['High'],days),columns=['stop_short'])
    roll_min = pd.DataFrame(pd.rolling_min(sts_trade['Low'],days),columns=['stop_long'])
    atr = talib.ATR(np.array(sts_trade['High']),np.array(sts_trade['Low']),np.array(sts_trade['Settle']),timeperiod = 14)
    stop = sts_trade['Settle'] + atr*atr_multiplier
    stop_short_post = pd.DataFrame(stop)
    stop_short_post.columns = ['stop_short_post']
    stop = sts_trade['Settle'] - atr*atr_multiplier
    stop_long_post = pd.DataFrame(stop)
    stop_long_post.columns = ['stop_long_post']
    stop = sts_trade['Settle'] + atr*atr_multiplier
    sts_trade = pd.concat([sts_trade,roll_max,roll_min,stop_short_post,stop_long_post],axis=1)
    return sts_trade
def stop_loss_methodology_bbands(sts_trade,days,atr_multiplier,ma_days,days_two):
    macd = talib.MACD(np.array(sts_trade['Settle']),macd_slow,macd_fast,macd_ma)
    macd = pd.DataFrame({'macd_slow':pd.Series(macd[0],index=sts_trade.index),'macd_fast':pd.Series(macd[1],index=sts_trade.index),'macd_dist':pd.Series(macd[2],index=sts_trade.index).shift(5)})    
    macd_shift = talib.MACD(np.array(sts_trade.shift(1)['Settle']),macd_slow,macd_fast,macd_ma)
    macd_shift = pd.DataFrame({'macd_slow_prev':pd.Series(macd_shift[0],index=sts_trade.index),'macd_fast_prev':pd.Series(macd_shift[1],index=sts_trade.index),'macd_dist_prev':pd.Series(macd_shift[2],index=sts_trade.index)})
    macd_shift_one = talib.MACD(np.array(sts_trade.shift(2)['Settle']),macd_slow,macd_fast,macd_ma)
    macd_shift_one = pd.DataFrame({'macd_slow_prev_one':pd.Series(macd_shift_one[0],index=sts_trade.index),'macd_fast_prev_one':pd.Series(macd_shift_one[1],index=sts_trade.index),'macd_dist_prev_one':pd.Series(macd_shift_one[2],index=sts_trade.index)})
    macd_shift_two = talib.MACD(np.array(sts_trade.shift(3)['Settle']),macd_slow,macd_fast,macd_ma)
    macd_shift_two = pd.DataFrame({'macd_slow_prev_two':pd.Series(macd_shift_two[0],index=sts_trade.index),'macd_fast_prev_two':pd.Series(macd_shift_two[1],index=sts_trade.index),'macd_dist_prev_two':pd.Series(macd_shift_two[2],index=sts_trade.index)})
    macd_shift_three = talib.MACD(np.array(sts_trade.shift(4)['Settle']),macd_slow,macd_fast,macd_ma)
    macd_shift_three = pd.DataFrame({'macd_slow_prev_three':pd.Series(macd_shift_three[0],index=sts_trade.index),'macd_fast_prev_three':pd.Series(macd_shift_three[1],index=sts_trade.index),'macd_dist_prev_three':pd.Series(macd_shift_three[2],index=sts_trade.index)})
    macd_shift_four = talib.MACD(np.array(sts_trade.shift(5)['Settle']),macd_slow,macd_fast,macd_ma)
    macd_shift_four = pd.DataFrame({'macd_slow_prev_four':pd.Series(macd_shift_four[0],index=sts_trade.index),'macd_fast_prev_four':pd.Series(macd_shift_four[1],index=sts_trade.index),'macd_dist_prev_four':pd.Series(macd_shift_four[2],index=sts_trade.index)})
    macd_shift_five = talib.MACD(np.array(sts_trade.shift(6)['Settle']),macd_slow,macd_fast,macd_ma)
    macd_shift_five = pd.DataFrame({'macd_slow_prev_five':pd.Series(macd_shift_five[0],index=sts_trade.index),'macd_fast_prev_five':pd.Series(macd_shift_five[1],index=sts_trade.index),'macd_dist_prev_five':pd.Series(macd_shift_five[2],index=sts_trade.index)}) 
    adx_min =  pd.DataFrame(talib.MINUS_DI(np.array(sts_trade['High']),np.array(sts_trade['Low']),np.array(sts_trade['Settle']),timeperiod = adx_days),columns=['adx_min'],index=sts_trade.index)
    adx_plus =  pd.DataFrame(talib.PLUS_DI(np.array(sts_trade['High']),np.array(sts_trade['Low']),np.array(sts_trade['Settle']),timeperiod = adx_days),columns=['adx_plus'],index=sts_trade.index)    
    adx_min_shift =  pd.DataFrame(talib.MINUS_DI(np.array(sts_trade.shift(1)['High']),np.array(sts_trade.shift(1)['Low']),np.array(sts_trade.shift(1)['Settle']),timeperiod = adx_days),columns=['adx_minprev'],index=sts_trade.index)
    adx_plus_shift =  pd.DataFrame(talib.PLUS_DI(np.array(sts_trade.shift(1)['High']),np.array(sts_trade.shift(1)['Low']),np.array(sts_trade.shift(1)['Settle']),timeperiod = adx_days),columns=['adx_plusprev'],index=sts_trade.index)    
    adx_min_shift_two =  pd.DataFrame(talib.MINUS_DI(np.array(sts_trade.shift(2)['High']),np.array(sts_trade.shift(2)['Low']),np.array(sts_trade.shift(2)['Settle']),timeperiod = adx_days),columns=['adx_minprev_two'],index=sts_trade.index)
    adx_plus_shift_two =  pd.DataFrame(talib.PLUS_DI(np.array(sts_trade.shift(2)['High']),np.array(sts_trade.shift(2)['Low']),np.array(sts_trade.shift(2)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_two'],index=sts_trade.index)    
    adx_min_shift_three =  pd.DataFrame(talib.MINUS_DI(np.array(sts_trade.shift(3)['High']),np.array(sts_trade.shift(3)['Low']),np.array(sts_trade.shift(3)['Settle']),timeperiod = adx_days),columns=['adx_minprev_three'],index=sts_trade.index)
    adx_plus_shift_three =  pd.DataFrame(talib.PLUS_DI(np.array(sts_trade.shift(3)['High']),np.array(sts_trade.shift(3)['Low']),np.array(sts_trade.shift(3)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_three'],index=sts_trade.index)   
    adx_min_shift_four =  pd.DataFrame(talib.MINUS_DI(np.array(sts_trade.shift(4)['High']),np.array(sts_trade.shift(4)['Low']),np.array(sts_trade.shift(4)['Settle']),timeperiod = adx_days),columns=['adx_minprev_four'],index=sts_trade.index)
    adx_plus_shift_four =  pd.DataFrame(talib.PLUS_DI(np.array(sts_trade.shift(4)['High']),np.array(sts_trade.shift(4)['Low']),np.array(sts_trade.shift(4)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_four'],index=sts_trade.index)   
    adx_min_shift_five =  pd.DataFrame(talib.MINUS_DI(np.array(sts_trade.shift(5)['High']),np.array(sts_trade.shift(5)['Low']),np.array(sts_trade.shift(5)['Settle']),timeperiod = adx_days),columns=['adx_minprev_five'],index=sts_trade.index)
    adx_plus_shift_five =  pd.DataFrame(talib.PLUS_DI(np.array(sts_trade.shift(5)['High']),np.array(sts_trade.shift(5)['Low']),np.array(sts_trade.shift(5)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_five'],index=sts_trade.index)   
    adx_min_shift_six =  pd.DataFrame(talib.MINUS_DI(np.array(sts_trade.shift(6)['High']),np.array(sts_trade.shift(6)['Low']),np.array(sts_trade.shift(6)['Settle']),timeperiod = adx_days),columns=['adx_minprev_six'],index=sts_trade.index)
    adx_plus_shift_six =  pd.DataFrame(talib.PLUS_DI(np.array(sts_trade.shift(6)['High']),np.array(sts_trade.shift(6)['Low']),np.array(sts_trade.shift(6)['Settle']),timeperiod = adx_days),columns=['adx_plusprev_six'],index=sts_trade.index)    
    roll_max = pd.DataFrame(pd.rolling_max(sts_trade['High'],days),columns=['stop_short'])
    roll_min = pd.DataFrame(pd.rolling_min(sts_trade['Low'],days),columns=['stop_long'])
    atr = talib.ATR(np.array(sts_trade['High']),np.array(sts_trade['Low']),np.array(sts_trade['Settle']),timeperiod = 18)
    stop = sts_trade['Settle'] + atr*atr_multiplier
    stop_short_post = pd.DataFrame(stop)
    stop_short_post.columns = ['ssp']
    stop = sts_trade['Settle'] - atr*atr_multiplier
    stop_long_post = pd.DataFrame(stop)
    stop_long_post.columns = ['slp']
    sts_trade = pd.concat([sts_trade,adx_min_shift,adx_min,adx_plus,adx_plus_shift,adx_min_shift_two,adx_plus_shift_two,adx_min_shift_three,adx_plus_shift_three,adx_min_shift_four,adx_plus_shift_four,adx_min_shift_five,adx_plus_shift_five,adx_min_shift_six,adx_plus_shift_six,roll_max,roll_min,stop_long_post,stop_short_post,macd,macd_shift,macd_shift_one,macd_shift_two,macd_shift_three,macd_shift_four,macd_shift_five],axis=1)
    def short(h):
        if (h['adx_plusprev'] < h['adx_minprev'] and h['adx_plus'] > h['adx_min'] and h['adx_plusprev_two'] < h['adx_minprev_two'] and h['adx_plusprev_three'] < h['adx_minprev_three'] and h['adx_plusprev_four'] < h['adx_minprev_four'] and h['adx_plusprev_five'] < h['adx_minprev_five']):
            return h['slp']
        else:
            return h['slp']       
    def long_(h):        
        if (h['adx_plusprev'] > h['adx_minprev'] and h['adx_plus'] < h['adx_min'] and h['adx_plusprev_two'] > h['adx_minprev_two'] and h['adx_plusprev_three'] > h['adx_minprev_three'] and h['adx_plusprev_four'] > h['adx_minprev_four'] and h['adx_plusprev_five'] > h['adx_minprev_five']):
            return h['ssp']
        else:
            return h['ssp']
    stop_long_post = pd.DataFrame(pd.rolling_min(sts_trade['Low'],days_two),columns=['stop_long_post'])
    stop_short_post = pd.DataFrame(pd.rolling_max(sts_trade['High'],days_two),columns=['stop_short_post'])    
    #stop_long_post = pd.DataFrame(sts_trade.apply(short,axis=1),columns=['stop_long_post'])
    #stop_short_post = pd.DataFrame(sts_trade.apply(long_,axis=1),columns=['stop_short_post'])
    sts_trade = pd.concat([sts_trade,stop_long_post,stop_short_post],axis=1)
    return sts_trade
#script that run the model

portfolio = initialize_portfolio(start_date,end_date,10000)
#tsa = get_quandl_data(security)
#(len(f.index)
stats = pd.DataFrame(columns = ['security','trade_open','trade_close','trade_tracker','quote','running_profit','adx','rsi','adx_min','adx_plus','adx_trade','mar_trade','Settle'])
#len(f.index)
strat_stats = pd.DataFrame(index=np.arange(0, 0), columns=('entry_high_low','adx_back','ma_slope','stop_one','stop_two','win_percentage','win_to_loss','average_trade_length'))

#def adx_adi_ma_gap_down(security_time_series,roll_days,adx_days,adx_offset,vol_ratio,ma_slope_days)
macd_slow = 36
macd_fast = 78
macd_ma = 27
adx_days = 14
rsi_days = 14
adx_avg_days = 30
diff_min_plus = 10
adx_trend_strength = 0
std = 1
maxxx = 55
ma_days = 200
days = 3
increment = .02     
max_amount = .2
atr_days = 10
atr_range = 1.0
for i in tested_securities:
    a = i
    tsa = get_quandl_data_and_standardize(a,start_date,end_date)
    if len(tsa.index) > 252:
        #tsa = adx(tsa,macd_slow,macd_fast,macd_ma,adx_days,rsi_days,adx_avg_days,adx_trend_strength,std,maxxx)      
        tsa = macd_test(tsa,macd_slow,macd_fast,macd_ma,adx_days,rsi_days,adx_avg_days,adx_trend_strength,std,ma_days)
        #tsa = bbands(tsa,1.25,14,14,14,45)    
        #tsa = stop_loss_methodology_bbands_counter(tsa,15,3)
        #tsa = stop_loss_methodology_bbands(tsa,10,60)
        tsa = stop_loss_methodology_bbands(tsa,10,5,ma_days,20)
        #tsa = stop_loss_methodology_macd(tsa,3,2)
        #tsa = stop_loss_methodology_bbands_counter(tsa,3,2)        
        #tsa = stop_loss_methodology_bbands(tsa,3,1.25)
        tsa = risk_metrics(tsa)
        tsa = trade_tracker(tsa,500)
        tsa = portfolio_daily(tsa,0)
        stats = trade_stats(tsa,stats,i+i)
        portfolio = pd.concat([portfolio, tsa], axis=1, join_axes=[portfolio.index])
        portfolio = portfolio_additions(portfolio)
        portfolio = pd.DataFrame(portfolio['running_portfolio'],columns=['running_portfolio'])
stats = stats.sort_index(ascending=True)
series=pd.Series((portfolio['running_portfolio']/10000) * (portfolio['running_portfolio']-10000) + 10000)
portfolio_cum = pd.DataFrame(series,index = portfolio.index)
portfolio_cum.columns = ['running_profit_compound']
portfolio_cum_join = pd.concat([portfolio,portfolio_cum,((portfolio_cum['running_profit_compound'] / portfolio_cum['running_profit_compound'].cummax())-1),((portfolio_cum['running_profit_compound'] / portfolio_cum.shift(1)['running_profit_compound'])-1)],axis=1)
portfolio_cum_join.columns = ['running_profit','running_profit_compound','cum_max','daily_return']
if stats["running_profit"].count() == 0:
    win_percentage = 0
else:
    win_percentage = float(stats[stats["running_profit"]>0].count()['running_profit']) / (stats["running_profit"].count())
win_to_loss = float(stats[stats["running_profit"]>0].mean()['running_profit']) / (abs(stats[stats["running_profit"]<0].mean()['running_profit']))
avg_profit = float(stats.mean()['running_profit'])
max_draw_down = portfolio_cum_join['cum_max'].min()
cumulative_returns_percent = ((portfolio_cum_join['running_profit_compound'][len(portfolio_cum_join.index)-1] / portfolio_cum_join['running_profit_compound'][0]) ** (1.0/((end_date - start_date).days/365))-1)
volatility = portfolio_cum_join['daily_return'].std() * (252**.5)
average_trade_length = stats['days_in_trade'].mean()
#strat_stats = strategy_stats(strat_stats,entry_high_low,adx_back,ma_slope,stop_one,stop_two,win_percentage,win_to_loss,average_trade_length)
plt.figure(figsize=(20,10))
plt.ylabel('Percent Return',fontsize=16)
plt.xlabel('Date',fontsize=16)
plt.plot(portfolio.index,portfolio['running_portfolio'],linewidth=4)
plt.suptitle('Returns', fontsize=32)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5,maxticks=10))
plt.gcf().autofmt_xdate()
plt.gcf().text(.15,.85,'volatility: ' + str(volatility), fontsize=12)
plt.gcf().text(.15,.825,'win_percentage: ' + str(win_percentage), fontsize=12)
plt.gcf().text(.15,.8,'win_to_loss: ' + str(win_to_loss), fontsize=12)
plt.gcf().text(.15,.775,'max_draw_down: ' + str(max_draw_down), fontsize=12)
plt.gcf().text(.15,.75,'cumulative_returns_percent: ' + str(cumulative_returns_percent), fontsize=12)
plt.gcf().text(.15,.725,'average_trade_length: ' + str(average_trade_length), fontsize=12)
plt.gcf().text(.15,.7,'average_profit: ' + str(avg_profit/500), fontsize=12)

plt.show()
#plot compound returns