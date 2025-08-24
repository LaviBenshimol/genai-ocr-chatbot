import React, { useState } from "react";
import SigmaSelector from "./SigmaSelector";
import SigmaRuleBlock from "./SigmaRuleBlock";
import "./styles/SigmaComparatorPanel.css";

function SigmaComparatorPanel({ rulesData }) {
  const models = Object.keys(rulesData || {});
  const enrichments = ["noEnrichment", "useJudge", "ruleRefine"];

  const [leftModel, setLeftModel] = useState("");
  const [leftEnrichment, setLeftEnrichment] = useState("");
  const [rightModel, setRightModel] = useState("");
  const [rightEnrichment, setRightEnrichment] = useState("");

  const getRule = (model, enrich) => {
    const rule = rulesData?.[model]?.[enrich];
    return rule || null;
  };

  const getEnrichmentDisplayName = (enrichment) => {
    const names = {
      noEnrichment: "No Enrichment",
      useJudge: "Judge Enhancement",
      ruleRefine: "Rule Refinement"
    };
    return names[enrichment] || enrichment;
  };

  const handleDownloadAll = () => {
    if (!rulesData) return;
    
    let allRules = '';
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    
    Object.keys(rulesData).forEach(model => {
      Object.keys(rulesData[model]).forEach(enrichment => {
        const rule = rulesData[model][enrichment];
        if (rule) {
          allRules += `# ========================================\n`;
          allRules += `# Model: ${model}\n`;
          allRules += `# Enrichment: ${getEnrichmentDisplayName(enrichment)}\n`;
          allRules += `# ========================================\n\n`;
          allRules += rule;
          allRules += '\n\n\n';
        }
      });
    });
    
    const blob = new Blob([allRules], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sigma-rules-all-${timestamp}.yml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const hasAnyRules = rulesData && Object.keys(rulesData).some(model => 
    Object.keys(rulesData[model]).some(enrichment => rulesData[model][enrichment])
  );

  const leftRule = getRule(leftModel, leftEnrichment);
  const rightRule = getRule(rightModel, rightEnrichment);

  return (
    <div className="comparator-container">
      <div className="comparator-header">
        <div className="comparator-icon"></div>
        <h2>Sigma Rule Comparator</h2>
        {hasAnyRules && (
          <button 
            className="download-all-button"
            onClick={handleDownloadAll}
            title="Download all generated rules"
          >
            Download All Rules
          </button>
        )}
      </div>

      <div className="selector-row">
        <SigmaSelector
          label="Left"
          models={models}
          enrichments={enrichments}
          selectedModel={leftModel}
          selectedEnrichment={leftEnrichment}
          onModelChange={setLeftModel}
          onEnrichmentChange={setLeftEnrichment}
        />
        
        <div className="comparison-indicator">
          VS
        </div>
        
        <SigmaSelector
          label="Right"
          models={models}
          enrichments={enrichments}
          selectedModel={rightModel}
          selectedEnrichment={rightEnrichment}
          onModelChange={setRightModel}
          onEnrichmentChange={setRightEnrichment}
        />
      </div>

      <div className="comparison-row">
        <SigmaRuleBlock 
          title={leftModel && leftEnrichment ? 
            `${leftModel} - ${getEnrichmentDisplayName(leftEnrichment)}` : 
            "Left Rule"
          }
          rule={leftRule}
          isEmpty={!leftRule}
        />
        
        <SigmaRuleBlock 
          title={rightModel && rightEnrichment ? 
            `${rightModel} - ${getEnrichmentDisplayName(rightEnrichment)}` : 
            "Right Rule"
          }
          rule={rightRule}
          isEmpty={!rightRule}
        />
      </div>
    </div>
  );
}

export default SigmaComparatorPanel;