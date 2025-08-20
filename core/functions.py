import json, orjson
import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
import asyncio
import functools
from typing import Optional, Any, List
from deep_translator import GoogleTranslator
import aiohttp
import os
import traceback
import inspect
import base64
import aiohttp
from urllib.parse import quote_plus
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis

import os
from dotenv import load_dotenv

load_dotenv()

# embed_link = os.getenv('embed_default_link')
yinxi_base_url = os.getenv('yinxi_base_url') # 這是我網域的基礎連結 https://yinxi.wales.com.tw
def get_embed_link() -> str:
    # 取得自己的圖片，並使用連結獲得
    path = f'./image/self.png'
    absolute_path = os.path.abspath(path)

    base_url = f'{yinxi_base_url}/api/image/?path='
    base_url += absolute_path
    return base_url

BASE_DIR = os.path.abspath(os.path.dirname(__name__))

embed_link = get_embed_link()
KeJCID = os.getenv('KeJC_ID')
TempHypixelApiKey = os.getenv('tmp_hypixel_api_key')
NewsApiKEY = os.getenv("news_api_KEY")
nasaApiKEY = os.getenv("nasa_api_KEY")
unsplashKEY = os.getenv('unsplash_api_access_KEY')
GIPHYKEY = os.getenv('GIPHY_KEY')
GENIUS_ACCESS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')

# mongo db
MONGO_USER = quote_plus(os.getenv('MONGO_USER'))
MONGO_PASSWORD = quote_plus(os.getenv('MONGO_PASSWORD'))

# Redis
redis_client = redis.Redis(
    host='redis', 
    port=6379, 
    db=0,
    decode_responses=True
)

def read_json(path: str) -> Optional[Any]:
    """將path讀取成物件並回傳"""
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            print(path + ' 不存在或為空，初始化為 {}')
            with open(path, 'wb') as f:
                f.write(orjson.dumps({}))
            return {}

        with open(path, mode='rb') as f:
            data = orjson.loads(f.read())
        return data
    except orjson.JSONDecodeError as e:
        print(f"JSON 解碼錯誤: {e}")
        return {}
    except Exception as e:
        print(f"其他錯誤: {e}")
        return None

def write_json(obj, path: str):
    """將物件寫入path當中， indent=4, ensure_ascii=False"""
    try:
        with open(path, mode='w', encoding='utf8') as f:
            json.dump(obj, f, indent=4, ensure_ascii=False)
            f.flush()
    except FileNotFoundError as e:
        print(f"文件未找到: {e}")
        return
    except Exception as e:
        print(f"其他錯誤: {traceback.format_exc()}")
        return


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
    '''傳送現在的Unix時間 (秒級)'''
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
    return time.strftime('%Y/%m/%d %H:%M:%S %A')

def current_time(UTC: int = 8) -> str:
    '''回傳現在時間(str)，arg: UTC: 使用者所提供的時區'''
    time = datetime.now(timezone(timedelta(hours=UTC)))
    return FormatTime(time)

async def thread_pool(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor=None, func=functools.partial(func, *args, **kwargs))

def secondToReadable(seconds):
    '''將傳入的秒數轉換為01:01:01的形式'''
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    elif minutes > 0:
        return f"00:{minutes:02d}:{seconds:02d}"
    else:
        return f"00:{seconds:02d}"
    
def translate(text, source:str='auto', target:str='zh-TW') -> str:
    '''將文本翻譯'''   
    translator = GoogleTranslator(source=source, target=target)
    translated_text = translator.translate(text) 
    return translated_text

async def async_translate(text: str, source:str='auto', target:str='zh-TW'):
    return await asyncio.to_thread(translate, text, source, target)

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

def math_round(x: float, ndigits: int = 0) -> float:
    factor = 10 ** ndigits
    if x >= 0: return int(x * factor + 0.5) / factor
    else: return int(x * factor - 0.5) / factor

