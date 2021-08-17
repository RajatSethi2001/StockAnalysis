import requests
import time
import re
import copy
import os
import asyncio
import aiohttp

backupFile = open("backup.txt", "r+")
saveFile = open("StockInfo.txt", "w")
nasdaqFile = open("nasdaqFile.txt", "w+")
nyseFile = open("nyseFile.txt", "w+")
os.system("bash ./nasdaq.sh > nasdaqFile.txt")
os.system("bash ./nyse.sh > nyseFile.txt")

nasdaqList = nasdaqFile.readlines()
nyseList = nyseFile.readlines()
symbolDict = {}

for line in range(len(nasdaqList)):
    nasdaqList[line] = nasdaqList[line].split(" ")
    symbolDict[nasdaqList[line][0]] = "NASDAQ"

for line in range(len(nyseList)):
    nyseList[line] = nyseList[line].split(" ")
    if (nyseList[line][2] == "N"):
        symbolDict[nyseList[line][0]] = "NYSE"

AnalystList = []
symbolNum = 0
PRICE_THRESHOLD = 100000000.0
MARKETCAP_THRESHOLD = 0.0
ANALYST_THRESHOLD = 6

PriceWeight = 0.0
MarketCapWeight = 0.0
DividendWeight = 0.05
AnalystWeight = 0.0
BuyWeight = 0.8
OverweightWeight = 0.5
HoldWeight = -0.5
SellWeight = -0.5
LowcastWeight = 0.8
ForecastWeight = 1.2
HighcastWeight = 0.05

RankingWeight = 0.6
PointWeight = 0.4

async def fetch(session, url, ticker):
    async with session.get(url) as resp:
        try:
            text = await resp.text()
            await scrape(text, ticker)
        except:
            pass

async def scrape(text, ticker):
    global symbolNum
    global ANALYST_THRESHOLD
    global PRICE_THRESHOLD
    global MARKETCAP_THRESHOLD
    global AnalystList
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
    
    MarketSource = text.replace("\n","").replace(" ","").replace(",","")

    try:
        marketCapStr = re.search('MarketCapitalization<strong>\$([0-9]+\.[0-9]*(m|b|t))', MarketSource).group(1)
        multiFactor = 0
        if (marketCapStr[-1] == 't'):
            multiFactor = 1000000000000
        elif(marketCapStr[-1] == 'b'):
            multiFactor = 1000000000
        elif(marketCapStr[-1] == 'm'):
            multiFactor = 1000000
        marketCap = int(float(marketCapStr[0:len(marketCapStr)-1]) * multiFactor)
    except:
        marketCap = 0

    try:
        dividendYield = float(re.search('DividendYield<strong>([0-9]+\.[0-9]*)%', MarketSource).group(1))
    except:
        dividendYield = 0

    try:
        price = float(re.search("'price'><strong>\$([0-9]+\.[0-9]*)</strong>", MarketSource).group(1))
    except:
        price = 0

    try:
        lowcast = round(float(re.search(f'thelowpricetargetfor{ticker}is\$([0-9]+\.[0-9]*)\.', MarketSource).group(1)) * 100/price - 100, 2)          
    except:
        lowcast = -100
        
    try:
        forecast = round(float(re.search('averagetwelve\-monthpricetargetis\$([0-9]+\.[0-9]*)predicting', MarketSource).group(1)) * 100/price - 100, 2)
    except:
        forecast = -100
    
    try:
        highcast = round(float(re.search(f'Thehighpricetargetfor{ticker}is\$([0-9]+\.[0-9]*)and', MarketSource).group(1)) * 100/price - 100, 2)
    except:
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
    #print([price, marketCap, analysts])
    if (price <= PRICE_THRESHOLD and price != 0 and marketCap >= MARKETCAP_THRESHOLD and analysts >= ANALYST_THRESHOLD):
        AnalystList.append([ticker,price,marketCap,dividendYield,analysts,Buy,Overweight,Hold,Sell,lowcast,forecast,highcast])
        print(f"{symbolNum+1}: {data}")

async def main(symbolDict):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for ticker in symbolDict.keys():
            url = f"https://www.marketbeat.com/stocks/{symbolDict[ticker]}/{ticker}/price-target/"
            task = asyncio.create_task(fetch(session, url, ticker))
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

    if (data[1] <= PRICE_THRESHOLD and data[1] != 0 and data[2] >= MARKETCAP_THRESHOLD and data[4] >= ANALYST_THRESHOLD):
        AnalystList.append(data)
    
    symbolDict.pop(data[0])

if (opMode == 0 or opMode == 1):
    asyncio.run(main(symbolDict))  

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