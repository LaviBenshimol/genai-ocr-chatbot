"""
Simple metrics client for emitting telemetry to metrics service
"""
import requests
import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MetricsClient:
    """Simple client to emit metrics to metrics service"""
    
    def __init__(self, metrics_url: str = "http://127.0.0.1:8031"):
        self.metrics_url = metrics_url
        self.enabled = True
        
    def emit_chat_metrics(self, 
                         processing_time: float,
                         tokens_used: int,
                         message_length: int,
                         language: str,
                         intent: str = None,
                         success: bool = True,
                         error_details: str = None):
        """Emit chat processing metrics"""
        if not self.enabled:
            return
            
        try:
            metrics_data = {
                "service_name": "chat-service",
                "event_type": "chat_processing",
                "processing_time_seconds": processing_time,
                "tokens_used": tokens_used,
                "success": success,
                "metadata": {
                    "message_length": message_length,
                    "language": language,
                    "intent": intent,
                    "error_details": error_details
                }
            }
            
            response = requests.post(
                f"{self.metrics_url}/ingest",
                json=metrics_data,
                timeout=2  # Quick timeout to not block chat
            )
            
            if response.status_code != 200:
                logger.warning(f"Metrics emission failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Failed to emit metrics: {e}")
            # Don't fail the chat if metrics fail