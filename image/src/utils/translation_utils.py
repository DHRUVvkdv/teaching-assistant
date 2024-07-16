# utils/translation_utils.py

import logging
from deep_translator import GoogleTranslator


async def translate_text(text: str, target_language: str) -> str:
    if not text:
        return ""

    try:
        translator = GoogleTranslator(source="auto", target=target_language)
        translated = translator.translate(text)
        return translated
    except Exception as e:
        logging.error(f"Failed to translate text: {str(e)}")
        return text  # Return original text if translation fails


async def translate_dict(data: dict, target_language: str) -> dict:
    translated_data = {}
    for key, value in data.items():
        logging.info(f"Translating key: {key}, value: {value[:100]}....")
        if isinstance(value, str):
            translated_data[key] = await translate_text(value, target_language)
        elif isinstance(value, list):
            translated_data[key] = [
                (
                    await translate_text(item, target_language)
                    if isinstance(item, str)
                    else item
                )
                for item in value
            ]
        else:
            translated_data[key] = value
    return translated_data
