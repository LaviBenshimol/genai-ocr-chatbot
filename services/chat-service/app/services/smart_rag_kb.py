#!/usr/bin/env python3
"""
Smart RAG Knowledge Base using Chroma for healthcare insurance
Combines traditional parsing with semantic embeddings for better retrieval
"""
import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from bs4 import BeautifulSoup
import re

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("⚠️ Chroma not available. Install with: pip install chromadb")

try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False
    print("⚠️ Azure OpenAI not available")

logger = logging.getLogger(__name__)

class SmartRAGHealthKB:
    """
    Smart RAG Knowledge Base that combines:
    1. Traditional structured parsing (fallback)
    2. Chroma vector embeddings (primary)
    3. Query augmentation with user profile
    4. Multi-modal document preprocessing
    """
    
    def __init__(self, kb_dir: str, use_embeddings: bool = True):
        self.kb_dir = kb_dir
        self.use_embeddings = use_embeddings and CHROMA_AVAILABLE
        
        # Traditional structured KB (fallback)
        self.by_category = {}
        
        # Chroma collection
        self.chroma_client = None
        self.collection = None
        
        # Initialize both systems
        self._load_traditional_kb()
        if self.use_embeddings:
            self._initialize_chroma()
        
        logger.info(f"SmartRAGHealthKB initialized: traditional={len(self.by_category)} categories, embeddings={self.use_embeddings}")
    
    def _load_traditional_kb(self):
        """Load traditional structured KB as fallback"""
        try:
            html_files = list(Path(self.kb_dir).glob("*.html"))
            logger.info(f"Loading {len(html_files)} HTML files for traditional KB")
            
            for html_file in html_files:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._parse_html_traditional(content, html_file.name)
                
        except Exception as e:
            logger.error(f"Failed to load traditional KB: {e}")
    
    def _parse_html_traditional(self, content: str, filename: str):
        """Parse HTML using traditional method (from original ChatHealthKB)"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract category from content
        category = self._extract_category_from_content(content)
        if not category:
            category = filename.replace('_services.html', '').replace('_', ' ')
        
        # Parse content into structured format
        # (Simplified version - you can expand this)
        funds_data = self._extract_funds_data(soup, filename)
        
        if category not in self.by_category:
            self.by_category[category] = {}
        
        for fund, services in funds_data.items():
            if fund not in self.by_category[category]:
                self.by_category[category][fund] = {}
            self.by_category[category][fund].update(services)
    
    def _extract_category_from_content(self, content: str) -> Optional[str]:
        """Extract category from HTML content"""
        category_mapping = {
            'optometry': 'אופטומטריה',
            'dental': 'מרפאות שיניים',
            'alternative': 'רפואה משלימה',
            'pregnancy': 'שירותי הריון',
            'communication': 'מרפאות תקשורת',
            'workshops': 'סדנאות'
        }
        
        content_lower = content.lower()
        for eng, heb in category_mapping.items():
            if eng in content_lower:
                return heb
        
        return None
    
    def _extract_funds_data(self, soup: BeautifulSoup, filename: str) -> Dict[str, Dict]:
        """Extract funds data from HTML soup"""
        # Simplified extraction - you can make this more sophisticated
        funds = {'מכבי': {}, 'מאוחדת': {}, 'כללית': {}}
        
        # Extract text content and create basic services
        text_content = soup.get_text()
        
        # Create basic service entries
        service_name = filename.replace('_services.html', '').replace('_', ' ')
        
        for fund in funds.keys():
            funds[fund][service_name] = [{
                'plan': 'זהב',
                'details': text_content[:500],  # First 500 chars
                'source_file': filename
            }]
        
        return funds
    
    def _initialize_chroma(self):
        """Initialize Chroma vector database"""
        if not CHROMA_AVAILABLE:
            logger.warning("Chroma not available, falling back to traditional KB")
            return
        
        try:
            # Initialize Chroma client
            self.chroma_client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=os.path.join(self.kb_dir, ".chroma_db")
            ))
            
            # Get or create collection
            collection_name = "healthcare_insurance_kb"
            try:
                self.collection = self.chroma_client.get_collection(collection_name)
                logger.info(f"Loaded existing Chroma collection: {self.collection.count()} documents")
            except:
                self.collection = self.chroma_client.create_collection(collection_name)
                self._populate_chroma_collection()
                logger.info(f"Created new Chroma collection: {self.collection.count()} documents")
                
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            self.use_embeddings = False
    
    def _populate_chroma_collection(self):
        """Populate Chroma with preprocessed documents"""
        if not self.collection:
            return
        
        documents = []
        metadatas = []
        ids = []
        
        try:
            html_files = list(Path(self.kb_dir).glob("*.html"))
            
            for html_file in html_files:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Smart preprocessing
                chunks = self._preprocess_document_smart(content, html_file.name)
                
                for i, chunk in enumerate(chunks):
                    doc_id = f"{html_file.stem}_{i}"
                    documents.append(chunk['text'])
                    metadatas.append(chunk['metadata'])
                    ids.append(doc_id)
            
            if documents:
                # Add to Chroma in batches
                batch_size = 100
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i+batch_size]
                    batch_metas = metadatas[i:i+batch_size]
                    batch_ids = ids[i:i+batch_size]
                    
                    self.collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                
                logger.info(f"Added {len(documents)} documents to Chroma")
                
        except Exception as e:
            logger.error(f"Failed to populate Chroma: {e}")
    
    def _preprocess_document_smart(self, html_content: str, filename: str) -> List[Dict]:
        """Smart preprocessing of HTML documents into enhanced chunks"""
        chunks = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract category
            category = self._extract_category_from_content(html_content)
            if not category:
                category = filename.replace('_services.html', '').replace('_', ' ')
            
            # Extract services and benefits
            services = self._extract_services_smart(soup)
            
            # Create enhanced chunks
            for service in services:
                chunk_text = f"""
קטגוריה: {category}
שירות: {service['name']}
תיאור: {service['description']}
הטבות: {service.get('benefits', '')}
תהליך: {service.get('process', '')}
זכאות: {service.get('eligibility', '')}
מילות מפתח: {' '.join(service.get('keywords', []))}
""".strip()
                
                chunk = {
                    'text': chunk_text,
                    'metadata': {
                        'category': category,
                        'service_name': service['name'],
                        'filename': filename,
                        'keywords': service.get('keywords', [])
                    }
                }
                chunks.append(chunk)
        
        except Exception as e:
            logger.error(f"Failed to preprocess {filename}: {e}")
            # Fallback to simple text extraction
            text = BeautifulSoup(html_content, 'html.parser').get_text()
            chunks.append({
                'text': text[:1000],  # First 1000 chars
                'metadata': {
                    'category': filename.replace('_services.html', ''),
                    'filename': filename,
                    'keywords': []
                }
            })
        
        return chunks
    
    def _extract_services_smart(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract services from HTML with smart parsing"""
        services = []
        
        # Look for structured content (tables, lists, etc.)
        tables = soup.find_all('table')
        lists = soup.find_all(['ul', 'ol'])
        
        # Extract from tables
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    service_name = cells[0].get_text().strip()
                    description = cells[1].get_text().strip()
                    
                    services.append({
                        'name': service_name,
                        'description': description,
                        'keywords': [service_name.lower()]
                    })
        
        # Extract from lists
        for lst in lists:
            items = lst.find_all('li')
            for item in items:
                text = item.get_text().strip()
                if ':' in text:
                    name, desc = text.split(':', 1)
                    services.append({
                        'name': name.strip(),
                        'description': desc.strip(),
                        'keywords': [name.strip().lower()]
                    })
        
        # If no structured content, extract from paragraphs
        if not services:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50:  # Meaningful content
                    services.append({
                        'name': text[:50] + '...',
                        'description': text,
                        'keywords': text.lower().split()[:5]
                    })
        
        return services
    
    def _augment_query_with_profile(self, query: str, profile: Dict[str, Any]) -> str:
        """Augment user query with profile context for better embedding matching"""
        augmented = query
        
        # Add HMO context
        if profile.get('hmo'):
            augmented = f"{profile['hmo']} {augmented}"
        
        # Add tier context
        if profile.get('tier'):
            augmented = f"{profile['tier']} {augmented}"
        
        # Add general healthcare context
        augmented += " הטבות כיסוי ביטוח בריאות"
        
        return augmented
    
    def retrieve(self, message: str, profile: Dict[str, Any], language: str = "he", max_chars: int = 3500) -> Dict[str, Any]:
        """
        Smart retrieval using both embeddings and traditional fallback
        """
        
        # Try embedding-based retrieval first
        if self.use_embeddings and self.collection:
            try:
                result = self._retrieve_with_embeddings(message, profile, max_chars)
                if result.get('snippets'):
                    logger.info(f"Embedding retrieval successful: {len(result['snippets'])} snippets")
                    return result
            except Exception as e:
                logger.error(f"Embedding retrieval failed: {e}")
        
        # Fallback to traditional retrieval
        logger.info("Using traditional retrieval as fallback")
        return self._retrieve_traditional(message, profile, language, max_chars)
    
    def _retrieve_with_embeddings(self, message: str, profile: Dict[str, Any], max_chars: int) -> Dict[str, Any]:
        """Retrieve using Chroma embeddings"""
        if not self.collection:
            return {'snippets': [], 'citations': [], 'context_chars': 0, 'snippets_chars': 0}
        
        # Augment query with profile
        augmented_query = self._augment_query_with_profile(message, profile)
        
        # Query Chroma
        results = self.collection.query(
            query_texts=[augmented_query],
            n_results=10,  # Get top 10 results
            include=['documents', 'metadatas', 'distances']
        )
        
        snippets = []
        citations = []
        total_chars = 0
        
        if results['documents'] and results['documents'][0]:
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]
            
            for doc, metadata, distance in zip(documents, metadatas, distances):
                # Filter by relevance (distance threshold)
                if distance > 0.8:  # Skip very irrelevant results
                    continue
                
                # Filter by profile if specified
                if profile.get('hmo') and 'hmo' in metadata:
                    if metadata['hmo'] != profile['hmo']:
                        continue
                
                chunk_text = doc
                if total_chars + len(chunk_text) > max_chars:
                    chunk_text = chunk_text[:max_chars - total_chars]
                
                snippet = {
                    'category': metadata.get('category', 'אחר'),
                    'service': metadata.get('service_name', 'שירות כללי'),
                    'fund': profile.get('hmo', 'כללי'),
                    'plan': profile.get('tier', 'כללי'),
                    'text': chunk_text,
                    'source_file': metadata.get('filename', 'unknown'),
                    'relevance_score': 1.0 - distance  # Convert distance to relevance
                }
                
                citation = {
                    'source_file': metadata.get('filename', 'unknown'),
                    'category': metadata.get('category', 'אחר'),
                    'service': metadata.get('service_name', 'שירות כללי'),
                    'fund': profile.get('hmo', 'כללי'),
                    'plan': profile.get('tier', 'כללי')
                }
                
                snippets.append(snippet)
                citations.append(citation)
                total_chars += len(chunk_text)
                
                if total_chars >= max_chars:
                    break
        
        return {
            'snippets': snippets,
            'citations': citations,
            'context_chars': total_chars,
            'snippets_chars': total_chars
        }
    
    def _retrieve_traditional(self, message: str, profile: Dict[str, Any], language: str, max_chars: int) -> Dict[str, Any]:
        """Traditional retrieval method (from original ChatHealthKB)"""
        snippets = []
        citations = []
        total_chars = 0
        
        hmo = profile.get("hmo", "").strip()
        tier = profile.get("tier", "").strip()
        
        # Simple keyword matching for categories
        category_keywords = {
            'אופטומטריה': ['עיניים', 'אופטומטריה', 'משקפיים', 'עדשות', 'ראייה'],
            'מרפאות שיניים': ['שיניים', 'דנטלי', 'ניקוי', 'סתימות'],
            'רפואה משלימה': ['דיקור', 'הומיאופתיה', 'רפואה משלימה'],
            'שירותי הריון': ['הריון', 'לידה', 'הנקה'],
            'מרפאות תקשורת': ['דיבור', 'שמיעה', 'תקשורת'],
            'סדנאות': ['סדנה', 'הרצאה', 'קורס']
        }
        
        matched_categories = []
        message_lower = message.lower()
        
        for category, keywords in category_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                matched_categories.append(category)
        
        # If no matches, search all categories
        if not matched_categories:
            matched_categories = list(self.by_category.keys())
        
        # Retrieve from matched categories
        for category in matched_categories:
            if category not in self.by_category:
                continue
                
            funds = self.by_category[category]
            fund_keys = [hmo] if hmo in funds else list(funds.keys())
            
            for fund in fund_keys:
                if fund not in funds:
                    continue
                    
                services = funds[fund]
                for service_name, plans in services.items():
                    for entry in plans:
                        if tier and entry.get("plan") != tier:
                            continue
                        
                        text = entry.get("details", "")
                        if total_chars + len(text) > max_chars:
                            continue
                        
                        snippet = {
                            "category": category,
                            "service": service_name,
                            "fund": fund,
                            "plan": entry.get("plan"),
                            "text": text,
                            "source_file": entry.get("source_file", "")
                        }
                        
                        citation = {
                            "source_file": entry.get("source_file", ""),
                            "category": category,
                            "service": service_name,
                            "fund": fund,
                            "plan": entry.get("plan")
                        }
                        
                        snippets.append(snippet)
                        citations.append(citation)
                        total_chars += len(text)
                        
                        if total_chars >= max_chars:
                            break
                    
                    if total_chars >= max_chars:
                        break
                        
                if total_chars >= max_chars:
                    break
                    
            if total_chars >= max_chars:
                break
        
        return {
            'snippets': snippets,
            'citations': citations,
            'context_chars': total_chars,
            'snippets_chars': total_chars
        }

# Factory function for backward compatibility
def create_kb(kb_dir: str, use_rag: bool = True) -> SmartRAGHealthKB:
    """Create a SmartRAGHealthKB instance"""
    return SmartRAGHealthKB(kb_dir, use_embeddings=use_rag)
