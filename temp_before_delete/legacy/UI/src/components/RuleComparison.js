import React, { useState } from "react";
import "./styles/RuleComparison.css";

function RuleComparison({ rules, onRemoveRule, onClearAll, onRuleDropped }) {
  const [dragOver, setDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    
    if (rules.length >= 3) return;

    try {
      const fileData = JSON.parse(e.dataTransfer.getData('application/json'));
      const isDuplicate = rules.some(rule => rule.id === fileData.id);
      
      if (!isDuplicate) {
        onRuleDropped(fileData);
      }
    } catch (error) {
      console.error('Error parsing dropped data:', error);
    }
  };

  const handleCopyRule = async (content) => {
    try {
      await navigator.clipboard.writeText(content);
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy rule:', err);
    }
  };

  const handleDownloadRule = (rule) => {
    const blob = new Blob([rule.content], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = rule.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownloadAll = () => {
    if (rules.length === 0) return;
    
    let allRules = '';
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    
    rules.forEach((rule, index) => {
      allRules += `# ========================================\n`;
      allRules += `# Rule ${index + 1}: ${rule.name}\n`;
      allRules += `# Model: ${rule.model}\n`;
      allRules += `# Enrichment: ${rule.enrichment}\n`;
      allRules += `# ========================================\n\n`;
      allRules += rule.content;
      allRules += '\n\n\n';
    });
    
    const blob = new Blob([allRules], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sigma-rules-comparison-${timestamp}.yml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rule-comparison">
      <div className="comparison-header">
        <h3>Rule Comparison</h3>
        <div className="comparison-actions">
          {rules.length > 0 && (
            <>
              <button 
                className="download-all-btn"
                onClick={handleDownloadAll}
                title="Download all compared rules"
              >
                Download All
              </button>
              <button 
                className="clear-all-btn"
                onClick={onClearAll}
                title="Clear all comparisons"
              >
                Clear All
              </button>
            </>
          )}
        </div>
      </div>

      <div 
        className={`comparison-content ${dragOver ? 'drag-over' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {rules.length === 0 ? (
          <div className="empty-comparison">
            <div className="drop-zone">
              <div className="drop-icon">🎯</div>
              <h4>Drop rules here to compare</h4>
              <p>Drag up to 3 rule files from the list above</p>
              <p>Compare different models and enrichments side by side</p>
            </div>
          </div>
        ) : (
          <div className="rules-grid">
            {rules.map((rule, index) => (
              <div key={rule.id} className="rule-panel">
                <div className="rule-panel-header">
                  <div className="rule-info">
                    <h4 className="rule-title">{rule.name}</h4>
                    <p className="rule-subtitle">{rule.model} • {rule.enrichment}</p>
                  </div>
                  <div className="rule-actions">
                    <button 
                      className="action-btn copy-btn"
                      onClick={() => handleCopyRule(rule.content)}
                      title="Copy rule"
                    >
                      Copy
                    </button>
                    <button 
                      className="action-btn download-btn"
                      onClick={() => handleDownloadRule(rule)}
                      title="Download rule"
                    >
                      Save
                    </button>
                    <button 
                      className="action-btn remove-btn"
                      onClick={() => onRemoveRule(rule.id)}
                      title="Remove from comparison"
                    >
                      ×
                    </button>
                  </div>
                </div>
                
                <div className="rule-content">
                  <pre className="rule-text">{rule.content}</pre>
                </div>
              </div>
            ))}
            
            {/* Show placeholder slots for remaining spaces */}
            {Array.from({ length: 3 - rules.length }).map((_, index) => (
              <div key={`placeholder-${index}`} className="rule-panel placeholder">
                <div className="placeholder-content">
                  <div className="placeholder-icon">📄</div>
                  <p>Drop rule {rules.length + index + 1}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default RuleComparison;