async def download_image(url: str, filename: str = None, path: str = None):
    """下載圖片

    Args:
        url (str): 圖片連結
        filename (str, optional): 預設下載到`./cmds/data.json/{filename}`，filename必須包括副檔名，跟path二選一輸入. Defaults to None.
        path (str, optional): 下載到`{path}`，跟filename二選一輸入. Defaults to None.
    """    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(f'./cmds/data.json/{filename}' if not path else path, "wb") as f:
                    f.write(await response.read())

def to_abspath(path: str) -> str:
    '''將相對路徑轉為絕對路徑'''
    return os.path.abspath(path)

def is_KeJC(userID: int):
    return str(userID) == KeJCID

settings = read_json('setting.json')
if not settings: print('Please add `setting.json` to current path.')

try: admins: List[int] = read_json('./cmds/data.json/admins.json')['admins']
except TypeError: print('Cannot fetch ./cmds/data.json/admins.json')
except: traceback.print_exc()

if settings:
    testing_guildID: int = settings['testing_guildID']
    DEVICE_IP: str = settings.get('DEVICE_IP')
    OLLAMA_IP: str = settings.get('OLLAMA_IP')
    BASE_OLLAMA_URL: str = f'http://{OLLAMA_IP}:11434'
else:
    testing_guildID: int = 123456789
    DEVICE_IP: str = '127.0.0.1'
    OLLAMA_IP: str = '127.0.0.1'
    BASE_OLLAMA_URL: str = f'http://{OLLAMA_IP}:11434'

MONGO_URL = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{DEVICE_IP}:27020/"
mongo_db_client = AsyncIOMotorClient(MONGO_URL)

def is_testing_guild():
    '''A guild checking function for commands.command'''
    def preficate(ctx: commands.Context):
        return ctx.guild.id == testing_guildID
    return commands.check(preficate)

def is_async(func) -> bool:
    return inspect.iscoroutinefunction(func)

async def image_to_base64(image_url: str) -> str:
    '''Conver image url to base64'''
    async with aiohttp.ClientSession() as sess:
        async with sess.get(image_url) as resp:
            if resp.status != 200: return ''
            image_data = await resp.read()
            return base64.b64encode(image_data).decode('utf-8')
    return ''

def split_str_by_len(text: str, chunk_size: int) -> list[str]:
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def split_str_by_len_and_backtick(text: str, chunk_size: int = 1800) -> list[str]:
    '''
    Gemini win :sob:
    cmds/useless/20250809 me.py
    '''
    lines = text.splitlines()
    chunks: list[list[str]] = []
    chunk: list[str] = []
    str_len = 0
    in_backtick = False
    curr_lang = ''

    for line in lines:
        # 判斷如果加入這行，長度是否會超過
        # 換行符要算進去，所以+1
        if chunk and (str_len + len(line) + 1) > chunk_size:
            # 超過長度，準備封裝目前的 chunk
            if in_backtick:
                chunk.append('```')
            
            chunks.append(chunk) # 儲存舊的 chunk

            # 建立新的 chunk
            if in_backtick:
                # 如果之前在程式碼區塊中，新 chunk 要以它開頭
                new_chunk_header = f'```{curr_lang}'
                chunk = [new_chunk_header]
                str_len = len(new_chunk_header)
            else:
                chunk = []
                str_len = 0
        
        # 把當前行加到 chunk (可能是舊的也可能是新的)
        # 如果 chunk 已經有內容，要加上換行符的長度
        str_len += (1 if chunk else 0) + len(line)
        chunk.append(line)

        # 在行的最後，根據內容更新 backtick 狀態給下一次迴圈用
        if line.strip().startswith('```'):
            if not in_backtick:
                # 進入程式碼區塊
                in_backtick = True
                curr_lang = line.strip()[3:]
            else:
                # 離開程式碼區塊
                in_backtick = False
                curr_lang = ''
    
    # 不要忘記最後一個 chunk
    if chunk:
        chunks.append(chunk)

    return ['\n'.join(c) for c in chunks]
