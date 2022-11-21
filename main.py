
from funcs import get_price_history, weekly_signals_into_csv, get_weekly_close_price, weekly_active_coins, week_startdate_list, weekly_signals_from_startdate, rebalanced_data_to_csv, weekly_wallet_data, rebalanced_portfolio, weekly_rebalancing
from backtest_config import symbol_list, initial_capital, even_weighting, symbol_list_BTC_ONLY, start_date_timestamp
from time import sleep
import json
import csv


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    """ STEP 1 - Download required coins"""
    print("\tStep 1 - Grabbing updates from binance\n")
    for symbol in symbol_list:
        get_price_history(symbol, "1h")


    """ Step 2 - Calculating weekly closes"""
    print("\n\tStep 2 - Calculating weekly closes \n")
    week_startdate_list(start_date_timestamp)
    for symbol in symbol_list:
        get_weekly_close_price(symbol, "1h")
        print(f"Got {symbol} weekly close prices stored")
    weekly_active_list = weekly_signals_from_startdate(symbol_list)


    """ Step 3 - Generating Rebalanced data and Creating CSV"""
    print("\n\tStep 3 - Generating Rebalanced data and Creating CSV")
    sleep(0.1)
    print("\nStarting Capital = $",initial_capital, "\nEven weighting:", even_weighting, "\nCoin selection:", symbol_list, "\nCapital distribution: $", int(initial_capital/len(symbol_list)), "max per coin.")
    weekly_active_coins_dict, weekly_active_coins_list = weekly_active_coins()
    print(weekly_active_coins_list)
    print("\n Weekly wallet generated.")
    total_portfolio_value = initial_capital
    wallet_data_dict = rebalanced_portfolio(start_date_timestamp, weekly_active_coins_dict, weekly_active_coins_list, total_portfolio_value, symbol_list)
    rebalanced_data_to_csv(wallet_data_dict)






    #trading_signal("BTCUSDT", 1598223600000)











