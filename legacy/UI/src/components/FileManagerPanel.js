import React, { useState, useEffect } from "react";
import URLDirectories from "./URLDirectories";
import RuleFiles from "./RuleFiles";
import RuleComparison from "./RuleComparison";
import "./styles/FileManagerPanel.css";

function FileManagerPanel({ ctiUrl, rulesData }) {
  const [urlDirectories, setUrlDirectories] = useState([]);
  const [selectedDirectory, setSelectedDirectory] = useState(null);
  const [ruleFiles, setRuleFiles] = useState([]);
  const [comparisonRules, setComparisonRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch directories from server
  const fetchDirectories = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:8000/directories");
      if (!response.ok) throw new Error("Failed to fetch directories");
      
      const data = await response.json();
      setUrlDirectories(data.directories || []);
    } catch (err) {
      console.error("Error fetching directories:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch files for selected directory
  const fetchDirectoryFiles = async (directoryId) => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/directories/${directoryId}/files`);
      if (!response.ok) throw new Error("Failed to fetch files");
      
      const data = await response.json();
      setRuleFiles(data.files || []);
    } catch (err) {
      console.error("Error fetching files:", err);
      setError(err.message);
      setRuleFiles([]);
    } finally {
      setLoading(false);
    }
  };

  // Load directories on component mount
  useEffect(() => {
    fetchDirectories();
  }, []);

  // Update files when new rules are generated
  useEffect(() => {
    if (rulesData && selectedDirectory) {
      // Refresh the file list to include newly generated files
      fetchDirectoryFiles(selectedDirectory.id);
    }
  }, [rulesData, selectedDirectory]);

  // Auto-select current directory when CTI URL changes
  useEffect(() => {
    // Only try to auto-select if we have rules data (meaning generation completed)
    if (ctiUrl && rulesData && urlDirectories.length > 0) {
      // Find directory for current URL
      const currentDir = urlDirectories.find(dir => dir.url === ctiUrl);
      if (currentDir && (!selectedDirectory || selectedDirectory.id !== currentDir.id)) {
        setSelectedDirectory(currentDir);
        fetchDirectoryFiles(currentDir.id);
      }
    }
  }, [ctiUrl, urlDirectories, rulesData]); // Added rulesData as dependency

  const handleDirectorySelect = (directory) => {
    setSelectedDirectory(directory);
    setComparisonRules([]); // Clear comparison when switching directories
    fetchDirectoryFiles(directory.id);
  };

  const handleRuleDropped = (ruleFile) => {
    if (comparisonRules.length < 3) {
      const isDuplicate = comparisonRules.some(rule => rule.id === ruleFile.id);
      if (!isDuplicate) {
        setComparisonRules(prev => [...prev, ruleFile]);
      }
    }
  };

  const handleRemoveFromComparison = (ruleId) => {
    setComparisonRules(prev => prev.filter(rule => rule.id !== ruleId));
  };

  const handleClearComparison = () => {
    setComparisonRules([]);
  };

  const handleDeleteDirectory = async (directoryId) => {
    try {
      const response = await fetch(`http://localhost:8000/directories/${directoryId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) throw new Error("Failed to delete directory");
      
      // Refresh directories list
      await fetchDirectories();
      
      // Clear selection if deleted directory was selected
      if (selectedDirectory?.id === directoryId) {
        setSelectedDirectory(null);
        setRuleFiles([]);
        setComparisonRules([]);
      }
    } catch (err) {
      console.error("Error deleting directory:", err);
      setError(err.message);
    }
  };

  return (
    <div className="file-manager-panel">
      <div className="file-manager-header">
        <h2>Rule Management</h2>
        <div className="header-stats">
          <span>{urlDirectories.length} directories</span>
          <span>{ruleFiles.length} files</span>
          <span>{comparisonRules.length}/3 comparing</span>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="file-manager-content">
        <div className="file-browser">
          <div className="browser-section">
            <h3>URL Directories</h3>
            <URLDirectories
              directories={urlDirectories}
              selectedDirectory={selectedDirectory}
              onDirectorySelect={handleDirectorySelect}
              onDeleteDirectory={handleDeleteDirectory}
              currentUrl={ctiUrl}
              loading={loading}
            />
          </div>

          <div className="browser-section">
            <h3>Rule Files</h3>
            <RuleFiles
              files={ruleFiles}
              selectedDirectory={selectedDirectory}
              onRuleDrop={handleRuleDropped}
              comparisonCount={comparisonRules.length}
              loading={loading}
            />
          </div>
        </div>

        <div className="comparison-area">
          <RuleComparison
            rules={comparisonRules}
            onRemoveRule={handleRemoveFromComparison}
            onClearAll={handleClearComparison}
            onRuleDropped={handleRuleDropped}
          />
        </div>
      </div>
    </div>
  );
}

export default FileManagerPanel;