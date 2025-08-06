from .model_select import model_select, split_provider_model
from .process_tag import get_think, clean_text
from .auto_complete import chat_history_autocomplete, model_autocomplete
from .button import add_think_button, add_history_button

__all__ = ['model_select', 'get_think', 'clean_text', 'chat_history_autocomplete', 'model_autocomplete', 'add_think_button', 'add_history_button', 'split_provider_model']

def to_system_message(prompt: str) -> list:
    return [{'role': 'system', 'content': prompt}]

def to_user_message(prompt: str) -> list:
    return [{'role': 'user', 'content': prompt}]

def to_assistant_message(prompt: str) -> list:
    return [{'role': 'assistant', 'content': prompt}]