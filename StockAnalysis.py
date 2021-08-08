import finnhub
import requests
import time
import re
import copy
import os

finnhub_client = finnhub.Client(api_key="YOUR_FINNHUB_KEY")
symbolDict = finnhub_client.stock_symbols('US')
symbolList = []
AnalystList = []
doNotAnalyze = set()
howMany = 100000
PRICE_THRESHOLD = 10.0
MARKETCAP_THRESHOLD = 1000000000.0
ANALYST_THRESHOLD = 8


backupFile = open("backup.txt", "r+")
saveFile = open("StockInfo.txt", "w")

PriceWeight = 0.0
MarketCapWeight = 0.0
DividendWeight = 0.05
AnalystWeight = 0.1
BuyWeight = 0.3
OverweightWeight = 0.1
HoldWeight = -0.1
UnderweightWeight = -0.3
SellWeight = -0.5
LowcastWeight = 0.6
ForecastWeight = 0.4
HighcastWeight = 0.1

price = 0.0
marketCap = 0
dividendYield = 0.0

analysts = 0
Buy = 0
Overweight = 0
Hold = 0
Underweight = 0
Sell = 0

lowcast = -100.0
forecast = -100.0
highcast = -100.0


opMode = 0
try:
    print("Press 0 for Continuation: ")
    print("Press 1 for Restart: ")
    print("Press Anything Else for Instant Calculation")
    opMode = int(input("Select Option: "))
    if (opMode != 0 and opMode != 1):
        opMode = 2
except:
    opMode = 2

if (opMode == 1):
    backupFile.truncate(0)
    saveFile.truncate(0)

backupData = backupFile.readlines()
for datastr in backupData:
    data = datastr.split(",")
    for i in range(1, len(data)):
        data[i] = float(data[i])

    if (data[1] <= PRICE_THRESHOLD and data[1] != 0 and data[2] >= MARKETCAP_THRESHOLD and data[4] >= ANALYST_THRESHOLD):
        AnalystList.append(data)
    
    doNotAnalyze.add(data[0])

if (opMode == 0 or opMode == 1):
    for symbol in symbolDict:
        if (symbol['symbol'] not in doNotAnalyze):
            symbolList.append(symbol['symbol'])

    if (howMany > len(symbolList)):
        howMany = len(symbolList)

    for symbol in range(howMany):
        ticker = symbolList[symbol]
        CNBC = f"https://www.cnbc.com/quotes/{ticker}?qsearchterm={ticker}"
        CNBCSource = requests.get(CNBC).text.replace("\n","").replace(" ","")

        try:
            marketCapStr = re.search('MarketCap.*-value">([0-9]*\.[0-9]*(M|B|T)).*SharesOut', CNBCSource).group(1)
            multiFactor = 0
            if (marketCapStr[-1] == 'T'):
                multiFactor = 1000000000000
            elif(marketCapStr[-1] == 'B'):
                multiFactor = 1000000000
            elif(marketCapStr[-1] == 'M'):
                multiFactor = 1000000
            marketCap = float(marketCapStr[0:len(marketCapStr)-1]) * multiFactor
        except:
                marketCap = 0
        
        try:
            price = float(re.search('Open.*-price">([0-9]*\.[0-9]*).*-name">DayHigh', CNBCSource).group(1))
        except:
            price = 0

        try:
            dividendYield = float(re.search('DividendYield.*-price">([0-9]*\.[0-9]*)%.*Beta', CNBCSource).group(1))
        except:
            dividendYield = 0

        MKTWatch = f"https://www.marketwatch.com/investing/stock/{ticker}/analystestimates?mod=mw_quote_tabs"
        MKTSource = requests.get(MKTWatch).text.replace("\n","").replace(" ","")

        try:
            AnalystData = re.search('analyst-ratings(.*)Consensus', MKTSource).group(1)
            AnalystList = re.findall('value">([0-9]*)</span></div></td></tr>', AnalystData)
            analysts = 0
            for i in range(len(AnalystList)):
                AnalystList[i] = int(AnalystList[i])
                analysts += AnalystList[i]
            Buy = AnalystList[0]
            Overweight = AnalystList[1]
            Hold = AnalystList[2]
            Underweight = AnalystList[3]
            Sell = AnalystList[4]

        except:
            analysts = 0
            Buy = 0
            Overweight = 0
            Hold = 0
            Underweight = 0
            Sell = 0

        try:
            ForecastData = re.search('StockPriceTargets(.*)YearlyNumbers', MKTSource).group(1)
            ForecastList = re.findall('cellw25">\$([0-9]*\.[0-9]*)</td></tr>', ForecastData)
            for i in range(len(ForecastList)):
                ForecastList[i] = float(ForecastList[i])

            highcast = round(((ForecastList[0] / price) - 1) * 100, 2)
            forecast = round(((ForecastList[1] / price) - 1) * 100, 2)
            lowcast = round(((ForecastList[2] / price) - 1) * 100, 2)
                
        except:
            lowcast = -100
            forecast = -100
            highcast = -100
        
        data = (f"{ticker},{price},{marketCap},{dividendYield},{analysts},{Buy},{Overweight},{Hold},{Underweight},{Sell},{lowcast},{forecast},{highcast}")
        backupFile.write(f"{data}\n")
        if (price <= PRICE_THRESHOLD and price != 0 and marketCap >= MARKETCAP_THRESHOLD and analysts >= ANALYST_THRESHOLD):
            AnalystList.append([ticker,price,marketCap,dividendYield,analysts,Buy,Overweight,Hold,Underweight,Sell,lowcast,forecast,highcast])
            print(f"{symbol+1} out of {howMany}: {data}")

PointList = copy.deepcopy(AnalystList)

WeightList = [None, PriceWeight, MarketCapWeight, DividendWeight, AnalystWeight, BuyWeight, OverweightWeight, HoldWeight, UnderweightWeight, SellWeight, LowcastWeight, ForecastWeight, HighcastWeight]
for c in range(1, len(PointList[0])):
    PointList.sort(key=lambda x: x[c])
    for r in range(len(PointList)):
        PointList[r][c] = PointList[r][c] / PointList[len(PointList)-1][c]
        PointList[r][c] = round(PointList[r][c], 4)

PointList.sort(key=lambda x: x[0])
AnalystList.sort(key=lambda x: x[0])
for r in range(len(PointList)):
    points = 0
    for c in range(1, len(WeightList)):
        points += PointList[r][c] * WeightList[c]
    AnalystList[r].append(round(points, 4))
    PointList[r].append(round(points, 4))

TotalLength = len(AnalystList[0]) - 1
AnalystList.sort(key=lambda x: x[TotalLength])
PointList.sort(key=lambda x: x[TotalLength])

AnalystList.reverse()

for i in range(len(AnalystList)):
    saveFile.write(f"{str(AnalystList[i])}\n") 
saveFile.close()
backupFile.close()