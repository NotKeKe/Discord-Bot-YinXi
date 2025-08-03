import re

def get_think(text):
    think_content = re.search(r'<think>(.*?)</think>', text, re.DOTALL)

    if think_content:
        return think_content.group(1).strip()
    else: return ''

def clean_text(text):
    '''清除工具調用以及think'''
    clean_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.DOTALL)
    return clean_text