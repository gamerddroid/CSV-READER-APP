import React from 'react';

const DataViewer = ({ 
  selectedFile, 
  fileData, 
  loading, 
  pageSize, 
  onPageChange, 
  onPageSizeChange 
}) => {
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
            <select value={pageSize} onChange={onPageSizeChange} disabled={loading}>
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
          onClick={() => onPageChange(fileData.page - 1)}
          disabled={!fileData.has_previous || loading}
        >
          Previous
        </button>
        <span>
          Page {fileData.page} of {fileData.total_pages}
        </span>
        <button
          onClick={() => onPageChange(fileData.page + 1)}
          disabled={!fileData.has_next || loading}
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default DataViewer;