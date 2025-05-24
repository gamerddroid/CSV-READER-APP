import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileData, setFileData] = useState(null);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);

  // Load uploaded files on component mount
  useEffect(() => {
    loadUploadedFiles();
  }, []);

  // Poll for file status updates
  useEffect(() => {
    const interval = setInterval(() => {
      loadUploadedFiles();
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, []);

  const loadUploadedFiles = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/files/');
      setUploadedFiles(response.data.files);
    } catch (err) {
      console.error('Error loading files:', err);
    }
  };

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        'http://localhost:8000/api/upload-large-csv/',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setFile(null);
      // Reset file input
      const fileInput = document.querySelector('input[type="file"]');
      if (fileInput) fileInput.value = '';
      
      // Reload files list
      await loadUploadedFiles();
      
    } catch (err) {
      if (err.response && err.response.data && err.response.data.error) {
        setError(err.response.data.error);
      } else {
        setError('An error occurred while uploading the file');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadFileData = async (fileId, newPage = 1, newPageSize = pageSize) => {
    try {
      setLoading(true);
      const response = await axios.get(
        `http://localhost:8000/api/files/${fileId}/data/?page=${newPage}&page_size=${newPageSize}`
      );
      setFileData(response.data);
      setPage(newPage);
      setPageSize(newPageSize);
    } catch (err) {
      setError('Error loading file data: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = async (file) => {
    setSelectedFile(file);
    setFileData(null);
    setPage(1);
    
    if (file.status === 'completed') {
      await loadFileData(file.file_id, 1, pageSize);
    }
  };

  const handlePageChange = (newPage) => {
    if (selectedFile && selectedFile.status === 'completed') {
      loadFileData(selectedFile.file_id, newPage, pageSize);
    }
  };

  const handlePageSizeChange = (e) => {
    const newSize = parseInt(e.target.value, 10);
    setPageSize(newSize);
    if (selectedFile && selectedFile.status === 'completed') {
      loadFileData(selectedFile.file_id, 1, newSize);
    }
  };

  const deleteFile = async (fileId) => {
    try {
      await axios.delete(`http://localhost:8000/api/files/${fileId}/delete/`);
      await loadUploadedFiles();
      
      // Clear selected file if it was deleted
      if (selectedFile && selectedFile.file_id === fileId) {
        setSelectedFile(null);
        setFileData(null);
      }
    } catch (err) {
      setError('Error deleting file: ' + (err.response?.data?.error || err.message));
    }
  };

  const formatFileSize = (bytes) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Bytes';
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const renderUploadSection = () => (
    <div className="upload-section">
      <h2>Upload Large CSV File</h2>
      <p>Supports files up to 50GB with efficient memory usage</p>
      <div className="file-input">
        <input
          type="file"
          accept=".csv"
          onChange={handleFileChange}
        />
      </div>
      <button
        className="upload-btn"
        onClick={handleUpload}
        disabled={loading || !file}
      >
        {loading ? 'Uploading...' : 'Upload and Process'}
      </button>
    </div>
  );

  const renderFilesList = () => (
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
              onClick={() => handleFileSelect(file)}
            >
              <div className="file-header">
                <h4>{file.filename}</h4>
                <button 
                  className="delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteFile(file.file_id);
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

  const renderDataViewer = () => {
    if (!selectedFile) {
      return (
        <div className="data-section">
          <h2>Data Viewer</h2>
          <p>Select a completed file to view its data.</p>
        </div>
      );
    }

    if (selectedFile.status !== 'completed') {
      return (
        <div className="data-section">
          <h2>Data Viewer</h2>
          <p>File is {selectedFile.status}. Data will be available once processing is complete.</p>
        </div>
      );
    }

    if (!fileData) {
      return (
        <div className="data-section">
          <h2>Data Viewer</h2>
          <p>Loading data...</p>
        </div>
      );
    }

    return (
      <div className="data-section">
        <h2>Data Viewer - {selectedFile.filename}</h2>
        
        <div className="data-controls">
          <div className="pagination-info">
            <p>
              Showing {((fileData.page - 1) * fileData.page_size) + 1} to {Math.min(fileData.page * fileData.page_size, fileData.total_rows)} 
              of {fileData.total_rows.toLocaleString()} rows
            </p>
          </div>
          
          <div className="controls">
            <label>
              Rows per page:
              <select value={pageSize} onChange={handlePageSizeChange} disabled={loading}>
                {[50, 100, 500, 1000, 5000].map(size => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                {fileData.columns.map((col, index) => (
                  <th key={index}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fileData.data.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {fileData.columns.map((col, colIndex) => (
                    <td key={colIndex}>
                      {row[col] !== null && row[col] !== undefined ? String(row[col]) : ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="pagination-controls">
          <button
            onClick={() => handlePageChange(fileData.page - 1)}
            disabled={!fileData.has_previous || loading}
          >
            Previous
          </button>
          <span>
            Page {fileData.page} of {fileData.total_pages}
          </span>
          <button
            onClick={() => handlePageChange(fileData.page + 1)}
            disabled={!fileData.has_next || loading}
          >
            Next
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <div className="container">
        <h1>Large CSV Reader</h1>
        <p>Upload and efficiently browse large CSV files (up to 50GB) with chunked processing.</p>
        
        {renderUploadSection()}
        
        {error && (
          <div className="error">
            Error: {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}
        
        <div className="main-content">
          <div className="left-panel">
            {renderFilesList()}
          </div>
          <div className="right-panel">
            {renderDataViewer()}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;