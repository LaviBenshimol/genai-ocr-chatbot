import React, { useState } from "react";
import ResizablePanels from "./components/ResizablePanels";
import CTIViewer from "./components/CTIViewer";
import FileManagerPanel from "./components/FileManagerPanel";
import ConfigurationModal from "./components/ConfigurationModal";
import { useSigmaRules } from "./hooks/useSigmaRules";
import { useServerOptions } from "./hooks/useServerOptions";
import "./App.css";

function App() {
  const [ctiUrl, setCtiUrl] = useState("");
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  
  const { rulesData, loading, generateRulesForConfigurations, clearRules } = useSigmaRules();
  const { models, enrichments, loading: optionsLoading, error: optionsError } = useServerOptions();

  const handleOpenConfigModal = () => {
    setIsConfigModalOpen(true);
  };

  const handleCloseConfigModal = () => {
    setIsConfigModalOpen(false);
  };

  const handleGenerateRules = (configurations) => {
    generateRulesForConfigurations(ctiUrl, configurations);
  };

  const handleUrlSubmit = (url, callback) => {
    setCtiUrl(url);
    // Clear previous rules when URL changes
    clearRules();
    
    // If callback is provided, execute it after state is set
    if (callback) {
      // Use setTimeout to ensure state update happens first
      setTimeout(callback, 0);
    }
  };

  // CTI Viewer is on the left (smaller panel)
  const leftPanel = (
    <CTIViewer 
      onUrlSubmit={handleUrlSubmit}
      onConfigureExperiment={handleOpenConfigModal}
      hasUrl={!!ctiUrl}
      isGenerating={loading}
    />
  );

  // File Manager Panel is on the right (bigger panel)
  const rightPanel = (
    <FileManagerPanel 
      ctiUrl={ctiUrl}
      rulesData={rulesData}
    />
  );

  return (
    <>
      <ResizablePanels
        leftContent={leftPanel}
        rightContent={rightPanel}
      />
      
      <ConfigurationModal
        isOpen={isConfigModalOpen}
        onClose={handleCloseConfigModal}
        onGenerate={handleGenerateRules}
        isGenerating={loading}
        availableModels={models}
        availableEnrichments={enrichments}
      />
      
      {optionsError && (
        <div className="error-toast">
          <span>⚠️ Could not load server options: {optionsError}</span>
          <span>Using fallback values.</span>
        </div>
      )}
    </>
  );
}

export default App;