import React, { useState } from "react";
import "./styles/ConfigurationModal.css";

function ConfigurationModal({ isOpen, onClose, onGenerate, isGenerating, availableModels, availableEnrichments }) {
  const [selectedConfigurations, setSelectedConfigurations] = useState([]);

  const addConfiguration = () => {
    const newConfig = {
      id: Date.now() + Math.random(),
      model: "",
      enrichment: "",
      isValid: false
    };
    setSelectedConfigurations([...selectedConfigurations, newConfig]);
  };

  const updateConfiguration = (id, field, value) => {
    setSelectedConfigurations(configs => 
      configs.map(config => {
        if (config.id === id) {
          const updated = { ...config, [field]: value };
          updated.isValid = updated.model && updated.enrichment;
          return updated;
        }
        return config;
      })
    );
  };

  const removeConfiguration = (id) => {
    setSelectedConfigurations(configs => configs.filter(config => config.id !== id));
  };

  const handleGenerate = () => {
    const validConfigs = selectedConfigurations.filter(config => config.isValid);
    if (validConfigs.length > 0) {
      onGenerate(validConfigs);
      onClose();
      setSelectedConfigurations([]); // Reset after generation
    }
  };

  const handleClose = () => {
    if (!isGenerating) {
      onClose();
    }
  };

  const validConfigurationsCount = selectedConfigurations.filter(config => config.isValid).length;
  const canGenerate = validConfigurationsCount > 0 && !isGenerating;

  const getEnrichmentDisplayName = (enrichment) => {
    const names = {
      noEnrichment: "No Enrichment",
      useJudge: "Judge Enhancement",
      ruleRefine: "Rule Refinement"
    };
    return names[enrichment] || enrichment;
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Configure Experiment</h2>
          <button 
            className="modal-close-btn"
            onClick={handleClose}
            disabled={isGenerating}
          >
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="config-section">
            <div className="section-header">
              <h3>Model & Enrichment Combinations</h3>
              <button 
                className="add-config-btn"
                onClick={addConfiguration}
                disabled={isGenerating}
              >
                + Add Configuration
              </button>
            </div>

            <div className="configurations-list">
              {selectedConfigurations.length === 0 ? (
                <div className="empty-configs">
                  <div className="empty-icon">⚙️</div>
                  <p>No configurations added yet.</p>
                  <p>Add model/enrichment combinations to generate rules.</p>
                </div>
              ) : (
                selectedConfigurations.map((config) => (
                  <div key={config.id} className={`config-item ${config.isValid ? 'valid' : 'invalid'}`}>
                    <div className="config-fields">
                      <div className="field-group">
                        <label>Model</label>
                        <select
                          value={config.model}
                          onChange={(e) => updateConfiguration(config.id, 'model', e.target.value)}
                          disabled={isGenerating}
                        >
                          <option value="">Select Model</option>
                          {availableModels.map(model => (
                            <option key={model} value={model}>{model}</option>
                          ))}
                        </select>
                      </div>

                      <div className="field-group">
                        <label>Enrichment</label>
                        <select
                          value={config.enrichment}
                          onChange={(e) => updateConfiguration(config.id, 'enrichment', e.target.value)}
                          disabled={isGenerating}
                        >
                          <option value="">Select Enrichment</option>
                          {availableEnrichments.map(enrichment => (
                            <option key={enrichment} value={enrichment}>
                              {getEnrichmentDisplayName(enrichment)}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <button
                      className="remove-config-btn"
                      onClick={() => removeConfiguration(config.id)}
                      disabled={isGenerating}
                      title="Remove configuration"
                    >
                      ×
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <div className="footer-info">
            <span className="config-count">
              {validConfigurationsCount} configuration{validConfigurationsCount !== 1 ? 's' : ''} ready
            </span>
          </div>
          
          <div className="footer-actions">
            <button
              className="cancel-btn"
              onClick={handleClose}
              disabled={isGenerating}
            >
              Cancel
            </button>
            <button
              className="generate-btn"
              onClick={handleGenerate}
              disabled={!canGenerate}
            >
              {isGenerating ? (
                <>
                  <span className="loading-spinner"></span>
                  Generating...
                </>
              ) : (
                `Generate Rules (${validConfigurationsCount})`
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ConfigurationModal;