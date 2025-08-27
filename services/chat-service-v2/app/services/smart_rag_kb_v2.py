#!/usr/bin/env python3
"""
Enhanced Smart RAG Knowledge Base V2 for healthcare insurance
- Uses existing ChromaDB data  
- Improved fallback logic
- Better category and service management
- Enhanced retrieval with fallback to all benefits
"""
import os
import json
from typing import Dict, List, Any, Optional, Set
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
    print("⚠️ Chroma not available, using fallback mode")

logger = logging.getLogger(__name__)

class SmartRAGHealthKBV2:
    """
    Enhanced Smart RAG Knowledge Base V2 that:
    1. Uses existing ChromaDB data
    2. Provides better fallback mechanisms  
    3. Enhanced service scope detection
    4. Improved retrieval with all-benefits fallback
    """
    
    def __init__(self, kb_dir: str, chromadb_dir: str, use_embeddings: bool = True):
        self.kb_dir = kb_dir
        self.chromadb_dir = chromadb_dir
        self.use_embeddings = use_embeddings and CHROMA_AVAILABLE
        
        # Traditional structured KB (always available)
        self.by_category = {}
        self.services_by_category = {}
        self.all_services = []
        
        # Chroma collection
        self.chroma_client = None
        self.collection = None
        
        # Initialize
        self._load_traditional_kb()
        if self.use_embeddings:
            self._connect_to_existing_chromadb()
        
        logger.info(f"SmartRAGHealthKBV2 initialized: categories={len(self.by_category)}, "
                   f"services={len(self.all_services)}, embeddings={self.use_embeddings}")
    
    def _load_traditional_kb(self):
        """Load traditional structured KB from HTML files"""
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
        """Parse HTML using enhanced traditional method"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract category from content - improved logic
        category = self._extract_category_from_content(content)
        if not category:
            # Fallback to filename parsing with better mapping
            name_mapping = {
                'dentel_services': 'מרפאות שיניים',  # Fix typo in filename
                'dental_services': 'מרפאות שיניים', 
                'optometry_services': 'אופטומטריה',
                'alternative_services': 'רפואה משלימה',
                'pregnancy_services': 'שירותי הריון',
                'pragrency_services': 'שירותי הריון',  # Fix typo
                'communication_clinic_services': 'מרפאות תקשורת',
                'workshops_services': 'סדנאות'
            }
            base_name = filename.replace('.html', '')
            category = name_mapping.get(base_name, base_name.replace('_', ' '))
        
        if category not in self.by_category:
            self.by_category[category] = {}
            self.services_by_category[category] = set()
        
        # Parse services and benefits - enhanced parsing
        self._parse_services_from_html(soup, category)
        
        logger.info(f"Parsed {filename}: category='{category}', services={len(self.services_by_category.get(category, []))}")
    
    def _extract_category_from_content(self, content: str) -> str:
        """Extract category from HTML content with improved patterns"""
        # Look for Hebrew category indicators
        hebrew_patterns = {
            r'אופטומטר|עיניים|ראייה|משקפיים': 'אופטומטריה',
            r'שיניים|דנטל|סתימות|כתרים': 'מרפאות שיניים',
            r'רפואה משלימה|דיקור|הומיאופתיה': 'רפואה משלימה', 
            r'הריון|לידה|יולדת|הנקה': 'שירותי הריון',
            r'תקשורת|דיבור|שמיעה|לוגופד': 'מרפאות תקשורת',
            r'סדנא|סדנה|קורס|הרצאה': 'סדנאות'
        }
        
        for pattern, category in hebrew_patterns.items():
            if re.search(pattern, content):
                return category
                
        return ""
    
    def _parse_services_from_html(self, soup: BeautifulSoup, category: str):
        """Parse services from HTML tables and text"""
        
        services_found = set()
        
        # Strategy 1: Parse HTML tables (main structure)
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            headers = []
            
            # Get headers (usually first row)
            if rows:
                header_row = rows[0]
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
                
                # Process data rows
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:  # Need at least service name + one HMO
                        service_name = cells[0].get_text(strip=True)
                        if service_name and service_name not in ['שם השירות', '']:
                            services_found.add(service_name)
                            
                            # Process each HMO column
                            for i, cell in enumerate(cells[1:], 1):
                                hmo = headers[i] if i < len(headers) else f'HMO_{i}'
                                benefit_text = cell.get_text(strip=True)
                                
                                if benefit_text:
                                    # Parse tier information from benefit text
                                    tiers = self._parse_tier_benefits(benefit_text)
                                    
                                    for tier, tier_benefit in tiers.items():
                                        # Initialize nested structure
                                        if hmo not in self.by_category[category]:
                                            self.by_category[category][hmo] = {}
                                        if tier not in self.by_category[category][hmo]:
                                            self.by_category[category][hmo][tier] = []
                                        
                                        service_info = {
                                            'service': service_name,
                                            'hmo': hmo,
                                            'tier': tier,
                                            'benefit': tier_benefit,
                                            'content': f"{service_name} - {hmo} {tier}: {tier_benefit}"
                                        }
                                        self.by_category[category][hmo][tier].append(service_info)
        
        # Strategy 2: Parse list items for additional info
        list_items = soup.find_all(['li'])
        for item in list_items:
            text = item.get_text(strip=True)
            if text and ':' in text:
                # Extract service name from list items like "בדיקות וניקוי שיניים: בדיקות תקופתיות"
                parts = text.split(':', 1)
                if len(parts) == 2:
                    service_name = parts[0].strip()
                    description = parts[1].strip()
                    services_found.add(service_name)
                    
                    # Add as general service
                    hmo = 'כללי'
                    tier = 'כללי'
                    if hmo not in self.by_category[category]:
                        self.by_category[category][hmo] = {}
                    if tier not in self.by_category[category][hmo]:
                        self.by_category[category][hmo][tier] = []
                    
                    service_info = {
                        'service': service_name,
                        'hmo': hmo,
                        'tier': tier,
                        'benefit': description,
                        'content': text
                    }
                    self.by_category[category][hmo][tier].append(service_info)
        
        # Update services tracking
        self.services_by_category[category].update(services_found)
        self.all_services.extend(services_found)
    
    def _parse_tier_benefits(self, benefit_text: str) -> Dict[str, str]:
        """Parse tier benefits from cell text like 'זהב: xxx כסף: yyy ארד: zzz'"""
        tiers = {}
        
        # Look for tier patterns
        tier_patterns = {
            'זהב': r'זהב:\s*([^<\n]*?)(?=(?:כסף:|ארד:|$))',
            'כסף': r'כסף:\s*([^<\n]*?)(?=(?:זהב:|ארד:|$))',
            'ארד': r'ארד:\s*([^<\n]*?)(?=(?:זהב:|כסף:|$))'
        }
        
        for tier_name, pattern in tier_patterns.items():
            matches = re.findall(pattern, benefit_text, re.IGNORECASE | re.DOTALL)
            if matches:
                # Clean up the match (remove HTML tags, extra whitespace)
                benefit = re.sub(r'<[^>]+>', ' ', matches[0]).strip()
                benefit = ' '.join(benefit.split())  # Normalize whitespace
                if benefit:
                    tiers[tier_name] = benefit
        
        # If no specific tiers found, use the whole text as 'כללי'
        if not tiers:
            clean_text = re.sub(r'<[^>]+>', ' ', benefit_text).strip()
            clean_text = ' '.join(clean_text.split())
            if clean_text:
                tiers['כללי'] = clean_text
        
        return tiers
    
    def _extract_service_info(self, text: str) -> Optional[Dict[str, str]]:
        """Extract service information from text with improved parsing"""
        
        # Look for key patterns
        service_patterns = [
            r'שירות:\s*([^\n\r]+)',
            r'טיפול:\s*([^\n\r]+)', 
            r'בדיקה:\s*([^\n\r]+)',
            r'קטגוריה:\s*([^\n\r]+)'
        ]
        
        hmo_patterns = [
            r'קופת חולים:\s*(מכבי|מאוחדת|כללית)',
            r'(מכבי|מאוחדת|כללית)'
        ]
        
        tier_patterns = [
            r'מסלול:\s*(זהב|כסף|ארד)',
            r'(זהב|כסף|ארד)'
        ]
        
        benefit_patterns = [
            r'הטבה:\s*([^\n\r]+)',
            r'כיסוי:\s*([^\n\r]+)',
            r'תשלום:\s*([^\n\r]+)'
        ]
        
        # Extract information
        info = {}
        
        # Extract service name
        for pattern in service_patterns:
            match = re.search(pattern, text)
            if match:
                info['service'] = match.group(1).strip()
                break
        
        # Extract HMO
        for pattern in hmo_patterns:
            match = re.search(pattern, text)
            if match:
                info['hmo'] = match.group(1).strip()
                break
                
        # Extract tier
        for pattern in tier_patterns:
            match = re.search(pattern, text)
            if match:
                info['tier'] = match.group(1).strip()
                break
                
        # Extract benefit
        for pattern in benefit_patterns:
            match = re.search(pattern, text)
            if match:
                info['benefit'] = match.group(1).strip()
                break
        
        # If we found at least a service or benefit, it's valid
        if 'service' in info or 'benefit' in info:
            # Fill in defaults
            info.setdefault('service', 'שירות כללי')
            info.setdefault('hmo', 'כללי')
            info.setdefault('tier', 'כללי') 
            info.setdefault('benefit', text[:100])  # Use original text as benefit
            info['content'] = text  # Store full content
            return info
            
        return None
    
    def _connect_to_existing_chromadb(self):
        """Connect to existing ChromaDB data or create if empty/invalid"""
        try:
            if not os.path.exists(self.chromadb_dir):
                logger.info(f"ChromaDB directory not found, creating: {self.chromadb_dir}")
                os.makedirs(self.chromadb_dir, exist_ok=True)
            
            # Connect to persistent ChromaDB
            self.chroma_client = chromadb.PersistentClient(
                path=self.chromadb_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Try to get existing collection
            collections = self.chroma_client.list_collections()
            logger.info(f"Found {len(collections)} ChromaDB collections")
            
            # Check if we have a valid collection with data
            if collections:
                self.collection = collections[0]
                count = self.collection.count()
                logger.info(f"Connected to ChromaDB collection '{self.collection.name}' with {count} documents")
                
                # If collection is empty, populate it
                if count == 0:
                    logger.info("Collection is empty, populating with data...")
                    self._populate_chromadb()
            else:
                logger.info("No ChromaDB collections found, creating and populating...")
                self._populate_chromadb()
                
        except Exception as e:
            logger.warning(f"Failed to connect to ChromaDB: {e}")
            # Try to recreate from scratch
            try:
                logger.info("Attempting to recreate ChromaDB from scratch...")
                import shutil
                if os.path.exists(self.chromadb_dir):
                    shutil.rmtree(self.chromadb_dir)
                os.makedirs(self.chromadb_dir, exist_ok=True)
                
                self.chroma_client = chromadb.PersistentClient(
                    path=self.chromadb_dir,
                    settings=Settings(anonymized_telemetry=False)
                )
                self._populate_chromadb()
            except Exception as e2:
                logger.error(f"Failed to recreate ChromaDB: {e2}")
                self.use_embeddings = False
    
    def _populate_chromadb(self):
        """Populate ChromaDB with data from HTML files"""
        try:
            # Create collection
            collection_name = "health_kb_v2"
            try:
                self.collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "Medical services knowledge base"}
                )
                logger.info(f"Created ChromaDB collection: {collection_name}")
            except Exception as e:
                # Collection might already exist, try to get it
                if "already exists" in str(e):
                    self.collection = self.chroma_client.get_collection(collection_name)
                    logger.info(f"Using existing collection: {collection_name}")
                else:
                    raise e
            
            # Process HTML files and create embeddings
            documents = []
            metadatas = []
            ids = []
            
            doc_id = 0
            for category, hmos in self.by_category.items():
                for hmo, tiers in hmos.items():
                    for tier, services in tiers.items():
                        for service in services:
                            # Create document text
                            doc_text = f"קטגוריה: {category}\n"
                            doc_text += f"שירות: {service.get('service', 'לא מוגדר')}\n"
                            doc_text += f"קופת חולים: {service.get('hmo', hmo)}\n"
                            doc_text += f"מסלול: {service.get('tier', tier)}\n"
                            doc_text += f"הטבה: {service.get('benefit', 'לא מוגדר')}\n"
                            if 'content' in service:
                                doc_text += f"תוכן: {service['content']}\n"
                            
                            # Create metadata
                            metadata = {
                                "category": category,
                                "service": service.get('service', ''),
                                "fund": service.get('hmo', hmo),
                                "plan": service.get('tier', tier),
                                "source_file": f"{category}_services.html"
                            }
                            
                            documents.append(doc_text)
                            metadatas.append(metadata)
                            ids.append(f"doc_{doc_id}")
                            doc_id += 1
            
            if documents:
                # Add documents to collection in batches
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
                
                final_count = self.collection.count()
                logger.info(f"Successfully populated ChromaDB with {final_count} documents")
                self.use_embeddings = True
            else:
                logger.warning("No documents to add to ChromaDB")
                self.use_embeddings = False
                
        except Exception as e:
            logger.error(f"Failed to populate ChromaDB: {e}")
            self.use_embeddings = False
    
    def get_available_categories(self) -> Set[str]:
        """Get all available service categories"""
        return set(self.by_category.keys())
    
    def get_services_in_category(self, category: str) -> List[str]:
        """Get all services in a specific category"""
        return list(self.services_by_category.get(category, []))
    
    def get_total_services_count(self) -> int:
        """Get total number of unique services"""
        return len(set(self.all_services))
    
    def retrieve_enhanced(
        self, 
        message: str, 
        category: str,
        profile: Dict[str, Any], 
        language: str = "he",
        max_chars: int = 4000,
        fallback_to_all: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced retrieval with fallback logic
        
        Strategy:
        1. Try specific HMO + tier match first
        2. Try category-wide search with embeddings  
        3. If no specific match and fallback_to_all=True, return all benefits for category
        4. Traditional keyword fallback
        """
        
        logger.info(f"Enhanced retrieval: category='{category}', profile={profile}, fallback={fallback_to_all}")
        
        # Try embeddings first if available
        if self.use_embeddings and self.collection:
            try:
                embedding_result = self._retrieve_with_embeddings(message, category, profile, max_chars)
                if embedding_result.get("snippets"):
                    logger.info(f"Embeddings retrieval successful: {len(embedding_result['snippets'])} snippets")
                    return embedding_result
            except Exception as e:
                logger.warning(f"Embeddings retrieval failed: {e}")
        
        # Fallback to traditional with enhanced logic
        return self._retrieve_traditional_enhanced(message, category, profile, max_chars, fallback_to_all)
    
    def _retrieve_with_embeddings(
        self, 
        message: str, 
        category: str, 
        profile: Dict[str, Any], 
        max_chars: int
    ) -> Dict[str, Any]:
        """Retrieve using ChromaDB embeddings with profile awareness"""
        
        # Build enhanced query
        hmo = profile.get('hmo', '')
        tier = profile.get('tier', '')
        
        enhanced_query = message
        if hmo:
            enhanced_query += f" {hmo}"
        if tier:
            enhanced_query += f" {tier}"
        if category and category != "אחר":
            enhanced_query += f" {category}"
        
        # Query ChromaDB
        results = self.collection.query(
            query_texts=[enhanced_query],
            n_results=min(10, max_chars // 200),  # Estimate docs needed
            where={"category": category} if category != "אחר" else None
        )
        
        snippets = []
        citations = []
        total_chars = 0
        
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                if total_chars >= max_chars:
                    break
                    
                # Parse document metadata
                metadata = results.get('metadatas', [[]])[0]
                doc_meta = metadata[i] if i < len(metadata) else {}
                
                snippet = {
                    "content": doc[:500],  # Limit snippet size
                    "metadata": doc_meta
                }
                snippets.append(snippet)
                
                # Create citation
                citation = {
                    "source_file": doc_meta.get("source_file", "unknown"),
                    "category": doc_meta.get("category", category),
                    "service": doc_meta.get("service", ""),
                    "fund": doc_meta.get("fund", ""),
                    "plan": doc_meta.get("plan", "")
                }
                citations.append(citation)
                
                total_chars += len(doc)
        
        return {
            "snippets": snippets,
            "citations": citations,
            "context_chars": total_chars,
            "snippets_chars": sum(len(s["content"]) for s in snippets),
            "method": "embeddings",
            "fallback_used": False
        }
    
    def _retrieve_traditional_enhanced(
        self, 
        message: str, 
        category: str, 
        profile: Dict[str, Any], 
        max_chars: int,
        fallback_to_all: bool
    ) -> Dict[str, Any]:
        """Enhanced traditional retrieval with better fallback logic"""
        
        hmo = profile.get('hmo', '')
        tier = profile.get('tier', '')
        
        snippets = []
        citations = []
        fallback_used = False
        
        # Strategy 1: Exact profile match
        if category in self.by_category and hmo and tier:
            if hmo in self.by_category[category] and tier in self.by_category[category][hmo]:
                services = self.by_category[category][hmo][tier]
                snippets.extend(self._create_snippets_from_services(services, category, hmo, tier))
                logger.info(f"Exact match found: {len(services)} services for {hmo} {tier}")
        
        # Strategy 2: Category match with any HMO/tier  
        if not snippets and category in self.by_category:
            all_services = []
            for hmo_name, tiers in self.by_category[category].items():
                for tier_name, services in tiers.items():
                    all_services.extend(services)
            
            if all_services:
                snippets.extend(self._create_snippets_from_services(all_services[:5], category, "כללי", "כללי"))
                logger.info(f"Category match: {len(all_services)} services found")
        
        # Strategy 3: Keyword matching across all categories
        if not snippets:
            keyword_results = self._keyword_search_enhanced(message, max_chars)
            snippets.extend(keyword_results)
            logger.info(f"Keyword search: {len(keyword_results)} results")
        
        # Strategy 4: Fallback to all benefits in category if requested
        if not snippets and fallback_to_all and category in self.by_category:
            logger.info(f"Using fallback - returning all benefits for category: {category}")
            all_category_services = []
            for hmo_name, tiers in self.by_category[category].items():
                for tier_name, services in tiers.items():
                    all_category_services.extend(services)
            
            if all_category_services:
                snippets.extend(self._create_snippets_from_services(all_category_services, category, "כללי", "כללי"))
                fallback_used = True
        
        # Create citations from snippets
        for snippet in snippets:
            metadata = snippet.get("metadata", {})
            citation = {
                "source_file": metadata.get("source_file", f"{category}_services.html"),
                "category": metadata.get("category", category),
                "service": metadata.get("service", ""),
                "fund": metadata.get("fund", hmo),
                "plan": metadata.get("plan", tier)
            }
            citations.append(citation)
        
        total_chars = sum(len(s["content"]) for s in snippets)
        
        return {
            "snippets": snippets,
            "citations": citations,
            "context_chars": total_chars,
            "snippets_chars": total_chars,
            "method": "traditional_enhanced",
            "fallback_used": fallback_used
        }
    
    def _create_snippets_from_services(
        self, 
        services: List[Dict[str, str]], 
        category: str, 
        hmo: str, 
        tier: str
    ) -> List[Dict[str, Any]]:
        """Create snippets from service data"""
        snippets = []
        
        for service in services:
            content = f"קטגוריה: {category}\\n"
            content += f"שירות: {service.get('service', 'לא מוגדר')}\\n"
            content += f"קופת חולים: {service.get('hmo', hmo)}\\n"
            content += f"מסלול: {service.get('tier', tier)}\\n"
            content += f"הטבה: {service.get('benefit', 'לא מוגדר')}\\n"
            
            snippet = {
                "content": content,
                "metadata": {
                    "category": category,
                    "service": service.get('service', ''),
                    "fund": service.get('hmo', hmo),
                    "plan": service.get('tier', tier),
                    "source_file": f"{category}_services.html"
                }
            }
            snippets.append(snippet)
        
        return snippets
    
    def _keyword_search_enhanced(self, message: str, max_chars: int) -> List[Dict[str, Any]]:
        """Enhanced keyword search across all data"""
        
        message_words = set(re.findall(r'\\b\\w+\\b', message.lower()))
        results = []
        
        for category, hmos in self.by_category.items():
            for hmo, tiers in hmos.items():
                for tier, services in tiers.items():
                    for service in services:
                        # Score based on keyword matches
                        content = service.get('content', '')
                        service_name = service.get('service', '')
                        benefit = service.get('benefit', '')
                        
                        search_text = f"{content} {service_name} {benefit}".lower()
                        content_words = set(re.findall(r'\\b\\w+\\b', search_text))
                        
                        # Calculate match score
                        matches = message_words.intersection(content_words)
                        score = len(matches)
                        
                        if score > 0:
                            snippet = {
                                "content": f"קטגוריה: {category}\\nשירות: {service_name}\\nהטבה: {benefit}",
                                "metadata": {
                                    "category": category,
                                    "service": service_name,
                                    "fund": hmo,
                                    "plan": tier,
                                    "score": score,
                                    "source_file": f"{category}_services.html"
                                }
                            }
                            results.append(snippet)
        
        # Sort by score and return top results
        results.sort(key=lambda x: x["metadata"].get("score", 0), reverse=True)
        return results[:5]  # Top 5 results
    
    # Legacy method for compatibility
    def retrieve(self, message: str, profile: Dict[str, Any], language: str = "he", max_chars: int = 3500) -> Dict[str, Any]:
        """Legacy retrieve method for backward compatibility"""
        # Try to detect category from message for legacy calls
        category = "אחר"
        for cat in self.by_category:
            if cat in message:
                category = cat
                break
        
        return self.retrieve_enhanced(message, category, profile, language, max_chars, fallback_to_all=True)
