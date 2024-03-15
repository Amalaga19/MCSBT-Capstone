from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.schema import Identity

db = SQLAlchemy()

class Users(db.Model):
    __tablename__ = 'USERS'
    USER_ID = db.Column(db.Integer, Identity(start = 1, cycle = False), primary_key=True)
    USERNAME = db.Column(db.String(100), unique = True, nullable=False)
    PASSWORD = db.Column(db.String(100), nullable=False)
    stocks = db.relationship("STOCKS", back_populates="user")
    
    def user_dict(self):
        return {"id": self.USER_ID, "username": self.USERNAME, "stocks": [stock.stock_dict() for stock in self.stocks]}

class Stocks(db.Model):
    __tablename__ = 'STOCKS'
    STOCK_ID = db.Column(db.Integer, Identity(start = 1, cycle = False), primary_key=True)
    USER_ID = db.Column(db.Integer, db.ForeignKey('USERS.USER_ID'), nullable=False)
    SYMBOL = db.Column(db.String(100), nullable=False)
    QUANTITY = db.Column(db.Integer, nullable=False)
    user = db.relationship("Users", back_populates="stocks")

    def stock_dict(self):
        return {"id": self.STOCK_ID, "symbol": self.SYMBOL, "quantity": self.QUANTITY}
    

