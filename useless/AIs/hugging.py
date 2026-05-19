from huggingface_hub import InferenceClient
import re

from cmds.AIs.info import *

default_system_chat = [
    {
        'role': 'system',
        'content': '你的名字是克克的分身，是一個由台灣高中生所製作出來的Discord Bot，而你的任務是使用輕鬆的語氣，並且一定要增加一些顏文字(如: (つ´ω`)つ)來回應使用者的訊息。'+
                '如果使用者需要你寫出code的話，則需要加入註解。輸出內容要在1024個字元以內。' + 
                '而使用者如果像你提問問題的話，你必須要在解決問題後，為使用者提出至少一點建議。' + 
                '如果提供了使用者ID，則在對話內容中僅使用相同使用者ID的前後文。' + 
                '每次對話的使用者可能都會不一樣。' +
                '如果使用者使用繁體中文輸入，那你也必須全程以繁體中文做輸出。'
    }
]

def clean_text(text):
    '''清除deepseek的think'''
    clean_text = re.sub(r'<think>(.*?)</think>', '', text, flags=re.DOTALL)
    return clean_text

def get_thinking(text):
    '''獲得deepseek中的think'''
    think_content = re.search(r'<think>(.*?)</think>', text, re.DOTALL)

    if think_content:
        return think_content.group(1).strip()

def get_provider(module_name):
    for module in available_modules:
        if module['module'] == module_name:
            return module['provider']

def chat(content, model, history = None):
    provider = get_provider(model)

    client = InferenceClient(
        provider=provider,
        api_key=HUGGINGKEY
    )

    system = default_system_chat

    message = [
        {
            "role": "user",
            "content": content
        }
    ]

    if history is None: history = []
    messages = system + history + message
   

    completion = client.chat.completions.create(
        model=model, 
        messages=messages, 
        max_tokens=1024,
        temperature=0.7
    )

    generated = completion.choices[0].message.content
    think = get_thinking(generated) or None 
    result = clean_text(generated)

    return think, result