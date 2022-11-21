import requests
import json
from datetime import datetime, timedelta
import csv
from time import sleep
import os.path
import pandas as pd
from backtest_config import start_date_timestamp, symbol_list_BTC_ONLY, symbol_list, initial_capital
from collections import Counter
import xlsxwriter
import pandas as pdpip3


#url = "https://api.binance.com/api/v3/klines?symbol="+symbol+"&interval="+interval+"&startTime="+startTime+"&endTime="+endTime+"&limit=1000"
#Start time of: 1501545600000 = 2017-08-01 01:00:00
#Binance API call: https://api.binance.com/
#looking for kline: api/v3/klines
#kline data:
"""symbol	    STRING	    YES	
interval	    ENUM	    YES	
startTime	    LONG	    NO	
endTime	L       ONG	        NO	
limit	        INT     	NO"""

wallet = []

"""Get price history: This function searches binance, grabs the latest kline data at the interval charts and appends it to the bottom of the csv."""
def get_price_history(symbol, interval):
    """Get price history: This function searches binance, grabs the latest kline data at the interval charts and appends it to the bottom of the csv."""

    #The endtime must be identified to stop the script
    date_time_Last_2_hours = datetime.now() - timedelta(hours=2)
    endTime = datetime.fromtimestamp(int("1501545600000") / 1000)

    #check if a file already exists, if it does, collect data from last readding. if not, collect data from 2017 start time.
    file_exists = os.path.exists(f"{symbol}_prices_{interval}.csv")
    if file_exists:
        with open(f"{symbol}_prices_{interval}.csv", "r", newline='') as f1:
            last_line = f1.readlines()[-1]
            startTime = last_line[:13]

    #below is the standard start time for collecting data. 1501545600000 comes out to be: 2017-08-01 01:00:00
    else:
        data_csv = open(f"{symbol}_prices_{interval}.csv", "a", newline='')
        csv_writer = csv.writer(data_csv)
        csv_writer.writerow(
            ["Kline open time", "Open", "High", "Low", "Close", "Volume", "Kline Close time", "Quote asset volume",
             "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "unused field, Ignore"])
        startTime = "1501545600000"


    while endTime < date_time_Last_2_hours:
        url = "https://api.binance.com/api/v3/klines?symbol="+symbol+"&interval="+interval+"&startTime="+startTime+"&limit=1000"

        #run requests to get the url data from binance
        r = requests.get(url)
        prices_json = r.json()

        #save the json
        with open(f"{symbol}_prices_{interval}.json", "a") as fp:
            json.dump(prices_json, fp)

        #If there is data in the file, find the last entry to avoid duplicating entries.
        if file_exists:
            #open the csv to save data to
            data_csv = open(f"{symbol}_prices_{interval}.csv", "a", newline='')
            csv_writer = csv.writer(data_csv)

            #writing price data with timestap after
            for item in prices_json:
                if int(item[0]) > int(startTime):
                    print(symbol, item)
                    csv_writer.writerow(item)

        #if new file, create write file and use start date of 2017
        else:
            data_csv = open(f"{symbol}_prices_{interval}.csv", "a", newline='')
            csv_writer = csv.writer(data_csv)

            for item in prices_json:
                print(item)
                csv_writer.writerow(item)

        data_csv.close()
        list_len = len(prices_json)-1
        print(symbol, prices_json[list_len])
        startTime = str(prices_json[len(prices_json)-1][0])
        print('startTime:', startTime)
        endTime = datetime.fromtimestamp(prices_json[len(prices_json)-1][0]/1000)
        print('endTime:', endTime)
        sleep(0.3)

"""Create a list of each week Startdate. This can be used to change what day of the week trades are checked if there is statistical significance"""
def week_startdate_list(start_date_as_timestamp):
    weekly_loop = start_date_as_timestamp
    current_timestamp = int(datetime.now().timestamp())
    list_of_weeks_since_startdate = []
    weekly_milliseconds = 604800
    loop = 0
    print("Start date:", datetime.fromtimestamp(weekly_loop))
    print("Current date:", datetime.fromtimestamp(current_timestamp))
    while int(weekly_loop) < int(current_timestamp):
        date = datetime.fromtimestamp(int(weekly_loop))
        date_timestamped = date.timestamp()
        list_of_weeks_since_startdate.append(round(int(date_timestamped)))
        weekly_loop += weekly_milliseconds

    with open("list_of_weeks.csv", "w", newline='') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=",")
        csv_writer.writerow(list_of_weeks_since_startdate)
    print("list_of_weeks.csv UPDATED.")

"""This function aims to take the previous price data, and find the weekly_close times to allow calculation of trading signals and rebalancing"""
def get_weekly_close_price(coin, interval):

    #find the first saturday in price history
    fp = open(f"{coin}_prices_{interval}.csv", "r")
    #find a starting date to work from
    count = 0
    start_time = 0
    weekly_start_list = []
    for item in fp:
        if count == 0:
            count += 1
            pass
        else:
            start_time = int(item[:13])
            #if date.weekday == 0, then this is monday
            if datetime.fromtimestamp(start_time/1000).weekday() == 0:
                #print(datetime.fromtimestamp(start_time/1000),"\n")
                break
    #number of milliseconds in a week
    weekly_milliseconds = 604800

    #create a list of all the weekly start dates to check against the time.
    time = int(start_time/1000)
    weekly_closes = []
    current_timestamp = datetime.now().timestamp()
    while time < current_timestamp:
        weekly_start_list.append(time*1000)
        time += weekly_milliseconds

    #remove first item to ensure overlap is caught
    weekly_start_list = weekly_start_list[1:]

    for time in weekly_start_list:
        for item in fp:
            array = item.split(",")
            coin_time = int(array[0])
            price = array[3]
            if coin_time == time:
                weekly_closes.append([time, price])
                break
            else:
                pass
    data = pd.DataFrame(weekly_closes, columns=['timestamp', 'close_price'])
    data.to_csv(f"{coin}_weekly_closes.csv")

def weekly_signals_from_startdate(symbol_list):
    #initialising all variables
    start_date = start_date_timestamp
    weekly_clock = int(start_date)
    current_timestamp = int(datetime.now().timestamp())
    weekly_milliseconds = 604800000

    #get a list of active coins to aprse through and build portfolio.
    # quantities_list = []
    weekly_active_list = []

    for symbol in symbol_list:
        with open(f"{symbol}_weekly_closes.csv", "r") as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            count = 0
            for line in csv_reader:
                if count < 7:
                    count += 1
                else:
                    price_time = round(int(line[1])/1000)
                    sma7 = sma(symbol, 7, price_time * 1000)
                    sma50 = sma(symbol, 50, price_time * 1000)
                    if sma7 > sma50:
                        input1 = (price_time, datetime.fromtimestamp(int(line[1])/1000), symbol, line[2], "ACTIVE", sma7, sma50)
                        weekly_active_list.append(input1)
                    elif sma7 < sma50:
                        input2 = (price_time, datetime.fromtimestamp(int(line[1])/1000), symbol, line[2], "INACTIVE", sma7, sma50)
                        weekly_active_list.append(input2)
    data_csv = open("weekly_signals.csv", "w", newline='')
    csv_writer = csv.writer(data_csv)
    csv_writer.writerows(weekly_active_list)
    print("weekly_signals.csv UPDATED")

    return weekly_active_list

"""Calculate the weekly profits/losses, drawdowns, availability etc """

def weekly_signals_into_csv(weekly_active_list):
    workbook = xlsxwriter.Workbook('backteser_strategy.xlsx', "a")
    worksheet = workbook.add_worksheet("raw_data")
    for item in weekly_active_list:
        worksheet.write(item)

def func_backtest_start_data():
    #initialise variables
    backtest_start_data = []
    #open the weekly list document to calculate the outputs at each weekly date.
    with open("list_of_weeks.csv", "r") as list_of_weeks:
        list_of_weeks_reader = csv.reader(list_of_weeks)
        count = 0
        for weekly_timestamp in list_of_weeks_reader:
            #this loops through the full csv file. item is the list of dates. item[0] is the first weekly start date.
            #while count < len(item):
            while count < 1:
                # print("Count:", count)
                # print("len(timestamp):", len(weekly_timestamp))

                #For each date, collate weekly date and run processing.

                with open("weekly_signals.csv", "r") as weekly_signals:
                    weekly_signals_reader = csv.reader(weekly_signals)
                    for line in weekly_signals_reader:
                        #determining the startpoint, if startpoint then no selling, only buying if active.
                        if weekly_timestamp[count] == line[0]:
                            backtest_start_data.append(line)
                count +=1

    return backtest_start_data

"""weekly_wallet Generator creates a list of which coins are active each weeks."""
def weekly_active_coins():
    #initialise variables
    weekly_wallet = []
    wallet_dict = {}

    with open("list_of_weeks.csv", "r") as list_of_weeks:
        list_of_weeks_reader = csv.reader(list_of_weeks)
        for list in list_of_weeks_reader:
            for week in list:
                with open('weekly_signals.csv', "r") as weekly_signals:
                    weekly_signals_reader = csv.reader(weekly_signals)
                    intraweek_coins = []
                    for item in weekly_signals_reader:
                        if int(item[0]) == int(week) and item[4] == "ACTIVE":
                            data = [item[2], item[3]]
                            intraweek_coins.append(data)
                    wallet_dict[week] = {
                        'intraweek_coins': intraweek_coins,
                        }
                wallet_data = [week, intraweek_coins]
                weekly_wallet.append(wallet_data)
    return wallet_dict, weekly_wallet

"""Calculated the moving average for a given symbol, over a given period, froma  given date. SMA is also using an itnerval of 1DAy."""
def sma(symbol, sma_period, timestamp): # timestamp is the time from which you wich to establish the sma. ie if you want to know the last sma for the last 7 days, you use the current timestamp.

    """Initialise variables"""
    ave_prices = 0.0
    daily_milliseconds = 86400000
    iter_count_sma = sma_period
    sma_count = 0
    sma = 0
    #hour chart is able to provide the daily price close data by finding line[0] which matches weekly time - daily miliseconds
    with open(f"{symbol}_prices_1h.csv", "r") as hourly_csv:
        hourly_csv_reader = csv.reader(hourly_csv, delimiter=',')

        """Calcuating 7SMA start time"""
        #find the weekly close price on the hourly csv
        day_1_time = timestamp - (sma_period * daily_milliseconds)
        period_count = day_1_time
        row_counter = 0
        for line in hourly_csv_reader:
            if row_counter == 0:
                row_counter += 1
            elif row_counter == 1 and sma_count < iter_count_sma and int(line[0]) == period_count:
                ave_prices +=float(line[4])
                period_count += 86400000
                sma_count += 1
                sma = ave_prices/sma_period
            elif row_counter == 1 and sma_count >= iter_count_sma:
                break

    return sma

"""Generate an unbalanced wallet to bring forards into the rebalancing., this deliver for an individual timestamp so must be run for each timestamp ina  list"""
def week1_wallet_data(start_date_timestamp, week_timestamp, total_portfolio_value, weekly_active_coins_list, weekly_active_coins_dict, symbol_list):
    week_as_date = datetime.fromtimestamp(int(week_timestamp))
    wallet_coin_list = []
    buy_hold_wallet_data = []
    week1_wallet_data = []
    portfolio_split = 0
    cash_avail = 0
    running_total = 0
    cash_portfolio_value = {}
    week1_wallet_coin = []

    #Get the first weeks data. from the first week data, you can use first week data as last week to do automatic rebalancing
    for week in weekly_active_coins_list:
        if int(week[0]) == int(week_timestamp) and int(week[0]) == int(start_date_timestamp):
            for coin in week[1]:
                if len(week[1]) == 0:
                    portfolio_split = 0
                else:
                    portfolio_split = int(total_portfolio_value) / len(week[1])
                quantity = portfolio_split / float(coin[1])
                value = quantity * float(coin[1])
                coin_data = [coin[0], quantity, float(coin[1]), value]
                running_total += value
                week1_wallet_coin.append(coin_data)
                #print(len(symbol_list), len(week[1]))
                cash_avail = (len(symbol_list) - len(week[1])) * portfolio_split
            total_portfolio_value = cash_avail + running_total
    data = [cash_avail, total_portfolio_value]
    week1_wallet_data.append(week_timestamp)
    week1_wallet_data.append(week1_wallet_coin)
    week1_wallet_data.append(data)
    wallet_data_dict = {
        'wallet': week1_wallet_coin,
        'cash_avail': cash_avail,
        'portfolio_value': total_portfolio_value
        }

    return week1_wallet_data, wallet_data_dict
def symbol_in_both(data, this_week, last_week, start_date_timestamp, weekly_wallet, this_week_quantity, coins_only_last, coins_only_week, this_week_price,this_week_coin_data, symbol, weekly_active_coins_dict, this_week_portfolio_split):
    # print(symbol, "active symbol has coins in wallet. rebalancing required")
    print("line 391", int(last_week), int(start_date_timestamp))
    if int(last_week) == int(start_date_timestamp):
        for ww_item in weekly_wallet[1]:
            if ww_item[0] == symbol:
                last_week_quantity = ww_item[1]
                last_week_price = ww_item[2]
                for wacd_item in weekly_active_coins_dict[this_week]["intraweek_coins"]:
                    if wacd_item[0] == symbol:
                        this_week_price = float(wacd_item[1])
                        this_week_value = this_week_price * last_week_quantity
                        # print(symbol, this_week_value, this_week_portfolio_split)
                        if this_week_value >= this_week_portfolio_split:
                            this_week_quantity = this_week_portfolio_split / this_week_price
                            value_delta = last_week_quantity - this_week_quantity
                            # print(f"sell {value_delta}")
                        elif this_week_value <= this_week_portfolio_split:
                            this_week_quantity = this_week_portfolio_split / this_week_price
                            value_delta = this_week_quantity - last_week_quantity
                            # print(f"buy {value_delta}")
                data = [symbol, this_week_quantity, this_week_price, this_week_portfolio_split]
                print("data line 408:", data)
                if data == []:
                    print("409 line - error")
                else:
                    this_week_coin_data.append(data)
                this_week_cash_avail = 0
            else:
                print("417 - Error on if statement")
    else:
        print(f"419 - Error on if statement{symbol},{coins_only_last}, {coins_only_week}")

    return this_week_coin_data
def symbol_only_this_week(data, this_week, last_week, start_date_timestamp, weekly_wallet, this_week_quantity, coins_only_last, coins_only_week, this_week_price,this_week_coin_data, symbol, weekly_active_coins_dict, this_week_portfolio_split):
    for wacd_item in weekly_active_coins_dict[this_week]["intraweek_coins"]:
        if wacd_item[0] == symbol:
            this_week_price = float(wacd_item[1])
            this_week_quantity = this_week_portfolio_split / this_week_price
    data = [symbol, this_week_quantity, this_week_price, this_week_portfolio_split]
    print("data line 422:", data)
    if data == []:
        print("423 line - error")
    else:
        this_week_coin_data.append(data)
    return this_week_coin_data
def symbol_only_last_week(data, this_week, last_week, start_date_timestamp, weekly_wallet, this_week_quantity, coins_only_last, coins_only_week, this_week_price,this_week_coin_data, symbol, weekly_active_coins_dict, this_week_portfolio_split):
    # print(symbol, "coin now inactive, sell all coins")
    for wacd_item in weekly_active_coins_dict[this_week]["intraweek_coins"]:
        if wacd_item[0] == symbol:
            this_week_price = float(wacd_item[1])
            this_week_quantity = 0
    data = [symbol, this_week_quantity, this_week_price, this_week_portfolio_split]
    print("data line 435:", data)
    if data == []:
        print("435 line - error")
    else:
        this_week_coin_data.append(data)
    return this_week_coin_data
def symbol_in_neither(data, this_week, last_week, start_date_timestamp, weekly_wallet, this_week_quantity, coins_only_last, coins_only_week, this_week_price,this_week_coin_data, symbol, weekly_active_coins_dict, this_week_portfolio_split):
    # print(symbol, "do nothing")
    for wacd_item in weekly_active_coins_dict[this_week]["intraweek_coins"]:
        if wacd_item[0] == symbol:
            this_week_price = float(wacd_item[1])
            this_week_quantity = 0
    data = [symbol, this_week_quantity, this_week_price, this_week_portfolio_split]
    print("data line 448:", data)
    if data == "":
        print("447 line - error")
    else:
        this_week_coin_data.append(data)

    return this_week_coin_data

"""weekly wallet takes a week input and generates the balanced weekly wallet from that - it will need to utilise the week 1 wallet data!!!!!!"""
def weekly_wallet_data(weekly_wallet, start_date_timestamp, week_timestamp, total_portfolio_value, weekly_active_coins_list, weekly_active_coins_dict, symbol_list):
    week_as_date = datetime.fromtimestamp(int(week_timestamp))
    wallet_data_list = []
    # last_week_data = {}
    weekly_milliseconds = 604800
    last_week = str(int(week_timestamp) - weekly_milliseconds)
    this_week = str(week_timestamp)
    last_week_value = 0
    this_week_value = 0
    last_week_quantity = 0
    this_week_quantity = 0
    # last_week_price = 0
    this_week_price = 0
    # last_week_cash_avail = 0
    last_week_portfolio_split = 0
    # this_week_portfolio_split = 0
    price_data = []
    this_week_portfolio_value = 0
    buy_list = []
    sell_list = []
    coins_only_last = []
    coins_only_week = []
    this_week_coin_data = []
    this_week_wallet = []
    this_week_cash_avail = 0
    wallet_data_dict = {}


    #current portfolio value is based on last weeks trading decions and what current prices are
    #for each item in last weeks wallet
    # 'calculating the portfolio split'
    # for item in weekly_wallet:
    #     if item == last_week:
    #         print("line347",weekly_wallet)
    #         last_week_portfolio_split_data = str(weekly_wallet[1][1]).split(", ")
    #         last_week_portfolio_split_string = last_week_portfolio_split_data[3]
    #         last_week_portfolio_split = last_week_portfolio_split_string[:-1]
    #         print('last_week_portfolio_split', last_week_portfolio_split)

    'Calculating both last weeks and this weeks price for each coin'
    for coin_data in weekly_wallet[1]:
        last_week_price_data = str(coin_data).split(", ")
        last_week_price = last_week_price_data[2]
        last_week_quantity = last_week_price_data[1]
        price_data.append(last_week_price)
        for line in weekly_active_coins_list:
            for coins in line[1]:
                if line[0] == this_week:
                    if coins[0] == coin_data[0]:
                        this_week_price_data = str(coins).split(", ")
                        this_week_price = str(this_week_price_data[1])[1:(len(str(this_week_price_data[1]))-2)]
                        this_week_value = float(this_week_price) * float(last_week_quantity)
                        this_week_portfolio_value += this_week_value

    #print('current_portfolio_value', this_week_portfolio_value)
    this_week_portfolio_split = this_week_portfolio_value / len(symbol_list)
    #print('this_week_portfolio_split', this_week_portfolio_split)

    #establish if any coins must be bought/
    for week in weekly_active_coins_list:
        #make sure is if not the first week - otherwise it will failt o pull in last weeks data
        if int(week[0]) == int(week_timestamp) and int(week[0]) != int(start_date_timestamp):
            print(week[0], week_timestamp, start_date_timestamp)
            print("match")
            this_week_coin_data = []
            for symbol in symbol_list:
                coins_only_last = []
                coins_only_week = []
                for coin_last in weekly_active_coins_dict[last_week]["intraweek_coins"]:
                    coin_only = coin_last[0]
                    coins_only_last.append(coin_only)
                for coin_week in weekly_active_coins_dict[this_week]["intraweek_coins"]:
                    coin_only = coin_week[0]
                    coins_only_week.append(coin_only)

                "active symbol has coins in wallet. rebalancing required"
                if symbol in coins_only_last and symbol in coins_only_week:
                    this_week_coin_data = symbol_in_both(this_week, last_week, start_date_timestamp, weekly_wallet, this_week_quantity, coins_only_last, coins_only_week, this_week_price,this_week_coin_data, symbol, weekly_active_coins_dict, this_week_portfolio_split)

                elif symbol not in coins_only_last and symbol in coins_only_week:
                    this_week_coin_data = symbol_only_this_week(this_week, last_week, start_date_timestamp, weekly_wallet, this_week_quantity, coins_only_last, coins_only_week, this_week_price,this_week_coin_data, symbol, weekly_active_coins_dict, this_week_portfolio_split)

                elif symbol in coins_only_last and symbol not in coins_only_week:
                    this_week_coin_data = symbol_only_last_week(this_week, last_week, start_date_timestamp, weekly_wallet,
                                          this_week_quantity, coins_only_last, coins_only_week, this_week_price,
                                          this_week_coin_data, symbol, weekly_active_coins_dict,
                                          this_week_portfolio_split)

                elif symbol not in coins_only_week and symbol not in coins_only_week:
                    this_week_coin_data = symbol_in_neither(this_week, last_week, start_date_timestamp, weekly_wallet,
                                      this_week_quantity, coins_only_last, coins_only_week, this_week_price,
                                      this_week_coin_data, symbol, weekly_active_coins_dict, this_week_portfolio_split)
                else:
                    print("Line 451 - Error occured buuilding weekly wallet data")

                # print("this week data:", this_week_coin_data)
                # print("last week data:", weekly_wallet)
                this_week_cash_avail = (len(symbol_list) - len(weekly_active_coins_dict[this_week]["intraweek_coins"])) * this_week_portfolio_split

                wallet_data_list = [week_timestamp, this_week_coin_data, this_week_cash_avail, this_week_portfolio_value]
                wallet_data_dict = {
                    'wallet': this_week_coin_data,
                    'cash_avail': this_week_cash_avail,
                    'portfolio_value' : this_week_portfolio_value
                }
    print("467 - weekly wallet", wallet_data_list)
    return wallet_data_list, wallet_data_dict


"""From the unbalanced wallet, generate a new weekly rebalancing."""
def rebalanced_portfolio(start_date_timestamp, weekly_active_coins_dict, weekly_active_coins_list, total_portfolio_value, symbol_list):
    weekly_portfolio_dict = {}
    buy_hold_data = []
    wallet_data_dict = {}

    # with open("weekly_wallet_rebalanced.json", "r", encoding='utf-8') as rebalanced:
    #     rebalanced_dict = json.load(rebalanced)
    with open("list_of_weeks.csv", "r") as wl_csv:
        weekly_list_csv = csv.reader(wl_csv)
        for list in weekly_list_csv:
            for week in list:
                if int(week) == int(start_date_timestamp):
                    weekly_wallet, wallet_data_dict[week] = week1_wallet_data(start_date_timestamp, week, total_portfolio_value, weekly_active_coins_list, weekly_active_coins_dict, symbol_list)

                    with open("weekly_wallet_data_dict.json", "w", encoding='utf-8') as weekly_data:
                        json.dump(wallet_data_dict, weekly_data)
                elif int(week) >= int(start_date_timestamp):
                    wallet_data_list, wallet_data_dict[week] = weekly_wallet_data(weekly_wallet, start_date_timestamp, week, total_portfolio_value, weekly_active_coins_list, weekly_active_coins_dict, symbol_list)
                    weekly_wallet = wallet_data_list
                    with open("weekly_wallet_data_dict.json", "a", encoding='utf-8') as weekly_data:
                        json.dump(wallet_data_dict, weekly_data)
                elif int(week) <= int(start_date_timestamp):
                    pass
    print("line 477:", wallet_data_dict)
    return wallet_data_dict

def rebalanced_data_to_csv(wallet_data_dict):
    weekly_list_data = []
    weekly_milliseconds = 604800
    rebalanced_dict_as_list = []

    #with open("weekly_wallet_rebalanced.json", "r", encoding='utf-8') as rebalanced:
    try:
        with open("weekly_wallet_data_dict.json", "r", encoding='utf-8') as rebalanced:
            rebalanced_dict = json.load(rebalanced)
            with open("list_of_weeks.csv", "r") as wl_csv:
                weekly_list_csv = csv.reader(wl_csv)
                for list in weekly_list_csv:
                    for week in list:
                        week = str(week)
                        try:
                            weekly_list_data = datetime.fromtimestamp(int(week)), rebalanced_dict[week]["wallet"], rebalanced_dict[week]["wallet_value"], rebalanced_dict[week]["cash_avail"]
                            rebalanced_dict_as_list.append(weekly_list_data)
                        except:
                            print(f"error on week: {week}")
    except:
        pass

    with open("rebalanced_data2.csv", "w", newline="") as rebalanced_csv:
        csv_writer = csv.writer(rebalanced_csv)
        for item in wallet_data_dict:
            line = wallet_data_dict[item]
            data = item, line
            csv_writer.writerow(data)


    # print(rebalanced_dict_as_list)
    # with open("rebalanced_data2.csv", "w", newline = "") as rebalanced_csv:
    #     csv_writer = csv.writer(rebalanced_csv)
    #     for item in rebalanced_dict_as_list:
    #         csv_writer.writerow(item)


"_____________________________________________________________________________________________"
"""From the unbalanced wallet, generate a new weekly rebalancing."""
def rebalanced_portfolioOLD(weekly_active_coins_list, total_portfolio_value):
    week_wallet_dict = {}
    weekly_rebalanced_portfolio_data = {}
    weekly_portfolio_dict = {}
    # with open("weekly_wallet_rebalanced.json", "r", encoding='utf-8') as rebalanced:
    #     rebalanced_dict = json.load(rebalanced)
    with open("list_of_weeks.csv", "r") as wl_csv:
        weekly_list_csv = csv.reader(wl_csv)
        for list in weekly_list_csv:
            for week in list:
                #find the starting week. from here, the
                if int(week) == int(start_date_timestamp):
                    weekly_portfolio_dict = weekly_wallet_data(start_date_timestamp, week, total_portfolio_value, weekly_active_coins_list)
                    print(week,weekly_portfolio_dict)
                    week_wallet_dict[week] = weekly_portfolio_dict
                with open("Buy_Hold_week1.json", "w", encoding='utf-8') as first_week:
                    json.dump(week_wallet_dict, first_week)
            for week in list:
                rebalanced_weekly_dict = weekly_rebalancing(week_wallet_dict, symbol_list, week)
                weekly_rebalanced_portfolio_data[week] = rebalanced_weekly_dict
            with open("weekly_wallet_rebalanced.json", "w", encoding='utf-8') as rebalanced:
                json.dump(weekly_rebalanced_portfolio_data, rebalanced)
def weekly_wallet_dataOLD(start_date_timestamp, week_timestamp, total_portfolio_value, weekly_active_coins_list):
    week_as_date = datetime.fromtimestamp(int(week_timestamp))
    wallet_coin_list = []
    wallet = []
    wallet_value = 0
    cash_avail = 0
    allocation_value = 0
    match_count = 0
    quantity = 0
    weekly_portfolio_dict = {}
    all_weekly_portfolio_data = []

    # """The first loop is to calculate how many active coins there are in a given week and establish the reblance value for that week"""
    with open("weekly_signals.csv", "r") as weekly_signals:
        weekly_signals_reader = csv.reader(weekly_signals)

        # 1 Create wallet for active coins
        for each_week in weekly_signals_reader:
            # print(int(each_week[0]), week_timestamp, each_week[4] , "ACTIVE")
            if int(each_week[0]) == int(week_timestamp) and each_week[4] == "ACTIVE":
                match_count += 1
                wallet_coin_list.append(each_week[2])

        # 2 identify number of active coins
        active_coins = len(wallet_coin_list)
        # print("active_coins:", active_coins)

        # 3 identify rebalance value
        if active_coins > 0:
            allocation_value = total_portfolio_value / active_coins
            print('allocation_value', allocation_value)
        elif active_coins == 0:
            #print(f"Apparent bear market for week {week_as_date}")
            cash_avail = total_portfolio_value
        else:
            print("get_weekly_wallet_data - line 92: error")

        # 4 create a wallet to show coin and quantity

        with open("weekly_signals.csv", "r") as weekly_signals:
            weekly_signals_reader = csv.reader(weekly_signals)
            each_week_count = 0
            count = 0
            for each_week in weekly_signals_reader:
                while count < 1:
                    print(each_week)
                    count += 1
                for coin in wallet_coin_list:
                    # For first week, buy
                    if int(each_week[0]) == int(week_timestamp) and each_week[2] == coin and each_week[4] == "ACTIVE":
                        quantity = float(allocation_value) / float(each_week[3])
                        value = quantity * float(each_week[3])
                        data = [coin, quantity, float(each_week[3])]
                        wallet.append(data)
                    elif int(each_week[0]) == int(week_timestamp) and each_week[2] == coin and each_week[4] == "INACTIVE":
                        data = [coin, quantity, float(each_week[3])]
                        wallet.append(data)

            for coin in wallet:
                wallet_value += float(coin[2]) * coin[1]

            # print(wallet_value)
            cash_avail = total_portfolio_value - (active_coins * allocation_value)
            weekly_portfolio_dict = {
                'wallet': wallet,
                'wallet_value': wallet_value,
                'cash_avail': cash_avail,
            }

    #print(f"{week_as_date} Data Generated..")
    #print(weekly_portfolio_dict)

    return weekly_portfolio_dict

"""From the unbalanced wallet, generate a new weekly rebalancing."""
def weekly_rebalancing(weekly_portfolio_dict, symbol_list, week_timestamp):
    portfolio_num = len(symbol_list)
    # Get last weeks data to compare against:
    weekly_milliseconds = 604800
    # last_week_timestep = int(week_timestamp)-weekly_milliseconds
    last_weekly_portfolio_data = []
    last_week_timestamp = 0
    last_week_wallet = ""
    last_week_wallet_value = ""
    last_week_cash_avail = ""
    last_weekly_portfolio_data = []
    rebalanced_weekly_dict = {}
    rebalanced_wallet = []
    all_weekly_portfolio_data = {}
    week1_portfolio_data = {}
    coins_held = 0
    coins_curr = 0
    portfolio_split= 0
    wallet_value = 0
    cash_avail = 0
    #Start with the weekly data for the first week, then move onwards from there.

    # check if the file exists. if file exsist, look at previous wallet date to establish what rebalcning is required.
    file_exists = os.path.exists("Buy_Hold_week1.json")
    if file_exists:
        with open("Buy_Hold_week1.json", "r") as ww_json:
            week1_portfolio_data = json.load(ww_json)
            current_week = f"{week_timestamp}"
            last_week = int(week_timestamp) - weekly_milliseconds
            current_portfolio_value = 0
            current_week_wallet = all_weekly_portfolio_data[f"{current_week}"]["wallet"]
            try:
                last_week_wallet = all_weekly_portfolio_data[f"{last_week}"]["wallet"]

                #calculating the portfolio split value
                #This need to be tested with data where there are not 6 active coins to be sure that it can calculate the split effectivly
                for symbol in symbol_list:
                    for coins_prev in last_week_wallet:
                        for coins_curr in current_week_wallet:                                # print('coins_prev', coins_prev)
                                # print('coins_curr', coins_curr)
                            if symbol == coins_curr[0] and symbol == coins_prev[0]:
                                # print(f"____________",symbol,coins_curr[2],{week_timestamp}, "____________")
                                # print(coins_prev)
                                # print(coins_curr)
                                last_week_value = coins_prev[1] * coins_prev[2]
                                current_week_value = coins_prev[1] * coins_curr[2]
                                current_portfolio_value += current_week_value
                                # print(symbol, current_week_value)
                # print('current_portfolio_value', current_portfolio_value)
                portfolio_split = current_portfolio_value/(len(symbol_list))
                # print('portfolio_split', portfolio_split, "\n\n\n")

                #identifying total split of portfolio to each coin
                #there should be a cross reference to active coins.
                # print(f"\t\t ____Rebalancing wallet: {week_timestamp}____\n")

                for symbol in symbol_list:
                    for coins_prev in last_week_wallet:
                        for coins_curr in current_week_wallet:
                            if symbol == coins_curr[0] and symbol == coins_prev[0]:
                                #making sure the coin is active on the weekly list.
                                with open("weekly_signals.csv", "r") as csv_file:
                                    csv_reader = csv.reader(csv_file)
                                    for line in csv_reader:
                                        count = 0
                                        if line[0] == week_timestamp and line[4] == "ACTIVE" and line[2] == symbol:
                                            # print(f"\nActive:",symbol,coins_curr[2],{week_timestamp})
                                            last_week_value = coins_prev[1] * coins_prev[2]
                                            current_week_value = coins_prev[1] * coins_curr[2]
                                            if portfolio_split < current_week_value:
                                                sell_usd_quant = portfolio_split - current_week_value
                                                sell_asset_quant = sell_usd_quant/coins_curr[2]


                                                #creating a new variables for rebalanced wallet named coins_held
                                                while count < len(symbol_list):
                                                    if all_weekly_portfolio_data[f"{current_week}"]["wallet"][count][0] == symbol:
                                                        # print('portfolio_split', portfolio_split)
                                                        # print('current_week_value', current_week_value)
                                                        # print('coins_curr[2]', coins_curr[2])
                                                        # print('sell_asset_quant', sell_asset_quant)
                                                        # print('sell_usd_quant', sell_usd_quant)
                                                        # print("calcuating coins held:", symbol, coins_prev[1] , sell_asset_quant)
                                                        coins_held = (coins_prev[1] + sell_asset_quant)
                                                    count += 1

                                            elif portfolio_split >= current_week_value:
                                                buy_usd_quant = portfolio_split - current_week_value
                                                buy_asset_quant = buy_usd_quant/coins_curr[1]

                                                #creating a new variables for rebalanced wallet named coins_held
                                                while count < len(symbol_list):

                                                    if all_weekly_portfolio_data[f"{current_week}"]["wallet"][count][0] == symbol:
                                                        # print('portfolio_split', portfolio_split)
                                                        # print('current_week_value', current_week_value)
                                                        # print('coins_curr[2]', coins_curr[2])
                                                        # print('buy_asset_quant', sell_asset_quant)
                                                        # print('buy_usd_quant', sell_usd_quant)
                                                        # print("calcuating coins held:", symbol, coins_prev[1] , buy_asset_quant)
                                                        coins_held = (coins_prev[1] + buy_asset_quant)
                                                    count += 1

                                            elif portfolio_split == current_week_value:
                                                print("Identical situation.. strange!")

                                            current_portfolio_value += current_week_value
                                            wallet = [symbol, coins_held, coins_curr[2]]
                                            # print('Rebalanced wallet:', wallet)
                                            rebalanced_wallet.append(wallet)

                                        elif line[0] == week_timestamp and line[4] == "INACTIVE" and line[2] == symbol:
                                            # print(f"\nInactive:", symbol, coins_curr[2], {week_timestamp})
                                            last_week_value = coins_prev[1] * coins_prev[2]
                                            current_week_value = coins_prev[1] * coins_curr[2]
                                            cash_avail += current_week_value
                                            current_portfolio_value += current_week_value
                                            wallet = [symbol, 0, coins_curr[2]]
                                            # print('Rebalanced wallet:', wallet)
                                            rebalanced_wallet.append(wallet)


            except:
                if int(start_date_timestamp) != int(week_timestamp):

                    print(f"weekly_rebalancing error line 489 - {week_timestamp}")
                    print(f"weekly_rebalancing error line 489 - {int(start_date_timestamp)} == {int(week_timestamp)}")

        # print(f'\n\nrebalanced_weekly_data {current_week}', rebalanced_weekly_dict)
        # print(f'rebalanced_wallet {current_week}', rebalanced_wallet)

        for item in rebalanced_wallet:
            holding = float(item[1]) * float(item[2])
            wallet_value += holding
        # print(wallet_value)

        total_portfolio_value = portfolio_split*len(symbol_list)
        cash_avail = wallet_value - total_portfolio_value
        # print(cash_avail)

    else:
        print("first line of data, initial buy")
    #rebalanced_data = week_timestamp, wallet, wallet_value, cash_avail

    rebalanced_weekly_dict = {
        'wallet': rebalanced_wallet,
        'wallet_value': wallet_value,
        'cash_avail': cash_avail
    }
    return rebalanced_weekly_dict


# def weekly_rebalancing(weekly_portfolio_dict, symbol_list, week_timestamp):
#     portfolio_num = len(symbol_list)
#     # Get last weeks data to compare against:
#     weekly_milliseconds = 604800
#     # last_week_timestep = int(week_timestamp)-weekly_milliseconds
#     last_weekly_portfolio_data = []
#     last_week_timestamp = 0
#     last_week_wallet = ""
#     last_week_wallet_value = ""
#     last_week_cash_avail = ""
#     last_weekly_portfolio_data = []
#     rebalanced_weekly_dict = {}
#     rebalanced_wallet = []
#     all_weekly_portfolio_data = {}
#     week1_portfolio_data = {}
#     coins_held = 0
#     coins_curr = 0
#     portfolio_split= 0
#     wallet_value = 0
#     cash_avail = 0
#     #Start with the weekly data for the first week, then move onwards from there.
#
#     # check if the file exists. if file exsist, look at previous wallet date to establish what rebalcning is required.
#     file_exists = os.path.exists("Buy_Hold_week1.json")
#     if file_exists:
#         with open("Buy_Hold_week1.json", "r") as ww_json:
#             week1_portfolio_data = json.load(ww_json)
#             current_week = f"{week_timestamp}"
#             last_week = int(week_timestamp) - weekly_milliseconds
#             current_portfolio_value = 0
#             current_week_wallet = all_weekly_portfolio_data[f"{current_week}"]["wallet"]
#             try:
#                 last_week_wallet = all_weekly_portfolio_data[f"{last_week}"]["wallet"]
#
#                 #calculating the portfolio split value
#                 #This need to be tested with data where there are not 6 active coins to be sure that it can calculate the split effectivly
#                 for symbol in symbol_list:
#                     for coins_prev in last_week_wallet:
#                         for coins_curr in current_week_wallet:                                # print('coins_prev', coins_prev)
#                                 # print('coins_curr', coins_curr)
#                             if symbol == coins_curr[0] and symbol == coins_prev[0]:
#                                 # print(f"____________",symbol,coins_curr[2],{week_timestamp}, "____________")
#                                 # print(coins_prev)
#                                 # print(coins_curr)
#                                 last_week_value = coins_prev[1] * coins_prev[2]
#                                 current_week_value = coins_prev[1] * coins_curr[2]
#                                 current_portfolio_value += current_week_value
#                                 # print(symbol, current_week_value)
#                 # print('current_portfolio_value', current_portfolio_value)
#                 portfolio_split = current_portfolio_value/(len(symbol_list))
#                 # print('portfolio_split', portfolio_split, "\n\n\n")
#
#                 #identifying total split of portfolio to each coin
#                 #there should be a cross reference to active coins.
#                 # print(f"\t\t ____Rebalancing wallet: {week_timestamp}____\n")
#
#                 for symbol in symbol_list:
#                     for coins_prev in last_week_wallet:
#                         for coins_curr in current_week_wallet:
#                             if symbol == coins_curr[0] and symbol == coins_prev[0]:
#                                 #making sure the coin is active on the weekly list.
#                                 with open("weekly_signals.csv", "r") as csv_file:
#                                     csv_reader = csv.reader(csv_file)
#                                     for line in csv_reader:
#                                         count = 0
#                                         if line[0] == week_timestamp and line[4] == "ACTIVE" and line[2] == symbol:
#                                             # print(f"\nActive:",symbol,coins_curr[2],{week_timestamp})
#                                             last_week_value = coins_prev[1] * coins_prev[2]
#                                             current_week_value = coins_prev[1] * coins_curr[2]
#                                             if portfolio_split < current_week_value:
#                                                 sell_usd_quant = portfolio_split - current_week_value
#                                                 sell_asset_quant = sell_usd_quant/coins_curr[2]
#
#
#                                                 #creating a new variables for rebalanced wallet named coins_held
#                                                 while count < len(symbol_list):
#                                                     if all_weekly_portfolio_data[f"{current_week}"]["wallet"][count][0] == symbol:
#                                                         # print('portfolio_split', portfolio_split)
#                                                         # print('current_week_value', current_week_value)
#                                                         # print('coins_curr[2]', coins_curr[2])
#                                                         # print('sell_asset_quant', sell_asset_quant)
#                                                         # print('sell_usd_quant', sell_usd_quant)
#                                                         # print("calcuating coins held:", symbol, coins_prev[1] , sell_asset_quant)
#                                                         coins_held = (coins_prev[1] + sell_asset_quant)
#                                                     count += 1
#
#                                             elif portfolio_split >= current_week_value:
#                                                 buy_usd_quant = portfolio_split - current_week_value
#                                                 buy_asset_quant = buy_usd_quant/coins_curr[1]
#
#                                                 #creating a new variables for rebalanced wallet named coins_held
#                                                 while count < len(symbol_list):
#
#                                                     if all_weekly_portfolio_data[f"{current_week}"]["wallet"][count][0] == symbol:
#                                                         # print('portfolio_split', portfolio_split)
#                                                         # print('current_week_value', current_week_value)
#                                                         # print('coins_curr[2]', coins_curr[2])
#                                                         # print('buy_asset_quant', sell_asset_quant)
#                                                         # print('buy_usd_quant', sell_usd_quant)
#                                                         # print("calcuating coins held:", symbol, coins_prev[1] , buy_asset_quant)
#                                                         coins_held = (coins_prev[1] + buy_asset_quant)
#                                                     count += 1
#
#                                             elif portfolio_split == current_week_value:
#                                                 print("Identical situation.. strange!")
#
#                                             current_portfolio_value += current_week_value
#                                             wallet = [symbol, coins_held, coins_curr[2]]
#                                             # print('Rebalanced wallet:', wallet)
#                                             rebalanced_wallet.append(wallet)
#
#                                         elif line[0] == week_timestamp and line[4] == "INACTIVE" and line[2] == symbol:
#                                             # print(f"\nInactive:", symbol, coins_curr[2], {week_timestamp})
#                                             last_week_value = coins_prev[1] * coins_prev[2]
#                                             current_week_value = coins_prev[1] * coins_curr[2]
#                                             cash_avail += current_week_value
#                                             current_portfolio_value += current_week_value
#                                             wallet = [symbol, 0, coins_curr[2]]
#                                             # print('Rebalanced wallet:', wallet)
#                                             rebalanced_wallet.append(wallet)
#
#
#             except:
#                 if int(start_date_timestamp) != int(week_timestamp):
#
#                     print(f"weekly_rebalancing error line 489 - {week_timestamp}")
#                     print(f"weekly_rebalancing error line 489 - {int(start_date_timestamp)} == {int(week_timestamp)}")
#
#         # print(f'\n\nrebalanced_weekly_data {current_week}', rebalanced_weekly_dict)
#         # print(f'rebalanced_wallet {current_week}', rebalanced_wallet)
#
#         for item in rebalanced_wallet:
#             holding = float(item[1]) * float(item[2])
#             wallet_value += holding
#         # print(wallet_value)
#
#         total_portfolio_value = portfolio_split*len(symbol_list)
#         cash_avail = wallet_value - total_portfolio_value
#         # print(cash_avail)
#
#     else:
#         print("first line of data, initial buy")
#     #rebalanced_data = week_timestamp, wallet, wallet_value, cash_avail
#
#     rebalanced_weekly_dict = {
#         'wallet': rebalanced_wallet,
#         'wallet_value': wallet_value,
#         'cash_avail': cash_avail
#     }
#     return rebalanced_weekly_dict
# _____________________________________________________________________________________________
#     def ():
#     #look for the next weeks data, when we have to weeks data we can then compare the results
#     with open("list_of_weeks.csv", "r") as list_of_weeks:
#         list_of_weeks_reader = csv.reader(list_of_weeks)
#         count = 0
#         for weekly_timestamp in list_of_weeks_reader:
#             while count < len(weekly_timestamp):
#                 #Creating the first condition - buy if active
#                 if count == 0 and weekly_timestamp[count] == backtest_start_data[0][0]:
#                     print("wallet.append data:", datetime.fromtimestamp(int(weekly_timestamp[count])))
#                     wallet.append([datetime.fromtimestamp(int(weekly_timestamp[count]))])
#                     for i in backtest_start_data:
#                         for item in backtest_start_data:
#                             if item[4] == "ACTIVE":
#                                 active_counter +=1
#                         portfolio_split = initial_capital/(len(symbol_list))
#                         if i[4] == "ACTIVE":
#                             coin_bought = [i[2], (portfolio_split/float(i[3]))]
#                             wallet_data = [coin_bought]
#                             wallet.append(wallet_data)
#                         elif i[4] == "INACTIVE":
#                             coin_bought = [i[2], "0.00"]
#                             wallet_data = [coin_bought]
#                             wallet.append(wallet_data)
#                         else:
#                             print('ERROR: in funcs, line 256')
#                         #print(coin_bought)
#                     with open(f"weekly_wallet.csv", "w", newline='') as wt_wallet_csv:
#                         wt_wallet_csv_writer = csv.writer(wt_wallet_csv)
#                         wt_wallet_csv_writer.writerow(wallet)
#
#                 else:
#                     for i in backtest_start_data:
#                         pass
#
#                 print(weekly_timestamp[count])
#                 print(backtest_start_data)
#
#                 count+=1