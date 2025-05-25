import React from 'react';

const ErrorMessage = ({ error, onClose }) => {
  if (!error) return null;

  return (
    <div className="error">
      Error: {error}
      <button onClick={onClose}>×</button>
    </div>
  );
};

export default ErrorMessage;