import React from "react";
import "./styles/URLDirectories.css";

function URLDirectories({ directories, selectedDirectory, onDirectorySelect, onDeleteDirectory, loading }) {
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const truncateUrl = (url, maxLength = 40) => {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
  };

  const handleDeleteClick = (e, directoryId) => {
    e.stopPropagation(); // Prevent directory selection
    if (window.confirm("Are you sure you want to delete this directory and all its files?")) {
      onDeleteDirectory(directoryId);
    }
  };

  if (loading && directories.length === 0) {
    return (
      <div className="url-directories">
        <div className="loading-directories">
          <div className="loading-spinner"></div>
          <p>Loading directories...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="url-directories">
      {directories.length === 0 ? (
        <div className="empty-directories">
          <div className="empty-icon">📁</div>
          <p>No directories yet</p>
          <p>Generate rules from a CTI URL to create your first directory</p>
        </div>
      ) : (
        <div className="directories-list">
          {directories.map((directory) => (
            <div
              key={directory.id}
              className={`directory-item ${selectedDirectory?.id === directory.id ? 'selected' : ''}`}
              onClick={() => onDirectorySelect(directory)}
            >
              <div className="directory-header">
                <div className="directory-icon">📁</div>
                <div className="directory-info">
                  <h4 className="directory-name">{directory.name}</h4>
                  <p className="directory-url" title={directory.url}>
                    {truncateUrl(directory.url)}
                  </p>
                </div>
                <div className="directory-actions">
                  <button
                    className="delete-directory-btn"
                    onClick={(e) => handleDeleteClick(e, directory.id)}
                    title="Delete directory"
                  >
                    ×
                  </button>
                </div>
              </div>
              
              <div className="directory-meta">
                <span className="file-count">{directory.file_count} files</span>
                <span className="created-date">{formatDate(directory.created_at)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default URLDirectories;