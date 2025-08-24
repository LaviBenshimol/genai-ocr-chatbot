import { useState, useEffect } from "react";

export function useServerOptions() {
  const [models, setModels] = useState([]);
  const [enrichments, setEnrichments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchOptions = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch models and enrichments in parallel
        const [modelsResponse, enrichmentsResponse] = await Promise.all([
          fetch("http://localhost:8000/models"),
          fetch("http://localhost:8000/enrichments")
        ]);

        if (!modelsResponse.ok) {
          throw new Error(`Failed to fetch models: ${modelsResponse.status}`);
        }
        
        if (!enrichmentsResponse.ok) {
          throw new Error(`Failed to fetch enrichments: ${enrichmentsResponse.status}`);
        }

        const modelsData = await modelsResponse.json();
        const enrichmentsData = await enrichmentsResponse.json();

        setModels(modelsData.models || []);
        setEnrichments(enrichmentsData.enrichments || []);
        
      } catch (err) {
        console.error("Error fetching server options:", err);
        setError(err.message);
        
        // Fallback to default values if server is not available
        setModels(["Model A", "Model B", "Model C", "Model D", "Model E"]);
        setEnrichments(["noEnrichment", "useJudge", "ruleRefine"]);
        
      } finally {
        setLoading(false);
      }
    };

    fetchOptions();
  }, []);

  const refetch = () => {
    const fetchOptions = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const [modelsResponse, enrichmentsResponse] = await Promise.all([
          fetch("http://localhost:8000/models"),
          fetch("http://localhost:8000/enrichments")
        ]);

        if (!modelsResponse.ok || !enrichmentsResponse.ok) {
          throw new Error("Failed to fetch server options");
        }

        const modelsData = await modelsResponse.json();
        const enrichmentsData = await enrichmentsResponse.json();

        setModels(modelsData.models || []);
        setEnrichments(enrichmentsData.enrichments || []);
        
      } catch (err) {
        console.error("Error refetching server options:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchOptions();
  };

  return { 
    models, 
    enrichments, 
    loading, 
    error, 
    refetch 
  };
}