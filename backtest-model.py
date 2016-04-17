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
import math
import talib
import xlsxwriter as xlsx
pd.options.mode.chained_assignment = None
'''
Instructions:
1. Edit the user defined inputs to specify the contracts, portfolio, and risk for the analysis.
2. Edit entry_model() to specify the entry model
3. Edit exit_model() to specify the exit model
4. Run program and view excel output
'''
#user defined inputs
quandl_authtoken = ''
tested_securities = ['CURRFX/EURUSD','CURRFX/AUDUSD','CURRFX/GBPUSD']
start_date = d.date(1960,01,01)
end_date = d.date(2015,12,01)
starting_portfolio_value = 10000.0
risk_percent_per_trade = .05
margin_requirement = .1

#inputs for entry_model() and exit_model() for already defined time series
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
### Part I ###
'''
In this section, we define a series of functions that pulls the data from quandl, 
transforms that into a standardized data frame, performs the analysis, and then 
calculates a hypothetical portfolio based on the trades signaled
'''
#this pulls the quandl data and standardizes for the analytics process.
#standard support for CURRFX and SCF in base program
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
#setup to allow for margin requirements in the model, not incorporated in base program
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
#this function generates the trade signal by defining the technical indicator and running an apply function that generates 
#the entry signal when specific criteria are met. If already defined a few models I've personally tested and the current default
#is the one I found to be the best fit. Using any function in ta-lib, we can define the time series, concatenate it to the security_time_series
#and signal trades in the trade trigger function
def entry_model(security_time_series,macd_slow,macd_fast,macd_ma,adx_days,rsi_days,adx_avg_days,adx_trend_strength,std,ma_days):
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
#defines the price at which a trade would be closed. The stop loss methodology can be set as a simple stop or can include specific
#conditions. For example, 3 * ATR OR if adx_min adx_max crossover occurs. The complex item is included in the apply function, because the
#price has to default to that over the simple time series exit price. Define the exit price as a ta-lib function, or any trade series. To update
#name the simple stop price series for shorts ssp and longs slp. The short and long functions are used for complex stops that replace the simple
#stop with the current price when certain criteria has been met. For example, if we specify a 3 * ATR but also want the trade to exit when the 
#adx crossover occurs, the stop price series will be 3 * ATR, but will be replaced with close price in the event of a crossover, which would
#trigger the stop in the trade tracker function.
def exit_model(sts_trade,days,atr_multiplier,ma_days,days_two):
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
#this functions governs what happens after the trade has been initiated, essentially tracking trade profit and closing
#when the stop price is hit. If stop price is not hit, then the trade will continue into perpetuity.
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
                stst_stop['quote'][i] = max(dollar_risk / ( stst_stop['stop_short'][i-1] - stst_stop['trade_open'][i]),-(starting_portfolio_value/margin_requirement)/abs(stst_stop['trade_open'][i]))
            elif stst_stop['trade_open'][i-1] == 0 and stst_stop['trade_tracker'][i] == 1:
                stst_stop['days_in_trade'][i] == 1
                stst_stop['quote'][i] = min(dollar_risk / (stst_stop['trade_open'][i] - stst_stop['stop_long'][i-1]),(starting_portfolio_value/margin_requirement)/abs(stst_stop['trade_open'][i]))
            else:
                stst_stop['days_in_trade'][i] = stst_stop['days_in_trade'][i-1]+1
                stst_stop['quote'][i] = stst_stop['quote'][i-1]
        if stst_stop['trade_open'][i] != 0:
            if stst_stop['trade_close'][i] == 0:
                stst_stop['running_profit'][i] = ((stst_stop['Settle'][i] - stst_stop['trade_open'][i]) * stst_stop['quote'][i]) * stst_stop['trade_tracker'][i]
            else:
                stst_stop['running_profit'][i] = ((stst_stop['trade_close'][i] - stst_stop['trade_open'][i]) * stst_stop['quote'][i]) * stst_stop['trade_tracker'][i]
    return stst_stop
