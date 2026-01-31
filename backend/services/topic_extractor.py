"""Topic Extraction Service using Claude AI."""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import anthropic
from sqlalchemy.orm import Session

from models import Topic, ConversationTopic, Conversation, UserLearningProfile


class TopicExtractor:
    """Extract and categorize topics from conversations using Claude."""

    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("TOPIC_EXTRACTION_MODEL", "claude-3-haiku-20240307")

    async def extract_topics(
        self, conversation_text: str, user_id: int
    ) -> List[Dict[str, Any]]:
        """Extract topics from conversation text."""
        prompt = f"""Analyze the following conversation and extract the main topics discussed.
For each topic, provide:
1. topic_name: A concise name (2-4 words)
2. category: One of [technical, behavioral, situational, industry, personal, procedural]
3. importance: A score from 1-10 indicating topic importance
4. context: Brief context about how the topic was discussed

Conversation:
{conversation_text}

Respond in JSON format:
{{
    "topics": [
        {{
            "topic_name": "string",
            "category": "string",
            "importance": number,
            "context": "string"
        }}
    ]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            # Parse JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())
            return result.get("topics", [])

        except Exception as e:
            print(f"Topic extraction error: {e}")
            return []

    async def process_conversation(
        self, conversation: Conversation, user_id: int
    ) -> List[Topic]:
        """Process a conversation and store extracted topics."""
        # Combine heard text and response for analysis
        text = f"Question/Statement: {conversation.heard_text}\nResponse: {conversation.response_text}"

        extracted = await self.extract_topics(text, user_id)
        stored_topics = []

        for topic_data in extracted:
            # Check if topic already exists for user
            existing = (
                self.db.query(Topic)
                .filter(
                    Topic.user_id == user_id,
                    Topic.name.ilike(topic_data["topic_name"]),
                )
                .first()
            )

            if existing:
                # Update frequency and last discussed
                existing.frequency += 1
                existing.last_discussed_at = datetime.utcnow()
                topic = existing
            else:
                # Create new topic
                topic = Topic(
                    user_id=user_id,
                    name=topic_data["topic_name"],
                    category=topic_data.get("category", "general"),
                    frequency=1,
                    last_discussed_at=datetime.utcnow(),
                )
                self.db.add(topic)
                self.db.flush()

            # Link topic to conversation
            conv_topic = ConversationTopic(
                conversation_id=conversation.id,
                topic_id=topic.id,
                relevance_score=topic_data.get("importance", 5) / 10.0,
            )
            self.db.add(conv_topic)
            stored_topics.append(topic)

        self.db.commit()
        return stored_topics

    async def get_user_topic_profile(self, user_id: int) -> Dict[str, Any]:
        """Get a user's topic profile for AI context."""
        topics = (
            self.db.query(Topic)
            .filter(Topic.user_id == user_id)
            .order_by(Topic.frequency.desc())
            .limit(20)
            .all()
        )

        profile = {
            "frequent_topics": [],
            "topic_categories": {},
            "expertise_areas": [],
        }

        for topic in topics:
            topic_info = {
                "name": topic.name,
                "category": topic.category,
                "frequency": topic.frequency,
                "last_discussed": (
                    topic.last_discussed_at.isoformat()
                    if topic.last_discussed_at
                    else None
                ),
            }
            profile["frequent_topics"].append(topic_info)

            # Count by category
            cat = topic.category or "general"
            profile["topic_categories"][cat] = (
                profile["topic_categories"].get(cat, 0) + topic.frequency
            )

            # High frequency topics are expertise areas
            if topic.frequency >= 5:
                profile["expertise_areas"].append(topic.name)

        return profile

    async def find_related_topics(
        self, topic_name: str, user_id: int, limit: int = 5
    ) -> List[Topic]:
        """Find topics related to a given topic for the user."""
        # Get all user topics
        user_topics = (
            self.db.query(Topic).filter(Topic.user_id == user_id).all()
        )

        # Use Claude to find related topics
        topic_names = [t.name for t in user_topics]

        if not topic_names:
            return []

        prompt = f"""Given the topic "{topic_name}", find the most related topics from this list:
{json.dumps(topic_names)}

Return the top {limit} most related topics in order of relevance.
Respond as a JSON array of topic names: ["topic1", "topic2", ...]"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            if "```" in content:
                content = content.split("```")[1].split("```")[0]
                if content.startswith("json"):
                    content = content[4:]

            related_names = json.loads(content.strip())

            return [t for t in user_topics if t.name in related_names]

        except Exception as e:
            print(f"Related topics error: {e}")
            return []

    async def update_learning_profile_topics(self, user_id: int) -> None:
        """Update user's learning profile with topic data."""
        topic_profile = await self.get_user_topic_profile(user_id)

        profile = (
            self.db.query(UserLearningProfile)
            .filter(UserLearningProfile.user_id == user_id)
            .first()
        )

        if profile:
            profile.frequent_topics = {
                t["name"]: t["frequency"]
                for t in topic_profile["frequent_topics"]
            }
            profile.topic_expertise = {
                name: 0.8 for name in topic_profile["expertise_areas"]
            }
            profile.updated_at = datetime.utcnow()
            self.db.commit()
