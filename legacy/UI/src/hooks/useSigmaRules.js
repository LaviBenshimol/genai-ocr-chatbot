import { useState, useCallback } from "react";

export function useSigmaRules() {
  const [rulesData, setRulesData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generateRulesForConfigurations = useCallback(async (ctiUrl, configurations) => {
    if (!ctiUrl || !configurations.length) return;

    setLoading(true);
    setError(null);
    
    try {
      // Send the configurations to the updated server endpoint
      const response = await fetch("http://localhost:8000/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          cti_url: ctiUrl,
          configurations: configurations.map(config => ({
            model: config.model,
            enrichment: config.enrichment
          }))
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // The server now returns only the requested configurations
      setRulesData(data.rules);
      
    } catch (err) {
      console.error("Error generating rules:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearRules = useCallback(() => {
    setRulesData(null);
    setError(null);
  }, []);

  return { 
    rulesData, 
    loading, 
    error,
    generateRulesForConfigurations,
    clearRules
  };
}