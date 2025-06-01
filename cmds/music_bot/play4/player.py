import discord
from discord.ext import commands
import asyncio
import traceback
import time

from cmds.music_bot.play4 import utils
from cmds.music_bot.play4.downloader import Downloader

from core.functions import create_basic_embed, current_time, secondToReadable
# from core.classes import bot

loop_option = ('None', 'single', 'list')

class Player:
    '''Ensure the user is current in a channel, and bot already joined the channel'''
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx # 為了初始化數據，在後續的更改中不應該繼續使用當前的`ctx`
        self.query = None

        self.list = []
        self.current_index = 0
        self.loop_status = 'None'

        self.user = ctx.author
        self.guild = ctx.guild
        self.channel = ctx.voice_client.channel
        self.voice_client = ctx.voice_client
        self.bot = ctx.bot

        self.manual = False

        # 進度條
        self.init_bar()

        # self.downloader = Downloader(query)

        # self.downloader.run()
        # self.title, self.video_url, self.audio_url, self.thumbnail_url, self.duration = self.downloader.get_info()
    
    def __del__(self):
        try: self.update_progress_bar_task.cancel()
        except: ...

    def init_bar(self):
        self.duration_int = None
        self.passed_time = 0
        self.progress_bar = ''
        try: self.update_progress_bar_task.cancel()
        except: ...
        self.update_progress_bar_task: asyncio.Task = None

        self.paused: bool = False

    async def download(self):
        downloader = Downloader(self.query)
        await downloader.run()
        title, video_url, audio_url, thumbnail_url, duration, duration_int = downloader.get_info()
        return title, video_url, audio_url, thumbnail_url, duration, duration_int

    async def add(self, query: str, ctx: commands.Context):
        '''return len(self.list), title, video_url, audio_url, thumbnail_url, duration'''
        self.query = query
        title, video_url, audio_url, thumbnail_url, duration, duration_int = await self.download()
        self.list.append({
            'title': title,
            'video_url': video_url,
            'audio_url': audio_url,
            'thumbnail_url': thumbnail_url,
            'duration': duration,
            'duration_int': duration_int,
            'user': ctx.author
        })
        return len(self.list), title, video_url, audio_url, thumbnail_url, duration
    
    async def play(self):
        self.init_bar()
        
        if not self.list: 
            print('播放列表為空')
            return
            
        # 確保連接狀態
        if not self.voice_client or not self.voice_client.is_connected(): 
            print('未連接到語音頻道')
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
            self.voice_client.play(
                discord.FFmpegPCMAudio(audio_url, **utils.ffmpeg_options), 
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(e), self.bot.loop)
            )
        except Exception as e:
            print(f'播放錯誤: {e}')
            traceback.print_exc()

    def loop(self, loop_type: str):
        if loop_type not in loop_option: return 'Invalid loop type'
        self.loop_status = loop_type

    def turn_loop(self):
        index = loop_option.index(self.loop_status)
        index = (index + 1) % len(loop_option)
        self.loop_status = loop_option[index]

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
    
    async def pause(self):
        '''Pause to play music and `SEND` message to notice user'''
        if self.voice_client.is_paused():
            return await self.ctx.send('音樂已經暫停了欸:thinking:')
        if not self.voice_client.is_playing():
            return await self.ctx.send('沒有正在播放的音樂呢')

        self.voice_client.pause()
        self.paused = True
        return await self.ctx.send('已經幫你暫停音樂囉', ephemeral=True)
    
    async def resume(self):
        '''Resume to play music and `SEND` message to notice user'''
        if self.voice_client.is_playing():
            return await self.ctx.send('音汐正在播放中，不需要恢復喔:thinking:')
        if not self.voice_client.is_paused():
            return await self.ctx.send('這裡沒有暫停中的音樂')

        self.voice_client.resume()
        self.paused = False
        await self.ctx.send('已經幫你繼續播放音樂囉~', ephemeral=True)

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
            
        # 檢查播放列表是否為空
        if not self.list:
            print('播放列表為空，無法播放下一首')
            return
            
        # 更新索引
        if self.loop_status == 'None':
            if self.current_index + 1 < len(self.list):
                self.current_index += 1
            else: # 已到列表末尾且未啟用循環
                await asyncio.sleep(1)
                if not self.ctx.voice_client: return
                await self.ctx.send('我已經播完所有歌曲啦! 我就離開囉')
                await self.voice_client.disconnect()
                del self
                return
        elif self.loop_status == 'list':
            self.current_index = (self.current_index + 1) % len(self.list)
        # single 不需要改變索引

        print('play_next  {}  index: {}'.format(current_time(), self.current_index))
        
        # 添加短暫延遲避免重疊請求
        await asyncio.sleep(0.2)
        await self.play()

    def show_list(self, index: int = None) -> discord.Embed:
        '''Ensure index is index not id of song'''
        index = index or self.current_index
        if not (0 <= index < len(self.list)):  # 確保索引在範圍內
            return create_basic_embed('找不到該歌曲')
        
        eb = create_basic_embed(color=self.user.color, 功能='播放清單')
        eb.set_thumbnail(url=self.list[index]['thumbnail_url'])
        start = max(0, index - 2)  # 避免索引超出範圍
        end = min(len(self.list), index + 8)  # 讓結束索引最多到最後一項

        for i in range(start, end):
            title = self.list[i]['title']
            video_url = self.list[i]['video_url']
            duration = self.list[i]['duration']
            user = (self.list[i]).get('user')
            eb.add_field(name=f'{i + 1}. {title}', value=f'歌曲連結: [url]({video_url})\n時長: {duration}\n點播人: {user.global_name if user else "未知"}')

        return eb

    def handle_error(self, e):
        """處理播放錯誤並嘗試恢復"""
        print(f"播放錯誤: {e}")
        # 自動嘗試播放下一首
        asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)

    def clear_list(self):
        self.list = []

    def gener_progress_bar(self, bar_length: int = 20) -> str:
        """
        利用符號組成進度條
        - 已播放部分：■
        - 當前播放位置：🔵
        - 剩餘部分：□
        如果處於暫停狀態，末端會顯示 ⏸️ 表示暫停
        """
        current = self.passed_time
        paused = self.paused
        total = self.duration_int

        if total <= 0:
            return "□" * bar_length
        progress_ratio = current / total
        filled_length = int(bar_length * progress_ratio)
        if filled_length >= bar_length:
            bar = "■" * bar_length
        else:
            bar = "■" * filled_length + "🔵" + "□" * (bar_length - filled_length - 1)
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
        try:
            while True:
                if self.paused: return
                if self.passed_time + 1 >= self.duration_int: 
                    self.update_progress_bar_task.cancel()

                self.passed_time += 1
                self.gener_progress_bar()
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            # 如果被取消 (例如歌曲被切換)，結束 task
            return
            
    def cleanup(self):
        """釋放資源並取消所有任務"""
        # 取消進度條更新任務
        if self.update_progress_bar_task and not self.update_progress_bar_task.cancelled():
            self.update_progress_bar_task.cancel()
            
        # 確保斷開語音連接
        if self.voice_client and self.voice_client.is_connected():
            self.voice_client.stop()
            # 實際斷開會在外部調用disconnect()
            
        # 釋放引用，幫助垃圾回收
        self.ctx = None
        self.voice_client = None
        self.bot = None
