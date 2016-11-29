import pandas as pd
import quandl
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import xlsxwriter as xl
import pandas_datareader.data as web
def visualize_analysis_pyplot(x_return,y_return):
    plt.figure(figsize=(12,8))
    plt.ylabel('Portfolio Value',fontsize=16)
    plt.xlabel('Date',fontsize=16)
    plt.plot(x_return,y_return,linewidth=4)
    plt.suptitle('Cumulative Returns', fontsize=32)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5,maxticks=10))
    plt.gcf().autofmt_xdate()
    plt.show()
class portfolio:
    def __init__(self,firstDate,startingValue):
        self.dailyHoldings = dict()
        self.portfolioValue = startingValue
        self.dailyPAndL = pd.DataFrame({'dayPAndL':0},index=[firstDate])
        self.currentPortfolio = []
        self.dailyHoldingsInsert = []
        self.closedPortfolio = []
        self.equityCurve = pd.DataFrame({'portfolio':self.portfolioValue,'holdings':0.0},index=[firstDate])
    def profitAndLoss(self,currentPortfolio,marketData,marketDate,closedPortfolio):
        self.dailyHoldingsInsert = []
        dayPAndL = 0.0
        for i in currentPortfolio:
            tickerDataFrame = pd.DataFrame(marketData[i[0]][:marketDate])
            tickerDataFrame = tickerDataFrame.dropna(how='any')
            if marketDate == i[3]:
                positionPAndL = ((tickerDataFrame['Close'][-1] - i[1]) * i[2]) - (.001*i[2]*i[1])
            elif marketDate == tickerDataFrame.index[-1]:
                positionPAndL = (tickerDataFrame['Close'][-1] - tickerDataFrame['Close'][-2]) * i[2]
            else:
                positionPAndL = 0.0
            dayPAndL += positionPAndL
            dailyHoldingsInsert = [i[0],i[1],i[2],tickerDataFrame['Close'][-2],tickerDataFrame['Close'][-1],positionPAndL]
            self.dailyHoldingsInsert.append(dailyHoldingsInsert)
        for i in closedPortfolio:
            tickerDataFrame = pd.DataFrame(marketData[i[0]][:marketDate])
            tickerDataFrame = tickerDataFrame.dropna(how='any')
            if marketDate == i[3]:
                positionPAndL = (((tickerDataFrame['Open'][-1] - tickerDataFrame['Close'][-2]) * i[2] ) * (-1)) + .001*i[2]*tickerDataFrame['Open'][-1]
            dayPAndL += positionPAndL
            
        self.dailyHoldings[marketDate] = self.dailyHoldingsInsert
        return dayPAndL
    def portfolioValueUpdate(self,portfolioValue,totalProfitAndLoss):
        return portfolioValue + totalProfitAndLoss
    def currentHoldingsValue(self,marketData,currentPortfolio,marketDate,openClose):
        currentPortfolioValue = 0.0
        for i in currentPortfolio:
            if openClose == 1:
                lastPrice = marketData[i[0],marketDate]['Open']
                if np.isnan(lastPrice):
                    lastPrice = marketData[i[0]][:marketDate].dropna(how='any')[-2:-1]['Close'][0]
            elif openClose == 0:
                lastPrice = marketData[i[0],marketDate]['Close']
                if np.isnan(lastPrice):
                    lastPrice = marketData[i[0]][:marketDate].dropna(how='any')[-2:-1]['Close'][0]
            holdingValue = lastPrice * i[2]
            currentPortfolioValue += holdingValue
        return currentPortfolioValue
