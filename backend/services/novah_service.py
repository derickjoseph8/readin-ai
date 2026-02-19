"""
Novah AI Chatbot Service

Novah is the AI assistant that handles initial customer conversations,
searches the knowledge base, and provides solutions before transferring
to human agents if needed.
"""

import os
import re
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

    # Direct answers for common questions (no KB search needed)
    DIRECT_ANSWERS = {
        "pricing": {
            "keywords": ["price", "pricing", "cost", "how much", "plans", "subscription fee", "monthly", "yearly"],
            "response": """Great question! Here are our pricing plans:

**Free Trial** - 7 days free
- Full access to all features
- No credit card required

**Premium** - $29.99/month
- Unlimited AI assistance
- Real-time transcription
- Meeting summaries
- Priority support

**Team** - $19.99/user/month
- Everything in Premium
- 5 seats included
- Team admin dashboard
- Shared insights

Would you like more details about any specific plan?"""
        },
        "features": {
            "keywords": ["features", "what can it do", "what does it do", "capabilities", "functionality"],
            "response": """ReadIn AI helps you ace meetings with:

**Real-Time AI Assistance**
- Instant talking points during calls
- Contextual suggestions

**Live Transcription**
- Accurate speech-to-text
- Multiple languages supported

**Meeting Summaries**
- Auto-generated summaries
- Action items captured

**Works With**
- Zoom, Google Meet, Teams, Webex
- Windows & Mac

Would you like to know more about any specific feature?"""
        },
        "cancel": {
            "keywords": ["cancel", "cancellation", "stop subscription", "unsubscribe", "end subscription"],
            "response": """To cancel your subscription:

1. Go to **Settings** > **Billing**
2. Click **Manage Subscription**
3. Select **Cancel Subscription**
4. Confirm

Your access continues until the end of your billing period. No cancellation fees!

Need help with cancellation? Just say "talk to billing team" and I'll connect you."""
        },
        "refund": {
            "keywords": ["refund", "money back", "get refund", "refund policy"],
            "response": """Our refund policy:

- **Full refund** within 14 days of purchase
- **Pro-rated refunds** for annual plans
- Refunds processed within 5-7 business days

To request a refund, say "talk to billing team" and I'll connect you with our billing specialist."""
        },
        "download": {
            "keywords": ["download", "install", "get the app", "where to download"],
            "response": """You can download ReadIn AI from:

**getreadin.us/download**

Available for:
- Windows 10 and later
- macOS 11 (Big Sur) and later

The download is free, and your 7-day trial starts when you sign up!"""
        },
        "how_it_works": {
            "keywords": ["how does it work", "how to use", "getting started", "setup", "start using"],
            "response": """Here's how ReadIn AI works:

1. **Download** the app from getreadin.us/download
2. **Sign in** with your account
3. **Start a meeting** (Zoom, Meet, Teams, etc.)
4. **Click Start** in ReadIn AI
5. **Get AI suggestions** in real-time as you talk!

The app listens to your meeting audio and provides talking points you can glance at and use naturally.

Want me to walk you through any specific step?"""
        },
        "contact": {
            "keywords": ["contact", "email", "phone", "reach you", "support email"],
            "response": """You can reach us at:

**Support:** support@getreadin.us
**Sales:** sales@getreadin.us
**Billing:** billing@getreadin.us

Or just tell me what you need help with and I'll either assist you or connect you with the right team!"""
        },
        "trial": {
            "keywords": ["free trial", "trial", "try free", "test it", "demo"],
            "response": """Yes! We offer a **7-day free trial** with:

- Full access to all Premium features
- No credit card required to start
- No obligations

Just sign up at **getreadin.us/signup** to start your free trial!"""
        }
    }

    # Keywords that suggest transfer to human
    TRANSFER_KEYWORDS = [
        "human", "agent", "person", "representative", "talk to someone",
        "speak to someone", "real person", "live support", "escalate",
        "not helpful", "doesn't help", "complaint"
    ]

    # Keywords for transfer category detection
    TRANSFER_CATEGORY_KEYWORDS = {
        "sales": ["sales", "sales team", "pricing question", "demo", "buy", "purchase", "enterprise", "quote", "talk to sales"],
        "billing": ["billing", "billing team", "payment", "refund", "invoice", "charge", "cancel subscription", "subscription", "talk to billing"],
        "technical": ["technical", "tech", "tech support", "technical support", "bug", "error", "issue", "problem", "not working", "broken", "talk to tech", "talk to support"]
    }

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

    def get_direct_answer(self, message: str) -> Optional[str]:
        """Check if message matches a direct answer topic."""
        message_lower = message.lower()

        for topic, data in self.DIRECT_ANSWERS.items():
            for keyword in data["keywords"]:
                if keyword in message_lower:
                    return data["response"]

        return None

    def search_knowledge_base(
        self, query: str, db: Session, limit: int = 5
    ) -> List[KnowledgeBaseArticle]:
        """Search the knowledge base for relevant articles."""
        query_lower = query.lower()
        words = query_lower.split()

        # Build search conditions
        conditions = []
        for word in words:
            if len(word) > 2:  # Skip short words
                conditions.append(KnowledgeBaseArticle.title.ilike(f"%{word}%"))
                conditions.append(KnowledgeBaseArticle.content.ilike(f"%{word}%"))
                conditions.append(KnowledgeBaseArticle.summary.ilike(f"%{word}%"))
                # Also search tags
                conditions.append(KnowledgeBaseArticle.tags.cast(String).ilike(f"%{word}%"))

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

    def detect_transfer_category(self, message: str) -> Optional[str]:
        """Detect if message contains a transfer category (sales/billing/technical)."""
        message_lower = message.lower()
        for category, keywords in self.TRANSFER_CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return category
        return None

    def wants_to_transfer(self, message: str) -> bool:
        """Check if user explicitly wants to talk to a human."""
        message_lower = message.lower()
        for keyword in self.TRANSFER_KEYWORDS:
            if keyword in message_lower:
                return True
        return False

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
        message_lower = message.lower()
        category = self.detect_category(message)
        message_count = len(conversation_history) if conversation_history else 0

        # Check if user wants to transfer to human
        if self.wants_to_transfer(message):
            # Check if they specified a category
            transfer_category = self.detect_transfer_category(message)
            if transfer_category:
                # They specified a category, transfer directly
                response = f"I'll connect you with our {transfer_category} team right away. Please hold on..."
                return {
                    "response": response,
                    "articles": [],
                    "should_transfer": True,
                    "transfer_reason": f"Transferring to {transfer_category} team",
                    "transfer_category": transfer_category,
                    "detected_category": category
                }
            else:
                # Ask for category
                response = """I'd be happy to connect you with one of our team members!

To make sure I route you to the right person, what do you need help with?

- **Sales** - Pricing, demos, or enterprise inquiries
- **Billing** - Payments, refunds, or subscription questions
- **Technical** - Technical support or issues

Just reply with "sales", "billing", or "technical"."""
                return {
                    "response": response,
                    "articles": [],
                    "should_transfer": False,
                    "transfer_reason": "",
                    "detected_category": category,
                    "awaiting_category": True
                }

        # Check if this is a category response (sales/billing/technical) after we asked
        transfer_category = self.detect_transfer_category(message)
        if transfer_category and message_lower.strip() in ["sales", "billing", "technical", "tech", "support"]:
            response = f"Perfect! I'll connect you with our {transfer_category} team. Please hold on..."
            return {
                "response": response,
                "articles": [],
                "should_transfer": True,
                "transfer_reason": f"Transferring to {transfer_category} team",
                "transfer_category": transfer_category,
                "detected_category": category
            }

        # Check for direct answers first (pricing, features, etc.)
        direct_answer = self.get_direct_answer(message)
        if direct_answer:
            return {
                "response": direct_answer,
                "articles": [],
                "should_transfer": False,
                "transfer_reason": "",
                "detected_category": category
            }

        # Search knowledge base
        from sqlalchemy import String
        articles = self.search_knowledge_base(message, db)

        # Generate response based on articles found
        if articles:
            response = self._format_article_response(message, articles)
        else:
            response = self._generate_fallback_response(message, category)

        # Auto-transfer after too many messages without resolution
        should_transfer = message_count >= 10
        transfer_reason = "Extended conversation - transferring for human assistance" if should_transfer else ""

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
            response = f"Here's what I found:\n\n"
            response += f"**{article.title}**\n"
            if article.summary:
                response += f"{article.summary}\n"
            response += "\nIs there anything else you'd like to know?"
        else:
            response = "I found some information that might help:\n\n"
            for i, article in enumerate(articles[:3], 1):
                response += f"**{article.title}**"
                if article.summary:
                    response += f"\n{article.summary[:150]}..."
                response += "\n\n"
            response += "Would you like more details on any of these topics?"

        return response

    def _generate_fallback_response(self, message: str, category: str) -> str:
        """Generate a fallback response when no articles are found."""
        category_responses = {
            "billing": "I understand you have a billing question. Could you give me more details? Or if you'd prefer, I can connect you with our billing team - just say 'talk to billing'.",
            "technical": "I see you might be having a technical issue. Could you describe what's happening? Include any error messages if you see them. I'll do my best to help!",
            "account": "I can help with account questions! What would you like to do with your account?",
            "feature": "I'd be happy to explain how ReadIn AI works! What specific feature would you like to learn about?",
            "general": "Thanks for your message! Could you tell me more about what you need help with? I'm here to answer questions about ReadIn AI - pricing, features, billing, technical support, and more.",
        }

        return category_responses.get(category, category_responses["general"])

    def create_transfer_message(self, reason: str) -> str:
        """Create a message when transferring to a human agent."""
        return f"I'm connecting you with one of our team members. {reason}\n\nPlease hold on while I find the right person to help you."


# Singleton instance
novah_service = NovahService()