#here we cumulate profits over the contract time period
def portfolio_daily(ststs_trade,starting_value):
    portfolio_tracker = pd.DataFrame(pd.Series(np.zeros(len(ststs_trade.index)),index=ststs_trade.index),columns=['portfolio_tracker'])
    ststs_trade = pd.concat([ststs_trade,portfolio_tracker],axis=1)
    for i in range(len(ststs_trade.index)):
        if ststs_trade['trade_open'][i] != 0:
            ststs_trade['portfolio_tracker'][i] = ststs_trade['running_profit'][i] - ststs_trade['running_profit'][i-1] + ststs_trade['portfolio_tracker'][i-1]
        else:
            ststs_trade['portfolio_tracker'][i] = ststs_trade['portfolio_tracker'][i-1]
    return ststs_trade
#this function creates a portfolio that serves as the aggregate portfolio for all securities that will be analyzed
def initialize_portfolio(start_date,end_date,portfolio_value): 
    portfolio_test_period = (end_date - start_date).days
    dates = pd.date_range(start_date,periods = portfolio_test_period)
    portfolio = pd.DataFrame(pd.Series(np.zeros(portfolio_test_period),index=dates),columns=['running_portfolio'])
    portfolio['running_portfolio'] = portfolio_value
    return portfolio
#next 2 defines the metrics we want to track for each security evaluated, which will be used for the aggregate analysis. As we iterate
#through the list of securities, we track the analytics output before moving to the next security.
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
#adds the current security in the iteration to the portfolio
def portfolio_additions(h):
    h['portfolio_tracker'][0] = 0
    for i in range(len(h.index)):
        if math.isnan(h['portfolio_tracker'][i]):
            h['portfolio_tracker'][i] = h['portfolio_tracker'][i-1]
        h['running_portfolio'][i] =  h['portfolio_tracker'][i] + h['running_portfolio'][i]
    return h
def visualize_analysis_pyplot(x_return,y_return,x_win_loss,y_win_loss,x_percent,y_percent):
    plt.figure(figsize=(20,10))
    plt.ylabel('Portfolio Value',fontsize=16)
    plt.xlabel('Date',fontsize=16)
    plt.plot(x_return,y_return,linewidth=4)
    plt.suptitle('Cumulative Returns', fontsize=32)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5,maxticks=10))
    plt.gcf().autofmt_xdate()
    plt.gcf().text(.15,.85,'Volatility: ' + '{0:.1f}%'.format(volatility*100), fontsize=12)
    plt.gcf().text(.15,.825,'Win percentage: ' + '{0:.1f}%'.format(win_percentage*100), fontsize=12)
    plt.gcf().text(.15,.8,'Win to loss: ' + '{0:.1f}'.format(win_to_loss), fontsize=12)
    plt.gcf().text(.15,.775,'Max draw down: ' + '{0:.1f}%'.format(max_draw_down*100), fontsize=12)
    plt.gcf().text(.15,.75,'Cumulative returns percent: ' + '{0:.1f}%'.format(cumulative_returns_percent*100), fontsize=12)
    plt.gcf().text(.15,.725,'Average trade length: ' + '{0:.1f}'.format(average_trade_length), fontsize=12)
    plt.gcf().text(.15,.7,'Average profit to risk: ' + '{0:.1f}%'.format(avg_profit/dollar_per_trade*100), fontsize=12)
    plt.show()
    plt.figure(figsize=(20,10))
    plt.ylabel('Win to Loss Ratio',fontsize=16)
    plt.xlabel('Year',fontsize=16)
    plt.plot(x_win_loss,y_win_loss,linewidth=4)
    plt.suptitle('Win to Loss Ratio by year', fontsize=32)
    plt.gcf().autofmt_xdate()
    vals = plt.gca().get_yticks()
    plt.gca().set_yticklabels(['{:3.1f}'.format(x) for x in vals])
    plt.show()
    plt.figure(figsize=(20,10))
    plt.ylabel('Win Percent',fontsize=16)
    plt.xlabel('Year',fontsize=16)
    plt.plot(x_percent,y_percent,linewidth=4)
    plt.suptitle('Win Percent by Year', fontsize=32)
    plt.gcf().autofmt_xdate()
    vals = plt.gca().get_yticks()
    plt.gca().set_yticklabels(['{:3.0f}%'.format(x*100) for x in vals])
    plt.show()
