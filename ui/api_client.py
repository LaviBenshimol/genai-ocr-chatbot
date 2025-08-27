"""
API Client for microservices communication.
Handles calls to health-form-di-service and metrics-service.
"""
import requests
import streamlit as st
from typing import Dict, Any, Optional
import time

class MicroserviceClient:
    """Client for communicating with microservices."""
    
    def __init__(self, base_url: str = "http://localhost"):
        self.base_url = base_url
        # Direct service URLs for development
        self.health_form_service_url = f"{base_url}:8001"
        self.metrics_service_url = f"{base_url}:8031"
        self.chat_service_url = f"{base_url}:5000"
        # V2 Chat service (if different port)
        self.chat_service_v2_url = f"{base_url}:5002"
        
    def process_document(self, file_bytes: bytes, filename: str, language: str = "auto") -> Dict[str, Any]:
        """
        Process document using health-form-di-service.
        """
        try:
            files = {'file': (filename, file_bytes, 'application/pdf')}
            data = {'language': language}
            
            response = requests.post(
                f"{self.health_form_service_url}/process",
                files=files,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error",
                    "error": f"Service returned status {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "Request timeout",
                "details": "The service took too long to respond"
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error", 
                "error": "Connection failed",
                "details": "Could not connect to health-form-di-service. Make sure it's running on port 8001."
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "Unexpected error",
                "details": str(e)
            }
    
    def chat_turn(self, message: str, user_profile: Dict[str, Any], 
                  conversation_history: list, language: str = "he") -> Dict[str, Any]:
        """
        Send a chat message to the chat-service.
        """
        try:
            payload = {
                "message": message,
                "user_profile": user_profile,
                "conversation_history": conversation_history,
                "language": language
            }
            
            response = requests.post(
                f"{self.chat_service_url}/v1/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"Service returned status {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "details": "The chat service took too long to respond"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection failed",
                "details": "Could not connect to chat-service. Make sure it's running on port 8000."
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Unexpected error",
                "details": str(e)
            }

    def chat_turn_v2(self, message: str, user_profile: Dict[str, Any], 
                     conversation_history: list, language: str = "he") -> Dict[str, Any]:
        """
        Send a chat message to the v2 chat-service.
        """
        try:
            payload = {
                "message": message,
                "user_profile": user_profile,
                "conversation_history": conversation_history,
                "language": language
            }
            
            response = requests.post(
                f"{self.chat_service_v2_url}/v2/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"V2 Service returned status {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "details": "The v2 chat service took too long to respond"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection failed",
                "details": "Could not connect to v2 chat-service. Make sure it's running on port 5002."
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Unexpected error",
                "details": str(e)
            }

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics from metrics service."""
        try:
            response = requests.get(
                f"{self.metrics_service_url}/metrics",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Metrics service error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Failed to get metrics: {str(e)}"}
    
    def get_confidence_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get confidence distribution analytics."""
        try:
            response = requests.get(
                f"{self.metrics_service_url}/analytics/confidence",
                params={"hours": hours},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Analytics service error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Failed to get confidence analytics: {str(e)}"}
    
    def get_trends_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get processing trends analytics."""
        try:
            response = requests.get(
                f"{self.metrics_service_url}/analytics/trends",
                params={"hours": hours},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Trends service error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Failed to get trends analytics: {str(e)}"}
    
    def get_dashboard_data(self, hours: int = 24, phase: str = "both", format_type: str = "data") -> Dict[str, Any]:
        """Get dashboard data from metrics service."""
        try:
            response = requests.get(
                f"{self.metrics_service_url}/dashboard/combined",
                params={"hours": hours, "phase": phase},
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Dashboard service error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Failed to get dashboard data: {str(e)}"}
    
    def get_phase1_dashboard(self, hours: int = 24, format_type: str = "data") -> Dict[str, Any]:
        """Get Phase 1 specific dashboard data."""
        try:
            response = requests.get(
                f"{self.metrics_service_url}/dashboard/phase1",
                params={"hours": hours, "format": format_type},
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Phase 1 dashboard error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Failed to get Phase 1 dashboard: {str(e)}"}
    
    def get_phase2_dashboard(self, hours: int = 24, format_type: str = "data") -> Dict[str, Any]:
        """Get Phase 2 specific dashboard data."""
        try:
            response = requests.get(
                f"{self.metrics_service_url}/dashboard/phase2",
                params={"hours": hours, "format": format_type},
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Phase 2 dashboard error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Failed to get Phase 2 dashboard: {str(e)}"}
    
    def submit_test_scenarios(self, scenarios: list) -> Dict[str, Any]:
        """Submit test scenarios to metrics service for recording."""
        try:
            payload = {"scenarios": scenarios}
            
            response = requests.post(
                f"{self.metrics_service_url}/dashboard/scenarios",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Scenarios submission error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Failed to submit scenarios: {str(e)}"}
    
    def check_services_health(self) -> Dict[str, str]:
        """Check health of all microservices."""
        health_status = {}
        
        # Check health-form-di-service
        try:
            response = requests.get(f"{self.health_form_service_url}/health", timeout=5)
            if response.status_code == 200:
                health_status["health-form-di-service"] = "healthy"
            else:
                health_status["health-form-di-service"] = f"error: {response.status_code}"
        except Exception as e:
            health_status["health-form-di-service"] = f"offline: {str(e)}"
        
        # Check metrics service
        try:
            response = requests.get(f"{self.metrics_service_url}/health", timeout=5)
            if response.status_code == 200:
                health_status["metrics-service"] = "healthy"
            else:
                health_status["metrics-service"] = f"error: {response.status_code}"
        except Exception as e:
            health_status["metrics-service"] = f"offline: {str(e)}"
        
        # Check chat-service
        try:
            response = requests.get(f"{self.chat_service_url}/health", timeout=5)
            if response.status_code == 200:
                health_status["chat-service"] = "healthy"
            else:
                health_status["chat-service"] = f"error: {response.status_code}"
        except Exception as e:
            health_status["chat-service"] = f"offline: {str(e)}"
        
        # Check chat-service v2
        try:
            response = requests.get(f"{self.chat_service_v2_url}/health", timeout=5)
            if response.status_code == 200:
                health_status["chat-service-v2"] = "healthy"
            else:
                health_status["chat-service-v2"] = f"error: {response.status_code}"
        except Exception as e:
            health_status["chat-service-v2"] = f"offline: {str(e)}"
        
        # Check ChromaDB status (through V2 chat service info endpoint)
        try:
            # Try V2 service first
            response = requests.get(f"{self.chat_service_v2_url}/v2/info", timeout=5)
            if response.status_code == 200:
                info_data = response.json()
                if info_data.get('embeddings_enabled'):
                    health_status["chromadb"] = "320+ chunks loaded"
                else:
                    health_status["chromadb"] = "embeddings disabled"
            else:
                # Fallback to V1
                response = requests.get(f"{self.chat_service_url}/health", timeout=5)
                if response.status_code == 200:
                    health_status["chromadb"] = "legacy mode"
                else:
                    health_status["chromadb"] = "unknown"
        except Exception as e:
            health_status["chromadb"] = "offline"
        
        return health_status