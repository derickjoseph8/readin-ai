"""Claude AI integration for instant response drafting - optimized for verbal delivery."""

import threading
from typing import Callable, Optional
from collections import deque

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, RESPONSE_MODEL


class AIAssistant:
    """Generates instant talking points using Claude API."""

    def __init__(self, on_response: Callable[[str, str], None],
                 on_streaming_chunk: Optional[Callable[[str], None]] = None):
        """
        Initialize AI assistant.

        Args:
            on_response: Callback with (heard_text, response) when complete
            on_streaming_chunk: Optional callback for streaming response chunks
        """
        self.on_response = on_response
        self.on_streaming_chunk = on_streaming_chunk
        self._client: Optional[Anthropic] = None
        self._context: deque = deque(maxlen=3)  # Keep last 3 exchanges
        self._lock = threading.Lock()

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
        def _generate():
            try:
                client = self._get_client()

                system_prompt = """You are a real-time interview assistant. Generate SHORT talking points that someone can glance at and rephrase in their own words while speaking.

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

                messages = self._build_messages(heard_text)

                if self.on_streaming_chunk:
                    # Streaming response
                    full_response = ""
                    with client.messages.stream(
                        model=RESPONSE_MODEL,
                        max_tokens=200,  # Shorter for quick responses
                        system=system_prompt,
                        messages=messages,
                    ) as stream:
                        for text in stream.text_stream:
                            full_response += text
                            self.on_streaming_chunk(text)

                    response = full_response
                else:
                    # Non-streaming response
                    result = client.messages.create(
                        model=RESPONSE_MODEL,
                        max_tokens=200,
                        system=system_prompt,
                        messages=messages,
                    )
                    response = result.content[0].text

                # Store in context
                with self._lock:
                    self._context.append({
                        'heard': heard_text,
                        'response': response
                    })

                self.on_response(heard_text, response)

            except Exception as e:
                error_msg = f"Error: {e}"
                print(error_msg)
                self.on_response(heard_text, error_msg)

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()

    def clear_context(self):
        """Clear conversation context (call when session ends)."""
        with self._lock:
            self._context.clear()
