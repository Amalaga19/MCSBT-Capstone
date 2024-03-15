from datetime import date, timedelta
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import flask
import json
import os
import requests
from flask_cors import CORS
import models
from models import db, Users, Stocks  # Import db, Users, Stocks directly from models
from sqlalchemy.pool import NullPool
import oracledb

app = Flask(__name__)
CORS(app)
load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_KEY") #This gets the API key from the .env file

un = "ADMIN"
pw = "Capstone.1234" 
dsn = "(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.eu-madrid-1.oraclecloud.com))(connect_data=(service_name=g665fdafabbd3ee_capstonedb_high.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))"

pool = oracledb.create_pool(user=un, password=pw,dsn=dsn)

app.config['SQLALCHEMY_DATABASE_URI'] = 'oracle+oracledb://'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'creator': pool.acquire,
    'poolclass': NullPool
}
app.config['SQLALCHEMY_ECHO'] = True
db.init_app(app)

with app.app_context():
    db.create_all()


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

#Here we return the list of stocks owned by the user in the format {stock: quantity} (it's really a dictionary)
def get_user_stocks_list(username): 
    try:
        user = Users.query.filter_by(USERNAME = username).first()
        if user is None:
            return None
        else:
            return {stock.SYMBOL: stock.QUANTITY for stock in user.stocks}
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

def total_portfolio_calc(stocks): #This function calculates the total value of the portfolio
    total = 0
    for ticker, amount in stocks.items():
        data = call_api_daily(ticker)
        try:
            price = float(data["Time Series (Daily)"][get_last_weekday()]["4. close"])
            total += price * amount
        except KeyError:
            print(f"Could not fetch data for {ticker}.")
    return round(total, 2)

def make_portfolio(username): #This function builds the portfolio of a user
    try:
        user = Users.query.filter_by(USERNAME = username).first()
        if user is None:
            print(f"User {user} not found.")
            return jsonify({"error": "User not found."}), 404
        portfolio = { "username": username, "stocks_owned": {}, "total_value": 0 }
        stocks_list = get_user_stocks_list(username)
        portfolio["total_value"] = total_portfolio_calc(stocks_list)
        return portfolio
    except Exception as e:
        print(f"Error building portfolio for {username}: {e}")
        return jsonify({"error": "An error occured."}), 500


@app.route("/api/<user>/portfolio") #This route returns the complete portfolio of the user
def get_portfolio(user):
    portfolio = make_portfolio(user)
    return jsonify(portfolio)

@app.route("/api/<user>/portfolio/<stock>/<timeframe>") #This route returns the past prices of a stock in the user's portfolio for a given timeframe
def get_past_prices(user, stock, timeframe): #user is not used here, but it helps to keep the structure of the routes consistent
    data = call_api_daily(stock)
    timeframe = int(timeframe)
    if "Time Series (Daily)" in data:
        past_prices_data = custom_timeframe(data["Time Series (Daily)"], timeframe)
        past_prices = {}
        for date in past_prices_data:
            past_prices[date] = "{:.2f}".format(float(past_prices_data[date]["4. close"]))
        return jsonify(past_prices)
    else:
        return jsonify({"error": "Data not found for the given stock"}), 404


if __name__ == "__main__":
    app.run(debug = True)