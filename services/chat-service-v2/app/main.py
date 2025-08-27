"""
Chat Service V2 (Phase 2) - Improved KB-backed chat endpoint.

Enhanced Features:
1. Uses SmartRAGHealthKB with existing ChromaDB data
2. Improved three-stage extraction with service descriptions
3. Better fallback logic - shows all benefits if specific match not found
4. Polite information collection flow
5. Enhanced retrieval logic

Endpoint: POST /v2/chat

Request JSON schema:
{
  "message": "str (user text)",
  "language": "he|en",
  "user_profile": {
    "fullName": "str",
    "idNumber": "str(9)",
    "gender": "str",
    "age": "int(0-120)",
    "hmo": "מכבי|מאוחדת|כללית",
    "hmoCardNumber": "str(9)",
    "tier": "זהב|כסף|ארד"
  },
  "conversation_history": [{"role": "user|assistant", "content": "str"}]
}

Response JSON schema:
{
  "intent": "collection|qa|other",
  "answer_type": "general_description|specific_benefits|all_benefits_fallback|eligibility|cost_coverage|process_steps|other",
  "updated_profile": { ... },
  "known_fields": { ... },
  "missing_fields": [ ... ],
  "sufficient_context": true|false,
  "action": "collect|answer|clarify",
  "next_question": "str",
  "answer": "str (optional)",
  "citations": [{"source_file": "...", "category": "...", "service": "...", "fund": "...", "plan": "..."}],
  "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
  "context_metrics": {"kb_context_chars": 0, "snippets_chars": 0},
  "disclaimer": "str (optional)",
  "request_id": "str",
  "language": "he|en",
  "service_scope": "in_scope|out_of_scope|partial_scope",
  "available_services": ["list of services in the requested category"]
}
"""
import os
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Local imports - copy the services we need
from .services.three_stage_extractor_v2 import three_stage_process_v2
from .services.grounded_answerer_v2 import generate_grounded_answer_v2, format_kb_context_for_llm
from .services.smart_rag_kb_v2 import SmartRAGHealthKBV2
from .services.metrics_client import MetricsClient

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    # Initialize KB at startup using existing ChromaDB data
    kb_dir = os.environ.get("KNOWLEDGE_BASE_DIR") or os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "phase2_data"
    )
    chromadb_dir = os.environ.get("CHROMADB_DIR") or os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "chromadb_storage"
    )
    
    # Normalize paths
    kb_dir = os.path.abspath(kb_dir)
    chromadb_dir = os.path.abspath(chromadb_dir)
    
    # Use SmartRAGHealthKBV2 with existing ChromaDB data
    logger.info(f"Initializing SmartRAGHealthKBV2 from: {kb_dir}")
    logger.info(f"ChromaDB data: {chromadb_dir}")
    app.kb = SmartRAGHealthKBV2(kb_dir, chromadb_dir, use_embeddings=True)
    
    # Initialize metrics client
    app.metrics = MetricsClient()
    
    # Debug KB loading
    logger.info(f"KB V2 initialized successfully")
    logger.info(f"Categories available: {list(app.kb.get_available_categories())}")
    logger.info(f"Total services: {app.kb.get_total_services_count()}")
    logger.info(f"Embeddings enabled: {app.kb.use_embeddings}")

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "service": "chat-service-v2"}), 200
    
    @app.route("/v2/info", methods=["GET"])
    def service_info():
        """Get information about available services and categories"""
        categories = app.kb.get_available_categories()
        services_by_category = {}
        
        for category in categories:
            services_by_category[category] = app.kb.get_services_in_category(category)
        
        return jsonify({
            "version": "2.0",
            "categories": list(categories),
            "services_by_category": services_by_category,
            "total_services": app.kb.get_total_services_count(),
            "embeddings_enabled": app.kb.use_embeddings
        }), 200

    @app.route("/v2/chat", methods=["POST"])
    def chat_turn_v2():
        start = time.time()
        req = request.get_json(force=True, silent=True) or {}
        message = req.get("message", "").strip()
        language = req.get("language", "he").strip() or "he"
        user_profile = req.get("user_profile", {}) or {}
        history = req.get("conversation_history", []) or []

        if not message:
            return jsonify({"error": "message is required"}), 400

        try:
            # Run enhanced 3-stage pipeline
            logger.info(f"=== V2 PIPELINE INPUT ===")
            logger.info(f"Message: {message}")
            logger.info(f"User profile: {user_profile}")
            logger.info(f"Language: {language}")
            
            # Get available services for context
            available_categories = app.kb.get_available_categories()
            available_services = {}
            for cat in available_categories:
                available_services[cat] = app.kb.get_services_in_category(cat)
            
            pipeline_result = three_stage_process_v2(
                message=message,
                user_profile=user_profile,
                conversation_history=history,
                language=language,
                available_services=available_services
            )
            
            logger.info(f"=== V2 PIPELINE OUTPUT ===")
            logger.info(f"Classification: {pipeline_result.get('classification', {})}")
            logger.info(f"Requirements: {pipeline_result.get('requirements', {})}")
            logger.info(f"Service scope: {pipeline_result.get('service_scope', 'unknown')}")

            # Extract results from enhanced pipeline
            updated_profile = pipeline_result.get("updated_profile", {})
            classification = pipeline_result.get("classification", {})
            requirements = pipeline_result.get("requirements", {})
            service_scope = pipeline_result.get("service_scope", "unknown")
            
            category = classification.get("category", "אחר")
            intent = classification.get("intent", "other")
            action = requirements.get("action", "collect_info")
            
            logger.info(f"=== V2 DECISION ===")
            logger.info(f"Category: '{category}', Intent: '{intent}', Action: '{action}'")
            logger.info(f"Service scope: '{service_scope}'")
            logger.info(f"Profile: HMO='{updated_profile.get('hmo')}', Tier='{updated_profile.get('tier')}'")
            
            # Initialize response structure
            answer = ""
            citations = []
            token_usage = pipeline_result.get("token_usage", {})
            context_metrics = {"kb_context_chars": 0, "snippets_chars": 0}
            available_services_list = available_services.get(category, [])
            
            if action == "retrieve_answer":
                # Enhanced KB retrieval with fallback logic
                logger.info(f"=== V2 KB RETRIEVAL ===")
                logger.info(f"Category: {category}, Profile: {updated_profile}")
                
                retrieval = app.kb.retrieve_enhanced(
                    message=message,
                    category=category,
                    profile=updated_profile,
                    language=language,
                    max_chars=4000,
                    fallback_to_all=True  # If specific benefits not found, show all
                )
                
                logger.info(f"V2 retrieval: context_chars={retrieval.get('context_chars', 0)}, "
                          f"snippets={len(retrieval.get('snippets', []))}, "
                          f"fallback_used={retrieval.get('fallback_used', False)}")
                
                context_metrics["kb_context_chars"] = retrieval.get("context_chars", 0)
                context_metrics["snippets_chars"] = retrieval.get("snippets_chars", 0)
                citations = retrieval.get("citations", [])
                
                # Determine answer type based on retrieval
                answer_type = intent
                if retrieval.get("fallback_used"):
                    answer_type = "all_benefits_fallback"
                
                # Generate enhanced answer
                if retrieval.get("snippets"):
                    kb_context = format_kb_context_for_llm(retrieval["snippets"])
                    
                    answer_result = generate_grounded_answer_v2(
                        user_question=message,
                        user_profile=updated_profile,
                        kb_context=kb_context,
                        conversation_history=history,
                        language=language,
                        answer_type=answer_type,
                        category=category,
                        fallback_used=retrieval.get("fallback_used", False),
                        max_tokens=1200
                    )
                    
                    answer = answer_result.get("answer", "")
                    
                    # Merge token usage
                    au = answer_result.get("token_usage", {})
                    token_usage = {
                        "prompt_tokens": token_usage.get("prompt_tokens", 0) + au.get("prompt_tokens", 0),
                        "completion_tokens": token_usage.get("completion_tokens", 0) + au.get("completion_tokens", 0),
                        "total_tokens": token_usage.get("total_tokens", 0) + au.get("total_tokens", 0),
                    }
                else:
                    # No relevant information found
                    if service_scope == "out_of_scope":
                        if language == "he":
                            answer = f"מצטער, השירות '{category}' אינו זמין במערכת המידע שלנו. השירותים הזמינים הם: {', '.join(available_categories)}"
                        else:
                            answer = f"Sorry, the service '{category}' is not available in our system. Available services are: {', '.join(available_categories)}"
                    else:
                        if language == "he":
                            answer = "מצטער, לא מצאתי מידע ספציפי על הנושא. אנא נסה לנסח את השאלה בצורה אחרת או פנה לקופת החולים שלך."
                        else:
                            answer = "Sorry, I couldn't find specific information on this topic. Please try rephrasing your question or contact your health fund."
                    action = "answer"

            # Build enhanced response
            resp = {
                "intent": intent,
                "answer_type": answer_type if 'answer_type' in locals() else intent,
                "updated_profile": updated_profile,
                "known_fields": {k: v for k, v in updated_profile.items() if v},
                "missing_fields": requirements.get("missing_fields", []),
                "sufficient_context": requirements.get("can_answer", False),
                "action": "answer" if action == "retrieve_answer" else "collect",
                "next_question": requirements.get("question_to_ask", "") if action == "collect_info" else "",
                "answer": answer,
                "citations": citations,
                "token_usage": token_usage,
                "context_metrics": context_metrics,
                "disclaimer": "המידע כללי ואינו מהווה ייעוץ רפואי." if language == "he" and answer else "",
                "language": language,
                "service_scope": service_scope,
                "available_services": available_services_list
            }

            # Enhanced logging
            logger.info(
                "chat_turn_v2: lang=%s, ctx_chars=%s, tokens=%s, scope=%s, fallback=%s",
                language,
                resp["context_metrics"]["kb_context_chars"],
                resp["token_usage"].get("total_tokens", 0),
                service_scope,
                resp.get("answer_type") == "all_benefits_fallback"
            )

            # Emit enhanced metrics
            processing_time = time.time() - start
            total_tokens = resp["token_usage"].get("total_tokens", 0)
            app.metrics.emit_chat_metrics(
                processing_time=processing_time,
                tokens_used=total_tokens,
                message_length=len(message),
                language=language,
                intent=resp.get("intent"),
                success=True
            )
            
            return jsonify(resp), 200

        except Exception as e:
            # Emit error metrics
            processing_time = time.time() - start
            app.metrics.emit_chat_metrics(
                processing_time=processing_time,
                tokens_used=0,
                message_length=len(message),
                language=language,
                success=False,
                error_details=str(e)
            )
            
            logger.exception("/v2/chat failed: %s", e)
            return jsonify({"error": str(e)}), 500

    return app


if __name__ == "__main__":
    # Development server
    app = create_app()
    app.run(host="0.0.0.0", port=5002, debug=False)
