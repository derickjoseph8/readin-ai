"""
Novah AI Chatbot Service

Novah is the AI assistant that handles initial customer conversations,
searches the knowledge base, and provides solutions before transferring
to human agents if needed.
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from models import ChatSession, ChatMessage, KnowledgeBaseArticle, User


class NovahService:
    """AI chatbot service for initial customer support."""

    # Novah's greeting messages
    GREETINGS = [
        "Hi! I'm Novah, ReadIn AI's virtual assistant. How can I help you today?",
        "Hello! I'm Novah. I'm here to help you with any questions about ReadIn AI.",
        "Welcome! I'm Novah, your AI assistant. What can I assist you with?",
    ]

    # Keywords that suggest transfer to human
    TRANSFER_KEYWORDS = [
        "human", "agent", "person", "representative", "talk to someone",
        "speak to someone", "real person", "live support", "escalate",
        "not helpful", "doesn't help", "complaint", "refund", "cancel subscription"
    ]

    # Category mappings for routing
    CATEGORY_MAPPINGS = {
        "billing": ["billing", "payment", "invoice", "charge", "subscription", "price", "cost", "refund"],
        "technical": ["bug", "error", "crash", "not working", "broken", "issue", "problem"],
        "account": ["login", "password", "account", "email", "profile", "settings"],
        "feature": ["feature", "how to", "how do i", "can i", "does it"],
        "general": [],  # Fallback
    }

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    def get_greeting(self) -> str:
        """Get a random greeting message."""
        import random
        return random.choice(self.GREETINGS)

    def search_knowledge_base(
        self, query: str, db: Session, limit: int = 5
    ) -> List[KnowledgeBaseArticle]:
        """Search the knowledge base for relevant articles."""
        # Simple keyword search (can be enhanced with vector search)
        query_lower = query.lower()
        words = query_lower.split()

        # Build search conditions
        conditions = []
        for word in words:
            if len(word) > 2:  # Skip short words
                conditions.append(KnowledgeBaseArticle.title.ilike(f"%{word}%"))
                conditions.append(KnowledgeBaseArticle.content.ilike(f"%{word}%"))
                conditions.append(KnowledgeBaseArticle.summary.ilike(f"%{word}%"))

        if not conditions:
            return []

        articles = db.query(KnowledgeBaseArticle).filter(
            KnowledgeBaseArticle.is_published == True,
            or_(*conditions)
        ).limit(limit).all()

        return articles

    def detect_category(self, message: str) -> str:
        """Detect the category of the user's message."""
        message_lower = message.lower()

        for category, keywords in self.CATEGORY_MAPPINGS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return category

        return "general"

    def should_transfer_to_agent(
        self, message: str, message_count: int, session: ChatSession
    ) -> Tuple[bool, str]:
        """
        Determine if the conversation should be transferred to a human agent.

        Returns:
            Tuple of (should_transfer, reason)
        """
        message_lower = message.lower()

        # Check for explicit transfer requests
        for keyword in self.TRANSFER_KEYWORDS:
            if keyword in message_lower:
                return True, "User requested human agent"

        # Auto-transfer after too many messages without resolution
        if message_count >= 8:
            return True, "Extended conversation - transferring for human assistance"

        # Don't transfer by default
        return False, ""

    def generate_response(
        self,
        message: str,
        session: ChatSession,
        db: Session,
        conversation_history: List[ChatMessage] = None
    ) -> Dict[str, Any]:
        """
        Generate an AI response to the user's message.

        Returns:
            Dict with 'response', 'articles', 'should_transfer', 'transfer_reason'
        """
        # Search knowledge base
        articles = self.search_knowledge_base(message, db)
        category = self.detect_category(message)

        # Count messages in session
        message_count = len(conversation_history) if conversation_history else 0

        # Check if should transfer
        should_transfer, transfer_reason = self.should_transfer_to_agent(
            message, message_count, session
        )

        # Generate response based on articles found
        if articles:
            response = self._format_article_response(message, articles)
        else:
            response = self._generate_fallback_response(message, category)

        return {
            "response": response,
            "articles": [
                {
                    "id": a.id,
                    "title": a.title,
                    "summary": a.summary,
                    "url": a.url,
                    "category": a.category
                }
                for a in articles
            ],
            "should_transfer": should_transfer,
            "transfer_reason": transfer_reason,
            "detected_category": category
        }

    def _format_article_response(
        self, message: str, articles: List[KnowledgeBaseArticle]
    ) -> str:
        """Format a response based on found articles."""
        if len(articles) == 1:
            article = articles[0]
            response = f"I found some information that might help:\n\n"
            response += f"**{article.title}**\n"
            if article.summary:
                response += f"{article.summary}\n"
            if article.url:
                response += f"\nFor more details, check out: {article.url}"
            response += "\n\nDid this answer your question? If not, I can connect you with our support team."
        else:
            response = "I found a few articles that might help:\n\n"
            for i, article in enumerate(articles[:3], 1):
                response += f"{i}. **{article.title}**"
                if article.summary:
                    response += f"\n   {article.summary[:100]}..."
                response += "\n"
            response += "\nWould you like more details on any of these? Or I can connect you with our support team."

        return response

    def _generate_fallback_response(self, message: str, category: str) -> str:
        """Generate a fallback response when no articles are found."""
        category_responses = {
            "billing": "I understand you have a billing-related question. While I search for more information, could you provide more details about your billing inquiry? If you need immediate assistance, I can connect you with our accounts team.",
            "technical": "I see you're experiencing a technical issue. Could you tell me more about what's happening? Include any error messages if possible. I'll do my best to help, or connect you with our technical support team.",
            "account": "I can help with account-related questions. Could you specify what you'd like to do with your account? If you're having trouble logging in or accessing your account, I can guide you through the process.",
            "feature": "Great question! Let me help you understand ReadIn AI's features. Could you be more specific about what you'd like to learn? I can explain how things work or connect you with our team for a demo.",
            "general": "Thank you for reaching out! I want to make sure I understand your question correctly. Could you provide a bit more detail? That way I can give you the most helpful answer or connect you with the right team member.",
        }

        return category_responses.get(category, category_responses["general"])

    def create_transfer_message(self, reason: str) -> str:
        """Create a message when transferring to a human agent."""
        return f"I'm connecting you with one of our team members who can better assist you. {reason}\n\nPlease hold on for just a moment while I find the right person to help."


# Singleton instance
novah_service = NovahService()
