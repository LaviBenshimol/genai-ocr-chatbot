"""
Service-Based Knowledge Base with Azure OpenAI Embeddings
Creates one chunk per service+HMO+tier combination for precise matching
"""
import os
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from config.settings import (
        AZURE_OPENAI_ENDPOINT,
        AZURE_OPENAI_API_KEY,
        AZURE_OPENAI_API_VERSION,
        AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
    )
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class ServiceBasedKB:
    """
    Service-based KB: One chunk per service+HMO+tier combination
    """
    
    def __init__(self, kb_dir: str):
        self.kb_dir = kb_dir
        self.use_embeddings = CHROMADB_AVAILABLE and AZURE_OPENAI_AVAILABLE
        
        # Storage
        self.service_chunks = []
        self.chroma_client = None
        self.collection = None
        
        # Load and process
        self._load_html_files()
        
        if self.use_embeddings:
            try:
                self._init_chromadb()
                self._populate_embeddings()
                logger.info(f"ServiceBasedKB initialized with {len(self.service_chunks)} chunks + ChromaDB")
            except Exception as e:
                logger.warning(f"ChromaDB failed: {e}")
                self.use_embeddings = False
        else:
            logger.info(f"ServiceBasedKB initialized with {len(self.service_chunks)} chunks (no embeddings)")

    def _load_html_files(self):
        """Load and chunk all HTML files"""
        if not os.path.isdir(self.kb_dir):
            return
        
        for filename in os.listdir(self.kb_dir):
            if filename.lower().endswith('.html'):
                file_path = os.path.join(self.kb_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    chunks = self._create_service_chunks(content, filename)
                    self.service_chunks.extend(chunks)
                    logger.info(f"Created {len(chunks)} service chunks from {filename}")
                    
                except Exception as e:
                    logger.error(f"Failed to process {filename}: {e}")

    def _create_service_chunks(self, html_content: str, filename: str) -> List[Dict[str, Any]]:
        """Create service-based chunks from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        chunks = []
        
        # Extract category
        category = "אחר"
        h2 = soup.find('h2')
        if h2:
            category = h2.get_text().strip()
        
        # Find the main table
        table = soup.find('table')
        if not table:
            return chunks
        
        try:
            # Get HMO names from header
            header_row = table.find('tr')
            if not header_row:
                return chunks
            
            header_cells = header_row.find_all(['th', 'td'])
            if len(header_cells) < 2:
                return chunks
            
            # HMOs are in columns 1, 2, 3 (skip first column which is service name)
            hmos = []
            for cell in header_cells[1:]:
                hmo_name = cell.get_text().strip()
                hmos.append(hmo_name)
            
            # Process each service row
            service_rows = table.find_all('tr')[1:]  # Skip header
            
            for row in service_rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                
                service_name = cells[0].get_text().strip()
                
                # Process each HMO column
                for hmo_idx, hmo_name in enumerate(hmos):
                    if hmo_idx + 1 >= len(cells):
                        continue
                    
                    hmo_cell = cells[hmo_idx + 1]
                    
                    # Extract tier benefits from this cell
                    tier_benefits = self._extract_tier_benefits(hmo_cell)
                    
                    # Create one chunk per tier
                    for tier, benefit_text in tier_benefits.items():
                        if benefit_text.strip():
                            chunk = self._create_service_chunk(
                                category, service_name, hmo_name, tier, benefit_text, filename
                            )
                            chunks.append(chunk)
        
        except Exception as e:
            logger.error(f"Failed to create service chunks from {filename}: {e}")
        
        return chunks

    def _extract_tier_benefits(self, cell) -> Dict[str, str]:
        """Extract tier-specific benefits from table cell"""
        tier_benefits = {}
        
        # Look for <strong> tags (tier names)
        strong_tags = cell.find_all('strong')
        
        for strong in strong_tags:
            tier_name = strong.get_text().strip().rstrip(':')
            
            # Collect text after this strong tag until next strong tag
            benefit_parts = []
            element = strong.next_sibling
            
            while element and not (hasattr(element, 'name') and element.name == 'strong'):
                if hasattr(element, 'get_text'):
                    text = element.get_text().strip()
                elif isinstance(element, str):
                    text = element.strip()
                else:
                    text = str(element).strip()
                
                # Clean up text
                if text and text not in [',', '\n', '<br>', '<br/>', '\\n']:
                    benefit_parts.append(text)
                
                element = element.next_sibling
            
            # Join and clean benefit text
            benefit_text = ' '.join(benefit_parts).strip()
            benefit_text = benefit_text.lstrip(',').strip()
            
            if benefit_text:
                tier_benefits[tier_name] = benefit_text
        
        return tier_benefits

    def _create_service_chunk(self, category: str, service: str, hmo: str, tier: str, benefit: str, filename: str) -> Dict[str, Any]:
        """Create a single service chunk"""
        # Create unique ID
        chunk_id = f"{filename}_{service}_{hmo}_{tier}".replace(' ', '_').replace(':', '').replace('"', '')
        
        # Create content optimized for embedding
        content = f"""קטגוריה: {category}
שירות: {service}  
קופת חולים: {hmo}
מסלול: {tier}
הטבה: {benefit}
מילות מפתח: {category} {service} {hmo} {tier} ביטוח בריאות הטבות"""
        
        return {
            'id': chunk_id,
            'category': category,
            'service': service,
            'hmo': hmo,
            'tier': tier,
            'benefit': benefit,
            'content': content,
            'metadata': {
                'filename': filename,
                'category': category,
                'service': service,
                'hmo': hmo,
                'tier': tier,
                'type': 'service_benefit'
            }
        }

    def _init_chromadb(self):
        """Initialize persistent ChromaDB"""
        # Create persistent storage directory
        persist_dir = os.path.join(self.kb_dir, "..", "chromadb_storage")
        os.makedirs(persist_dir, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        
        collection_name = "service_based_kb"
        try:
            self.collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"Found existing ChromaDB collection with {self.collection.count()} documents")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new ChromaDB collection")

    def _populate_embeddings(self):
        """Populate ChromaDB with service chunks"""
        if not self.collection or not self.service_chunks:
            return
        
        # Check if collection already has data
        current_count = self.collection.count()
        if current_count > 0:
            logger.info(f"ChromaDB already has {current_count} documents, skipping population")
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for chunk in self.service_chunks:
            documents.append(chunk['content'])
            metadatas.append(chunk['metadata'])
            ids.append(chunk['id'])
        
        # Process in batches
        batch_size = 10
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            try:
                # Generate embeddings
                embeddings = self._generate_embeddings(batch_docs)
                
                # Add to ChromaDB
                self.collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids,
                    embeddings=embeddings
                )
                
                logger.info(f"Added batch {i//batch_size + 1}/{total_batches}")
                
            except Exception as e:
                logger.error(f"Failed to add batch {i//batch_size + 1}: {e}")

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Azure OpenAI"""
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        
        embeddings = []
        for text in texts:
            response = client.embeddings.create(
                model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
                input=text
            )
            embeddings.append(response.data[0].embedding)
        
        return embeddings

    def retrieve(self, message: str, profile: Dict[str, Any], language: str = "he", max_chars: int = 3500) -> Dict[str, Any]:
        """Retrieve top 3 service chunks"""
        if self.use_embeddings:
            return self._retrieve_with_embeddings(message, profile, max_chars)
        else:
            return self._retrieve_fallback(message, profile, max_chars)

    def _retrieve_with_embeddings(self, message: str, profile: Dict[str, Any], max_chars: int) -> Dict[str, Any]:
        """Retrieve using ChromaDB semantic search"""
        if not self.collection:
            return self._empty_result("no_collection")
        
        try:
            # Enhance query with profile
            enhanced_query = self._enhance_query_with_profile(message, profile)
            
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[enhanced_query],
                n_results=15,  # Get more to filter and rank
                include=['documents', 'metadatas', 'distances']
            )
            
            return self._process_results(results, profile, max_chars, "semantic")
            
        except Exception as e:
            logger.error(f"ChromaDB query failed: {e}")
            return self._retrieve_fallback(message, profile, max_chars)

    def _enhance_query_with_profile(self, message: str, profile: Dict[str, Any]) -> str:
        """Enhance query with profile context"""
        query_parts = [message]
        
        if profile.get('hmo'):
            query_parts.append(profile['hmo'])
        
        if profile.get('tier'):
            query_parts.append(profile['tier'])
        
        # Add age context
        age = profile.get('age')
        if age:
            if age < 18:
                query_parts.append("ילדים נוער")
            elif age > 65:
                query_parts.append("מבוגרים קשישים")
        
        return " ".join(query_parts)

    def _process_results(self, results, profile: Dict[str, Any], max_chars: int, method: str) -> Dict[str, Any]:
        """Process ChromaDB results and return top 3"""
        if not results['documents'] or not results['documents'][0]:
            return self._empty_result(f"{method}_no_results")
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0] or []
        distances = results['distances'][0] if results['distances'] else []
        
        # Score and rank results
        scored_results = []
        
        for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances)):
            if not metadata:
                continue
            
            # Calculate scores
            semantic_score = 1 - distance if distance is not None else 0
            profile_score = self._calculate_profile_match(metadata, profile)
            final_score = (semantic_score * 0.6) + (profile_score * 0.4)
            
            # Find original chunk
            original_chunk = self._find_chunk_by_id(metadata.get('filename', '') + '_' + 
                                                   metadata.get('service', '') + '_' + 
                                                   metadata.get('hmo', '') + '_' + 
                                                   metadata.get('tier', ''))
            
            if original_chunk:
                scored_results.append({
                    'chunk': original_chunk,
                    'metadata': metadata,
                    'semantic_score': semantic_score,
                    'profile_score': profile_score,
                    'final_score': final_score
                })
        
        # Sort by final score and take top 3
        scored_results.sort(key=lambda x: x['final_score'], reverse=True)
        top_3 = scored_results[:3]
        
        # Convert to expected format
        snippets = []
        citations = []
        total_chars = 0
        
        for result in top_3:
            chunk = result['chunk']
            benefit_text = chunk['benefit']
            
            if total_chars + len(benefit_text) <= max_chars:
                snippets.append({
                    "category": chunk['category'],
                    "service": chunk['service'],
                    "fund": chunk['hmo'],
                    "plan": chunk['tier'],
                    "text": benefit_text,
                    "source_file": chunk['metadata']['filename'],
                    "semantic_score": result['semantic_score'],
                    "profile_score": result['profile_score'],
                    "final_score": result['final_score']
                })
                
                citations.append({
                    "source_file": chunk['metadata']['filename'],
                    "category": chunk['category'],
                    "service": chunk['service'],
                    "fund": chunk['hmo'],
                    "plan": chunk['tier']
                })
                
                total_chars += len(benefit_text)
        
        return {
            "snippets": snippets,
            "citations": citations,
            "context_chars": total_chars,
            "snippets_chars": total_chars,
            "search_method": method,
            "total_candidates": len(scored_results)
        }

    def _calculate_profile_match(self, metadata: Dict[str, Any], profile: Dict[str, Any]) -> float:
        """Calculate profile match score"""
        score = 0.0
        
        # HMO exact match
        if profile.get('hmo') and metadata.get('hmo'):
            if profile['hmo'] == metadata['hmo']:
                score += 0.5
        
        # Tier exact match  
        if profile.get('tier') and metadata.get('tier'):
            if profile['tier'] == metadata['tier']:
                score += 0.3
        
        # Age relevance (basic)
        age = profile.get('age')
        if age and metadata.get('service'):
            service = metadata['service'].lower()
            if age < 18 and 'ילדים' in service:
                score += 0.2
            elif age > 65 and any(word in service for word in ['מבוגרים', 'זקנה']):
                score += 0.2
        
        return min(score, 1.0)

    def _find_chunk_by_id(self, partial_id: str) -> Optional[Dict[str, Any]]:
        """Find chunk by partial ID matching"""
        partial_id_clean = partial_id.replace(' ', '_').replace(':', '').replace('"', '')
        
        for chunk in self.service_chunks:
            if partial_id_clean in chunk['id']:
                return chunk
        return None

    def _retrieve_fallback(self, message: str, profile: Dict[str, Any], max_chars: int) -> Dict[str, Any]:
        """Fallback retrieval using keyword matching"""
        msg_lower = message.lower()
        relevant_chunks = []
        
        for chunk in self.service_chunks:
            score = 0
            content_lower = chunk['content'].lower()
            
            # Keyword matching
            query_words = msg_lower.split()
            for word in query_words:
                if len(word) > 2 and word in content_lower:
                    score += 1
            
            # Profile matching
            if profile.get('hmo') and chunk['hmo'] == profile['hmo']:
                score += 3
            if profile.get('tier') and chunk['tier'] == profile['tier']:
                score += 2
            
            if score > 0:
                relevant_chunks.append((score, chunk))
        
        # Sort and take top 3
        relevant_chunks.sort(key=lambda x: x[0], reverse=True)
        top_3 = relevant_chunks[:3]
        
        snippets = []
        citations = []
        total_chars = 0
        
        for score, chunk in top_3:
            benefit_text = chunk['benefit']
            if total_chars + len(benefit_text) <= max_chars:
                snippets.append({
                    "category": chunk['category'],
                    "service": chunk['service'],
                    "fund": chunk['hmo'],
                    "plan": chunk['tier'],
                    "text": benefit_text,
                    "source_file": chunk['metadata']['filename'],
                    "fallback_score": score
                })
                
                citations.append({
                    "source_file": chunk['metadata']['filename'],
                    "category": chunk['category'],
                    "service": chunk['service'],
                    "fund": chunk['hmo'],
                    "plan": chunk['tier']
                })
                
                total_chars += len(benefit_text)
        
        return {
            "snippets": snippets,
            "citations": citations,
            "context_chars": total_chars,
            "snippets_chars": total_chars,
            "search_method": "fallback"
        }

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        """Return empty result with reason"""
        return {
            "snippets": [],
            "citations": [],
            "context_chars": 0,
            "snippets_chars": 0,
            "search_method": f"empty_{reason}"
        }

    @property
    def by_category(self):
        """Compatibility property for existing code"""
        result = {}
        for chunk in self.service_chunks:
            category = chunk['category']
            hmo = chunk['hmo']
            service = chunk['service']
            
            if category not in result:
                result[category] = {}
            if hmo not in result[category]:
                result[category][hmo] = {}
            if service not in result[category][hmo]:
                result[category][hmo][service] = []
            
            result[category][hmo][service].append({
                'plan': chunk['tier'],
                'details': chunk['benefit'],
                'source_file': chunk['metadata']['filename']
            })
        
        return result