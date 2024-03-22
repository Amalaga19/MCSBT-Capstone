from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import flask
import json
import os
import requests
from flask_cors import CORS
from models import db, Users, Stocks  # Import db, Users, Stocks directly from models
from sqlalchemy.pool import NullPool
import oracledb
import argon2
import jwt
from functools import wraps

#User = User1
#Password = Password123

#Create User function will be brought back if time permits


app = Flask(__name__)
CORS(app, supports_credentials=True, origins='http://localhost:3000')
load_dotenv()
API_KEY = os.getenv("ALPHA_VANTAGE_KEY") #This gets the API key from the .env file
UN = "ADMIN"
PW = "Capstone.1234"
DSN = "(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.eu-madrid-1.oraclecloud.com))(connect_data=(service_name=g665fdafabbd3ee_capstonedb_high.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))"

pool = oracledb.create_pool(user=UN, password=PW,dsn=DSN)

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

def check_password(username, password): #This function checks if the password is correct for the given user
    try:
        user = Users.query.filter_by(USERNAME = username).first()
        if user is None:
            return jsonify({"error": "User not found."}), 404
        password_hash = user.PASSWORD
        if argon2.argon2_verify(password, password_hash):
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking password for user {username}: {e}")
        return jsonify({"error": "An error occured."}), 500

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

def get_latest_closing_price(stock):
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


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"message": "Token is missing!"}), 403
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            user = Users.query.filter_by(USERNAME = data["username"]).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(user, *args, **kwargs)
    return decorated

@app.route("/api/portfolio", methods = ["GET"]) #This route returns the complete portfolio of the user
@token_required
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
    for stock, quantity in stocks_list.items():
        latest_price = get_latest_closing_price(stock)
        if latest_price == float("NaN"):
            print(f"Could not fetch data for {stock}.")
            continue
        portfolio["stocks_owned"][stock] = {"quantity": quantity, "price": round(latest_price, 2), "price_total": round(latest_price * quantity, 2)}
    portfolio["total_value"] = total_portfolio_calc(stocks_list)
    return jsonify(portfolio)

@app.route("/api/portfolio/<stock_symbol>", methods = ["GET"])
def prices_history(stock_symbol):
    historical_data = {}
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if start_date is not None:
        start_date = get_next_weekday(datetime.strptime(start_date, "%Y-%m-%d").date()) #We get the start date for the API call and make sure it is a weekday
    else:
        start_date = get_next_weekday(datetime.today() - timedelta(days=30))
    if end_date is not None:
        end_date = get_last_weekday(datetime.strptime(end_date, "%Y-%m-%d").date()) #We get the end date for the API call and also make sure it is a weekday
    else:
        end_date = get_last_weekday(datetime.today())
    time_difference = datetime.strptime(end_date, "%Y-%m-%d").date() - datetime.strptime(start_date, "%Y-%m-%d").date()
    if time_difference.days > 180:
        data = call_api_monthly(stock_symbol)
        dates = list(data["Time Series (Monthly)"].keys())
    elif time_difference.days > 30:
        data = call_api_weekly(stock_symbol)
        dates = list(data["Time Series (Weekly)"].keys())
    else:
        data = call_api_daily(stock_symbol)
        dates = list(data["Time Series (Daily)"].keys())
    dates.sort()
    dates = dates[dates.index(start_date):(dates.index(end_date)+1)] #We get the dates between the start and end dates specified
    for date in dates:
        historical_data[date] = data["Time Series (Daily)"][date]["4. close"]
    return jsonify(historical_data)



@app.route("/update_user", methods = ["PUT"]) #This route is used to update the user's portfolio information
@token_required
def update_user():
    try:
        data = request.json
        action = data["action"]
        username = data["username"]
        stock = data["stock"]
        quantity = data["quantity"]
        if action == "add": #If the action is "add", we add the stock to the portfolio provided it is not already there
            if check_for_stock(username, stock):
                return jsonify({"message": "Stock {stock} already in portfolio."}), 200
            else:
                add_stock(username, stock, quantity)
                print("Adding {stock} to the portfolio, {quantity} shares will be added.")
                return jsonify({"message": "Stock {stock} added successfully."}), 200
        #If the actions are "remove" or "modify", we check if the stock is in the portfolio so it can be removed or modified
        elif action == "remove":
            if not check_for_stock(username, stock):
                return jsonify({"message": "Stock {stock} not in portfolio."}), 200
            else:
                remove_stock(username, stock)
                print("Removing {stock} from the portfolio.")
                return jsonify({"message": "Stock {stock} removed successfully."}), 200
        elif action == "modify":
            if not check_for_stock(username, stock):
                return jsonify({"message": "Stock {stock} not in portfolio."}), 200
            else:
                modify_stock_quantity(username, stock, quantity)
                if quantity > 0:
                    print("Updating {stock} in the portfolio to {quantity} shares.")
                    return jsonify({"message": "Stock {stock} updated successfully to {quantity} shares."}), 200
                else:
                    return jsonify({"message": "Stock {stock} removed successfully."}), 200
    except Exception as e:
        print(f"Error updating user: {e}")
        return jsonify({"message": "Error updating user."}), 400

@app.route('/login', methods = ['POST'])
def login(): #This route is used to check the user's credentials and return a token if they are correct
    data = request.json
    username = Users.query.filter_by(USERNAME = data["username"]).first()
    password = data["password"]
    if username is not None:
        if check_password(username, password):
            # Use username.USERNAME (or the correct attribute name) to get the actual username string
            token = jwt.encode(
                {"username": username.USERNAME, "iat": datetime.now(), "exp": datetime.now() + timedelta(minutes=120)},
                app.config["SECRET_KEY"], algorithm="HS256")
            return jsonify({"success": "true", "message": "Login successful.", "token": token}), 200
    else:
        return jsonify({"success": "false","message": "User not found or incorrect password."}), 404


if __name__ == "__main__":
    app.run(debug = True)