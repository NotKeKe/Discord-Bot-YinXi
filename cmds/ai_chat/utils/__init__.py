from .model_select import model_select
from .process_tag import get_think, clean_text

__all__ = ['model_select', 'get_think']

def to_system_message(prompt: str) -> list:
    return [{'role': 'system', 'content': prompt}]

def to_user_message(prompt: str) -> list:
    return [{'role': 'user', 'content': prompt}]