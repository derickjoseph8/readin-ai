"""
AI response generation service.

Provides:
- AI-powered response suggestions with streaming support
- Context-aware assistance
- Profession-tailored responses
- Multi-language support
"""

import logging
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
import threading
import queue
import time

logger = logging.getLogger(__name__)

# Default model - use fast model for real-time responses
DEFAULT_MODEL = "claude-sonnet-4-20250514"


@dataclass
class AIResponse:
    """AI response result."""
    text: str
    confidence: float
    response_type: str  # suggestion, answer, clarification
    context_used: List[str]
    timestamp: float
    latency_ms: float
    is_streaming: bool = False
    is_complete: bool = True


@dataclass
class ConversationContext:
    """Context for AI conversation."""
    meeting_type: str = "general"
    profession: Optional[str] = None
    profession_context: Optional[str] = None
    recent_topics: List[str] = field(default_factory=list)
    participant_info: Dict[str, Any] = field(default_factory=dict)
    custom_instructions: Optional[str] = None
    language: str = "en"  # User's preferred language (en, es, sw, fr, de, etc.)


# Language-specific instructions for AI responses
LANGUAGE_INSTRUCTIONS = {
    "en": "",  # English is default, no special instruction needed
    "es": "\n\nIMPORTANT: Respond entirely in Spanish (Español). Responde en español.",
    "sw": "\n\nIMPORTANT: Respond entirely in Swahili (Kiswahili). Jibu kwa Kiswahili.",
    "fr": "\n\nIMPORTANT: Respond entirely in French (Français). Répondez en français.",
    "de": "\n\nIMPORTANT: Respond entirely in German (Deutsch). Antworten Sie auf Deutsch.",
    "pt": "\n\nIMPORTANT: Respond entirely in Portuguese (Português). Responda em português.",
    "it": "\n\nIMPORTANT: Respond entirely in Italian (Italiano). Rispondi in italiano.",
    "ja": "\n\nIMPORTANT: Respond entirely in Japanese (日本語). 日本語で回答してください。",
    "zh": "\n\nIMPORTANT: Respond entirely in Chinese (中文). 请用中文回答。",
    "ko": "\n\nIMPORTANT: Respond entirely in Korean (한국어). 한국어로 답변해 주세요.",
    "ar": "\n\nIMPORTANT: Respond entirely in Arabic (العربية). الرجاء الرد بالعربية.",
    "hi": "\n\nIMPORTANT: Respond entirely in Hindi (हिंदी). कृपया हिंदी में जवाब दें।",
}


