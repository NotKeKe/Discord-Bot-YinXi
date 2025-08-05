from .model_select import model_select
from .process_tag import get_think, clean_text
from .auto_complete import chat_history_autocomplete, model_autocomplete

__all__ = ['model_select', 'get_think', 'clean_text', 'chat_history_autocomplete', 'model_autocomplete']

def to_system_message(prompt: str) -> list:
    return [{'role': 'system', 'content': prompt}]

def to_user_message(prompt: str) -> list:
    return [{'role': 'user', 'content': prompt}]

def to_assistant_message(prompt: str) -> list:
    return [{'role': 'assistant', 'content': prompt}]