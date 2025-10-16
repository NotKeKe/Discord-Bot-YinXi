from datetime import datetime, timezone
import yt_dlp
import asyncio
from discord.ext import commands
from concurrent.futures import ProcessPoolExecutor

from core.mongodb import MongoDB_DB

from .utils import convert_to_short_url, is_url, Semaphore_multi_processing_pool
from .player import Player, loop_option

db = MongoDB_DB.music
metas_coll = db['metas']
custom_play_list_coll = db['custom_play_list']

def get_url_title(url: str) -> dict:
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'title': info['title'],
            'duration': info['duration'], # 原本就是 int
            'thumbnail': info['thumbnail'],
        }

async def add_to_custom_list(url: str, list_name: str, user_id: int) -> str | bool:
    """將使用者指定的連結，加入 MongoDB 當中

    Returns:
        str: True | 'Invaild url'
    """    
    if not is_url(url): return 'Invaild url'
    short_url = convert_to_short_url(url)
    if not short_url: return 'Cannot convert your url to "https://youtu.be/..."'

    # add to metas
    _filter = {'type': 'custom_play_list', 'user_id': user_id, 'list_name': list_name}
    if not (await metas_coll.find_one(_filter)):
        await metas_coll.insert_one(
            _filter | 
            {
                'list_played_times': 0, 
                'list_created_at': datetime.now(timezone.utc).isoformat(), 
                'list_last_played_at': ''
            }
        )

    _filter = {'user_id': user_id, 'list_name': list_name, 'video_url': short_url}
    if not (await custom_play_list_coll.find_one(_filter)):
        # 取得影片資訊
        loop = asyncio.get_running_loop()
        async with Semaphore_multi_processing_pool:
            with ProcessPoolExecutor() as executor:
                result: dict = await loop.run_in_executor(executor, get_url_title, short_url)
        title = result['title']
        duration = result['duration']
        thumbnail = result['thumbnail']

        # 加進 custom_play_list collection
        await custom_play_list_coll.insert_one(
            _filter | {
                'title': title, 
                'duration_int': duration, 
                'thumbnail_url': thumbnail, 
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
        )

    return True

async def del_custom_list(list_name: str, user_id: int):
    _filter = {'user_id': user_id, 'list_name': list_name}
    await custom_play_list_coll.delete_many(_filter)
    await metas_coll.delete_one(_filter | {'type': 'custom_play_list'})

async def get_custom_list(list_name: str, user_id: int) -> list[tuple[str, str]]:
    _filter = {'user_id': user_id, 'list_name': list_name}
    results = []
    async for song in custom_play_list_coll.find(_filter):
        results.append((song['title'], song['video_url']))
    return results

class CustomListPlayer:
    '''這個類主要用於將 custom_play_list 的歌曲 加進 Player 物件當中'''
    def __init__(self, ctx: commands.Context, list_name: str):
        self.user_id = ctx.author.id
        self.player = Player(ctx)
        self.ctx = ctx
        self.list_name = list_name

        self.songs: list[str] = [] # list[url]
    
    async def load_songs(self):
        _filter = {'user_id': self.user_id, 'list_name': self.list_name}
        async for song in custom_play_list_coll.find(_filter):
            self.songs.append(song['video_url'])

        # 順便修改 metas 的 list_last_played_at
        new_doc = await metas_coll.find_one_and_update(
            {'user_id': self.user_id, 'type': 'custom_play_list', 'list_name': self.list_name},
            {
                '$set': {'list_last_played_at': datetime.now(timezone.utc).isoformat()},
                '$inc': {'list_played_times': 1}
            },
            return_document=True, # 回傳更新後的 doc
            upsert=True
        )
        self.new_doc = new_doc

    async def add_songs_to_player(self):
        await self.player.add(self.songs[0], self.ctx)

        # 先讓第一首歌出去後，剩下的歌用背景任務的方式新增，避免使用者等待過久
        async def task():
            for song in self.songs[1:]:
                await self.player.add(song, self.ctx)

        asyncio.create_task(task())

    def change_loop_status(self):
        self.player.loop(self.new_doc.get('loop_status') or 'None')

    def cover_functions(self):
        # cover turn_loop function
        _filter = {'user_id': self.user_id, 'type': 'custom_play_list', 'list_name': self.list_name}
        def turn_loop(self: Player):
            index = loop_option.index(self.loop_status)
            index = (index + 1) % len(loop_option)
            self.loop_status = loop_option[index]

            async def change_to_metas():
                await metas_coll.update_one(
                    _filter,
                    {'$set': {'loop_status': self.loop_status}},
                    upsert=True
                )
            asyncio.create_task(change_to_metas())

        self.player.turn_loop = turn_loop.__get__(self.player) # what is this um

    async def run(self) -> Player:
        await self.load_songs()
        await self.add_songs_to_player()
        self.change_loop_status()
        self.cover_functions()
        return self.player