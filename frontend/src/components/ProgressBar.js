import React from 'react';

const ProgressBar = ({ progress, text }) => {
  return (
    <div className="upload-progress">
      <div className="progress-bar-container">
        <div className="progress-bar" style={{width: `${progress}%`}}></div>
      </div>
      <div className="progress-text">{text || `${progress}%`}</div>
    </div>
  );
};

export default ProgressBar;