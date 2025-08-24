import React, { useState } from "react";
import "../components/styles/CTIViewer.css";

function CTIViewer({ onUrlSubmit, onConfigureExperiment, hasUrl, isGenerating, currentUrl }) {
  const [inputUrl, setInputUrl] = useState("");
  const [showIframeError, setShowIframeError] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputUrl.trim()) return;
    
    // Reset iframe error state
    setShowIframeError(false);
    
    // Set the URL first, then open configuration modal
    onUrlSubmit(inputUrl, () => {
      // Callback to open modal after URL is set
      onConfigureExperiment();
    });
  };

  const isValidUrl = (string) => {
    try {
      new URL(string);
      return true;
    } catch (_) {
      return false;
    }
  };

  const inputValid = isValidUrl(inputUrl);
  const displayUrl = currentUrl || inputUrl;

  return (
    <div className="cti-viewer-container">
      <div className="cti-header">
        <div className="cti-icon"></div>
        <h2>CTI Analyzer</h2>
      </div>
      
      <form onSubmit={handleSubmit}>
        <input
          className="cti-input"
          placeholder="Enter CTI URL (e.g., https://example.com/threat-report)"
          value={inputUrl}
          onChange={(e) => setInputUrl(e.target.value)}
          disabled={isGenerating}
        />
        <button 
          className="cti-button" 
          type="submit"
          disabled={isGenerating || !inputValid}
        >
          {isGenerating ? (
            <>
              <span className="loading-spinner"></span>
              Generating Rules...
            </>
          ) : (
            "Configure & Generate"
          )}
        </button>
      </form>
      
      {displayUrl && (
        <div className="cti-iframe-container">
          {showIframeError ? (
            <div className="iframe-error">
              <div className="error-icon">🔒</div>
              <h3>Preview Not Available</h3>
              <p>This website may block embedding for security reasons.</p>
              <p>You can still generate Sigma rules from this URL.</p>
              <div className="iframe-actions">
                <a 
                  href={displayUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="view-external-link"
                >
                  View in New Tab →
                </a>
                <button 
                  className="show-iframe-btn"
                  onClick={() => setShowIframeError(false)}
                >
                  Try Preview Again
                </button>
              </div>
            </div>
          ) : (
            <div className="iframe-wrapper">
              <iframe
                src={displayUrl}
                title="CTI Preview"
                className="cti-iframe"
                frameBorder="0"
                width="100%"
                height="100%"
              />
              <div className="iframe-help">
                <button 
                  className="iframe-help-btn"
                  onClick={() => setShowIframeError(true)}
                  title="Can't see the content? Click here"
                >
                  Can't see preview?
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CTIViewer;