class model:
    def __init__(self,countries,country_weights):
        self.dailyRankings = dict()
        self.recommendations = []
        self.weightedGDP = self.gdpData(countries,country_weights)
    def gdpData(self,countries,country_weights):
        gdpDf = pd.DataFrame({'Value':[],'country_code':[]})
        for i in countries:
            gdp = quandl.get("WWDI/"+i+"_NY_GDP_MKTP_KN", authtoken='')
            gdp['country_code'] = i
            gdpDf = gdpDf.append(gdp)
        gdpDf['Date']=gdpDf.index
        weightedGDP = pd.merge(gdpDf, country_weights, how='inner', on='country_code')
        weightedGDP['dollar'] = weightedGDP['allocation']*weightedGDP['Value']
        weightedGDP=weightedGDP.groupby(['ticker', 'Date'])['dollar'].sum() 
        return weightedGDP
    def initiatePositionSignal(self,endDate,timeSeriesPanel,weightedGDP):
        analysis = []
        analysisDataFrame = pd.DataFrame({'ticker':[],'gdpPercentile':[]})
        for i in timeSeriesPanel.axes[0]:
            tickerDataFrame = pd.DataFrame(timeSeriesPanel[i][:endDate])
            tickerDataFrame = tickerDataFrame.dropna(how='any')
            tickerDataFrame['movingAverage'] = tickerDataFrame.Close.rolling(window=40).mean()
            if len(tickerDataFrame.index) > 756 and tickerDataFrame.Close.iloc[-1] > tickerDataFrame.movingAverage.iloc[-1]:
                gdpPercentile = pd.DataFrame(weightedGDP[i])
                gdpPercentile['year'] = gdpPercentile.index.year + 1
                tickerDataFrame['year'] = tickerDataFrame.index.year
                tickerDataFrame = pd.merge(gdpPercentile, tickerDataFrame, how='inner', on='year')
                tickerDataFrame['closeToDollar'] = tickerDataFrame.Close / tickerDataFrame.dollar
                tickerDataFrame['rollMean'] = tickerDataFrame.closeToDollar.expanding(min_periods=1).mean()
                tickerDataFrame['rollStd'] = tickerDataFrame.closeToDollar.expanding(min_periods=1).std()
                gdpPercentile = (tickerDataFrame['rollMean'].iloc[-1] - tickerDataFrame['closeToDollar'].iloc[-1]) / tickerDataFrame['rollStd'].iloc[-1]
                analysisDataFrame = analysisDataFrame.append(pd.DataFrame({'ticker':i,'gdpPercentile':gdpPercentile},index = [0]))
        if len(analysisDataFrame) > 7:
            analysisDataFrame = analysisDataFrame.sort('gdpPercentile',ascending=True)
            analysisDataFrame = analysisDataFrame[0:3]
            toTrade = analysisDataFrame.ticker.tolist()
            for j in toTrade:
                analysis.append([j,1])
        analysisDataFrame = pd.DataFrame({'ticker':[],'gdpPercentile':[]})
        for i in timeSeriesPanel.axes[0]:
            tickerDataFrame = pd.DataFrame(timeSeriesPanel[i][:endDate])
            tickerDataFrame = tickerDataFrame.dropna(how='any')
            tickerDataFrame['movingAverage'] = tickerDataFrame.Close.rolling(window=40).mean()
            if len(tickerDataFrame.index) > 756 and tickerDataFrame.Close.iloc[-1] < tickerDataFrame.movingAverage.iloc[-1]:
                gdpPercentile = pd.DataFrame(weightedGDP[i])
                gdpPercentile['year'] = gdpPercentile.index.year + 1
                tickerDataFrame['year'] = tickerDataFrame.index.year
                tickerDataFrame = pd.merge(gdpPercentile, tickerDataFrame, how='inner', on='year')
                tickerDataFrame['closeToDollar'] = tickerDataFrame.Close / tickerDataFrame.dollar
                tickerDataFrame['rollMean'] = tickerDataFrame.closeToDollar.expanding(min_periods=1).mean()
                tickerDataFrame['rollStd'] = tickerDataFrame.closeToDollar.expanding(min_periods=1).std()
                gdpPercentile = (tickerDataFrame['rollMean'].iloc[-1] - tickerDataFrame['closeToDollar'].iloc[-1]) / tickerDataFrame['rollStd'].iloc[-1]
                analysisDataFrame = analysisDataFrame.append(pd.DataFrame({'ticker':i,'gdpPercentile':gdpPercentile},index = [0]))
        if len(analysisDataFrame) > 5:
            analysisDataFrame = analysisDataFrame.sort('gdpPercentile',ascending=False)
            analysisDataFrame = analysisDataFrame[0:1]
            toTrade = analysisDataFrame.ticker.tolist()
            for j in toTrade:
                analysis.append([j,-1])
        print len(analysis)
        return analysis
    def closePositionSignal(self,endDate,timeSeriesPanel,currentPortfolio):
        analysis = []
        for i in currentPortfolio:
            analysis.append([i[0],1])
        return analysis
