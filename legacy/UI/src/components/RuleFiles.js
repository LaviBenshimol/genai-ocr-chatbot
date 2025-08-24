import React from "react";
import "./styles/RuleFiles.css";

function RuleFiles({ files, selectedDirectory, onRuleDrop, comparisonCount, loading }) {
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getEnrichmentBadgeColor = (enrichment) => {
    const colors = {
      'noEnrichment': '#6b7280',
      'useJudge': '#3b82f6', 
      'ruleRefine': '#10b981'
    };
    return colors[enrichment] || '#6b7280';
  };

  const getEnrichmentDisplayName = (enrichment) => {
    const names = {
      'noEnrichment': 'No Enrichment',
      'useJudge': 'Judge Enhancement',
      'ruleRefine': 'Rule Refinement'
    };
    return names[enrichment] || enrichment;
  };

  const handleDragStart = (e, file) => {
    e.dataTransfer.setData('application/json', JSON.stringify(file));
    e.dataTransfer.effectAllowed = 'copy';
  };

  const canDrop = comparisonCount < 3;

  if (!selectedDirectory) {
    return (
      <div className="rule-files">
        <div className="empty-files">
          <div className="empty-icon">📄</div>
          <p>Select a directory</p>
          <p>Choose a URL directory to view its rule files</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rule-files">
        <div className="loading-files">
          <div className="loading-spinner"></div>
          <p>Loading files...</p>
        </div>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="rule-files">
        <div className="empty-files">
          <div className="empty-icon">📄</div>
          <p>No rule files</p>
          <p>Generate rules to populate this directory</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rule-files">
      <div className="files-header">
        <span className="files-count">{files.length} rule{files.length !== 1 ? 's' : ''}</span>
        {!canDrop && (
          <span className="drop-limit">Comparison limit reached (3/3)</span>
        )}
      </div>
      
      <div className="files-list">
        {files.map((file) => (
          <div
            key={file.id}
            className={`file-item ${file.isGenerated ? 'generated' : ''} ${!canDrop ? 'no-drop' : ''}`}
            draggable={canDrop}
            onDragStart={(e) => handleDragStart(e, file)}
            title={canDrop ? "Drag to comparison area" : "Comparison area is full"}
          >
            <div className="file-header">
              <div className="file-icon">
                {file.isGenerated ? '⚡' : '📄'}
              </div>
              <div className="file-info">
                <h4 className="file-name">{file.name}</h4>
                <p className="file-model">{file.model}</p>
              </div>
              {file.isGenerated && (
                <div className="generated-badge">New</div>
              )}
            </div>

            <div className="file-meta">
              <div className="file-details">
                <span 
                  className="enrichment-badge"
                  style={{ backgroundColor: getEnrichmentBadgeColor(file.enrichment) }}
                >
                  {getEnrichmentDisplayName(file.enrichment)}
                </span>
                <span className="file-size">{file.size}</span>
              </div>
              <span className="file-date">{formatDate(file.created_at)}</span>
            </div>

            {canDrop && (
              <div className="drag-hint">
                <span>Drag to compare</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default RuleFiles;