import re
import yt_dlp
from datetime import datetime
import asyncio
from concurrent.futures import ProcessPoolExecutor

from cmds.music_bot.play4 import utils
from core.functions import math_round, secondToReadable

def extract_info(video_url: str):
    with yt_dlp.YoutubeDL(utils.YTDL_OPTIONS) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return {
            "audio_url": info.get("url"),
            "thumbnail_url": info.get("thumbnail"),
            "title": info.get("title"),
            "duration": info.get("duration"),
        }

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
        self.process_time = None

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

        loop = asyncio.get_running_loop()
        # 使用多進程
        async with utils.Semaphore_multi_processing_pool:
            with ProcessPoolExecutor() as executor:
                result = await loop.run_in_executor(executor, extract_info, self.video_url)

        # 更新 self 的屬性
        self.audio_url = result["audio_url"]
        self.thumbnail_url = result["thumbnail_url"]
        self.title = result["title"]
        self.duration = secondToReadable(result["duration"])
        self.duration_int = result["duration"]

        self.process_time = math_round((datetime.now() - self.start_time).total_seconds(), 0)

    async def run(self):
        await self.get_url()
        await self.to_audio()