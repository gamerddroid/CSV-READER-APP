import React from 'react';
import { formatFileSize, formatDate } from '../utils/helpers';

const FilesList = ({ 
  uploadedFiles, 
  selectedFile, 
  onFileSelect, 
  onDeleteFile 
}) => {
  return (
    <div className="files-section">
      <h2>Uploaded Files</h2>
      {uploadedFiles.length === 0 ? (
        <p>No files uploaded yet.</p>
      ) : (
        <div className="files-list">
          {uploadedFiles.map((file) => (
            <div 
              key={file.file_id} 
              className={`file-item ${selectedFile?.file_id === file.file_id ? 'selected' : ''}`}
              onClick={() => onFileSelect(file)}
            >
              <div className="file-header">
                <h4>{file.filename}</h4>
                <button 
                  className="delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteFile(file.file_id);
                  }}
                >
                  ×
                </button>
              </div>
              <div className="file-info">
                <p><strong>Size:</strong> {formatFileSize(file.file_size)}</p>
                <p><strong>Status:</strong> 
                  <span className={`status ${file.status}`}>{file.status}</span>
                </p>
                {file.total_rows && (
                  <p><strong>Rows:</strong> {file.total_rows.toLocaleString()}</p>
                )}
                {file.status === 'processing' && (
                  <div className="progress">
                    <div 
                      className="progress-bar" 
                      style={{width: `${file.processing_progress}%`}}
                    ></div>
                    <span>{file.processing_progress.toFixed(1)}%</span>
                  </div>
                )}
                <p><strong>Uploaded:</strong> {formatDate(file.created_at)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FilesList;