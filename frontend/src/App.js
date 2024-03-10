import React, { useState, useEffect } from 'react';
import './App.css';


function App() {
  const [portfolio, setPortfolio] = useState(null);
  const [error, setError] = useState("");
  const [total, setTotal] = useState(null);
  const [priceHistory, setPriceHistory] = useState(null);
  const [selectedTicker, setSelectedTicker] = useState(null);

  const user = "user1";
  const backendUrl = "http://localhost:5000/api";

  const handleTickerClick = async (ticker) => {
    const time = prompt("How far back do you want to see the price history? (Enter the number of days)");
    time = parseInt(time);
    if (time) {
      fetchTickerPriceHistory(ticker, time);
      setSelectedTicker(ticker);
    }

  };
  const fetchPortfolio = async () => {
    try {
      const response = await fetch(`${backendUrl}/${user}/portfolio`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const portfolio = await response.json();
      setPortfolio(portfolio);
    } catch(error) {
      console.error("Error fetching data: ", error);
      setError("Failed to load data.");
    }
  }
  
  const fetchPortfolioTotal = async () => {
    try {
      const response = await fetch(`${backendUrl}/${user}/portfolio/total`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const total = await response.json();
      setTotal(total);
    } catch(error) {
      console.error("Error fetching data: ", error);
      setError("Failed to load data.");
    }
  }
  const fetchTickerPriceHistory = async (ticker, time) => {
    try {
      const response = await fetch(`${backendUrl}/${user}/portfolio/${ticker}/${time}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const priceHistory = await response.json();
      setPriceHistory(priceHistory);
    } catch(error) {
      console.error("Error fetching data: ", error);
      setError("Failed to load data.");
    }
  };
  
  useEffect(() => {
    fetchPortfolio();
    fetchPortfolioTotal();
  }, [user]); 

  return (
    <div className="App">
      <h1>Your Portfolio</h1>
      {error && <p>{error}</p>}
      {total && <h2>Total Portfolio Value: ${total['Total Value of Portfolio: ']}</h2>}
      {portfolio && portfolio.stocks_owned && (
        <div>
          {Object.entries(portfolio.stocks_owned).map(([stock, details]) => (
            <p key={stock} onClick={() => handleTickerClick(stock)}>
              {stock}: {details.amount_owned} shares, Last Closing Price: ${details.latest_closing_price}
            </p>
          ))}
        </div>
      )}
      {!selectedTicker && <h2>Click on a ticker to see its price history</h2>}
      {selectedTicker && priceHistory && (
        <div>
          <h3>{selectedTicker}'s price history:</h3>
          {Object.entries(priceHistory).reverse().map(([date, price]) => (
            <p key={date}>{date}: ${price}</p>
          ))}
        </div>
      )}
      {!portfolio && <p>Loading...</p>}
    </div>
  );
}

export default App;