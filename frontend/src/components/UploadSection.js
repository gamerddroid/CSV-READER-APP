import React from 'react';

const UploadSection = ({ 
  file, 
  uploading, 
  uploadProgress, 
  onFileChange, 
  onUpload 
}) => {
  return (
    <div className="upload-section">
      <h2>Upload Large CSV File</h2>
      <p>Supports files up to 50GB with efficient memory usage</p>
      <div className="file-input">
        <input
          type="file"
          accept=".csv"
          onChange={onFileChange}
          disabled={uploading}
        />
      </div>
      {uploading && (
        <div className="upload-progress">
          <div className="progress-bar-container">
            <div className="progress-bar" style={{width: `${uploadProgress}%`}}></div>
          </div>
          <div className="progress-text">{uploadProgress}% uploaded</div>
        </div>
      )}
      <button
        className="upload-btn"
        onClick={onUpload}
        disabled={uploading || !file}
      >
        {uploading ? `Uploading... ${uploadProgress}%` : 'Upload and Process'}
      </button>
    </div>
  );
};

export default UploadSection;