class trader:
    def __init__(self,minSize,maxSize):
        self.orders = []
        self.closingOrders = []
        self.portfolioCloseTest = []
        self.tradeLog = dict()
        self.dailyTradeLog = []
        self.minSize = minSize
        self.maxSize = maxSize
    def positionSizer(self,cashAvailableToTrade,numberOfOrders,portfolioValue,minSize,maxSize):
        minDollar = minSize * portfolioValue
        maxDollar = maxSize * portfolioValue
        size = np.minimum(maxDollar,(cashAvailableToTrade / numberOfOrders) * .9985)
        if size < minDollar:
            return 0.0
        else:
            return size
    def orderExecute(self,marketDate,marketData,portfolioValue,order,currentPortfolio,holdingsValue):
        tradesMade = []
        cashAvailableToTrade = portfolioValue - holdingsValue
        dollarSize = self.positionSizer(cashAvailableToTrade,len(order),portfolioValue,self.minSize,self.maxSize)
        ordersNotMade = []
        for order in order:
            try:
                tradePrice = marketData.timeSeriesPanel[order[0],marketDate]['Open']
                sharesTraded = int(dollarSize / tradePrice) * order[1]
                if not np.isnan(tradePrice):                
                    tradesMade.append([order[0],tradePrice,sharesTraded,marketDate])
                else:
                    ordersNotMade.append(order)
            except:
                ordersNotMade.append(order)
        self.orders = ordersNotMade
        return tradesMade
    def orderExecuteClose(self,marketDate,marketData,portfolioValue,order,currentPortfolio):
        tradesMade = []
        ordersNotMade = []
        for order in order:
            try:
                tradePrice = marketData.timeSeriesPanel[order[0],marketDate]['Open']
                value = [i for i,x in enumerate(currentPortfolio) if x[0] == order[0]]
                sharesTraded = currentPortfolio[value[0]][2] * -1
                if not np.isnan(tradePrice):
                    tradesMade.append([order[0],tradePrice,sharesTraded,marketDate])
                else:
                    ordersNotMade.append(order)
            except:
                ordersNotMade.append(order)
        self.closingOrders = ordersNotMade
        return tradesMade
class marketData:
    def __init__(self,tickerList,source):
        self.toPanelDict = {}
        self.tickerList = tickerList
        if source == 'pd-datareader':
            for i in self.tickerList:
                try:
                    timeSeries = web.DataReader(i, 'yahoo', datetime.date(2000,01,01), datetime.datetime.now().date())
                    timeSeries = self.dataTransformYahoo(timeSeries)
                    timeSeries = self.dataQuality(timeSeries)
                    self.toPanelDict[i] = timeSeries
                except:
                    print i
        if source == 'quandl':
            for i in self.tickerList:
                print i
                timeSeries = quandl.get(i, authtoken='',trim_start = datetime.date(2000,01,01))
                timeSeries = self.dataTransformGoog(timeSeries)
                timeSeries = self.dataQuality(timeSeries)
                self.toPanelDict[i] = timeSeries
        self.timeSeriesPanel=pd.Panel(self.toPanelDict)
    def dataTransformYahoo(self,timeSeries):
        timeSeries['Open'] = timeSeries['Open'] - (timeSeries['Close'] - timeSeries['Adj Close'])
        timeSeries['High'] = timeSeries['High'] - (timeSeries['Close'] - timeSeries['Adj Close'])
        timeSeries['Low'] = timeSeries['Low'] - (timeSeries['Close'] - timeSeries['Adj Close'])
        timeSeries['Close'] = timeSeries['Adj Close']
        return timeSeries
    def dataTransformGoog(self,timeSeries):
        timeSeries['Open'] = timeSeries['Open'].where((timeSeries['Open'] > 0),timeSeries['Close'])
        return timeSeries[['Open','High','Low','Close']]
    def dataQuality(self,timeSeries):
        timeSeries['pctChangeDay'] = timeSeries['Close'] / timeSeries['Close'].shift(1) - 1
        timeSeries['ReturnOpen'] = abs(timeSeries['Open']/timeSeries['Close']-1)
        timeSeries['Open'] = timeSeries['Open'].where((timeSeries['ReturnOpen'] < 0.4),timeSeries['Close'])
        timeSeries = timeSeries[(timeSeries.pctChangeDay < .5) & (timeSeries.pctChangeDay > -.5)][['Open','High','Low','Close']]
        return timeSeries
