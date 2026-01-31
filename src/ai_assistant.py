"""Claude AI integration for instant response drafting - optimized for verbal delivery."""

import threading
from typing import Callable, Optional, List, Dict, Any, TYPE_CHECKING
from collections import deque
from datetime import datetime

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, RESPONSE_MODEL, DEFAULT_CONTEXT_WINDOW, MAX_CONTEXT_WINDOW

if TYPE_CHECKING:
    from context_provider import ContextProvider


class AIAssistant:
    """Generates instant talking points using Claude API."""

    def __init__(
        self,
        on_response: Callable[[str, str], None],
        on_streaming_chunk: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        system_prompt: Optional[str] = None,
        context_size: int = DEFAULT_CONTEXT_WINDOW,
        model: str = RESPONSE_MODEL,
        context_provider: Optional["ContextProvider"] = None
    ):
        """
        Initialize AI assistant.

        Args:
            on_response: Callback with (heard_text, response) when complete
            on_streaming_chunk: Optional callback for streaming response chunks
            on_error: Optional callback for error handling
            system_prompt: Custom system prompt (uses default if None)
            context_size: Number of exchanges to keep in context
            model: Claude model to use
            context_provider: Optional context provider for personalization
        """
        self.on_response = on_response
        self.on_streaming_chunk = on_streaming_chunk
        self.on_error = on_error
        self._client: Optional[Anthropic] = None
        self._context_size = min(max(context_size, 1), MAX_CONTEXT_WINDOW)
        self._context: deque = deque(maxlen=self._context_size)
        self._lock = threading.Lock()
        self._model = model
        self._custom_system_prompt = system_prompt
        self._is_generating = False
        self._context_provider = context_provider
        self._meeting_type = "general"

    @property
    def default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return """You are a real-time interview assistant. Generate SHORT talking points that someone can glance at and rephrase in their own words while speaking.

FORMAT RULES:
- Use bullet points (•) for key ideas
- Keep each point to 5-10 words MAX
- 2-4 bullet points total
- NO full sentences - just key phrases
- NO introductions like "Here's what to say"
- Start immediately with the first bullet

STYLE:
- Direct, confident language
- Facts and specific details when relevant
- Easy to scan in 2 seconds

EXAMPLE OUTPUT:
• Main point in few words
• Supporting detail or fact
• Optional third point

Remember: The person will SPEAK these naturally - you're just giving them the key ideas to hit."""

    @property
    def system_prompt(self) -> str:
        """Get the current system prompt with personalization."""
        base_prompt = self._custom_system_prompt or self.default_system_prompt

        # Enhance with context provider if available
        if self._context_provider:
            return self._context_provider.build_enhanced_system_prompt(
                base_prompt, self._meeting_type
            )
        return base_prompt

    def set_system_prompt(self, prompt: Optional[str]):
        """Set a custom system prompt.

        Args:
            prompt: Custom prompt or None to use default
        """
        self._custom_system_prompt = prompt

    def set_context_provider(self, provider: "ContextProvider"):
        """Set the context provider for personalization.

        Args:
            provider: ContextProvider instance
        """
        self._context_provider = provider

    def set_meeting_type(self, meeting_type: str):
        """Set the current meeting type for context.

        Args:
            meeting_type: Type of meeting (interview, manager, client, etc.)
        """
        self._meeting_type = meeting_type

    def refresh_context(self) -> bool:
        """Refresh personalization context from backend.

        Returns:
            True if refresh was successful
        """
        if self._context_provider:
            return self._context_provider.refresh_context(force=True)
        return False

    def set_context_size(self, size: int):
        """Set the context window size.

        Args:
            size: Number of exchanges to keep (1-10)
        """
        new_size = min(max(size, 1), MAX_CONTEXT_WINDOW)
        if new_size != self._context_size:
            with self._lock:
                self._context_size = new_size
                # Recreate deque with new maxlen
                old_context = list(self._context)
                self._context = deque(old_context[-new_size:], maxlen=new_size)

    def set_model(self, model: str):
        """Set the AI model to use.

        Args:
            model: Model identifier string
        """
        self._model = model

    def _get_client(self) -> Anthropic:
        """Get or create Anthropic client."""
        if self._client is None:
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set in config or environment")
            self._client = Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._client

    def _build_messages(self, heard_text: str) -> list:
        """Build message history for Claude."""
        messages = []

        # Add recent context
        for exchange in self._context:
            messages.append({
                "role": "user",
                "content": f"Question: \"{exchange['heard']}\""
            })
            messages.append({
                "role": "assistant",
                "content": exchange['response']
            })

        # Add current request
        messages.append({
            "role": "user",
            "content": f"Question: \"{heard_text}\""
        })

        return messages

    def generate_response(self, heard_text: str):
        """Generate a response to what was heard (runs in background thread)."""
        if self._is_generating:
            return  # Prevent concurrent generations

        def _generate():
            self._is_generating = True
            try:
                client = self._get_client()

                messages = self._build_messages(heard_text)

                if self.on_streaming_chunk:
                    # Streaming response
                    full_response = ""
                    with client.messages.stream(
                        model=self._model,
                        max_tokens=200,  # Shorter for quick responses
                        system=self.system_prompt,
                        messages=messages,
                    ) as stream:
                        for text in stream.text_stream:
                            full_response += text
                            self.on_streaming_chunk(text)

                    response = full_response
                else:
                    # Non-streaming response
                    result = client.messages.create(
                        model=self._model,
                        max_tokens=200,
                        system=self.system_prompt,
                        messages=messages,
                    )
                    response = result.content[0].text

                # Store in context
                with self._lock:
                    self._context.append({
                        'heard': heard_text,
                        'response': response,
                        'timestamp': datetime.now().isoformat()
                    })

                self.on_response(heard_text, response)

            except Exception as e:
                error_msg = f"AI Error: {str(e)}"
                print(error_msg)
                if self.on_error:
                    self.on_error(str(e))
                self.on_response(heard_text, error_msg)
            finally:
                self._is_generating = False

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()

    def clear_context(self):
        """Clear conversation context (call when session ends)."""
        with self._lock:
            self._context.clear()

    def get_context(self) -> List[Dict[str, Any]]:
        """Get the current conversation context.

        Returns:
            List of context entries with 'heard', 'response', and 'timestamp'
        """
        with self._lock:
            return list(self._context)

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get conversation history for export.

        Returns:
            List of dicts with 'question', 'answer', and 'timestamp' keys
        """
        with self._lock:
            return [
                {
                    'question': entry['heard'],
                    'answer': entry['response'],
                    'timestamp': entry.get('timestamp', '')
                }
                for entry in self._context
            ]

    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the current context state.

        Returns:
            Dict with context stats
        """
        with self._lock:
            summary = {
                'entries': len(self._context),
                'max_entries': self._context_size,
                'model': self._model,
                'using_custom_prompt': self._custom_system_prompt is not None,
                'meeting_type': self._meeting_type
            }

            # Add personalization info
            if self._context_provider:
                ctx_summary = self._context_provider.get_context_summary()
                summary['personalization'] = {
                    'has_profession': ctx_summary.get('has_profession', False),
                    'profession_name': ctx_summary.get('profession_name'),
                    'has_learning_profile': ctx_summary.get('has_learning_profile', False),
                    'learning_confidence': ctx_summary.get('learning_confidence')
                }

            return summary

    def is_generating(self) -> bool:
        """Check if currently generating a response."""
        return self._is_generating
