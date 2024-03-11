from datetime import date, timedelta
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import json
import os
import requests

load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_KEY") #This gets the API key from the .env file

app = Flask(__name__)

#Here we store the user database in a dictionary (currently all users are hardcoded into the db)
with open("user_database.json", 'r') as users:
    users_dict = json.load(users)

#Here we return the list of stocks a specific user has. If the user is not in the database the function will return "User not found."
def get_user_stocks_list(id): 
    try:
        return users_dict[id]
    except KeyError:
        print("User not found.")

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


@app.route("/api/portfolio")
def get_portfolio():
    user = "user1" #This is hardcoded for now, but it should be the user that is logged in with a proper login system
    portfolio = get_user_stocks_list(id =user)
    stocks_values = {} #Stores every stock in the portfolio and its most recent closing price as "TICKER" : "PRICE"
    for stock in portfolio:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={stock}&apikey={API_KEY}" #API call to get the stock's most recent closing price
        response = requests.get(url) #Sends the request to the API
        data = response.json() #Gets the response in JSON format
        closing_price = data["Time Series (Daily)"][get_last_weekday()]["4. close"] #Gets the most recent closing price
        stocks_values[stock] = closing_price #Adds the stock and its most recent closing price to the dictionary
    return jsonify(stocks_values)

@app.route("/api/portfolio/<stock>")
def get_price(stock):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={stock}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    series = data['Time Series (Daily)'] #Gets the stock's daily values (Open, Close, High, Low, Volume)
    start_date = get_next_weekday((date.today()-timedelta(days=30))) #Gets the date 30 days ago to show the stock's value for the last 30 days
    end_date = get_last_weekday(date.today()) #Gets the most recent weekday to the current date to show the stock's value up to that day
    filtered_data = {date: details for date, details in series.items() if start_date <= date <= end_date} #Percy wrote this, it filters the data to only show the stock's value for the specified time period
    past_prices = {} #Stores the stock's ticker and its daily values for the last 30 days
    past_prices["ticker"] = stock #Adds the stock's ticker to the dictionary
    past_prices["daily_values"] = filtered_data #Adds the stock's daily values to the dictionary
    return jsonify(past_prices)

if __name__ == "__main__":
    app.run(debug = True)