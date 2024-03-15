import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [portfolio, setPortfolio] = useState(null); //The user's portfolio.
  const [error, setError] = useState(""); //Error message to display if fetching data fails.
  const [selectedTicker, setTicker] = useState(null); //The ticker whose price history is currently being viewed.
  const [priceHistory, setPriceHistory] = useState(null); //Price history of the selected ticker.
  const [timeframe, setTimeframe] = useState(null); //The timeframe for which to view the price history of the selected ticker.

  const user = "user1"; //currently hardcoded, but will be dynamic in the future, as a sign-in page will be added.
  const backendUrl = "http://localhost:5000/api"; //The URL of the backend API. Once deployed, this will be the URL of the deployed backend.

const clickTicker = async (ticker) =>{ //selects a ticker to view its price history.
  if(ticker !== selectedTicker){
    setTicker(ticker);
    setPriceHistory(null);
    setTimeframe(null);
}
}

  const changeTimeframe = async (days) => { //changes the timeframe for which to view the price history of the selected ticker. Triggered when one of the buttons is clicked.
    setTimeframe(days);
    // If a ticker is already selected, fetch its price history with the new timeframe.
    if (selectedTicker) {
      fetchTickerPriceHistory(selectedTicker, days);
    }
  };

  const fetchPortfolio = async () => { //fetches the user's portfolio dictionary.
    try {
      const response = await fetch(`${backendUrl}/${user}/portfolio`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const portfolio = await response.json();
      setPortfolio(portfolio);
    } catch (error) {
      console.error("Error fetching data: ", error);
      setError("Failed to load data.");
    }
  };

  const fetchTickerPriceHistory = async (ticker, time) => { //fetches the price history of the selected ticker for the specified timeframe.
    try {
      const response = await fetch(`${backendUrl}/${user}/portfolio/${ticker}/${time}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const priceHistory = await response.json();
      setPriceHistory(priceHistory);
    } catch (error) {
      console.error("Error fetching data: ", error);
      setError("Failed to load data.");
    }
  };

  useEffect(() => { //As soon as the app loads the user's portfolio and its total value are fetched.
    fetchPortfolio();
  }, []);

  return (
    <div className="App">
      <h1>Your Portfolio</h1> 
      {error && <p className="error">{error}</p>}
      {portfolio && portfolio.stocks_owned && ( //Once the portfolio has been fetched, display the stocks owned by the user.
        <div>
          {Object.entries(portfolio.stocks_owned).map(([stock, details]) => (
            <div key={stock} className="stock-item" onClick={() => clickTicker(stock)}>
              <span className="stock-ticker" style={{ cursor: 'pointer', textDecoration: 'underline', color: 'blue' }}>
                {stock}
              </span>
              <span className="ticker-details" style={{color:'darkslategrey'}}>: {details.amount_owned} shares, Last Closing Price: ${details.latest_closing_price}</span>
            </div>
          ))}
        </div>
      )}
      {portfolio && <h2>Total Portfolio Value: ${portfolio['total_value'] }</h2> /*shows the total value of the user's portfolio.*/} 
      {!selectedTicker && <h2>Click on a ticker to view its price history.</h2>}
      {selectedTicker && ( //If a ticker is selected, display buttons to select or change the timeframe for which to view its price history.
        <>
          <h2>View {selectedTicker}'s price history for the last:</h2>
          <div className="day-buttons">
            {[7, 14, 30].map((day) => (
              <button key={day} onClick={() => changeTimeframe(day)}>
                {day} days
              </button>
            ))}
          </div>
        </>
      )}
      {selectedTicker && priceHistory && ( //Display the price history of the selected ticker for the selected timeframe.
        <div>
          <h3>{selectedTicker}'s price history for the last {timeframe} days:</h3>
          {Object.entries(priceHistory).reverse().map(([date, price]) => (
            <p key={date}>{date}: ${price}</p>
          ))}
          <h3>To view the price history of another ticker, click it.</h3>
        </div>
      )}
      {!portfolio && <p>Loading...</p>}
    </div>
  );

}

export default App;
