import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [portfolio, setPortfolio] = useState(null);
  const [error, setError] = useState("");
  const [selectedTicker, setTicker] = useState(null);
  const [priceHistory, setPriceHistory] = useState(null);
  const [authToken, setAuthToken] = useState(localStorage.getItem('authToken') || null);
  const [stocksQuantity, setStocksQuantity] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loggedIn, setLoggedIn] = useState(authToken !== null);
  const [updateStock, setUpdateStock] = useState({ticker: "", quantity: 0});


  const backendUrl = "http://localhost:5000"; // Adjusted for accuracy


  const login = async () => {
    try {
      const response = await fetch(`${backendUrl}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      if (data.success === "false") {
        throw new Error(data.message);
      }
      const authToken = data.token;
      setAuthToken(authToken);
      localStorage.setItem('authToken', authToken);
      setLoggedIn(true);
    } catch (error) {
      console.error("Error logging in: ", error);
      setError("Failed to log in.");
    }
  };

  const logout = () => {
    setAuthToken(null);
    localStorage.removeItem('authToken');
    setLoggedIn(false);
  };

  const fetchPortfolio = async () => {
    if (!username) return;
    try {
      const response = await fetch(`${backendUrl}/api/portfolio?username=${username}`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const portfolio = await response.json();
      setPortfolio(portfolio);
    } catch (error) {
      console.error("Error fetching portfolio: ", error);
      setError("Failed to load portfolio.");
    }
  };

  const fetchTickerPriceHistory = async (ticker, startDate, endDate) => {
    try {
      const response = await fetch(`${backendUrl}/api/portfolio/${ticker}?start_date=${startDate}&end_date=${endDate}`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const priceHistory = await response.json();
      setPriceHistory(priceHistory);
    } catch (error) {
      console.error("Error fetching ticker price history: ", error);
      setError("Failed to load ticker price history.");
    }
  };

  const updateUserPortfolio = async (e, action, stock) => {
    e.preventDefault();
    if (stocksQuantity < 0) {
      console.error("Quantity cannot be negative.");
      setError("Quantity cannot be negative.");
      return;
    }
    try {
      const response = await axios.put(`${backendUrl}/update_user`, {
        username: username,
        action: action,
        stock: stock,
        quantity: parseInt(stocksQuantity),
      }, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        }
      });
  
      if (response.data) {
        alert(`Stocks updated successfully. You now own ${stocksQuantity} shares of ${stock}.`);
        fetchPortfolio();
      }
    } catch (error) {
      console.error("Error updating portfolio: ", error);
      setError("Failed to update the portfolio.");
    }
  };
  
  useEffect(() => {
    if (loggedIn) {
      fetchPortfolio();
    }
  }, [loggedIn, authToken, username]);
  
  useEffect(() => {
    if (selectedTicker) {
      fetchTickerPriceHistory(selectedTicker, null, null);
    }
  }, [selectedTicker, authToken]); 
  
  return (
    <div className="App">
      {!loggedIn ? (
        <div className="login-form">
          <h2>Login</h2>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button onClick={login}>Login</button>
          {error && <p className="error">{error}</p>}
        </div>
      ) : (
        <div>
          <button onClick={logout}>Logout</button>
          <div className="portfolio">
            <h2>Portfolio</h2>
            {portfolio ? (
              <>
                <p>Total Portfolio Value: ${portfolio.total_value}</p>
                <ul>
                  {Object.entries(portfolio.stocks_owned).map(([ticker, details]) => (
                    <li key={ticker} onClick={() => setTicker(ticker)}>
                      {ticker}: {details.quantity} shares at ${details.price} each, total ${details.price_total}
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p>Loading portfolio...</p>
            )}
          </div>
          {selectedTicker && (
            <div className="price-history">
              <h3>Price History for {selectedTicker}</h3>
              {priceHistory ? (
                <ul>
                  {Object.entries(priceHistory).map(([date, price]) => (
                    <li key={date}>{date}: ${price}</li>
                  ))}
                </ul>
              ) : (
                <p>Loading price history...</p>
              )}
            </div>
          )}
          <div className="update-portfolio">
            <h2>Update Portfolio</h2>
            <input
              type="text"
              placeholder="Ticker"
              value={updateStock.ticker}
              onChange={(e) => setUpdateStock({ ...updateStock, ticker: e.target.value })}
            />
            <input
              type="number"
              placeholder="Quantity"
              value={updateStock.quantity}
              onChange={(e) => setUpdateStock({ ...updateStock, quantity: e.target.value })}
            />
            <button onClick={(e) => updateUserPortfolio(e, 'modify', updateStock.ticker)}>Update</button>
          </div>
        </div>
      )}
    </div>
  );
}  
export default App;
