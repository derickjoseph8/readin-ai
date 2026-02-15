"""Language Service for multi-language AI responses."""

from typing import Dict, Optional

# Supported languages with their names and AI instructions
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "en": {
        "name": "English",
        "native_name": "English",
        "instruction": "Respond in English.",
    },
    "es": {
        "name": "Spanish",
        "native_name": "Español",
        "instruction": "Responde en español. Respond entirely in Spanish.",
    },
    "sw": {
        "name": "Swahili",
        "native_name": "Kiswahili",
        "instruction": "Jibu kwa Kiswahili. Respond entirely in Swahili (Kiswahili).",
    },
}

DEFAULT_LANGUAGE = "en"


def get_language_instruction(language_code: str) -> str:
    """Get the AI instruction for generating responses in a specific language.

    Args:
        language_code: The language code (en, es, sw)

    Returns:
        The instruction string to include in AI prompts
    """
    language = SUPPORTED_LANGUAGES.get(language_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    return language["instruction"]


def get_language_name(language_code: str) -> str:
    """Get the display name for a language code.

    Args:
        language_code: The language code (en, es, sw)

    Returns:
        The display name of the language
    """
    language = SUPPORTED_LANGUAGES.get(language_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    return language["name"]


def get_native_language_name(language_code: str) -> str:
    """Get the native name for a language code.

    Args:
        language_code: The language code (en, es, sw)

    Returns:
        The native name of the language
    """
    language = SUPPORTED_LANGUAGES.get(language_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    return language["native_name"]


def is_supported_language(language_code: str) -> bool:
    """Check if a language code is supported.

    Args:
        language_code: The language code to check

    Returns:
        True if the language is supported
    """
    return language_code in SUPPORTED_LANGUAGES


def get_supported_languages() -> Dict[str, Dict[str, str]]:
    """Get all supported languages.

    Returns:
        Dictionary of supported languages with their metadata
    """
    return SUPPORTED_LANGUAGES.copy()


def get_localized_prompt_suffix(language_code: str) -> str:
    """Get a prompt suffix that instructs the AI to respond in the specified language.

    Args:
        language_code: The language code (en, es, sw)

    Returns:
        A prompt suffix with language instructions
    """
    if language_code == "en":
        return ""

    language = SUPPORTED_LANGUAGES.get(language_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])

    return f"""

IMPORTANT LANGUAGE INSTRUCTION:
{language['instruction']}
All text content in your response must be in {language['name']} ({language['native_name']}).
JSON keys should remain in English, but all values containing text for the user should be in {language['name']}.
"""


# Pre-translated common phrases for fallback responses
FALLBACK_TRANSLATIONS = {
    "en": {
        "unable_to_generate": "Unable to generate response",
        "error_occurred": "An error occurred",
        "no_data": "No data available",
        "summary_unavailable": "Summary unavailable",
    },
    "es": {
        "unable_to_generate": "No se pudo generar la respuesta",
        "error_occurred": "Ocurrió un error",
        "no_data": "No hay datos disponibles",
        "summary_unavailable": "Resumen no disponible",
    },
    "sw": {
        "unable_to_generate": "Haiwezekani kutengeneza jibu",
        "error_occurred": "Kosa limetokea",
        "no_data": "Hakuna data inayopatikana",
        "summary_unavailable": "Muhtasari haupatikani",
    },
}


def get_fallback_message(key: str, language_code: str) -> str:
    """Get a pre-translated fallback message.

    Args:
        key: The message key (unable_to_generate, error_occurred, etc.)
        language_code: The language code

    Returns:
        The translated message or English fallback
    """
    translations = FALLBACK_TRANSLATIONS.get(
        language_code, FALLBACK_TRANSLATIONS[DEFAULT_LANGUAGE]
    )
    return translations.get(key, FALLBACK_TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
