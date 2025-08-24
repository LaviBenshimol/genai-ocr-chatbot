import React, { useState } from "react";
import "./styles/SigmaRuleBlock.css";

function SigmaRuleBlock({ title, rule, isEmpty = false }) {
  const [showCopyFeedback, setShowCopyFeedback] = useState(false);

  const handleCopy = async () => {
    if (!rule) return;
    
    try {
      await navigator.clipboard.writeText(rule);
      setShowCopyFeedback(true);
      setTimeout(() => setShowCopyFeedback(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const handleDownload = () => {
    if (!rule) return;
    
    const blob = new Blob([rule], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sigma-rule-${Date.now()}.yml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderLineNumbers = () => {
    return null; // Removed line numbers functionality
  };

  const highlightSyntax = (text) => {
    if (!text) return text;
    
    return text
      .replace(/^(title:.*$)/gm, '<span class="sigma-title">$1</span>')
      .replace(/^(status:.*$)/gm, '<span class="sigma-status">$1</span>')
      .replace(/^(description:.*$)/gm, '<span class="sigma-description">$1</span>')
      .replace(/^(author:.*$)/gm, '<span class="sigma-author">$1</span>')
      .replace(/^(date:.*$)/gm, '<span class="sigma-date">$1</span>')
      .replace(/^(detection:.*$)/gm, '<span class="sigma-detection">$1</span>')
      .replace(/^(\s+selection.*:)/gm, '<span class="sigma-selection">$1</span>')
      .replace(/^(\s+condition:.*$)/gm, '<span class="sigma-condition">$1</span>')
      .replace(/^(logsource:.*$)/gm, '<span class="sigma-logsource">$1</span>')
      .replace(/^(falsepositives:.*$)/gm, '<span class="sigma-falsepositives">$1</span>')
      .replace(/^(level:.*$)/gm, '<span class="sigma-level">$1</span>')
      .replace(/^(tags:.*$)/gm, '<span class="sigma-tags">$1</span>');
  };

  if (isEmpty || !rule) {
    return (
      <div className="sigma-rule-block">
        <div className="sigma-rule-title">
          {title}
        </div>
        <div className="sigma-rule-empty">
          <h3>No Rule Selected</h3>
          <p>Select a model and enrichment type to view the generated Sigma rule.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="sigma-rule-block">
      <div className="sigma-rule-title">
        {title}
        <div className="sigma-rule-actions">
          <button 
            className="sigma-rule-action" 
            onClick={handleCopy}
            title="Copy to clipboard"
          >
            Copy
          </button>
          <button 
            className="sigma-rule-action" 
            onClick={handleDownload}
            title="Download rule"
          >
            Save
          </button>
        </div>
      </div>
      
      <div className="sigma-rule-content-wrapper">
        <div className="sigma-rule-content-inner">
          <pre 
            className="sigma-rule-content"
            dangerouslySetInnerHTML={{ __html: highlightSyntax(rule) }}
          />
        </div>
        
        {showCopyFeedback && (
          <div className="copy-feedback show">
            ✓ Copied to clipboard!
          </div>
        )}
      </div>
    </div>
  );
}

export default SigmaRuleBlock;