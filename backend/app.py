from datetime import date, timedelta
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import flask
import json
import os
import requests
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_KEY") #This gets the API key from the .env file


#Here we store the user database in a dictionary (currently all users are hardcoded into the db)
with open("user_database.json", 'r') as users:
    users_dict = json.load(users)

def call_api_daily(ticker): #This function calls the Alpha Vantage API to get the daily values of a stock
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={API_KEY}"
    response = requests.get(url) #We send a GET request to the API
    data = response.json() #The data is returned in JSON format
    return data

def get_last_weekday(today = None):
    #Stocks are not traded on weekends, so we need to get the last weekday date to use it in the API call (before the current date).
    #This means what we need to set the date to the last friday if today is monday or sunday, and to the previous day for the rest of the week.
    if today == None:
        today = date.today()
    if today.weekday()==0: #Monday
        delta = timedelta(days=3)
    elif today.weekday()==6: #Sunday
        delta = timedelta(days=2)
    else: #Rest of the week
        delta = timedelta(days=1)
    return (today-delta).strftime("%Y-%m-%d") #Returns the date in the format "YYYY-MM-DD"

def get_next_weekday(today = None):
    #If we want to find values for a time period in the past we need to get the first weekday after the furthest date in the past in case it is a weekend
    #This means we need to set the date to the next monday if today is saturday or sunday, and keep it on the same day for the rest of the week.
    if today == None:
        today = date.today()
    elif today.weekday()==6: #Sunday
        delta = timedelta(days=2)
    elif today.weekday()==5: #Saturday
        delta = timedelta(days=1)
    else: #Rest of the week
        delta = timedelta(days=0)
    return (today+delta).strftime("%Y-%m-%d") #Returns the date in the format "YYYY-MM-DD"

def custom_timeframe(price_history, time):
    try:
        dates = list(price_history.keys())
        dates.sort() #We get all the dates available from the earlies to the latest
        dates = dates[-time:] #We get the last "time" dates
        timeframe = {}
        for date in dates:
            timeframe[date] = price_history[date]
        return timeframe
    except Exception as e:
        print("Error:", e)
        return {}

#Here we return the list of stocks a specific user has. If the user is not in the database the function will return "User not found."
def get_user_stocks_list(id): 
    try:
        return users_dict[id]
    except KeyError:
        flask.abort(404)

def get_latest_closing_price(price_history):
    try:
        # Access the "Time Series (Daily)" directly and handle any potential absence of this key.
        time_series = price_history.get("Time Series (Daily)", {})
        if not time_series:
            print("No 'Time Series (Daily)' data found.")
            return float("NaN")

        # Extract the latest date available in the time series data.
        latest_date = max(time_series.keys())
        latest_data = time_series[latest_date]
        latest_price = latest_data.get("4. close")
        if latest_price is None:
            print("No '4. close' data found for the latest date.")
            return float("NaN")
        return float(latest_price)
    except Exception as e:
        print(f"Error fetching the latest closing price: {e}")
        return float("NaN")

def total_portfolio_calc(stocks):
    total = 0
    for ticker, amount in stocks.items():
        data = call_api_daily(ticker)
        try:
            price = float(data["Time Series (Daily)"][get_last_weekday()]["4. close"])
            total += price * amount
        except KeyError:
            print(f"Could not fetch data for {ticker}.")
    return round(total, 2)

def build_user_stocks_and_prices(user):
    stocks_list = get_user_stocks_list(user)
    tickers_and_prices = {}
    for ticker in stocks_list:
        try:
            closing_price = get_latest_closing_price(call_api_daily(ticker))
        except Exception as e:
            print("Error:", e)
            closing_price = float("NaN")
        tickers_and_prices[ticker] = closing_price
    return tickers_and_prices

def make_portfolio(user): #setting this up for later
    portfolio = {}
    portfolio["username"] = user
    stocks_list = get_user_stocks_list(user)
    if stocks_list is None:
        print(f"User {user} not found.")
        return jsonify({"error": "User not found."})
    portfolio["stocks_owned"] = {}
    for ticker, amount in stocks_list.items():
        portfolio["stocks_owned"][ticker] = {"amount_owned": amount}
        try:
            data = call_api_daily(ticker)
            closing_price = get_latest_closing_price(data)
            portfolio["stocks_owned"][ticker]["latest_closing_price"] = closing_price
        except Exception as e:
            print(f"Error fetching or processing data for {ticker}: {e}")
            portfolio["stocks_owned"][ticker]["latest_closing_price"] = float("NaN")
    portfolio["total_value"] = total_portfolio_calc(get_user_stocks_list(user))
    return portfolio



@app.route("/api/<user>/portfolio")
def get_portfolio(user):
    portfolio = make_portfolio(user)
    user_tickers_and_prices = build_user_stocks_and_prices(user)
    return jsonify(portfolio)

@app.route("/api/<user>/portfolio/total")
def get_total_portfolio(user):
    portfolio = make_portfolio(user)
    return jsonify({"Total Value of Portfolio: ": portfolio["total_value"],})



@app.route("/api/<user>/portfolio/<stock>/<timeframe>")
def get_past_prices(user, stock, timeframe):
    data = call_api_daily(stock)
    timeframe = int(timeframe)
    if "Time Series (Daily)" in data:
        past_prices_data = custom_timeframe(data["Time Series (Daily)"], timeframe)
        past_prices = {}
        for date in past_prices_data:
            past_prices[date] = past_prices_data[date]["4. close"]
        return jsonify(past_prices)
    else:
        return jsonify({"error": "Data not found for the given stock"}), 404


if __name__ == "__main__":
    app.run(debug = True)