class AIService:
    """
    Service for AI-powered response generation.

    Integrates with Claude API for intelligent responses with streaming support.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        """
        Initialize AI service.

        Args:
            api_key: Anthropic API key (optional, can use backend)
            model: Claude model to use
        """
        self._api_key = api_key
        self._model = model
        self._client = None
        self._is_running = False
        self._is_generating = False
        self._request_queue: queue.Queue = queue.Queue()
        self._process_thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[AIResponse], None]] = []
        self._streaming_listeners: List[Callable[[str], None]] = []
        self._context = ConversationContext()
        self._conversation_history: List[Dict[str, str]] = []
        self._max_history = 20
        self._max_tokens = 200  # Short responses for real-time use
        self._enable_streaming = True

    @property
    def is_running(self) -> bool:
        """Check if AI service is running."""
        return self._is_running

    def set_context(self, context: ConversationContext):
        """Update conversation context."""
        self._context = context
        logger.info(f"AI context updated: {context.meeting_type}")

    def set_profession(self, profession: str, context: str = None):
        """Set profession for tailored responses."""
        self._context.profession = profession
        self._context.profession_context = context
        logger.info(f"AI profession set: {profession}")

    def set_language(self, language: str):
        """Set preferred language for AI responses."""
        self._context.language = language
        if language not in LANGUAGE_INSTRUCTIONS:
            logger.warning(f"Language {language} has no custom instructions, responses will be in English")
        logger.info(f"AI language set: {language}")

    def set_model(self, model: str):
        """Set the Claude model to use."""
        self._model = model
        logger.info(f"AI model set: {model}")

    def set_max_tokens(self, max_tokens: int):
        """Set maximum tokens for responses."""
        self._max_tokens = max_tokens

    def set_streaming_enabled(self, enabled: bool):
        """Enable or disable streaming responses."""
        self._enable_streaming = enabled

    def add_listener(self, callback: Callable[[AIResponse], None]):
        """Add response listener."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[AIResponse], None]):
        """Remove response listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def add_streaming_listener(self, callback: Callable[[str], None]):
        """Add streaming chunk listener."""
        self._streaming_listeners.append(callback)

    def remove_streaming_listener(self, callback: Callable[[str], None]):
        """Remove streaming chunk listener."""
        if callback in self._streaming_listeners:
            self._streaming_listeners.remove(callback)

    def _notify_streaming(self, chunk: str):
        """Notify listeners of streaming chunk."""
        for listener in self._streaming_listeners:
            try:
                listener(chunk)
            except Exception as e:
                logger.error(f"Error in streaming listener: {e}")

    def _notify_listeners(self, response: AIResponse):
        """Notify listeners of AI response."""
        for listener in self._listeners:
            try:
                listener(response)
            except Exception as e:
                logger.error(f"Error in AI listener: {e}")

    def _init_client(self) -> bool:
        """Initialize Anthropic client."""
        if self._client is not None:
            return True

        try:
            from anthropic import Anthropic

            if self._api_key:
                self._client = Anthropic(api_key=self._api_key)
            else:
                # Try to get from environment
                self._client = Anthropic()

            return True

        except ImportError:
            logger.error("Anthropic not installed. Run: pip install anthropic")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            return False

    def start(self) -> bool:
        """Start AI service."""
        if self._is_running:
            return True

        if not self._init_client():
            logger.warning("AI service starting without direct API access")

        self._is_running = True
        self._process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True
        )
        self._process_thread.start()

        logger.info("AI service started")
        return True

    def stop(self):
        """Stop AI service."""
        self._is_running = False

        if self._process_thread and self._process_thread.is_alive():
            self._process_thread.join(timeout=2.0)

        self._process_thread = None
        logger.info("AI service stopped")

    def request_response(
        self,
        heard_text: str,
        speaker: str = "other",
        response_type: str = "suggestion"
    ):
        """
        Request an AI response.

        Args:
            heard_text: What was heard/said
            speaker: Who said it (user, other, unknown)
            response_type: Type of response needed
        """
        if self._is_running:
            self._request_queue.put({
                "heard_text": heard_text,
                "speaker": speaker,
                "response_type": response_type,
                "timestamp": time.time(),
            })

    def _build_system_prompt(self) -> str:
        """Build system prompt based on context."""
        parts = [
            "You are a real-time meeting assistant helping the user during a live conversation.",
            "Provide concise, helpful responses that the user can use immediately.",
            "Keep responses brief (1-3 sentences) unless more detail is needed.",
        ]

        # Add meeting type context
        if self._context.meeting_type == "interview":
            parts.append(
                "This is a job interview. Help the user give strong, professional answers. "
                "Use the STAR method when appropriate."
            )
        elif self._context.meeting_type == "tv_appearance":
            parts.append(
                "This is a media appearance. Help the user give clear, quotable responses. "
                "Vary talking points to avoid repetition."
            )
        elif self._context.meeting_type == "manager_meeting":
            parts.append(
                "This is a meeting with management. Help the user communicate clearly "
                "and professionally about their work and achievements."
            )

        # Add profession context
        if self._context.profession:
            parts.append(f"The user is a {self._context.profession}.")
            if self._context.profession_context:
                parts.append(self._context.profession_context)

        # Add custom instructions
        if self._context.custom_instructions:
            parts.append(self._context.custom_instructions)

        # Add language instructions
        language_instruction = LANGUAGE_INSTRUCTIONS.get(self._context.language, "")
        if language_instruction:
            parts.append(language_instruction)

        return "\n\n".join(parts)

    def _process_loop(self):
        """AI processing loop."""
        while self._is_running:
            try:
                # Get request from queue
                try:
                    request = self._request_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # Prevent concurrent generations
                if self._is_generating:
                    continue

                self._is_generating = True
                start_time = time.time()

                try:
                    # Store what was heard (always as user message for context)
                    heard_text = request["heard_text"]

                    # Generate response
                    if self._client:
                        response_text = self._generate_with_claude(request)
                    else:
                        response_text = self._generate_fallback(request)

                    latency_ms = (time.time() - start_time) * 1000

                    if response_text:
                        # Add to conversation history (heard -> response pair)
                        self._conversation_history.append({
                            "role": "user",
                            "content": f'Question asked: "{heard_text}"'
                        })
                        self._conversation_history.append({
                            "role": "assistant",
                            "content": response_text
                        })

                        # Trim history
                        if len(self._conversation_history) > self._max_history:
                            self._conversation_history = self._conversation_history[-self._max_history:]

                        response = AIResponse(
                            text=response_text,
                            confidence=0.85,
                            response_type=request["response_type"],
                            context_used=[self._context.meeting_type, self._context.profession or "general"],
                            timestamp=time.time(),
                            latency_ms=latency_ms,
                            is_complete=True,
                        )

                        self._notify_listeners(response)

                finally:
                    self._is_generating = False

            except Exception as e:
                logger.error(f"AI processing error: {e}")
                self._is_generating = False

    def _generate_with_claude(self, request: Dict) -> Optional[str]:
        """Generate response using Claude API with optional streaming."""
        try:
            # Build messages with proper alternating user/assistant pattern
            messages = []

            # Add conversation history (already in correct format)
            history_to_use = self._conversation_history[-10:]  # Last 5 exchanges (10 messages)
            for entry in history_to_use:
                messages.append({
                    "role": entry["role"],
                    "content": entry["content"]
                })

            # Add current request
            prompt = f'Question asked: "{request["heard_text"]}"\n\nProvide a helpful response.'
            messages.append({
                "role": "user",
                "content": prompt
            })

            system_prompt = self._build_system_prompt()

            if self._enable_streaming and self._streaming_listeners:
                # Streaming response
                full_response = ""
                with self._client.messages.stream(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system_prompt,
                    messages=messages,
                ) as stream:
                    for text in stream.text_stream:
                        full_response += text
                        self._notify_streaming(text)

                return full_response.strip()
            else:
                # Non-streaming response
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system_prompt,
                    messages=messages,
                )
                return response.content[0].text.strip()

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None

    def _generate_fallback(self, request: Dict) -> str:
        """Generate simple fallback response."""
        # Simple pattern-based fallback when API unavailable
        heard = request["heard_text"].lower()

        if "?" in request["heard_text"]:
            return "Consider addressing this question by sharing a relevant example from your experience."
        elif "tell me about" in heard:
            return "This is a great opportunity to highlight your key achievements and relevant experience."
        elif "why" in heard:
            return "Explain your reasoning clearly, focusing on the value and impact of your decisions."
        else:
            return "Listen actively and prepare to build on this point when appropriate."

    def clear_history(self):
        """Clear conversation history."""
        self._conversation_history = []
        logger.info("AI conversation history cleared")

    def is_generating(self) -> bool:
        """Check if currently generating a response."""
        return self._is_generating

    def get_status(self) -> Dict[str, Any]:
        """Get AI service status."""
        return {
            "is_running": self._is_running,
            "is_generating": self._is_generating,
            "has_api_client": self._client is not None,
            "model": self._model,
            "meeting_type": self._context.meeting_type,
            "profession": self._context.profession,
            "language": self._context.language,
            "history_length": len(self._conversation_history),
            "queue_size": self._request_queue.qsize(),
            "streaming_enabled": self._enable_streaming,
            "max_tokens": self._max_tokens,
        }
