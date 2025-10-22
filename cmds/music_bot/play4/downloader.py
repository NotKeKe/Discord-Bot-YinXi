import re
import yt_dlp
from pytubefix import YouTube
from datetime import datetime
import asyncio
from concurrent.futures import ProcessPoolExecutor

from cmds.music_bot.play4 import utils
from core.functions import math_round, secondToReadable, redis_client
from .utils import get_video_id, check_audio_url_alive

def extract_info(video_url: str):
    with yt_dlp.YoutubeDL(utils.YTDL_OPTIONS) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return {
            "audio_url": info.get("url"),
            "thumbnail_url": info.get("thumbnail"),
            "title": info.get("title"),
            "duration": info.get("duration"),
        }
    
def extract_info_pytube(video_url: str):
    yt = YouTube(video_url)
    return {
        "audio_url": yt.streams.filter(only_audio=True).order_by('abr').desc().first().url,
        "thumbnail_url": yt.thumbnail_url,
        "title": yt.title,
        "duration": yt.length,
    }

class RedisTemp:
    redis_base_key = 'musics:'

    @classmethod
    async def search(cls, video_url: str) -> dict | None:
        video_id = get_video_id(video_url)
        if not video_id: return

        key = cls.redis_base_key + video_id

        data = await redis_client.hgetall(key)
        if data:
            d = data.copy()

            audio_url = d['audio_url']
            # 確認 audio url 可用，不用特別刪除，因為後面在搜尋一次時，就會覆蓋掉原本的 key
            if not (await check_audio_url_alive(audio_url)): return

            return d | {'duration_int': int(d['duration_int'])}

    @classmethod
    async def upload(cls, title, video_url, audio_url, thumbnail_url, duration, duration_int):
        video_id = get_video_id(video_url)
        if not video_id: return
        key = cls.redis_base_key + video_id

        data = {
            'title': title,
            'video_url': video_url,
            'audio_url': audio_url,
            'thumbnail_url': thumbnail_url,
            'duration': duration,
            'duration_int': duration_int
        }

        await redis_client.hset(key, mapping=data)
        await redis_client.expire(key, 60*60) # 60 分鐘後過期

class Downloader:
    '''User await Downloader(query).run()'''
    def __init__(self, query: str):
        self.query = query

        self.title = None
        self.video_url = None
        self.audio_url = None
        self.thumbnail_url = None
        self.duration = None
        self.duration_int = None

        self.start_time = datetime.now()
        self.process_time = 0

    def get_info(self) -> tuple:
        '''return (title, video_url, audio_url, thumbnail_url, duration)'''
        return (self.title, self.video_url, self.audio_url, self.thumbnail_url, self.duration, self.duration_int)

    async def get_url(self):
        if utils.is_url(self.query):
            self.video_url = self.query
        else:
            # self.title, self.video_url, self.duration = utils.query_search(self.query)
            self.title, self.video_url, self.duration = await asyncio.to_thread(utils.query_search, self.query)

    async def to_audio(self):
        if not self.video_url: print('Please get_url first'); return

        cache = await RedisTemp.search(self.video_url)
        if cache:
            for key, value in cache.items():
                setattr(self, key, value)
            return

        loop = asyncio.get_running_loop()
        # 使用多進程, get result
        async with utils.Semaphore_multi_processing_pool:
            with ProcessPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, extract_info, self.video_url)
        
                # check if audio url from yt-dlp is available, else use pytubefix (其實不需要用到多現程 但為了統一 我還用了)
                if not (await check_audio_url_alive(result["audio_url"])): 
                    result = await loop.run_in_executor(executor, extract_info_pytube, self.video_url)

        # 更新 self 的屬性
        self.audio_url = result["audio_url"]
        self.thumbnail_url = result["thumbnail_url"]
        self.title = result["title"]
        self.duration = secondToReadable(result["duration"])
        self.duration_int = result["duration"]

        self.process_time = math_round((datetime.now() - self.start_time).total_seconds(), 0)

        # add to redis
        func = RedisTemp.upload(self.title, self.video_url, self.audio_url, self.thumbnail_url, self.duration, self.duration_int)
        asyncio.create_task(func)

    async def run(self):
        await self.get_url()
        await self.to_audio()