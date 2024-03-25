from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
import flask
import json
import os
import requests
from flask_cors import CORS
from models import db, Users, Stocks  # Import db, Users, Stocks directly from models
from sqlalchemy.pool import NullPool
import oracledb
import argon2
from argon2 import PasswordHasher

#User = User1
#Password = Password123

#Create User function will be brought back if time permits


app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*" : {"origins" : "*"}}) #This is needed for the CORS to work with the frontend
load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_KEY") #This gets the API key from the .env file
UN = os.getenv("ORACLE_UN") #This gets the Oracle username from the .env file
PW = os.getenv("ORACLE_PW") #This gets the Oracle password from the .env file
DSN = os.getenv("ORACLE_DSN") #This gets the Oracle DSN from the .env file

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") #This gets the secret key from the .env file
app.config['SESSION_COOKIE_SAMESITE'] = "None" #This is needed for the session to work with CORS
app.config['SESSION_COOKIE_SECURE'] = True #This too


ph = PasswordHasher() #This is the password hasher object using the argon2 algorithm

pool = oracledb.create_pool(user=UN, password=PW,dsn=DSN) #This creates the connection pool to the Oracle database

#This is the configuration for the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'oracle+oracledb://'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'creator': pool.acquire,
    'poolclass': NullPool
}
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
db.init_app(app)

with app.app_context():
    db.create_all()

#This is a decorator function that adds the CORS headers to the response so the frontend can access the API
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

app.after_request(add_cors_headers)


def call_api_daily(ticker): #This function calls the Alpha Vantage API to get the daily values of a stock
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={API_KEY}"
    response = requests.get(url) #We send a GET request to the API
    data = response.json() #The data is returned in JSON format
    return data

def call_api_weekly(ticker): #This function calls the Alpha Vantage API to get the weekly values of a stock
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol={ticker}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    return data

def call_api_monthly(ticker): #This function calls the Alpha Vantage API to get the monthly values of a stock
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol={ticker}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
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

def check_if_stock_exists(stock): #This function checks if a stock exists in the API
    try:
        data = call_api_daily(stock)
        data = data["Time Series (Daily)"]
        if data:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking if {stock} exists: {e}")
        return False

