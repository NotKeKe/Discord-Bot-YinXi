import discord
from discord.ext import commands
import asyncio
import traceback

from cmds.music_bot.play4 import utils
from cmds.music_bot.play4.downloader import Downloader

from core.functions import create_basic_embed, current_time
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

        # self.downloader = Downloader(query)

        # self.downloader.run()
        # self.title, self.video_url, self.audio_url, self.thumbnail_url, self.duration = self.downloader.get_info()

    async def download(self):
        downloader = Downloader(self.query)
        await downloader.run()
        title, video_url, audio_url, thumbnail_url, duration = downloader.get_info()
        return title, video_url, audio_url, thumbnail_url, duration

    async def add(self, query: str, ctx: commands.Context):
        '''return len(self.list), title, video_url, audio_url, thumbnail_url, duration'''
        self.query = query
        title, video_url, audio_url, thumbnail_url, duration = await self.download()
        self.list.append({
            'title': title,
            'video_url': video_url,
            'audio_url': audio_url,
            'thumbnail_url': thumbnail_url,
            'duration': duration,
            'user': ctx.author
        })
        return len(self.list), title, video_url, audio_url, thumbnail_url, duration
    
    async def play(self):
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
        
        try:
            # 播放新音訊
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
                await self.ctx.send('我已經播完所有歌曲啦! 我就離開囉')
                await self.voice_client.disconnect()
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