def output_to_excel():
    asdf = {'Volatility':[volatility],'Win percentage':[win_percentage],'Win to Loss':[win_to_loss],'Max Drawdown':[max_draw_down],'Cumulative Return':[cumulative_returns_percent],'Average Days in Trade':[average_trade_length],'Average profit to risked':[avg_profit/dollar_per_trade]}
    summary = pd.DataFrame(asdf)
    trades_executed = stats[['security','days_in_trade','running_profit','trade_open','trade_close','trade_tracker']]
    trades_executed.columns = ['Security', 'Days in trade','Trade profit, base risk', 'Open Price', 'Close Price', 'Long/Short']
    analysis_by_security = pd.concat([avg_win_loss_by_security,win_percent_by_security,avg_win_to_risk_by_security,number_of_trades_by_security],axis=1)
    analysis_by_security.columns = ['Win Loss Ratio','Win Percent','Average Profit to Risk','Number of Trades']
    analysis_by_year = pd.concat([win_loss_by_year,win_percent,profit_by_year,number_of_trades_per_year],axis=1)
    analysis_by_year.columns = ['Win Loss Ratio','Win Percent','Average Profit to Risk','Number of Trades']
    writer = pd.ExcelWriter('strategy_analysis.xlsx', engine='xlsxwriter')
    summary.to_excel(writer, sheet_name = 'Summary')
    trades_executed.to_excel(writer, sheet_name='Strategy Trades')
    analysis_by_security.to_excel(writer, sheet_name='By Security')
    analysis_by_year.to_excel(writer, sheet_name='By Year')
    compound_growth.to_excel(writer,sheet_name='Cumulative Returns')
    workbook = writer.book
    percent_format = workbook.add_format({'num_format': '0.0%'})
    number_format = workbook.add_format({'num_format': '0.0'})
    date_format = workbook.add_format({'num_format': 'm/d/yyyy'})
    worksheet = writer.sheets['Summary']
    worksheet.set_column('A:A', 0, number_format)
    worksheet.set_column('B:B', 24, number_format)
    worksheet.set_column('C:G', 24, percent_format)
    worksheet.set_column('H:H', 24, number_format)
    writer.sheets['By Year'].set_column('B:B', 24, number_format)
    writer.sheets['By Year'].set_column('C:D', 24, percent_format)
    writer.sheets['By Year'].set_column('E:E', 24, number_format)
    writer.sheets['Cumulative Returns'].set_column('A:A', 24, date_format)
    writer.sheets['Cumulative Returns'].set_column('B:B', 24, number_format)
    chart1 = workbook.add_chart({'type': 'line'})
    chart2 = workbook.add_chart({'type': 'line'})
    chart3 = workbook.add_chart({'type': 'line'})
    chart4 = workbook.add_chart({'type': 'line'})
    chart1.set_size({'width': 640, 'height': 400})
    chart2.set_size({'width': 640, 'height': 400})
    chart3.set_size({'width': 640, 'height': 400})
    chart4.set_size({'width': 640, 'height': 400})
    cumulative_returns_length = len(compound_growth.index)
    chart1.add_series({'values': '=\'Cumulative Returns\'!$B$2:$B$'+ str(cumulative_returns_length),'name':'Portfolio Value','categories':'=\'Cumulative Returns\'!$A$2:$A$'+ str(cumulative_returns_length)})
    chart2.add_series({'values': '=\'By Year\'!$B$2:$B$'+ str(len(analysis_by_year.index)),'name':'Win/Loss Ratio','categories': '=\'By Year\'!$A$2:$A$'+ str(len(analysis_by_year.index))})
    chart3.add_series({'values': '=\'By Year\'!$C$2:$C$'+ str(len(analysis_by_year.index)),'name':'Win Percent','categories': '=\'By Year\'!$A$2:$A$'+ str(len(analysis_by_year.index))})
    chart4.add_series({'values': '=\'By Year\'!$D$2:$D$'+ str(len(analysis_by_year.index)),'name':'Average Profit to Risk','categories': '=\'By Year\'!$A$2:$A$'+ str(len(analysis_by_year.index))})
    chart1.set_legend({'position': 'bottom'})
    chart2.set_legend({'position': 'bottom'})
    chart3.set_legend({'position': 'bottom'})
    chart4.set_legend({'position': 'bottom'})
    worksheet.insert_chart('B4', chart1)
    worksheet.insert_chart('F4', chart2)
    worksheet.insert_chart('B24', chart3)
    worksheet.insert_chart('F24', chart4)
    writer.save()
