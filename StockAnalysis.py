import finnhub
import requests
import time
import re
import copy
import os
import asyncio
import aiohttp

finnhub_client = finnhub.Client(api_key="YOUR_FINNHUB_KEY")
symbolDict = finnhub_client.stock_symbols('US')
symbolList = []
AnalystList = []
doNotAnalyze = set()
howMany = 100000
symbolNum = 0
PRICE_THRESHOLD = 100000000.0
MARKETCAP_THRESHOLD = 1000000000.0
ANALYST_THRESHOLD = 6


backupFile = open("backup.txt", "r+")
saveFile = open("StockInfo.txt", "w")

PriceWeight = 0.0
MarketCapWeight = 0.0
DividendWeight = 0.05
AnalystWeight = 0.0
BuyWeight = 0.5
OverweightWeight = 0.3
HoldWeight = -0.3
SellWeight = -0.5
LowcastWeight = 0.8
ForecastWeight = 0.8
HighcastWeight = 0.05

RankingWeight = 0.6
PointWeight = 0.4

async def fetch(session, url):
    async with session.get(url) as resp:
        return await resp.text()

async def fetch_all(session, urls, ticker):
    tasks = []
    CNBCTask = asyncio.create_task(fetch(session, urls[0]))
    tasks.append(CNBCTask)
    CNNTask = asyncio.create_task(fetch(session, urls[1]))
    tasks.append(CNNTask)
    results = await asyncio.gather(*tasks)
    if (re.search("NYSE", results[1]) == None):
        urls[2] = f"{urls[2]}/NASDAQ/{ticker}/price-target/"
    else:
        urls[2] = f"{urls[2]}/NYSE/{ticker}/price-target/"
    MarketTask = await fetch(session, urls[2])
    results.append(MarketTask)
    return results

async def scrape(texts, ticker):
    global symbolNum
    price = 0.0
    marketCap = 0
    dividendYield = 0.0

    analysts = 0
    Buy = 0
    Overweight = 0
    Hold = 0
    Sell = 0

    lowcast = -100.0
    forecast = -100.0
    highcast = -100.0

    CNBCSource = texts[0].replace("\n","").replace(" ","").replace(",","")
    CNNSource = texts[1].replace("\n","").replace(" ","").replace(",","")
    MarketSource = texts[2].replace("\n","").replace(" ","").replace(",","")

    try:
        marketCapStr = re.search('MarketCap.*-value">([0-9]*\.[0-9]*(M|B|T)).*SharesOut', CNBCSource).group(1)
        multiFactor = 0
        if (marketCapStr[-1] == 'T'):
            multiFactor = 1000000000000
        elif(marketCapStr[-1] == 'B'):
            multiFactor = 1000000000
        elif(marketCapStr[-1] == 'M'):
            multiFactor = 1000000
        marketCap = round(float(marketCapStr[0:len(marketCapStr)-1]) * multiFactor, 1)
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

    try:
        highcast = round(float(re.search('highestimateof(.*)andalow', CNNSource).group(1)) * 100/price - 100, 2)
        forecast = float(re.search('representsa<spanclass="(pos|neg)Data">(.*)%</span>(incr|decr)', CNNSource).group(2))
        lowcast = round(float(re.search('lowestimateof(.*)\.Themediane', CNNSource).group(1)) * 100/price - 100, 2)
                            
    except:
        lowcast = -100
        forecast = -100
        highcast = -100

    try:
        CurrentRatings = re.search("AnalystRatings:</strong></td><td>(.*)StrongBuyRating\(s\)",MarketSource).group(1)
        RemoveIndex = CurrentRatings.index("</td><td>")
        CurrentRatings = CurrentRatings[0:RemoveIndex]
        AnalystArray = re.findall("([0-9]+)", CurrentRatings)
        Buy = int(AnalystArray[3])
        Overweight = int(AnalystArray[2])
        Hold = int(AnalystArray[1])
        Sell = int(AnalystArray[0])
        analysts = Buy + Overweight + Hold + Sell

    except:
        analysts = 0
        Buy = 0
        Overweight = 0
        Hold = 0
        Sell = 0
            
    data = (f"{ticker},{price},{marketCap},{dividendYield},{analysts},{Buy},{Overweight},{Hold},{Sell},{lowcast},{forecast},{highcast}")
    backupFile.write(f"{data}\n")
    symbolNum += 1
    if (len(ticker) < 5 and price <= PRICE_THRESHOLD and price != 0 and marketCap >= MARKETCAP_THRESHOLD and analysts >= ANALYST_THRESHOLD):
        AnalystList.append([ticker,price,marketCap,dividendYield,analysts,Buy,Overweight,Hold,Sell,lowcast,forecast,highcast])
        print(f"{symbolNum+1} out of {howMany}: {data}")

async def runAll(session, urls, ticker):
    await asyncio.sleep(1)
    texts = await fetch_all(session, urls, ticker)
    await scrape(texts, ticker)

async def main(howMany, symbolList):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for symbol in range(howMany):
            ticker = symbolList[symbol]
            urls = [f"https://www.cnbc.com/quotes/{ticker}?qsearchterm={ticker}",
                    f"https://money.cnn.com/quote/forecast/forecast.html?symb={ticker}",
                    f"https://www.marketbeat.com/stocks"]

            task = asyncio.create_task(runAll(session, urls, ticker))
            tasks.append(task)

        await asyncio.gather(*tasks)


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

    if (len(data[0]) < 5 and data[1] <= PRICE_THRESHOLD and data[1] != 0 and data[2] >= MARKETCAP_THRESHOLD and data[4] >= ANALYST_THRESHOLD):
        AnalystList.append(data)
    
    doNotAnalyze.add(data[0])

if (opMode == 0 or opMode == 1):
    for symbol in symbolDict:
        if (symbol['symbol'] not in doNotAnalyze and len(symbol['symbol']) < 5):
            symbolList.append(symbol['symbol'])

    if (howMany > len(symbolList)):
        howMany = len(symbolList)

    asyncio.run(main(howMany, symbolList))    

PointList = copy.deepcopy(AnalystList)
RankingList = copy.deepcopy(AnalystList)

WeightList = [None, PriceWeight, MarketCapWeight, DividendWeight, AnalystWeight, BuyWeight, OverweightWeight, HoldWeight, SellWeight, LowcastWeight, ForecastWeight, HighcastWeight]
for c in range(1, len(PointList[0])):
    PointList.sort(key=lambda x: x[c])
    for r in range(len(PointList)):
        PointList[r][c] = PointList[r][c] / PointList[len(PointList)-1][c]
        PointList[r][c] = round(PointList[r][c], 4)

for c in range(1, len(RankingList[0])):
    RankingList.sort(key=lambda x: x[c])
    for r in range(len(RankingList)):
        RankingList[r][c] = (r + 1) / len(RankingList)

RankingList.sort(key=lambda x: x[0])
PointList.sort(key=lambda x: x[0])
AnalystList.sort(key=lambda x: x[0])
for r in range(len(PointList)):
    for c in range(1, len(PointList[0])):
        PointList[r][c] = PointList[r][c] * PointWeight + RankingList[r][c] * RankingWeight

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