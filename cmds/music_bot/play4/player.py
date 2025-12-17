import discord
from discord.ext import commands
from discord import PCMVolumeTransformer
import asyncio
import traceback
from typing import Literal
from httpx import AsyncClient, Limits
import orjson
import uuid

from cmds.music_bot.play4 import utils
from cmds.music_bot.play4.downloader import Downloader
from cmds.music_bot.play4.lyrics import search_lyrics

from core.functions import create_basic_embed, current_time, secondToReadable, math_round, redis_client
from core.translator import load_translated

loop_option = ('None', 'single', 'list')
loop_type = Literal['None', 'single', 'list']

PREFER_LOOP_KEY = 'musics_prefer_loop'

class Player:
    '''Ensure the user is current in a channel, and bot already joined the channel'''
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx # 為了初始化數據，在後續的更改中不應該繼續使用當前的`ctx`
        self.query = None

        self.list = []
        self.current_index = 0
        self.loop_status: loop_type = 'None'

        self.user = ctx.author
        self.guild = ctx.guild
        self.channel = ctx.voice_client.channel
        self.voice_client = ctx.voice_client
        self.bot = ctx.bot
        self.translator = self.bot.tree.translator

        if ctx.interaction and hasattr(ctx.interaction, 'locale'):
            self.locale = ctx.interaction.locale.value
        elif ctx.guild.preferred_locale.value:
            self.locale = ctx.guild.preferred_locale.value
        else:
            self.locale = 'zh-TW'

        # volume
        self.source = None
        self.volume: float = 1
        self.transformer: PCMVolumeTransformer = None

        self.manual = False
        self.downloading = False

        # 進度條
        self.init_bar()

        # Tasks
        self.update_progress_bar_task: asyncio.Task | None = None
        self.playlist_load_task: asyncio.Task | None = None
        self.add_to_api_task: asyncio.Task | None = None
        self.update_to_api_task: asyncio.Task | None = None
        self.clean_up_task: asyncio.Task | None = None

        # api
        _limit = Limits(max_keepalive_connections=2, max_connections=2)
        self.httpx_client = AsyncClient(limits=_limit)
        self._uuid = str(uuid.uuid4())
    
    def __del__(self):
        if not self.clean_up_task:
            asyncio.create_task(self._cleanup())

    async def _cleanup(self):
        try: 
            print(f'Clean up for player: {self.ctx.guild.id}:{self._uuid}')
            tasks = []
            if self.update_progress_bar_task:
                self.update_progress_bar_task.cancel()
                tasks.append(self.update_progress_bar_task)
            if self.playlist_load_task:
                self.playlist_load_task.cancel()
                tasks.append(self.playlist_load_task)
            if self.add_to_api_task:
                self.add_to_api_task.cancel()
                tasks.append(self.add_to_api_task)
            if self.update_to_api_task:
                self.update_to_api_task.cancel()
                tasks.append(self.update_to_api_task)

            async def delete_song():
                await redis_client.srem('musics_player_ids', f'{self.ctx.guild.id}:{self._uuid}') # type: ignore
                resp = await self.httpx_client.post(url='http://api_server:3000/player/delete_song', data={'guild_id': self.ctx.guild.id, 'uuid': self._uuid})
                if resp.status_code != 200:
                    print(resp.status_code, resp.text)
                await self.httpx_client.aclose()

            tasks.append(delete_song())

            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            ...
        except:
            traceback.print_exc()

    def init_bar(self):
        self.duration_int = None
        self.passed_time = 0
        self.progress_bar = ''
        try: self.update_progress_bar_task.cancel()
        except: ...
        self.update_progress_bar_task: asyncio.Task = None

        self.paused: bool = False

    async def download(self, priority: int = 1):
        self.downloading = True
        downloader = Downloader(self.query, priority)
        await downloader.run()
        title, video_url, audio_url, thumbnail_url, duration, duration_int, subtitles = downloader.get_info()
        self.downloading = False
        return title, video_url, audio_url, thumbnail_url, duration, duration_int, subtitles
    
    async def add_playlist(self, playlist_id: str):
        # 取得 playlist 的所有 video id
        video_ids = await utils.get_all_video_ids_from_playlist(playlist_id)
        
        # 取得第一個 result
        first_result = await self.add(utils.video_id_to_url(video_ids[0]), self.ctx)

        # 創建一個 task，用於在背景新增其他歌曲
        if len(video_ids) > 1:
            async def task():
                for video_id in video_ids[1:]:
                    await self.add(utils.video_id_to_url(video_id), self.ctx, 2)

            self.playlist_load_task = asyncio.create_task(task())

        return first_result

    async def add(self, query: str, ctx: commands.Context, priority: int = 1):
        '''return len(self.list), title, video_url, audio_url, thumbnail_url, duration'''
        self.query = query

        # 加入進 redis，用於讓使用者下次快速選擇 query
        key = f'musics_query:{ctx.author.id}'
        await redis_client.lpush(key, query) # 插入 list 的 head
        await redis_client.ltrim(key, 0, 9) # 只保留前 10 個，避免過大

        play_list_id = utils.get_playlist_id(query)
        if not utils.get_video_id(query) and play_list_id: # 代表使用者傳入一個 playlist，而非帶有 playlist 的 video
            return await self.add_playlist(play_list_id)

        title, video_url, audio_url, thumbnail_url, duration, duration_int, subtitles = await self.download(priority)
        self.list.append({
            'title': title,
            'video_url': video_url,
            'audio_url': audio_url,
            'thumbnail_url': thumbnail_url,
            'duration': duration,
            'duration_int': duration_int,
            'user': ctx.author,
            'subtitles': subtitles
        })
        return len(self.list), title, video_url, audio_url, thumbnail_url, duration, subtitles
    
    async def play(self):
        self.init_bar()

        # try to get user prefer loop
        prefer_loop = await redis_client.get(f'{PREFER_LOOP_KEY}:{self.ctx.author.id}')
        if prefer_loop:
            self.loop(prefer_loop)
        
        if not self.list:
            if not self.downloading:
                print('播放列表為空')
                return
            else:
                # 等待下一首歌下載完成
                while len(self.list) - 1 == self.current_index:
                    await asyncio.sleep(0.1)

            
        # 確保連接狀態
        if not self.voice_client or not self.voice_client.is_connected(): 
            print('未連接到語音頻道')
            self.clean_up_task = asyncio.create_task(self._cleanup())
            await self.clean_up_task
            return
            
        # 停止當前播放並等待完成
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
            # 等待停止操作完成
            await asyncio.sleep(0.2)
            
        # 獲取音訊URL
        audio_url = self.list[self.current_index]['audio_url']
        self.user = self.list[self.current_index]['user']
        self.duration_int = self.list[self.current_index]['duration_int']
        
        try:
            # 播放新音訊
            self.gener_progress_bar()
            self.update_progress_bar_task = self.bot.loop.create_task(self.update_passed_time())
            self.source = discord.FFmpegPCMAudio(audio_url, **utils.ffmpeg_options)
            self.transformer = PCMVolumeTransformer(self.source, self.volume)
            if self.voice_client.is_playing():
                self.voice_client.stop()
            self.voice_client.play(
                self.transformer, 
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(e), self.bot.loop)
            )

            # 向 api 發送請求，以獲得 url
            try:
                if self.add_to_api_task:
                    self.add_to_api_task.cancel()
                    try: await self.add_to_api_task
                    except: pass
                self.add_to_api_task = asyncio.create_task(self.upload_to_api(audio_url))
                if not self.update_to_api_task:
                    self.update_to_api_task = asyncio.create_task(self.update_to_api())
            except:
                traceback.print_exc()
        except Exception as e:
            print(f'播放錯誤: {e}')
            traceback.print_exc()
            await self.ctx.send((await self.translator.get_translate('send_player_play_error', self.locale)).format(e=str(e)))

    async def upload_to_api(self, audio_url: str):
        # post to api
        srts = self.list[self.current_index].get('subtitles', {})
        await redis_client.sadd('musics_player_ids', f'{self.ctx.guild.id}:{self._uuid}')
        await self.httpx_client.post(
            f'http://api_server:3000/player/upload_song',
            data={
                'guild_id': self.ctx.guild.id,
                'uuid': self._uuid,
                'title': self.list[self.current_index]['title'],
                'audio_url': audio_url,
                'duration': self.list[self.current_index]['duration_int'],
                'srts': orjson.dumps(srts).decode()
            },
        )
    async def update_to_api(self):
        while True:
            await asyncio.sleep(3)
            if self.add_to_api_task and not self.add_to_api_task.done(): continue

            srts = self.list[self.current_index].get('subtitles', {})
            resp = await self.httpx_client.post(
                f'http://api_server:3000/player/update_song',
                data={
                    'guild_id': self.ctx.guild.id,
                    'uuid': self._uuid,
                    'title': self.list[self.current_index]['title'],
                    'audio_url': self.list[self.current_index]['audio_url'],
                    'srts': orjson.dumps(srts).decode(),
                    'duration': self.list[self.current_index]['duration_int'],
                    'current_time': self.passed_time,
                    'is_paused': self.voice_client.is_paused(),
                }
            )

            if resp.status_code == 200: continue
            print(resp.status_code, resp.text)

            if resp.status_code in (400, 404): break

    def _change_prefer_loop(self):
        if self.loop_status not in loop_option: return 'Invalid loop type'

        key = f'{PREFER_LOOP_KEY}:{self.ctx.author.id}'
        asyncio.create_task(redis_client.set(key, self.loop_status))

    def loop(self, loop_type: str):
        if loop_type not in loop_option: return 'Invalid loop type'
        self.loop_status = loop_type
        self._change_prefer_loop()

    def turn_loop(self) -> str:
        '''Return current loop type and change to next loop type'''
        index = loop_option.index(self.loop_status)
        index = (index + 1) % len(loop_option)
        self.loop_status = loop_option[index]
        self._change_prefer_loop()
        return self.loop_status

    async def back(self):
        if self.current_index - 1 < 0:
            if self.loop_status != 'list': return False
            self.current_index = len(self.list) - 1
        else:
            self.current_index -= 1

        self.manual = True
        await self.play()
        self.manual = False
        return True

    async def skip(self):
        if self.current_index + 1 > len(self.list) - 1: # 遇到超出範圍
            if self.loop_status != 'list': return False
            self.current_index = 0
        else:
            self.current_index += 1

        self.manual = True
        await self.play()
        self.manual = False
        return True
    
    async def pause(self, ctx: commands.Context = None):
        '''Pause to play music and `SEND` message to notice user'''
        ctx = ctx or self.ctx

        if self.voice_client.is_paused():
            return await ctx.send(await self.translator.get_translate('send_player_already_paused', self.locale))
        if not self.voice_client.is_playing():
            return await ctx.send(await self.translator.get_translate('send_player_not_playing', self.locale))

        self.voice_client.pause()
        self.paused = True
        return await ctx.send(await self.translator.get_translate('send_player_paused_success', self.locale), ephemeral=True)
    
    async def resume(self, ctx: commands.Context = None):
        '''Resume to play music and `SEND` message to notice user'''
        ctx = ctx or self.ctx

        # if self.voice_client.is_playing():
        #     return await ctx.send(await self.translator.get_translate('send_player_is_playing', self.locale))
        # if not self.voice_client.is_paused():
        #     return await ctx.send(await self.translator.get_translate('send_player_not_paused', self.locale))

        try:
            self.voice_client.resume()
        except:
            return
        self.paused = False
        await ctx.send(await self.translator.get_translate('send_player_resumed_success', self.locale), ephemeral=True)

    def delete_song(self, index: int):
        '''Ensure index is index not id of song'''
        item = self.list.pop(index)
        return item

    async def play_next(self, e=None):
        # 如果有錯誤，直接處理
        if e:
            self.handle_error(e)
            return
        if self.manual: return
            
        # 檢查播放列表是否為空, wait for self.list not empty
        if not self.list:
            while not self.list:
                await asyncio.sleep(0.1)
            await self.play()
            return
            
        # 更新索引
        if self.loop_status == 'None':
            if self.current_index + 1 < len(self.list):
                self.current_index += 1
            else: # 已到列表末尾且未啟用循環
                await asyncio.sleep(1)
                if not self.ctx.voice_client: return
                from cmds.play4 import players
                await self.ctx.send(await self.translator.get_translate('send_player_finished_playlist', self.locale))
                await self.voice_client.disconnect()
                del players[self.ctx.guild.id]
                del self
                return
        elif self.loop_status == 'list':
            self.current_index = (self.current_index + 1) % len(self.list)
        # single 不需要改變索引

        # print('play_next  {}  index: {}'.format(current_time(), self.current_index))
        
        # 添加短暫延遲避免重疊請求
        await asyncio.sleep(0.2)
        await self.play()

    async def show_list(self, index: int = None) -> discord.Embed:
        '''Ensure index is index not id of song'''
        index = index or self.current_index
        if not (0 <= index < len(self.list)):  # 確保索引在範圍內
            return create_basic_embed((await self.translator.get_translate('send_player_not_found_song', self.locale)).format(index=index+1))
        
        '''i18n'''
        i18n_queue_str = await self.translator.get_translate('embed_player_queue', self.locale)
        i18n_queue_data = load_translated(i18n_queue_str)[0]
        i18n_np_str = await self.translator.get_translate('embed_music_now_playing', self.locale)
        i18n_np_data = load_translated(i18n_np_str)[0]
        ''''''
        eb = create_basic_embed(color=self.user.color, 功能=i18n_queue_data['title'])
        eb.set_thumbnail(url=self.list[index]['thumbnail_url'])
        start = max(0, index - 2)
        end = min(len(self.list), index + 8)

        for i in range(start, end):
            item = self.list[i]
            title = item['title']
            video_url = item['video_url']
            duration = item['duration']
            user = item.get('user')
            
            prefix = ''
            if i == index:
                prefix = f'{i18n_queue_data["field"][0]["name"]} '
            elif i == index + 1:
                prefix = f'{i18n_queue_data["field"][1]["name"]} '

            eb.add_field(
                name=f'{prefix}{i + 1}. {title}',
                value=f'[URL]({video_url})\n{i18n_np_data["duration"]}: {duration}\n{i18n_np_data["requester"]}: {user.global_name if user else "N/A"}',
                inline=False
            )

        return eb

    def handle_error(self, e):
        """處理播放錯誤並嘗試恢復"""
        print(f"播放錯誤: {e}")
        # 自動嘗試播放下一首
        asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)

    def clear_list(self):
        self.list = []
        self.voice_client.stop()
        self.current_index = 0

    def gener_progress_bar(self, bar_length: int = 20) -> str:
        """
        利用符號組成進度條
        - 已播放部分：■
        - 當前播放位置：🔵
        - 剩餘部分：□ (因大小不依 已刪除)
        如果處於暫停狀態，末端會顯示 ⏸️ 表示暫停
        """
        current = self.passed_time
        paused = self.paused
        total = self.duration_int or 0

        if total <= 0:
            return "□" * bar_length
        progress_ratio = current / total
        filled_length = int(bar_length * progress_ratio)
        if filled_length >= bar_length:
            bar = "■" * bar_length
        else:
            bar = "■" * filled_length + "🔵" + "■" * (bar_length - filled_length - 1)
        if paused:
            bar += " ⏸️"

        bar = f"`{secondToReadable(current)}`  {bar}  `{secondToReadable(self.duration_int)}`"

        self.progress_bar = bar
        return bar

    async def update_passed_time(self):
        """
        Background task：
        每秒更新一次進度條訊息，如果遇到影片結束則結束迴圈
        """
        while True:
            if self.paused:
                self.gener_progress_bar()
            else:
                self.passed_time += 1
                self.gener_progress_bar()

                if self.passed_time >= self.duration_int:
                    self.update_progress_bar_task.cancel()
                    break

            await asyncio.sleep(1)

    async def search_lyrics(self) -> str:
        query = self.list[self.current_index].get('title')
        result = await search_lyrics(query=query)
        if not result: return await self.translator.get_translate('send_player_lyrics_not_found', self.locale)
        return result
    
    async def volume_adjust(self, volume: float = None, add: float = None, reduce: float = None) -> discord.Message | bool:
        '''調整音量，add 和 reduce 皆為`正`浮點數，且音量最大值為 2.0。此 func 也會傳送訊息通知使用者將音量調整為多少'''
        if not volume and not add and not reduce: return False
        self.volume = ( self.volume + (add or 0) - (reduce or 0) ) if add or reduce else volume
        if self.volume > 2: self.volume = 2

        self.transformer.volume = self.volume
        self.voice_client.source = self.transformer
    
        msg = await self.ctx.send((await self.translator.get_translate('send_player_volume_adjusted', self.locale)).format(volume=int(math_round(self.volume * 100))), silent=True, ephemeral=True)
        return msg