class backtester:
    def __init__(self,tickerList,startingValue,minSize,maxSize,country_weights,countries):
        self.model = model(countries,country_weights)
        self.trader = trader(minSize,maxSize)        
        self.marketData = marketData(tickerList,'pd-datareader')
        self.portfolio = portfolio(self.marketData.timeSeriesPanel.axes[1][0],startingValue)
    def startBacktest(self,backTestOffset):
        marketDateMonthPrev = 0
        for marketDate in self.marketData.timeSeriesPanel.axes[1][backTestOffset:]:
            self.trader.dailyTradeLog = []            
            if len(self.trader.closingOrders) > 0:
                portfolioClose = self.trader.orderExecuteClose(marketDate,self.marketData,self.portfolio.portfolioValue,self.trader.closingOrders,self.portfolio.currentPortfolio)
                self.trader.portfolioCloseTest = portfolioClose
                if len(portfolioClose) > 0:
                    for i in portfolioClose:
                        value = [j for j,x in enumerate(self.portfolio.currentPortfolio) if i[0] == x[0]]
                        self.portfolio.currentPortfolio.remove(self.portfolio.currentPortfolio[value[0]])
                        self.portfolio.closedPortfolio.append(i)
                        self.trader.dailyTradeLog.append(i)
            if len(self.trader.orders) > 0:
                holdingsValue = self.portfolio.currentHoldingsValue(self.marketData.timeSeriesPanel,self.portfolio.currentPortfolio,marketDate,1)
                portfolioInitiate = self.trader.orderExecute(marketDate,self.marketData,self.portfolio.portfolioValue,self.trader.orders,self.portfolio.currentPortfolio,holdingsValue)
                if len(portfolioInitiate) > 0:
                    for i in portfolioInitiate:
                        self.portfolio.currentPortfolio.append(i)
                        self.trader.dailyTradeLog.append(i)
            if len(self.trader.dailyTradeLog) > 0:
                self.trader.tradeLog[marketDate] = self.trader.dailyTradeLog
            if marketDate.month <> marketDateMonthPrev:
                toInitiate = self.model.initiatePositionSignal(marketDate,self.marketData.timeSeriesPanel,self.model.weightedGDP)
                self.model.recommendations.append([marketDate,toInitiate])
                toClose = self.model.closePositionSignal(marketDate,self.marketData.timeSeriesPanel,self.portfolio.currentPortfolio)
                self.trader.closingOrders = toClose
                self.trader.orders = toInitiate
            dayPAndL = self.portfolio.profitAndLoss(self.portfolio.currentPortfolio,self.marketData.timeSeriesPanel,marketDate,self.portfolio.closedPortfolio)
            self.portfolio.dailyPAndL = self.portfolio.dailyPAndL.append(pd.DataFrame({'dayPAndL':dayPAndL},index=[marketDate]))
            self.portfolio.closedPortfolio = []
            self.portfolio.portfolioValue = self.portfolio.portfolioValueUpdate(self.portfolio.portfolioValue,dayPAndL)
            holdingsValue = self.portfolio.currentHoldingsValue(self.marketData.timeSeriesPanel,self.portfolio.currentPortfolio,marketDate,0)
            self.portfolio.equityCurve = self.portfolio.equityCurve.append(pd.DataFrame({'portfolio':self.portfolio.portfolioValue,'holdings':holdingsValue},index=[marketDate]))
            marketDateMonthPrev = marketDate.month
backTestStartOffset = 252
startingValue = 1000000
country_weights = pd.read_csv('country_indices.csv')
countries = country_weights.country_code.unique()
tickerList = country_weights.ticker.unique()
bbc = backtester(tickerList,startingValue,.03,.25,country_weights,countries)
bbc.startBacktest(backTestStartOffset)

visualize_analysis_pyplot(bbc.portfolio.equityCurve.index,bbc.portfolio.equityCurve.portfolio)

