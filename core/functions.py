import json, orjson
import discord
from datetime import datetime, timedelta, timezone
import asyncio
import functools
from typing import Optional, Any
from deep_translator import GoogleTranslator
import aiohttp
import ast
import inspect
import re
import traceback

import os
from dotenv import load_dotenv

load_dotenv()

embed_link = os.getenv('embed_default_link')
KeJCID = os.getenv('KeJC_ID')
TempHypixelApiKey = os.getenv('tmp_hypixel_api_key')
NewsApiKEY = os.getenv("news_api_KEY")
nasaApiKEY = os.getenv("nasa_api_KEY")
unsplashKEY = os.getenv('unsplash_api_access_KEY')

def read_json(path: str) -> Optional[Any]:
    """將path讀取成物件並回傳"""
    try:
        with open(path, mode='rb') as f:
            data = orjson.loads(f.read())
        return data
    except orjson.JSONDecodeError as e:
        print(f"JSON 解碼錯誤: {e}")
        return None
    except FileNotFoundError as e:
        print(f"文件未找到: {e}")
        return None
    except Exception as e:
        print(f"其他錯誤: {e}")
        return None

def write_json(obj, path: str):
    """將物件寫入path當中， indent=4, ensure_ascii=False"""
    with open(path, mode='w', encoding='utf8') as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)


def create_basic_embed(title = None, description = None, color = discord.Color.blue(), 功能:str = None, time=True):
    '''
    會設定discord.Embed(title, description, color, timestamp)
        embed.set_author(功能, embed_default_link)
    功能會跑去author
    '''

    embed=discord.Embed(title=title if title is not None else None, description=description, color=color, timestamp=datetime.now() if time else None)
    if 功能 is not None: embed.set_author(name=功能, icon_url=embed_link)
    return embed

def UnixNow() -> int:
    '''傳送現在的Unix時間'''
    timestamp = int(datetime.now().timestamp())
    return timestamp

def UnixToReadable(timestamp) -> str:
    '''將timestamp轉成可閱讀的時間'''
    if timestamp > 10**10:  # 通常 10^10 以上的數字是毫秒級
        timestamp /= 1000  # 轉換為秒級別
    dt_object = datetime.fromtimestamp(timestamp)
    formatted_time = dt_object.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_time

def strToDatetime(time_str: str) -> datetime:
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    return dt

def FormatTime(time: datetime) -> str:
    return time.strftime('%Y/%m/%d %H:%M:%S')

def current_time(UTC: int = 8) -> str:
    '''回傳現在時間(str)，arg: UTC: 使用者所提供的時區'''
    time = datetime.now(timezone(timedelta(hours=UTC)))
    return FormatTime(time)

async def thread_pool(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor=None, func=functools.partial(func, *args, **kwargs))

def secondToReadable(seconds: str):
    '''將傳入的秒數轉換為01:01:01的形式'''
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    elif minutes > 0:
        return f"00:{minutes:02d}:{seconds:02d}"
    else:
        return f"00:00:{seconds:02d}"
    
def translate(text, source:str='auto', target:str='zh-TW') -> str:
    '''將文本翻譯'''   
    translator = GoogleTranslator(source=source, target=target)
    translated_text = translator.translate(text) 
    return translated_text

def get_attachment(msg: discord.Message, to_base64:bool=False) -> list:
    a = [
        attachment.url
        for attachment in msg.attachments
        if attachment.content_type and attachment.content_type.startswith('image/')
    ]
    if to_base64:
        from cmds.AIsTwo.utils import image_url_to_base64
        a = [image_url_to_base64(u) for u in a]
    return a

def math_round(x: float, ndigits: int = 0) -> int:
    factor = 10 ** ndigits
    if x >= 0: return int(x * factor + 0.5) / factor
    else: return int(x * factor - 0.5) / factor

async def download_image(url: str, filename: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(f'./cmds/data.json/{filename}', "wb") as f:
                    f.write(await response.read())

settings = read_json('setting.json')
admins = read_json('./cmds/data.json/admins.json')['admins']