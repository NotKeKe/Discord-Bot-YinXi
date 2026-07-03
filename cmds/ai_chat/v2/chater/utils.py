import re

def get_think(text):
    think_content = re.search(r'<think>(.*?)</think>', text, re.DOTALL)

    if think_content:
        return think_content.group(1).strip()
    else: return ''

def clean_text(text):
    '''清除 think'''
    clean_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return clean_text