workbook = xl.Workbook('backtestIshares.xlsx')
worksheetDashboard = workbook.add_worksheet('Dashboard')
worksheetTradeLog = workbook.add_worksheet('Trade Log')
worksheetDailyHoldings = workbook.add_worksheet('Daily Holdings')
worksheetEquityCurve = workbook.add_worksheet('EquityCurve')
i=2
for date in sorted(bbc.trader.tradeLog):
    worksheetTradeLog.write(i,0,date)
    for j in bbc.trader.tradeLog[date]:
        worksheetTradeLog.write(i,1,j[0])
        worksheetTradeLog.write(i,2,j[1])
        worksheetTradeLog.write(i,3,j[2])
        i += 1
worksheetTradeLog.write(0,0,'Date')
worksheetTradeLog.write(0,1,'Security')
worksheetTradeLog.write(0,2,'Trade Price')
worksheetTradeLog.write(0,3,'Shares')
i=2
for date in sorted(sorted(bbc.portfolio.dailyHoldings)):
    worksheetDailyHoldings.write(i,0,date)
    for j in bbc.portfolio.dailyHoldings[date]:
        worksheetDailyHoldings.write(i,1,j[0])
        worksheetDailyHoldings.write(i,2,j[1])
        worksheetDailyHoldings.write(i,3,j[2])
        worksheetDailyHoldings.write(i,4,j[3])
        worksheetDailyHoldings.write(i,5,j[4])
        worksheetDailyHoldings.write(i,6,j[5])
        i += 1
worksheetDailyHoldings.write(0,0,'Date')
worksheetDailyHoldings.write(0,1,'Security')
worksheetDailyHoldings.write(0,2,'Trade Price')
worksheetDailyHoldings.write(0,3,'Shares')
worksheetDailyHoldings.write(0,4,'Previous Close')
worksheetDailyHoldings.write(0,5,'Close')
worksheetDailyHoldings.write(0,6,'Day P&L')
portfolioDays = len(bbc.portfolio.equityCurve.index)
for i in range(portfolioDays):
    worksheetEquityCurve.write(i+1,0,bbc.portfolio.equityCurve.index[i])
    worksheetEquityCurve.write(i+1,1,bbc.portfolio.equityCurve.portfolio[i])
    worksheetEquityCurve.write(i+1,2,bbc.portfolio.equityCurve.holdings[i])
worksheetEquityCurve.write(0,0,'Date')
worksheetEquityCurve.write(0,1,'Portfolio Close Value')


dateFormat = workbook.add_format({'num_format':'mm/dd/yyyy'})
dollarFormat = workbook.add_format({'num_format':'$###,###,##0'})
worksheetDailyHoldings.set_column('A:A', 11, dateFormat)
worksheetTradeLog.set_column('A:A', 11, dateFormat)
worksheetEquityCurve.set_column('A:A', 11, dateFormat)
worksheetEquityCurve.set_column('B:B', 11, dollarFormat)

chart1 = workbook.add_chart({'type': 'line','trendline': {'type': 'linear'}})
chart1.add_series({'values': '=EquityCurve!B2:B'+str(portfolioDays+1),'categories': '=EquityCurve!A2:A'+str(portfolioDays+1)})

chart1.set_title({'name': 'Equity Curve','name_font': {'name': 'Calibri','color': '#E5E5E5','bold':True,'size':14}})
chart1.set_legend({'position': 'none'})
chart1.set_size({'width': 578, 'height': 400})
chart1.set_x_axis({
    'minor_tick_mark':'none',
    'major_tick_mark':'none',
    'num_font': {
        'name': 'Calibri',
        'color': '#E5E5E5'
    },'major_gridlines': {
        'visible': True,
        'line': {'width': 0.25},
        'color':'gray'}})
chart1.set_y_axis({
    'minor_tick_mark':'none',
    'major_tick_mark':'none',
    'num_font': {
        'name': 'Calibri',
        'color': '#E5E5E5'
    },'major_gridlines': {
        'visible': True,
        'line': {'width': 0.25},
        'color':'gray'}})
chart1.set_chartarea({'fill':{'color': '#404040'},'border': {'none': True}})
chart1.set_plotarea({'fill':{'color': '#404040'}})
worksheetDashboard.insert_chart('A1', chart1)
workbook.close()