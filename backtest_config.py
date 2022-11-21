from datetime import datetime, timedelta, time
from calendar import timegm
import datetime

""" Setting backtest parameters"""
even_weighting = True #<< will the portfolio be evely weighted
slow_ma = 100
fast_ma = 50
initial_capital = 10000

start_date = '01/08/2022' # < MUST select a monday at the moment.
day, month, year = start_date.split('/')
start_date_timestamp = int(datetime.datetime(int(year), int(month), int(day)).timestamp())
#print(start_date_timestamp)

#print(datetime.date(replace(start_date,"/",",")))
#start_date_timestamp = int(datetime.datetime.strptime(start_date, "%d/%m/%Y").strftime("%s"))
#print(start_date_timestamp)

symbol_list_BTC_ONLY = ["BTCUSDT"]
symbol_list = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOTUSDT", "SANDUSDT", "ADAUSDT"]
