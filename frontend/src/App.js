import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import UploadSection from './components/UploadSection';
import FilesList from './components/FilesList';
import DataViewer from './components/DataViewer';
import ErrorMessage from './components/ErrorMessage';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
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

    setUploading(true);
    setUploadProgress(0);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(
        'http://localhost:8000/api/upload-large-csv/',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
          },
        }
      );

      setFile(null);
      setUploadProgress(100);
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
      setUploading(false);
      setUploadProgress(0);
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

  return (
    <div className="App">
      <div className="container">
        <h1>Large CSV Reader</h1>
        <p>Upload and efficiently browse large CSV files (up to 50GB) with chunked processing.</p>
        
        <UploadSection
          file={file}
          uploading={uploading}
          uploadProgress={uploadProgress}
          onFileChange={handleFileChange}
          onUpload={handleUpload}
        />
        
        <ErrorMessage
          error={error}
          onClose={() => setError(null)}
        />
        
        <div className="main-content">
          <div className="left-panel">
            <FilesList
              uploadedFiles={uploadedFiles}
              selectedFile={selectedFile}
              onFileSelect={handleFileSelect}
              onDeleteFile={deleteFile}
            />
          </div>
          <div className="right-panel">
            <DataViewer
              selectedFile={selectedFile}
              fileData={fileData}
              loading={loading}
              pageSize={pageSize}
              onPageChange={handlePageChange}
              onPageSizeChange={handlePageSizeChange}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;