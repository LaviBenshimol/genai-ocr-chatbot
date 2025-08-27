#!/usr/bin/env python3
"""
Analytics Framework for Metrics Service
Provides structured analytics for Phase 1 and Phase 2 services with Plotly visualizations.
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random

try:
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError as e:
    print(f"Analytics dependencies missing: {e}")
    print("Please install: pip install pandas plotly scipy")
    # Create dummy classes to prevent import errors
    class pd:
        DataFrame = dict
        @staticmethod
        def read_sql_query(*args, **kwargs):
            return {}
        @staticmethod
        def to_datetime(*args, **kwargs):
            return None
    
    class go:
        Figure = dict
        Scatter = dict
        Bar = dict
        Pie = dict
        @staticmethod
        def add_annotation(*args, **kwargs):
            pass
    
    def make_subplots(*args, **kwargs):
        return go.Figure()

class Phase1Analytics:
    """Phase 1 (OCR/Document Intelligence) Analytics"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "metrics.db"
        self.db_path = Path(db_path)
    
    def get_phase1_data(self, hours: int = 24) -> pd.DataFrame:
        """Get Phase 1 specific data"""
        if not self.db_path.exists():
            return pd.DataFrame()
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT 
                    timestamp,
                    processing_time_seconds,
                    tokens_used,
                    success,
                    confidence_score,
                    metadata,
                    document_id
                FROM processing_events 
                WHERE (service_name LIKE '%di-service%' OR event_type = 'document_processing')
                AND timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            """.format(hours)
            
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                return df
            
            # Parse metadata
            df['metadata_parsed'] = df['metadata'].apply(
                lambda x: json.loads(x) if x else {}
            )
            
            # Extract Phase 1 specific metadata
            df['file_size_bytes'] = df['metadata_parsed'].apply(
                lambda x: x.get('file_size_bytes', 0)
            )
            df['language'] = df['metadata_parsed'].apply(
                lambda x: x.get('language', 'unknown')
            )
            df['extraction_time'] = df['metadata_parsed'].apply(
                lambda x: x.get('extraction_time', 0)
            )
            
            # Convert timestamp to proper format - SQLite default format
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            
            # Remove rows with invalid timestamps
            df = df.dropna(subset=['timestamp'])
            
            df['hour'] = df['timestamp'].dt.hour
            
            # Add document index
            df = df.reset_index(drop=True)
            df['doc_index'] = df.index + 1
            
            return df
    
    def create_dashboard(self, hours: int = 24) -> go.Figure:
        """Create Phase 1 dashboard with improved visualizations"""
        df = self.get_phase1_data(hours)
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No Phase 1 (OCR) data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            fig.update_layout(
                title="Phase 1: Document Intelligence Analytics",
                height=800
            )
            return fig
        
        # Clean data to replace None values with appropriate defaults
        df = df.fillna({
            'tokens_used': 0,
            'extraction_time': 0.0,
            'confidence_score': 0.0,
            'document_size': 0,
            'language': 'unknown'
        })
        
        # Ensure numeric columns are actually numeric
        df['tokens_used'] = pd.to_numeric(df['tokens_used'], errors='coerce').fillna(0)
        df['extraction_time'] = pd.to_numeric(df['extraction_time'], errors='coerce').fillna(0.0)
        df['confidence_score'] = pd.to_numeric(df['confidence_score'], errors='coerce').fillna(0.0)
        df['document_size'] = pd.to_numeric(df['document_size'], errors='coerce').fillna(0)
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Token Usage Across All Runs',
                'Confidence Scores by Document',
                'Processing Time vs File Size',
                'Language Distribution & Success Rate'
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # 1. Token usage across all runs
        fig.add_trace(
            go.Scatter(
                x=df['doc_index'],
                y=df['tokens_used'],
                mode='markers+lines',
                name='Token Usage',
                marker=dict(
                    size=10,
                    color=df['processing_time_seconds'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Processing Time (s)", x=0.48)
                ),
                line=dict(color='rgba(31, 119, 180, 0.3)', width=1),
                hovertemplate='<b>Doc %{x}</b><br>Tokens: %{y}<br>Time: %{marker.color:.2f}s<br>File: %{customdata}<extra></extra>',
                customdata=df['document_id']
            ),
            row=1, col=1
        )
        
        # 2. Confidence scores by document
        valid_confidence = df[df['confidence_score'] > 0]
        if not valid_confidence.empty:
            fig.add_trace(
                go.Scatter(
                    x=valid_confidence['doc_index'],
                    y=valid_confidence['confidence_score'],
                    mode='markers+lines',
                    name='Confidence Score',
                    marker=dict(
                        size=12,
                        color=valid_confidence['tokens_used'],
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title="Tokens Used", x=1.02)
                    ),
                    line=dict(color='rgba(50, 160, 50, 0.4)', width=2),
                    hovertemplate='<b>Doc %{x}</b><br>Confidence: %{y:.3f}<br>Tokens: %{marker.color}<br>Lang: %{customdata}<extra></extra>',
                    customdata=valid_confidence['language']
                ),
                row=1, col=2
            )
        
        # 3. Processing Time vs File Size
        fig.add_trace(
            go.Scatter(
                x=df['file_size_bytes'],
                y=df['processing_time_seconds'],
                mode='markers',
                name='Processing vs Size',
                marker=dict(
                    size=df['tokens_used'] / 200,
                    color=df['confidence_score'],
                    colorscale='Blues',
                    sizemode='diameter',
                    sizemin=8,
                    sizeref=2,
                    line=dict(width=1, color='white'),
                    opacity=0.8
                ),
                hovertemplate='<b>File Size:</b> %{x:,.0f} bytes<br><b>Processing Time:</b> %{y:.2f}s<br><b>Tokens:</b> %{customdata}<br><b>Confidence:</b> %{marker.color:.3f}<extra></extra>',
                customdata=df['tokens_used']
            ),
            row=2, col=1
        )
        
        # 4. Language distribution with success rate
        lang_stats = df.groupby('language').agg({
            'success': ['mean', 'count'],
            'confidence_score': 'mean',
            'tokens_used': 'mean'
        }).round(3)
        
        lang_stats.columns = ['success_rate', 'count', 'avg_confidence', 'avg_tokens']
        lang_stats = lang_stats.reset_index()
        
        # Success rate bars
        fig.add_trace(
            go.Bar(
                x=lang_stats['language'],
                y=lang_stats['success_rate'] * 100,
                name='Success Rate %',
                marker_color='lightblue',
                hovertemplate='<b>%{x}</b><br>Success: %{y:.1f}%<br>Count: %{customdata}<extra></extra>',
                customdata=lang_stats['count']
            ),
            row=2, col=2
        )
        
        # Average confidence line
        fig.add_trace(
            go.Scatter(
                x=lang_stats['language'],
                y=lang_stats['avg_confidence'] * 100,
                mode='markers+lines',
                name='Avg Confidence %',
                marker=dict(size=15, color='red', symbol='diamond'),
                line=dict(color='red', width=2),
                yaxis='y',
                hovertemplate='<b>%{x}</b><br>Avg Confidence: %{y:.1f}%<br>Avg Tokens: %{customdata}<extra></extra>',
                customdata=lang_stats['avg_tokens']
            ),
            row=2, col=2
        )
        
        # Update layout with grid lines
        fig.update_layout(
            title_text=f"Phase 1: Document Intelligence Analytics (Last {hours} hours)",
            title_x=0.5,
            height=800,
            showlegend=False,
            hovermode='closest',
            plot_bgcolor='rgba(240,240,240,0.3)'
        )
        
        # Update axes with grid lines
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
        
        # Add axis titles
        fig.update_xaxes(title_text="Document Index", row=1, col=1)
        fig.update_yaxes(title_text="Tokens Used", row=1, col=1)
        fig.update_xaxes(title_text="Document Index", row=1, col=2)
        fig.update_yaxes(title_text="Confidence Score", row=1, col=2)
        fig.update_xaxes(title_text="File Size (bytes)", row=2, col=1)
        fig.update_yaxes(title_text="Processing Time (s)", row=2, col=1)
        fig.update_xaxes(title_text="Language", row=2, col=2)
        fig.update_yaxes(title_text="Success Rate / Confidence (%)", row=2, col=2)
        
        return fig

class Phase2Analytics:
    """Phase 2 (Chat Service) Analytics"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "metrics.db"
        self.db_path = Path(db_path)
    
    def get_phase2_data(self, hours: int = 24) -> pd.DataFrame:
        """Get Phase 2 specific data"""
        if not self.db_path.exists():
            return pd.DataFrame()
        
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT 
                    timestamp,
                    processing_time_seconds,
                    tokens_used,
                    success,
                    metadata,
                    event_type,
                    service_name
                FROM processing_events 
                WHERE (service_name LIKE '%chat%' OR event_type = 'chat_processing')
                AND timestamp > datetime('now', '-{} hours')
                ORDER BY timestamp DESC
            """.format(hours)
            
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                return df
            
            # Parse metadata and extract useful fields
            def parse_metadata(metadata_str):
                try:
                    return json.loads(metadata_str) if metadata_str else {}
                except:
                    return {}
            
            df['metadata_parsed'] = df['metadata'].apply(parse_metadata)
            
            # Extract fields from metadata for easier analysis
            df['language'] = df['metadata_parsed'].apply(lambda x: x.get('language', 'unknown'))
            df['intent'] = df['metadata_parsed'].apply(lambda x: x.get('intent', 'unknown'))
            df['message_length'] = df['metadata_parsed'].apply(lambda x: x.get('message_length', 0))
            df['error_details'] = df['metadata_parsed'].apply(lambda x: x.get('error_details'))
            
            # Rename columns to match expected names
            df['response_time'] = df['processing_time_seconds']
            
            # Add conversation tracking (simple approach for now)
            df['conversation_id'] = 'conv_' + (df.index // 3 + 1).astype(str)  # Group every 3 messages as a conversation
            df['turn_number'] = (df.index % 3) + 1
            df['message'] = 'Chat message ' + df.index.astype(str)
            
            # Convert timestamp to proper format - SQLite default format
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            
            # Remove rows with invalid timestamps
            df = df.dropna(subset=['timestamp'])
            
            return df
    
    def create_dashboard(self, hours: int = 24) -> go.Figure:
        """Create Phase 2 dashboard"""
        df = self.get_phase2_data(hours)
        
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="No Phase 2 (Chat) data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=16)
            )
            fig.update_layout(
                title="Phase 2: Chat Service Analytics",
                height=800
            )
            return fig
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Token Usage Over Time',
                'Intent Distribution',
                'Processing Time vs Message Length',
                'Hourly Chat Activity'
            ),
            specs=[[{"secondary_y": False}, {"type": "domain"}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # 1. Token usage over time
        fig.add_trace(
            go.Scatter(
                x=df['chat_index'],
                y=df['tokens_used'],
                mode='markers+lines',
                name='Token Usage',
                marker=dict(
                    size=8,
                    color=df['processing_time_seconds'],
                    colorscale='Plasma',
                    showscale=True,
                    colorbar=dict(title="Processing Time (s)", x=0.48)
                ),
                line=dict(color='rgba(255, 100, 50, 0.4)', width=1),
                hovertemplate='<b>Chat %{x}</b><br>Tokens: %{y}<br>Time: %{marker.color:.2f}s<br>Intent: %{customdata}<extra></extra>',
                customdata=df['intent']
            ),
            row=1, col=1
        )
        
        # 2. Intent distribution
        if 'intent' in df.columns:
            intent_counts = df['intent'].value_counts()
            fig.add_trace(
                go.Pie(
                    labels=intent_counts.index,
                    values=intent_counts.values,
                    name="Intent Distribution",
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                ),
                row=1, col=2
            )
        
        # 3. Processing Time vs Message Length
        fig.add_trace(
            go.Scatter(
                x=df['message_length'],
                y=df['processing_time_seconds'],
                mode='markers',
                name='Processing vs Length',
                marker=dict(
                    size=df['tokens_used'] / 100,
                    color=df['response_length'],
                    colorscale='Greens',
                    sizemode='diameter',
                    sizemin=6,
                    sizeref=2,
                    line=dict(width=1, color='white'),
                    opacity=0.7
                ),
                hovertemplate='<b>Message Length:</b> %{x} chars<br><b>Processing Time:</b> %{y:.2f}s<br><b>Tokens:</b> %{customdata}<br><b>Response Length:</b> %{marker.color}<extra></extra>',
                customdata=df['tokens_used']
            ),
            row=2, col=1
        )
        
        # 4. Hourly activity
        if 'hour' in df.columns:
            hourly_stats = df.groupby('hour').agg({
                'tokens_used': 'sum',
                'processing_time_seconds': 'mean'
            }).reset_index()
            
            fig.add_trace(
                go.Bar(
                    x=hourly_stats['hour'],
                    y=hourly_stats['tokens_used'],
                    name='Hourly Tokens',
                    marker_color='lightcoral',
                    hovertemplate='<b>Hour %{x}:00</b><br>Total Tokens: %{y}<br>Avg Time: %{customdata:.2f}s<extra></extra>',
                    customdata=hourly_stats['processing_time_seconds']
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            title_text=f"Phase 2: Chat Service Analytics (Last {hours} hours)",
            title_x=0.5,
            height=800,
            showlegend=False,
            hovermode='closest',
            plot_bgcolor='rgba(240,240,240,0.3)'
        )
        
        # Update axes with grid lines
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
        
        # Add axis titles
        fig.update_xaxes(title_text="Chat Index", row=1, col=1)
        fig.update_yaxes(title_text="Tokens Used", row=1, col=1)
        fig.update_xaxes(title_text="Message Length (chars)", row=2, col=1)
        fig.update_yaxes(title_text="Processing Time (s)", row=2, col=1)
        fig.update_xaxes(title_text="Hour", row=2, col=2)
        fig.update_yaxes(title_text="Total Tokens", row=2, col=2)
        
        return fig

class AnalyticsDashboard:
    """Combined analytics dashboard"""
    
    def __init__(self, db_path: str = None):
        self.phase1_analytics = Phase1Analytics(db_path)
        self.phase2_analytics = Phase2Analytics(db_path)
    
    def get_combined_dashboard(self, hours: int = 24, phase_selection: str = "both") -> Dict[str, Any]:
        """Get combined dashboard data"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "hours": hours,
            "phase_selection": phase_selection,
            "phase1_data": None,
            "phase2_data": None,
            "phase1_figure": None,
            "phase2_figure": None
        }
        
        if phase_selection in ["phase1", "both"]:
            try:
                phase1_data = self.phase1_analytics.get_phase1_data(hours)
                result["phase1_data"] = phase1_data.to_dict('records') if hasattr(phase1_data, 'to_dict') else []
                result["phase1_summary"] = {
                    "total_documents": len(phase1_data) if hasattr(phase1_data, '__len__') else 0,
                    "avg_confidence": float(phase1_data['confidence_score'].mean()) if hasattr(phase1_data, 'mean') and not phase1_data.empty else 0.0,
                    "avg_processing_time": float(phase1_data['extraction_time'].mean()) if hasattr(phase1_data, 'mean') and not phase1_data.empty else 0.0,
                    "total_tokens": int(phase1_data['tokens_used'].sum()) if hasattr(phase1_data, 'sum') and not phase1_data.empty else 0
                }
            except Exception as e:
                result["phase1_data"] = []
                result["phase1_summary"] = {"error": f"Phase 1 data unavailable: {str(e)}"}
        
        if phase_selection in ["phase2", "both"]:
            try:
                phase2_data = self.phase2_analytics.get_phase2_data(hours)
                result["phase2_data"] = phase2_data.to_dict('records') if hasattr(phase2_data, 'to_dict') else []
                result["phase2_summary"] = {
                    "total_chats": len(phase2_data) if hasattr(phase2_data, '__len__') else 0,
                    "avg_response_time": float(phase2_data['response_time'].mean()) if hasattr(phase2_data, 'mean') and not phase2_data.empty and 'response_time' in phase2_data.columns else 0.0,
                    "total_tokens": int(phase2_data['tokens_used'].sum()) if hasattr(phase2_data, 'sum') and not phase2_data.empty and 'tokens_used' in phase2_data.columns else 0,
                    "success_rate": float(phase2_data['success'].mean() * 100) if hasattr(phase2_data, 'mean') and not phase2_data.empty and 'success' in phase2_data.columns else 0.0,
                    "unique_conversations": int(phase2_data['conversation_id'].nunique()) if 'conversation_id' in phase2_data.columns and not phase2_data.empty else 0,
                    "avg_turns_per_conv": float(len(phase2_data) / phase2_data['conversation_id'].nunique()) if 'conversation_id' in phase2_data.columns and not phase2_data.empty and phase2_data['conversation_id'].nunique() > 0 else 0.0
                }
            except Exception as e:
                result["phase2_data"] = []
                result["phase2_summary"] = {"error": f"Phase 2 data unavailable: {str(e)}"}
        
        return result