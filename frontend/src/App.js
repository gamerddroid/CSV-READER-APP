import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setResult(null);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        'http://localhost:8000/api/upload-csv/',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      setResult(response.data);
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

  const renderDataFrameInfo = () => {
    if (!result || !result.dataframe_info) return null;

    const { dataframe_info } = result;

    return (
      <div className="dataframe-info">
        <h3>DataFrame Information</h3>
        
        <div className="info-section">
          <h4>Basic Info</h4>
          <p><strong>Shape:</strong> {dataframe_info.shape[0]} rows × {dataframe_info.shape[1]} columns</p>
          <p><strong>Memory Usage:</strong> {Math.round(dataframe_info.info.memory_usage / 1024)} KB</p>
        </div>

        <div className="info-section">
          <h4>Columns and Data Types</h4>
          <ul>
            {dataframe_info.columns.map((col, index) => (
              <li key={index}>
                <strong>{col}:</strong> {dataframe_info.dtypes[col]}
              </li>
            ))}
          </ul>
        </div>

        <div className="info-section">
          <h4>Null Values Count</h4>
          <ul>
            {Object.entries(dataframe_info.info.null_counts).map(([col, count]) => (
              <li key={col}>
                <strong>{col}:</strong> {count} null values
              </li>
            ))}
          </ul>
        </div>

        <div className="info-section">
          <h4>Sample Data (First 5 rows)</h4>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  {dataframe_info.columns.map((col, index) => (
                    <th key={index}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dataframe_info.head.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {dataframe_info.columns.map((col, colIndex) => (
                      <td key={colIndex}>{row[col]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="App">
      <div className="container">
        <h1>CSV Reader App</h1>
        <p>Upload a CSV file to convert it to a pandas DataFrame and view its information.</p>
        
        <div className="upload-section">
          <h2>Upload CSV File</h2>
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
            {loading ? 'Processing...' : 'Upload and Process'}
          </button>
        </div>

        {error && (
          <div className="error">
            Error: {error}
          </div>
        )}

        {result && (
          <div className="results-section">
            <div className="success">
              Successfully processed: {result.filename}
            </div>
            {renderDataFrameInfo()}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;