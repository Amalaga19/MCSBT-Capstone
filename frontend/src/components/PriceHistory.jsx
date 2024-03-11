import React from 'react';

const PriceHistory = ({ priceHistory, ticker }) => {
  return (
    <div>
      <h3>{ticker}'s price history:</h3>
      {Object.entries(priceHistory).reverse().map(([date, price]) => (
        <p key={date}>{date}: ${price}</p>
      ))}
    </div>
  );
}

export default PriceHistory;
