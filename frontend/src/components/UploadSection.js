import React, { useState, useEffect } from 'react';

const UploadSection = ({ 
  file, 
  uploading, 
  uploadProgress, 
  onFileChange, 
  onUpload 
}) => {
  const [diskSpace, setDiskSpace] = useState(null);
  const [loadingDiskSpace, setLoadingDiskSpace] = useState(true);

  useEffect(() => {
    fetchDiskSpace();
    // Refresh disk space every 30 seconds
    const interval = setInterval(fetchDiskSpace, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDiskSpace = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/disk-space/');
      if (response.ok) {
        const data = await response.json();
        setDiskSpace(data);
      }
    } catch (error) {
      console.error('Failed to fetch disk space:', error);
    } finally {
      setLoadingDiskSpace(false);
    }
  };
  return (
    <div className="upload-section">
      <h2>Upload Large CSV File</h2>
      <p>Supports files up to 50GB with efficient memory usage</p>
      
      {/* Disk Space Information */}
      <div className="disk-space-info">
        {loadingDiskSpace ? (
          <p>Loading disk space...</p>
        ) : diskSpace ? (
          <div className="space-details">
            <h4>Storage Space (/tmp)</h4>
            <div className="space-bar">
              <div 
                className="space-used" 
                style={{width: `${diskSpace.usage_percentage}%`}}
              ></div>
            </div>
            <div className="space-text">
              <span className="free-space">
                Free: {diskSpace.free_space.formatted}
              </span>
              <span className="total-space">
                Total: {diskSpace.total_space.formatted}
              </span>
              <span className="usage-percent">
                {diskSpace.usage_percentage}% used
              </span>
            </div>
          </div>
        ) : (
          <p>Could not load disk space information</p>
        )}
      </div>

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