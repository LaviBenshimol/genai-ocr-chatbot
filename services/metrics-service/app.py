"""
Metrics Service: SQLite WAL-based analytics aggregation microservice.
Collects telemetry from all other services and provides analytics endpoints.
"""
import sqlite3
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
import traceback

# Import analytics framework
from analytics_framework import AnalyticsDashboard, Phase1Analytics, Phase2Analytics

app = Flask(__name__)
CORS(app)

# Database setup
DB_PATH = Path(__file__).parent / "data" / "metrics.db"
DB_PATH.parent.mkdir(exist_ok=True)

class MetricsStorage:
    """SQLite WAL storage for metrics aggregation."""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with WAL mode."""
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for concurrent reads/writes
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            
            # Create tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    document_id TEXT,
                    processing_time_seconds REAL,
                    confidence_score REAL,
                    tokens_used INTEGER,
                    cost_estimate REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS service_health (
                    service_name TEXT PRIMARY KEY,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'healthy',
                    instance_count INTEGER DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON processing_events(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_service 
                ON processing_events(service_name, timestamp)
            """)
            
            conn.commit()
    
    def ingest_event(self, event_data: Dict[str, Any]) -> bool:
        """Store a telemetry event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO processing_events (
                        service_name, event_type, document_id, processing_time_seconds,
                        confidence_score, tokens_used, cost_estimate, success,
                        error_message, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_data.get('service_name'),
                    event_data.get('event_type', 'processing'),
                    event_data.get('document_id'),
                    event_data.get('processing_time_seconds'),
                    event_data.get('confidence_score'),
                    event_data.get('tokens_used'),
                    event_data.get('cost_estimate'),
                    event_data.get('success', True),
                    event_data.get('error_message'),
                    json.dumps(event_data.get('metadata', {}))
                ))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to ingest event: {e}")
            return False
    
    def update_service_health(self, service_name: str, status: str = 'healthy') -> bool:
        """Update service health status."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO service_health (service_name, status, last_seen)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (service_name, status))
                conn.commit()
            return True
        except Exception as e:
            print(f"Failed to update service health: {e}")
            return False
    
    def get_confidence_distribution(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get confidence score distribution."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT confidence_score
                    FROM processing_events
                    WHERE confidence_score IS NOT NULL
                      AND timestamp > datetime('now', '-{} hours')
                      AND success = 1
                """.format(hours))
                
                scores = [row[0] for row in cursor.fetchall()]
                
                if not scores:
                    return []
                
                # Create distribution bins
                bins = [
                    {"range": "0.0-0.7", "min": 0.0, "max": 0.7, "count": 0},
                    {"range": "0.7-0.85", "min": 0.7, "max": 0.85, "count": 0},
                    {"range": "0.85-1.0", "min": 0.85, "max": 1.0, "count": 0}
                ]
                
                for score in scores:
                    for bin_data in bins:
                        if bin_data["min"] <= score < bin_data["max"] or (bin_data["max"] == 1.0 and score == 1.0):
                            bin_data["count"] += 1
                            break
                
                total = len(scores)
                for bin_data in bins:
                    bin_data["percentage"] = round((bin_data["count"] / total) * 100, 1) if total > 0 else 0
                
                return bins
        except Exception as e:
            print(f"Failed to get confidence distribution: {e}")
            return []
    
    def get_processing_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get processing time trends."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        strftime('%H', timestamp) as hour,
                        AVG(processing_time_seconds) as avg_time,
                        COUNT(*) as count,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as errors
                    FROM processing_events
                    WHERE timestamp > datetime('now', '-{} hours')
                      AND processing_time_seconds IS NOT NULL
                    GROUP BY strftime('%H', timestamp)
                    ORDER BY hour
                """.format(hours))
                
                trends = []
                for row in cursor.fetchall():
                    trends.append({
                        "hour": int(row[0]),
                        "avg_processing_time": round(row[1], 2) if row[1] else 0,
                        "document_count": row[2],
                        "error_count": row[3],
                        "error_rate": round((row[3] / row[2]) * 100, 1) if row[2] > 0 else 0
                    })
                
                return {"trends": trends}
        except Exception as e:
            print(f"Failed to get processing trends: {e}")
            return {"trends": []}
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current aggregate metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Overall stats
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_docs,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_docs,
                        AVG(CASE WHEN success = 1 THEN processing_time_seconds END) as avg_time,
                        AVG(CASE WHEN success = 1 THEN confidence_score END) as avg_confidence,
                        SUM(tokens_used) as total_tokens,
                        SUM(cost_estimate) as total_cost
                    FROM processing_events
                    WHERE timestamp > datetime('now', '-24 hours')
                """)
                
                row = cursor.fetchone()
                total_docs = row[0] or 0
                successful_docs = row[1] or 0
                
                metrics = {
                    "total_documents": total_docs,
                    "successful_documents": successful_docs,
                    "success_rate": round((successful_docs / total_docs) * 100, 1) if total_docs > 0 else 100,
                    "avg_processing_time": round(row[2], 2) if row[2] else 0,
                    "avg_confidence_score": round(row[3], 3) if row[3] else 0,
                    "total_tokens_used": row[4] or 0,
                    "estimated_cost": round(row[5], 4) if row[5] else 0
                }
                
                # Service health
                cursor = conn.execute("""
                    SELECT service_name, status, last_seen
                    FROM service_health
                    ORDER BY service_name
                """)
                
                services = []
                for row in cursor.fetchall():
                    services.append({
                        "service": row[0],
                        "status": row[1],
                        "last_seen": row[2]
                    })
                
                metrics["services"] = services
                return metrics
        except Exception as e:
            print(f"Failed to get current metrics: {e}")
            return {"error": str(e)}

# Initialize storage and analytics
storage = MetricsStorage()
analytics_dashboard = AnalyticsDashboard()
phase1_analytics = Phase1Analytics()  
phase2_analytics = Phase2Analytics()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "metrics-service"}), 200

@app.route('/ingest', methods=['POST'])
def ingest_telemetry():
    """Ingest telemetry events from other services."""
    try:
        event_data = request.get_json()
        if not event_data:
            return jsonify({"error": "No event data provided"}), 400
        
        success = storage.ingest_event(event_data)
        if success:
            return jsonify({"message": "Event ingested successfully"}), 200
        else:
            return jsonify({"error": "Failed to store event"}), 500
            
    except Exception as e:
        print(f"Ingest error: {e}")
        return jsonify({"error": "Failed to process event", "details": str(e)}), 500

@app.route('/analytics/confidence', methods=['GET'])
def get_confidence_analytics():
    """Get confidence score distribution."""
    try:
        hours = int(request.args.get('hours', 24))
        distribution = storage.get_confidence_distribution(hours)
        return jsonify({"confidence_distribution": distribution}), 200
    except Exception as e:
        print(f"Confidence analytics error: {e}")
        return jsonify({"error": "Failed to get confidence analytics", "details": str(e)}), 500

@app.route('/analytics/trends', methods=['GET'])
def get_trends_analytics():
    """Get processing trends."""
    try:
        hours = int(request.args.get('hours', 24))
        trends = storage.get_processing_trends(hours)
        return jsonify(trends), 200
    except Exception as e:
        print(f"Trends analytics error: {e}")
        return jsonify({"error": "Failed to get trends analytics", "details": str(e)}), 500

@app.route('/metrics', methods=['GET'])
def get_current_metrics():
    """Get current aggregate metrics."""
    try:
        metrics = storage.get_current_metrics()
        return jsonify(metrics), 200
    except Exception as e:
        print(f"Current metrics error: {e}")
        return jsonify({"error": "Failed to get current metrics", "details": str(e)}), 500

@app.route('/dashboard/combined', methods=['GET'])
def get_combined_dashboard():
    """Get combined Phase 1 and Phase 2 dashboard data."""
    try:
        hours = int(request.args.get('hours', 24))
        phase_selection = request.args.get('phase', 'both')  # phase1, phase2, both
        
        dashboard_data = analytics_dashboard.get_combined_dashboard(hours, phase_selection)
        return jsonify(dashboard_data), 200
    except Exception as e:
        import traceback
        print(f"Combined dashboard error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        # Return empty dashboard data instead of error
        return jsonify({
            "phase1_data": {"summary": {"total_processing_events": 0}},
            "phase2_data": {"summary": {"total_chat_events": 0}},
            "error": f"Dashboard temporarily unavailable: {str(e)}"
        }), 200

@app.route('/dashboard/phase1', methods=['GET'])
def get_phase1_dashboard():
    """Get Phase 1 (OCR) specific dashboard data."""
    try:
        hours = int(request.args.get('hours', 24))
        format_type = request.args.get('format', 'data')  # data, figure, both
        
        result = {}
        
        if format_type in ['data', 'both']:
            phase1_data = phase1_analytics.get_phase1_data(hours)
            result['data'] = phase1_data.to_dict('records') if not phase1_data.empty else []
            result['summary'] = {
                'total_documents': len(phase1_data),
                'avg_confidence': float(phase1_data['confidence_score'].mean()) if not phase1_data.empty and phase1_data['confidence_score'].mean() > 0 else 0,
                'avg_processing_time': float(phase1_data['processing_time_seconds'].mean()) if not phase1_data.empty else 0,
                'total_tokens': int(phase1_data['tokens_used'].sum()) if not phase1_data.empty else 0
            }
        
        if format_type in ['figure', 'both']:
            phase1_figure = phase1_analytics.create_dashboard(hours)
            result['figure'] = phase1_figure.to_dict()
        
        result['hours'] = hours
        result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(result), 200
    except Exception as e:
        print(f"Phase 1 dashboard error: {e}")
        return jsonify({"error": "Failed to get Phase 1 dashboard", "details": str(e)}), 500

@app.route('/dashboard/phase2', methods=['GET'])
def get_phase2_dashboard():
    """Get Phase 2 (Chat) specific dashboard data."""
    try:
        hours = int(request.args.get('hours', 24))
        format_type = request.args.get('format', 'data')  # data, figure, both
        
        result = {}
        
        if format_type in ['data', 'both']:
            phase2_data = phase2_analytics.get_phase2_data(hours)
            result['data'] = phase2_data.to_dict('records') if not phase2_data.empty else []
            result['summary'] = {
                'total_interactions': len(phase2_data),
                'avg_processing_time': float(phase2_data['processing_time_seconds'].mean()) if not phase2_data.empty else 0,
                'total_tokens': int(phase2_data['tokens_used'].sum()) if not phase2_data.empty else 0,
                'unique_intents': len(phase2_data['intent'].unique()) if not phase2_data.empty and 'intent' in phase2_data else 0
            }
        
        if format_type in ['figure', 'both']:
            phase2_figure = phase2_analytics.create_dashboard(hours)
            result['figure'] = phase2_figure.to_dict()
        
        result['hours'] = hours
        result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(result), 200
    except Exception as e:
        print(f"Phase 2 dashboard error: {e}")
        return jsonify({"error": "Failed to get Phase 2 dashboard", "details": str(e)}), 500

@app.route('/dashboard/scenarios', methods=['POST'])
def run_test_scenarios():
    """Run debug scenarios and store results."""
    try:
        scenarios_data = request.get_json()
        if not scenarios_data:
            return jsonify({"error": "No scenarios data provided"}), 400
        
        results = []
        for scenario in scenarios_data.get('scenarios', []):
            # Process each scenario and store metrics
            scenario_name = scenario.get('name', 'unknown')
            turns = scenario.get('turns', [])
            
            for turn_idx, turn in enumerate(turns):
                # Create a metrics entry for this turn
                metrics_event = {
                    'service_name': 'chat-service-v2',
                    'event_type': 'scenario_test',
                    'processing_time_seconds': turn.get('processing_time', 0),
                    'tokens_used': turn.get('tokens_used', 0),
                    'success': turn.get('success', True),
                    'metadata': {
                        'scenario_name': scenario_name,
                        'turn_index': turn_idx,
                        'message_length': len(turn.get('message', '')),
                        'intent': turn.get('intent', 'unknown'),
                        'language': turn.get('language', 'he'),
                        'phase': 'phase2_chat'
                    }
                }
                
                storage.ingest_event(metrics_event)
                results.append({
                    'scenario': scenario_name,
                    'turn': turn_idx,
                    'status': 'recorded'
                })
        
        return jsonify({"message": "Scenarios recorded", "results": results}), 200
    except Exception as e:
        print(f"Scenarios error: {e}")
        return jsonify({"error": "Failed to process scenarios", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8031))
    
    print(f"Starting Metrics Service on port {port}")
    print("Endpoints: /health, /ingest, /analytics/confidence, /analytics/trends, /metrics")
    print("Dashboard APIs: /dashboard/combined, /dashboard/phase1, /dashboard/phase2, /dashboard/scenarios")
    print(f"Database: {DB_PATH} (WAL mode)")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )