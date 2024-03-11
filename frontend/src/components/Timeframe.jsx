import React from 'react';

const Timeframe = ({ selectedTicker, onSelectTimeframe }) => {
  if (!selectedTicker) return null;

  return (
    <div className="timeframe-selection">
      <p>Select timeframe for {selectedTicker}:</p>
      {[7, 14, 30].map((day) => (
        <button key={day} onClick={() => onSelectTimeframe(day)}>
          {day} days
        </button>
      ))}
    </div>
  );
}

export default Timeframe;
