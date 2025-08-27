"""
Chat Service (Phase 2) - Stateless KB-backed chat endpoint.

Endpoint: POST /v1/chat

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

Response JSON schema (unified per turn):
{
  "intent": "collection|qa|other",
  "answer_type": "general_description|specific_benefits|eligibility|cost_coverage|documents_required|process_steps|other",
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
  "language": "he|en"
}

This service is stateless: the client sends full profile and chat history each turn.
"""
import os
import time
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Local imports (service layer)
from .services.three_stage_extractor import three_stage_process
from .services.grounded_answerer import generate_grounded_answer, format_kb_context_for_llm
from .services.chat_health_kb import ChatHealthKB
from .services.smart_rag_kb import SmartRAGHealthKB
from .services.service_based_kb import ServiceBasedKB
from .services.metrics_client import MetricsClient

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    # Initialize KB at startup (still stateless per user)
    # Calculate correct path: services/chat-service/app/main.py -> ../../data/phase2_data
    kb_dir = os.environ.get("KNOWLEDGE_BASE_DIR") or os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "phase2_data"
    )
    # Normalize the path
    kb_dir = os.path.abspath(kb_dir)
    
    # Use Service-Based KB with semantic search and profile-aware retrieval
    logger.info(f"Initializing Service-Based KB from: {kb_dir}")
    app.kb = ServiceBasedKB(kb_dir)
    
    # Initialize metrics client
    app.metrics = MetricsClient()
    
    # Debug KB loading
    logger.info(f"KB path: {kb_dir}")
    logger.info(f"Service chunks created: {len(app.kb.service_chunks) if hasattr(app.kb, 'service_chunks') else 'N/A'}")
    logger.info(f"Embeddings enabled: {app.kb.use_embeddings if hasattr(app.kb, 'use_embeddings') else 'N/A'}")
    logger.info(f"KB categories: {len(app.kb.by_category)}")
    if app.kb.by_category:
        for cat, funds in list(app.kb.by_category.items())[:3]:  # Show first 3 only
            logger.info(f"  {cat}: {len(funds)} funds")

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "service": "chat-service"}), 200

    @app.route("/v1/chat", methods=["POST"])
    def chat_turn():
        start = time.time()
        req = request.get_json(force=True, silent=True) or {}
        message = req.get("message", "").strip()
        language = req.get("language", "he").strip() or "he"
        user_profile = req.get("user_profile", {}) or {}
        history = req.get("conversation_history", []) or []

        if not message:
            return jsonify({"error": "message is required"}), 400

        try:
            # Run 3-stage pipeline
            logger.info(f"=== 3-STAGE PIPELINE INPUT ===")
            logger.info(f"Message: {message}")
            logger.info(f"User profile: {user_profile}")
            logger.info(f"History: {history}")
            logger.info(f"Language: {language}")
            
            pipeline_result = three_stage_process(
                message=message,
                user_profile=user_profile,
                conversation_history=history,
                language=language
            )
            
            logger.info(f"=== 3-STAGE PIPELINE OUTPUT ===")
            logger.info(f"Classification: {pipeline_result.get('classification', {})}")
            logger.info(f"Requirements: {pipeline_result.get('requirements', {})}")
            logger.info(f"Updated profile: {pipeline_result.get('updated_profile', {})}")

            # Extract results from 3-stage pipeline
            updated_profile = pipeline_result.get("updated_profile", {})
            classification = pipeline_result.get("classification", {})
            requirements = pipeline_result.get("requirements", {})
            
            category = classification.get("category", "אחר")
            intent = classification.get("intent", "other")
            action = requirements.get("action", "collect_info")
            
            logger.info(f"=== PIPELINE DECISION ===")
            logger.info(f"Category: '{category}', Intent: '{intent}', Action: '{action}'")
            logger.info(f"Profile: HMO='{updated_profile.get('hmo')}', Tier='{updated_profile.get('tier')}'")
            
            # Initialize response structure
            answer = ""
            citations = []
            token_usage = pipeline_result.get("token_usage", {})
            context_metrics = {"kb_context_chars": 0, "snippets_chars": 0}
            
            if action == "retrieve_answer":
                # Step 2: Retrieve relevant KB context
                
                logger.info(f"=== KB RETRIEVAL ===")
                logger.info(f"Category: {category}, Profile: {updated_profile}")
                logger.info(f"KB instance categories: {list(app.kb.by_category.keys())}")
                logger.info(f"KB optometry funds: {list(app.kb.by_category.get('אופטומטריה', {}).keys()) if 'אופטומטריה' in app.kb.by_category else 'NOT FOUND'}")
                
                retrieval = app.kb.retrieve(
                    message=message,
                    profile=updated_profile,
                    language=language,
                    max_chars=3500
                )
                
                logger.info(f"KB retrieval raw result: context_chars={retrieval.get('context_chars', 0)}, snippets={len(retrieval.get('snippets', []))}, citations={len(retrieval.get('citations', []))}")
                
                context_metrics["kb_context_chars"] = retrieval.get("context_chars", 0)
                context_metrics["snippets_chars"] = retrieval.get("snippets_chars", 0)
                citations = retrieval.get("citations", [])
                
                logger.info(f"KB retrieved {len(retrieval.get('snippets', []))} snippets, {context_metrics['kb_context_chars']} chars")

                # Step 3: Generate grounded answer
                if retrieval.get("snippets"):
                    kb_context = format_kb_context_for_llm(retrieval["snippets"])
                    
                    answer_result = generate_grounded_answer(
                        user_question=message,
                        user_profile=updated_profile,
                        kb_context=kb_context,
                        conversation_history=history,
                        language=language,
                        max_tokens=1000
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
                    answer = "מצטער, לא מצאתי מידע על הנושה בבקשה מערכת המידע. אנא נסה לנסח את השאלה בצורה אחרת או פנה לקופת החולים שלך."
                    action = "answer"

            # Build unified response
            resp = {
                "intent": intent,
                "answer_type": intent,
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
            }

            # Simple logging of context sizes
            logger.info(
                "chat_turn: lang=%s, ctx_chars=%s, snip_chars=%s, tokens=%s",
                language,
                resp["context_metrics"]["kb_context_chars"],
                resp["context_metrics"]["snippets_chars"],
                resp["token_usage"].get("total_tokens", 0),
            )

            # Emit metrics
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
            
            logger.exception("/v1/chat failed: %s", e)
            return jsonify({"error": str(e)}), 500

    return app