#script that run the model
dollar_per_trade = starting_portfolio_value * risk_percent_per_trade
portfolio = initialize_portfolio(start_date,end_date,starting_portfolio_value)
#tsa = get_quandl_data(security)
#(len(f.index)
stats = pd.DataFrame(columns = ['security','trade_open','trade_close','trade_tracker','quote','running_profit','adx','rsi','adx_min','adx_plus','adx_trade','mar_trade','Settle'])
#len(f.index)
strat_stats = pd.DataFrame(index=np.arange(0, 0), columns=('entry_high_low','adx_back','ma_slope','stop_one','stop_two','win_percentage','win_to_loss','average_trade_length'))
#def adx_adi_ma_gap_down(security_time_series,roll_days,adx_days,adx_offset,vol_ratio,ma_slope_days)
for i in tested_securities:
    a = i
    tsa = get_quandl_data_and_standardize(a,start_date,end_date)
    if len(tsa.index) > 252:    
        tsa = entry_model(tsa,macd_slow,macd_fast,macd_ma,adx_days,rsi_days,adx_avg_days,adx_trend_strength,std,ma_days)
        tsa = exit_model(tsa,10,5,ma_days,20)
        tsa = risk_metrics(tsa)
        tsa = trade_tracker(tsa,dollar_per_trade)
        tsa = portfolio_daily(tsa,0)
        stats = trade_stats(tsa,stats,i)
        portfolio = pd.concat([portfolio, tsa], axis=1, join_axes=[portfolio.index])
        portfolio = portfolio_additions(portfolio)
        portfolio = pd.DataFrame(portfolio['running_portfolio'],columns=['running_portfolio'])
stats = stats.sort_index(ascending=True)
series=pd.Series((portfolio['running_portfolio']/starting_portfolio_value) * (portfolio['running_portfolio']-starting_portfolio_value) + starting_portfolio_value)
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
volatility = portfolio_cum_join['daily_return'].std() * (252**.5)
average_trade_length = stats['days_in_trade'].mean()
compound_growth = pd.DataFrame(np.zeros(len(stats.index)),columns=['compound_growth'],index = stats.index)
for i in range(len(stats.index)):
    if i == 0:
        compound_growth['compound_growth'][i] = starting_portfolio_value + stats.running_profit[i]
    else:
        compound_growth['compound_growth'][i] = (((risk_percent_per_trade * compound_growth['compound_growth'][i-1]) / dollar_per_trade)*stats.running_profit[i]) + compound_growth['compound_growth'][i-1]
cumulative_returns_percent = ((compound_growth['compound_growth'][len(compound_growth.index)-1] / compound_growth['compound_growth'][0]) ** (1.0/((pd.to_datetime(end_date) - pd.to_datetime(compound_growth.index[0],format='%Y%m%d')).days/365))-1)
avg_win_loss_by_security = abs(stats[stats["running_profit"]>0].groupby(['security']).mean()['running_profit'] / stats[stats["running_profit"]<0].groupby(['security']).mean()['running_profit'])
win_percent_by_security = stats[stats["running_profit"]>0].groupby(['security']).count()['running_profit'] / stats.groupby(['security']).count()['running_profit']
number_of_trades_by_security = stats.groupby(['security']).count()['running_profit']
avg_win_to_risk_by_security = abs(stats.groupby(['security']).mean()['running_profit'] / dollar_per_trade)
win_percent = abs(stats[stats["running_profit"]>0]['running_profit'].groupby(stats[stats["running_profit"]>0].index.map(lambda x: x.year)).count() / stats['running_profit'].groupby(stats.index.map(lambda x: x.year)).count())
number_of_trades_per_year = stats['running_profit'].groupby(stats.index.map(lambda x: x.year)).count()
win_loss_by_year = abs(stats[stats["running_profit"]>0]['running_profit'].groupby(stats[stats["running_profit"]>0].index.map(lambda x: x.year)).mean() / stats[stats["running_profit"]<0]['running_profit'].groupby(stats[stats["running_profit"]<0].index.map(lambda x: x.year)).mean())
profit_by_year = abs(stats['running_profit'].groupby(stats.index.map(lambda x: x.year)).mean() / dollar_per_trade)

#output
#pyplot graphs
visualize_analysis_pyplot(compound_growth.index,compound_growth['compound_growth'],win_loss_by_year.index,win_loss_by_year,win_percent.index,win_percent)
#excel
output_to_excel()