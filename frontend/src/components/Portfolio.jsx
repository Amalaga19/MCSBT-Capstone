import React from 'react';

const Tickers = ({ stocks, onTickerClick }) => {
  return (
    <div>
      {Object.entries(stocks).map(([stock, details]) => (
        <div key={stock} className="stock-item">
          <span className="stock-ticker" onClick={() => onTickerClick(stock)} style={{ cursor: 'pointer', textDecoration: 'underline' }}>
            <p>{stock}</p>
          </span>: {details.amount_owned} shares, Last Closing Price: ${details.latest_closing_price}
        </div>
      ))}
    </div>
  );
}

export default Tickers;
