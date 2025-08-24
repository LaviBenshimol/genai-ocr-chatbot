import React from "react";
import "./styles/SigmaSelector.css";

function SigmaSelector({ 
  label, 
  models, 
  enrichments, 
  selectedModel, 
  selectedEnrichment, 
  onModelChange, 
  onEnrichmentChange 
}) {
  const hasCompleteSelection = selectedModel && selectedEnrichment;
  const selectorClass = hasCompleteSelection ? "sigma-selector has-selection" : "sigma-selector";

  const getEnrichmentDisplayName = (enrichment) => {
    const names = {
      noEnrichment: "No Enrichment",
      useJudge: "Judge Enhancement", 
      ruleRefine: "Rule Refinement"
    };
    return names[enrichment] || enrichment;
  };

  return (
    <div className={selectorClass}>
      <div className="sigma-selector-header">
        <h4>{label} Configuration</h4>
        <div className="sigma-selector-badge">{label}</div>
      </div>
      
      <div className="selector-field-group">
        <label>AI Model</label>
        <select 
          value={selectedModel} 
          onChange={(e) => {
            onModelChange(e.target.value);
            // Reset enrichment when model changes
            if (!e.target.value) {
              onEnrichmentChange("");
            }
          }}
        >
          <option value="">Choose a model...</option>
          {models.map((model) => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
        <div className={`selection-status ${selectedModel ? 'complete' : 'incomplete'}`}>
          {selectedModel ? `Selected: ${selectedModel}` : 'No model selected'}
        </div>
      </div>

      <div className="selector-field-group">
        <label>Enrichment Type</label>
        <select 
          value={selectedEnrichment} 
          onChange={(e) => onEnrichmentChange(e.target.value)}
          disabled={!selectedModel}
        >
          <option value="">Choose enrichment...</option>
          {enrichments.map((enrichment) => (
            <option key={enrichment} value={enrichment}>
              {getEnrichmentDisplayName(enrichment)}
            </option>
          ))}
        </select>
        <div className={`selection-status ${selectedEnrichment ? 'complete' : 'incomplete'}`}>
          {selectedEnrichment ? 
            `Selected: ${getEnrichmentDisplayName(selectedEnrichment)}` : 
            selectedModel ? 'Choose an enrichment type' : 'Select model first'
          }
        </div>
      </div>
    </div>
  );
}

export default SigmaSelector;