def check_password(username, password): #This function checks if the password is correct for the user by hashing it and comparing it to the stored hash
    try:
        user = Users.query.filter_by(USERNAME=username).first()
        if user is None:
            return False
        password_hash = user.PASSWORD
        # Verify the password
        try:
            ph.verify(password_hash, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
    except Exception as e:
        print(f"Error checking password for user {username}: {e}")
        return False

def hash_password(password): #This function hashes the password
    return argon2.argon2_hash(password)


def add_stock(username, stock, quantity): #This function adds a stock to the user's portfolio
    try:
        user = Users.query.filter_by(USERNAME = username).first()
        if user is None:
            return jsonify({"error": "User not found."}), 404
        stock = Stocks(USER_ID = user.USER_ID, SYMBOL = stock, QUANTITY = quantity)
        db.session.add(stock)
        db.session.commit() #We commit the changes to the database
        return jsonify({"message": "Stock added successfully."}), 200
    except Exception as e:
        db.session.rollback() #We rollback the changes in case of an error
        print(f"Error adding stock to {username}'s portfolio: {e}")
        return jsonify({"error": "An error occured."}), 500

def remove_stock(username, stock): #This function removes a stock from the user's portfolio
    try:
        user = Users.query.filter_by(USERNAME = username).first()
        if user is None:
            return jsonify({"error": "User not found."}), 404
        stock = Stocks.query.filter_by(USER_ID = user.USER_ID, SYMBOL = stock).first()
        if stock is None:
            return jsonify({"error": "Stock not found."}), 404
        db.session.delete(stock)
        db.session.commit() #We commit the changes to the database
        return jsonify({"message": "Stock removed successfully."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error removing stock from {username}'s portfolio: {e}")
        return jsonify({"error": "An error occured."}), 500

def modify_stock_quantity(username, stock, new_quantity): #This function modifies the quantity of a stock in the user's portfolio
    try:
        user = Users.query.filter_by(USERNAME = username).first()
        if user is None:
            return jsonify({"error": "User not found."}), 404
        stock = Stocks.query.filter_by(USER_ID = user.USER_ID, SYMBOL = stock).first()
        if stock is None:
            return jsonify({"error": "Stock not found."}), 404
        stock.QUANTITY = new_quantity
        if stock.QUANTITY == 0:
            db.session.delete(stock) #If the quantity is 0, we remove the stock from the portfolio
        db.session.commit() #We commit the changes to the database
        return jsonify({"message": "Stock updated successfully."}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error modifying stock quantity in {username}'s portfolio: {e}")
        return jsonify({"error": "An error occured."}), 500

def check_for_stock(username, stock): #This function checks if a stock is in the user's portfolio, returns True if it is and False if it is not
    try:
        user = Users.query.filter_by(USERNAME = username).first()
        if user is None:
            return jsonify({"error": "User not found."}), 404      
        stock = Stocks.query.filter_by(USER_ID = user.USER_ID, SYMBOL = stock).first()
        if stock:
            return True
        else:
            return False 
    except Exception as e:
        print(f"Error checking for stock in {username}'s portfolio: {e}")
        return jsonify({"error": "An error occured."}), 500

def get_latest_closing_price(stock): #This function gets the latest closing price of a stock
    try:
        data = call_api_daily(stock)
        latest_date = max(data["Time Series (Daily)"].keys())
        latest_data = data["Time Series (Daily)"][latest_date]
        latest_price = latest_data["4. close"]
        return latest_price
    except Exception as e:
        print(f"Error fetching the latest closing price for {stock}: {e}")
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

@app.route("/api/portfolio/", methods = ["GET"]) #This route returns the complete portfolio of the user
def get_portfolio():
    user = request.args.get("username")
    portfolio = {}
    user = Users.query.filter_by(USERNAME = user).first()
    if user is None:
        print(f"User {user} not found.")
        return jsonify({"message": "User not found."}), 404
    portfolio["username"] = user.USERNAME
    portfolio["stocks_owned"] = {}
    portfolio["total_value"] = 0
    stocks_list = get_user_stocks_list(user.USERNAME)
    if len(stocks_list) > 0:
        for stock, quantity in stocks_list.items():
            latest_price = get_latest_closing_price(stock)
            if latest_price == float("NaN"):
                print(f"Could not fetch data for {stock}.")
                continue
            portfolio["stocks_owned"][stock] = {"quantity": quantity, "price": round(float(latest_price), 2), "price_total": round(float(latest_price) * quantity, 2)}
        portfolio["total_value"] = total_portfolio_calc(stocks_list)
    return jsonify(portfolio)

@app.route("/api/portfolio/<stock_symbol>", methods = ["GET"])
def prices_history(stock_symbol): #This route returns the historical prices of a stock
    historical_data = {}
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        start_date = get_next_weekday(start_date)
    else:
        start_date = get_next_weekday(datetime.today() - timedelta(days=30))
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        end_date = get_last_weekday(end_date)
    else:
        end_date = get_last_weekday(datetime.today())
    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    time_difference = end_date - start_date
    if time_difference.days > 180:
        data = call_api_monthly(stock_symbol)
        time_series_key = "Monthly Time Series"
    elif time_difference.days > 30:
        data = call_api_weekly(stock_symbol)
        time_series_key = "Weekly Time Series"
    elif time_difference.days > 0:
        data = call_api_daily(stock_symbol)
        time_series_key = "Time Series (Daily)"
    else:
        return jsonify({"message": "Invalid date range."}), 200
    dates = list(data[time_series_key].keys())
    dates.sort(key=lambda date: datetime.strptime(date, "%Y-%m-%d"))
    while str(start_date) not in dates and start_date <= end_date:
        start_date += timedelta(days=1)
    while str(end_date) not in dates and end_date >= start_date:
        end_date -= timedelta(days=1)
    dates = [date for date in dates if datetime.strptime(date, "%Y-%m-%d").date() >= start_date and datetime.strptime(date, "%Y-%m-%d").date() <= end_date]
    for date in dates:
        historical_data[date] = str(round(float(data[time_series_key][date]["4. close"]), 2))
    return jsonify(historical_data)



@app.route("/update_user", methods = ["PUT"]) #This route is used to update the user's portfolio information
def update_user():
    try:
        data = request.json
        action = data["action"]
        username = data["username"]
        stock = data["stock"]
        quantity = int(data["quantity"])
        if check_if_stock_exists(stock):
            if action == "add": #If the action is "add", we add the stock to the portfolio provided it is not already there
                if check_for_stock(username, stock):
                    return jsonify({"message": "Stock {stock} already in portfolio."}), 200
                else:
                    if quantity == 0:
                        return jsonify({"message": "Quantity must be greater than 0."}), 200
                    elif quantity < 0:
                        return jsonify({"message": "Quantity cannot be negative."}), 200
                    add_stock(username, stock, quantity)
                    print("Adding to the portfolio.")
                    return jsonify({"message": "Stock added successfully."}), 200
            #If the actions are "remove" or "modify", we check if the stock is in the portfolio so it can be removed or modified
            elif action == "modify":
                if not check_for_stock(username, stock):
                    return jsonify({"message": "Stock not in portfolio."}), 200
                else:
                    if quantity > 0:
                        modify_stock_quantity(username, stock, quantity)
                        print("Updating stock quantity in the portfolio.")
                        return jsonify({"message": "Stock quantity updated successfully."}), 200
                    elif quantity<0:
                        return jsonify({"message": "Stock quantity cannot be negative."}), 200
                    else:
                        action = "remove"
            elif action == "remove":
                if not check_for_stock(username, stock):
                    return jsonify({"message": "Stock not in portfolio."}), 200
                else:
                    remove_stock(username, stock)
                    print("Removing from the portfolio.")
                    return jsonify({"message": "Stock removed successfully."}), 200

        else:
            return jsonify({"message": "Stock does not exist."}), 200 #If the stock does not exist, we return a message saying so. 200 because it is not an error

    except Exception as e:
        print(f"Error updating user: {e}")
        return jsonify({"message": "Error updating user."}), 400

@app.route('/login', methods=['POST', 'OPTIONS'])
def login(): #This route is used to log in the user
    if request.method == 'OPTIONS':
        response = flask.make_response()
        return add_cors_headers(response)
    data = request.json
    user = data.get("username")
    username = Users.query.filter_by(USERNAME=user).first()
    password = data.get("password")
    if username and check_password(username.USERNAME, password):
        session.permanent = True
        session.modified = True
        session['username'] = username.USERNAME
        return jsonify({"username": session['username'], "message": "Logged in successfully."}), 200
    else:
        return jsonify({"success": "false", "message": "User not found or incorrect password."}), 404

@app.route('/logout', methods=['GET']) #This route is used to log out the user
def logout():
    session.clear()
    return jsonify({"message": "Logged out."}), 200


if __name__ == "__main__":
    app.run(debug = True)