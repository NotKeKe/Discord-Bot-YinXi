import base64
from PIL import Image
from io import BytesIO
import requests
from datetime import datetime
import re
import discord
from discord import app_commands
import traceback
import typing
from openai import OpenAI
from core.functions import KeJCID

BOTNAME = '尖峰'

def image_size(image_base64) -> str:
    image_data = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_data))

    # 获取圖片大小
    width, height = image.size
    return f'{width}x{height}'

def image_url_to_base64(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        base64_string = base64.b64encode(response.content).decode('utf-8')
        return base64_string
    else:
        return None
    
def on_timeout(time):
    t = datetime.now() - datetime.fromtimestamp(timestamp=time)
    if t.total_seconds() > 1200:
        return True
    
def to_user_message(prompt: str, userID: str = None, attachments: list = None, time: str = None) -> list:
    return [{'role': 'user', 'content': prompt, **({'userID': userID} if userID else {}), **({'images': attachments} if attachments else {}), **({'time': time} if time else {})}]

def to_system_message(prompt: str) -> list:
    return [{'role': 'system', 'content': prompt}]

def to_assistant_message(prompt: str, reasoning: str = None) -> list:
    return [{'role': 'assistant', 'content': prompt, **({'reasoning': reasoning} if reasoning is not None and reasoning != '' else {})}]

def clean_text(text):
    '''清除工具調用以及think'''
    clean_text = re.sub(r'<[^>]+>.*?</[^>]+>', '', text, flags=re.DOTALL)
    return clean_text

def get_thinking(text):
    '''獲得deepseek中的think, return str or None'''
    think_content = re.search(r'<think>(.*?)</think>', text, re.DOTALL)

    if think_content:
        return think_content.group(1).strip()
    else: return ''

def get_pref(text: str):
    '''從文字中提取使用者喜好'''
    pref = re.search(r'<preference>(.*?)</preference>', text, re.DOTALL)

    if pref:
        return pref.group(1).strip()
    else: return ''

def get_user_data(text: str):
    '''從文字中提取使用者的資訊'''
    data = re.search(r'<data>(.*?)</data>', text, re.DOTALL)

    if data:
        return data.group(1).strip()
    else: return ''

def choice_model(model:str):
    from cmds.AIsTwo.base_chat import zhipu_moduels, openrouter_moduels, ollama_modules, gemini_moduels
    from cmds.AIsTwo.base_chat import base_openrouter_chat, base_zhipu_chat, base_ollama_chat, base_gemini_chat
    if model in zhipu_moduels: return base_zhipu_chat
    elif model in openrouter_moduels: return base_openrouter_chat
    elif model in ollama_modules: return base_ollama_chat
    elif model in gemini_moduels: return base_gemini_chat

def halfToFull(content: str) -> str:
    '''將文字中的全形標點符號轉為半形'''
    return content.replace('，', '  ').replace('？', '? ').replace('！', '! ').replace('：', ': ')

def is_vision_model(model: str, client) -> bool:
    from cmds.AIsTwo.base_chat import gemini_moduels, ollama_modules, openrouter_moduels, true_ollama
    try:
        if model in gemini_moduels: return True
        elif 'vision' in model.lower(): return True
        elif model in ollama_modules: 
            model_info = str(true_ollama.show(model)).lower()
            if 'vision' in model_info or 'clip' in model_info:
                return True
        elif model in openrouter_moduels:
            if 'vision' in next((x.description.lower() for x in client.models.list().data if x.id == model)):
                return True
        return False
    except:
        traceback.print_exc()

async def select_moduels_auto_complete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    try:
        from cmds.AIsTwo.base_chat import zhipu_moduels, openrouter_moduels, ollama_modules, gemini_moduels, cerebras_models
        moduels = zhipu_moduels + openrouter_moduels + cerebras_models
        if str(interaction.user.id) == KeJCID: moduels += ollama_modules + gemini_moduels

        if current:
            moduels = [model for model in moduels if current.lower().strip() in model.lower()]

        moduels.sort()

        # 限制最多回傳 25 個結果
        return [app_commands.Choice(name=model[:100], value=model[:100]) for model in moduels[:25]]
    except:
        traceback.print_exc()