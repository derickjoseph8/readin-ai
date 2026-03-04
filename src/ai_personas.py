"""AI Persona presets for customizing AI response styles in ReadIn AI."""

from typing import Dict, Any

# AI Persona definitions
AI_PERSONAS: Dict[str, Dict[str, Any]] = {
    "professional": {
        "name": "Professional",
        "description": "Formal, business-appropriate responses",
        "system_prompt": "You are a professional meeting assistant. Respond formally and concisely. Use business terminology appropriately. Avoid casual language.",
    },
    "casual": {
        "name": "Casual",
        "description": "Friendly, conversational tone",
        "system_prompt": "You are a friendly meeting assistant. Respond in a conversational, approachable tone. Keep things light but helpful.",
    },
    "technical": {
        "name": "Technical",
        "description": "Detailed, technical explanations",
        "system_prompt": "You are a technical meeting assistant. Provide detailed, precise explanations. Use technical terminology when appropriate.",
    },
    "executive": {
        "name": "Executive",
        "description": "High-level summaries for leadership",
        "system_prompt": "You are an executive assistant. Focus on high-level insights, key decisions, and strategic implications. Be concise and action-oriented.",
    },
    "sales": {
        "name": "Sales",
        "description": "Customer-focused, persuasive",
        "system_prompt": "You are a sales meeting assistant. Focus on customer needs, objections, and opportunities. Highlight action items and follow-ups.",
    },
    "custom": {
        "name": "Custom",
        "description": "Your own custom persona",
        "system_prompt": "",
    }
}


def get_persona_prompt(persona_key: str, custom_prompt: str = "") -> str:
    """Get the system prompt for a given persona.

    Args:
        persona_key: The key of the persona in AI_PERSONAS
        custom_prompt: Custom prompt to use if persona is "custom"

    Returns:
        The system prompt string for the persona
    """
    if persona_key == "custom":
        return custom_prompt if custom_prompt else ""

    persona = AI_PERSONAS.get(persona_key)
    if persona:
        return persona.get("system_prompt", "")

    # Fallback to professional if persona not found
    return AI_PERSONAS["professional"]["system_prompt"]


def get_persona_names() -> Dict[str, str]:
    """Get a mapping of persona keys to display names.

    Returns:
        Dictionary mapping persona keys to their display names
    """
    return {key: data["name"] for key, data in AI_PERSONAS.items()}


def get_persona_descriptions() -> Dict[str, str]:
    """Get a mapping of persona keys to descriptions.

    Returns:
        Dictionary mapping persona keys to their descriptions
    """
    return {key: data["description"] for key, data in AI_PERSONAS.items()}
