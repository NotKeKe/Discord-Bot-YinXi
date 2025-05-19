import itertools
from pytubefix import YouTube, Search
import yt_dlp as youtube_dl
import re
from datetime import datetime, timedelta
import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
embed_link = os.getenv('embed_default_link')

queues = {}
looping = []
current_playing = {}
played = {}
# played = {
#     ctx.guild.id: [
#         {
#             'song': 1
#         },
#         {
#             'song': 2
#         }
#     ]
# }
skip = []

ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "volume=0.25"',
    }

# ytdlp
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)


# Select view
class MyView(discord.ui.View):
    def __init__(self, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.value = None
        

    @discord.ui.select(
        placeholder="選擇一首歌!", min_values=1, max_values=1,
            options=[
                discord.SelectOption(label=1),
                discord.SelectOption(label=2),
                discord.SelectOption(label=3),
                discord.SelectOption(label=4),
                discord.SelectOption(label=5),
            ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.value = select.values
        # await interaction.response.send_message(f'{self.value}, select call back')
        self.stop()

async def get_ctx(bot:commands.Bot, interaction: discord.Interaction) -> commands.Context:
    ctx = await bot.get_context(interaction)
    return ctx

def initialize_played(ctx, played):
    '''
    初始化played list
    '''
    if ctx.guild.id not in played:
        played[ctx.guild.id] = []

# ⏯️⏭️⏹️🔂📄
class ButtonView(discord.ui.View):
    def __init__(self, bot:commands.Bot, timeout = 300):
        super().__init__(timeout=timeout)
        self.bot = bot

    @discord.ui.button(label='⏮️上一首歌')
    async def pervious_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.voice_client: await interaction.response.send_message('我尚未連接任何頻道', ephemeral=True); return
        if interaction.guild.id not in played: await interaction.response.send_message('沒上一首歌r 你在幹嘛', ephemeral=True); return

        if interaction.guild.voice_client.is_playing(): await interaction.guild.voice_client.stop()

        try:
            link = played[interaction.guild.id][-1]['audio_url']
            title = played[interaction.guild.id][-1]['title']
            url = played[interaction.guild.id][-1]['video_url']
            length = played[interaction.guild.id][-1]['length']
            thumbnail = played[interaction.guild.id][-1]['thumbnail']

            await interaction.response.send_message('已開始準備播放上一首歌')
            await machine_play(self.bot, interaction, link, title, url, length, thumbnail)
        except Exception as e:
            print('pervious_callback' + e)


    @discord.ui.button(label='⏯️')
    async def pause_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.is_playing():
                interaction.guild.voice_client.pause()
                await interaction.response.send_message('已暫停播放音樂')
            elif interaction.guild.voice_client.is_paused():
                interaction.guild.voice_client.resume()
                await interaction.response.send_message('已繼續播放音樂')
            else:
                await interaction.response.send_message('沒有正在播放的音樂', ephemeral=True)
        else:
            await interaction.response.send_message('我不在任何語音頻道當中', ephemeral=True)
    
    @discord.ui.button(
        label='⏭️下一首歌'
    )
    async def skip_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            interaction.guild.voice_client.stop()
        except:
            await interaction.response.send_message("我未加入任何頻道", ephemeral=True)

        try:
            await interaction.response.send_message('已跳過音樂')

            if interaction.guild.id not in played: 
                initialize_played(interaction, played)

            played[interaction.guild.id].append(current_playing[interaction.guild.id])

            if interaction.guild.id in queues:
                if queues[interaction.guild.id]:
                    ctx = await self.bot.get_context(interaction)
                    await play_next(self.bot, ctx)
        except Exception as e:
            print('skip_button_callback' + e)

    @discord.ui.button(label='⏹️停止播放')
    async def stop_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild.voice_client:
            await interaction.response.send_message(content='我不在任何語音頻道當中', ephemeral=True)
            return

        interaction.guild.voice_client.stop()
        await interaction.guild.voice_client.disconnect()
        if interaction.guild.id in queues:
            del queues[interaction.guild.id]
        if interaction.guild.id in played:
            del current_playing[interaction.guild.id]
        await interaction.response.send_message(content='已停止音樂', ephemeral=True)

    @discord.ui.button(label='🔂單曲循環')
    async def loop_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.id not in current_playing:
            await interaction.response.send_message(content='沒有正在播放的音樂', ephemeral=True)
            return

        if interaction.guild.id not in looping:
            looping.append(interaction.guild.id)
            await interaction.response.send_message('已開始循環播放')
            embed = create_info_embed(title=current_playing[interaction.guild.id]['title'],
                                        video_url=current_playing[interaction.guild.id]['video_url'],
                                        length=current_playing[interaction.guild.id]['length'],
                                        thumbnail=current_playing[interaction.guild.id]['thumbnail'], 
                                        author=interaction.user
                                    )
            await interaction.message.edit(embed=embed)
        else:
            looping.remove(interaction.guild.id)
            await interaction.response.send_message('已停止循環播放')

    @discord.ui.button(label='📄列表')
    async def queue_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title='🎵 LIST 🎵', color=interaction.user.color, timestamp=datetime.now())
        embed.set_footer(text=interaction.user.name, icon_url=interaction.user.avatar.url)
        embed.set_author(name='歌曲列表 (最多顯示10項)', icon_url=embed_link)
        embed.add_field(name='1. ', value=f'[{current_playing[interaction.guild.id]['title']}]({current_playing[interaction.guild.id]['video_url']})    時長: {current_playing[interaction.guild.id]['length']}', inline=True)
        if interaction.guild.id in queues:
            # 顯示最多9項 (for迴圈中)
            for song in itertools.islice(queues[interaction.guild.id], 9):
                embed.add_field(name=f'{queues[interaction.guild.id].index(song)+2}. ', value=f'[{song["title"]}]({song["video_url"]})  時長: {song['length']}', inline=True)
        embed.add_field(name='循環狀態', value='開啟' if interaction.guild.id in looping else '關閉', inline=True)
        await interaction.response.send_message(embed=embed)

def is_youtube_url(string):
    # 定義 YouTube URL 的正則表達式模式
    youtube_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)')
    # 使用正則表達式匹配字串
    return bool(youtube_pattern.search(string))

def is_audio_url(url):
    pattern = r"https://rr\d+---sn-ipoxu-un5es\.googlevideo\.com/videoplayback\?expire="
    return re.match(pattern, url) is not None



def ytSearch(query: str) -> dict:
    # 使用 pytube 搜尋 YouTube 音樂
    search = Search(query, 'WEB')
    # search = Search(query, 'WEB')
    results = search.videos
    if results:
        return results

def get_url(url):
    '''
    Get final url and audio infos
    '''
    yt = YouTube(url, 'WEB')
    # 獲取所有音訊
    audio = yt.streams.filter(only_audio=True, abr='128kbps').first()

    if audio:
        link = audio.url
    else:
        audio2 = yt.streams.filter(only_audio=True).first()
        link =  audio2.url

    title = yt.title
    length = str(timedelta(seconds=yt.length))
    thumbnail = yt.thumbnail_url

    return link, title, length, thumbnail

    # info = ytdl.extract_info(url, download=False)
    # # video_link = info.get('webpage_url')
    # audio_link = info.get('url')
    # title = info.get('title')
    # duration = info.get('duration')
    # length = str(timedelta(seconds=duration))
    # thumbnail = info.get('thumbnail')
    # return audio_link, title, length, thumbnail

def is_looping(ctx:commands.Context):
    if ctx.guild.id in looping:
        return True
    else:
        return False

async def return_video_url(ctx:commands.Context, 文字):
    # Send searching message and also Search context
    message = await ctx.send('搜尋中...')
    # options = await ytSearch(輸入文字或連結)
    async with ctx.typing():
        # 使用 asyncio 來避免阻塞
        loop = asyncio.get_event_loop()
        options = await loop.run_in_executor(executor=None, func = lambda: ytSearch(文字))

    # View (新增下拉式選單)
    view = MyView()

    # Embed
    embed=discord.Embed(title="**音樂搜尋結果**", description="請選擇一首歌", color=ctx.author.color, timestamp=datetime.now())
    embed.set_author(name='播放音樂', icon_url=embed_link)
    embed.set_footer(text=f"搜尋用戶 「{ctx.author.name}」", icon_url=ctx.author.avatar.url)
    i = 1
    for video in options:
        title = video.title
        video_url = video.watch_url
        length = str(timedelta(seconds=video.length))
        embed.add_field(name=f'{i}.', value=f'[{title}]({video_url})\n時長: {length}', inline=True)
        i+=1
        if i == 6: break

    # Send message, and wait user's interaction
    message = await message.edit(content=None, embed=embed, view=view)
    await view.wait()

    # 取得選擇的值
    if view.value is None: await ctx.send('There is no value'); return
    # 將dict轉換為list
    value = int(view.value[0])-1

    url = options[value].watch_url
    title = options[value].title
    message = await message.edit(content=f'你選擇了第{view.value[0]}首歌\n歌名: {title}\nLoading...', embed=None, view=None)

    return url, message

async def play_next(bot: commands.Bot, ctx):
    try:
        if not ctx.guild.voice_client: return

        # 歌曲播完了
        if not queues[ctx.guild.id]:
            del queues[ctx.guild.id]
            del current_playing[ctx.guild.id]

        # 儲存使用者播放過的歌
        if ctx.guild.id not in played:
            initialize_played(ctx, played)
        played[ctx.guild.id].append(current_playing[ctx.guild.id])

        if is_looping(ctx):
            link = current_playing[ctx.guild.id]['audio_url']
            title = current_playing[ctx.guild.id]['title']
            url = current_playing[ctx.guild.id]['video_url']
            length = current_playing[ctx.guild.id]['length']
            thumbnail = current_playing[ctx.guild.id]['thumbnail']

            await machine_play(bot, ctx, link, title, url, length, thumbnail)
        elif ctx.guild.id in queues:
            if not queues[ctx.guild.id]: del queues[ctx.guild.id]; return
            link = queues[ctx.guild.id].pop(0)
            current_playing[ctx.guild.id] = link
            # await play(ctx, link=link)
            await machine_play(bot, ctx, link['audio_url'], link['title'], link['video_url'], link['length'], link['thumbnail'])
    except Exception as e:
        print('play_next' + e)

def create_info_embed(title, video_url, length, thumbnail, author: discord.member.Member):
    embed=discord.Embed(title=f'🎵 NOW PLAYING 🎵', description=f'[{title}]({video_url})', color=discord.Color.random(), timestamp=datetime.now())
    embed.add_field(name='時長: ', value=length, inline=True)
    embed.add_field(name='循環狀態', value='開啟' if author.guild.id in looping else '關閉', inline=True)
    embed.set_author(name="音樂資訊", icon_url=embed_link)
    embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=f"播放用戶 「{author.name}」", icon_url=author.avatar.url)

    return embed

async def human_play(bot: commands.Bot, ctx: commands.Context, 輸入文字或連結):
        # 確定是否要return command

        # 1.Ensure that user in voice channel
        if not ctx.author.voice: await ctx.send("你不在任何頻道裡面"); return
        voice_channel = ctx.author.voice.channel

        # 2.Check if bot in channel and then check if bot is playing audio
        if ctx.voice_client:
            if ctx.voice_client.is_playing(): 
                await ctx.send('請使用[queue 進行下一首歌歌的播放'); return

        # 確定是audio url, youtube url或就是文字
        # 會出現message跟url

        # 1.確定是否是youtube url
        if is_youtube_url(輸入文字或連結): 
            message = await ctx.send(content='Loading...')
            url = 輸入文字或連結
        else: # 3.就是文字
            url, message = await return_video_url(ctx, 輸入文字或連結)

        # 取得音樂資訊 (including the link that can be played)
        async with ctx.typing():
            # 使用 asyncio 來避免阻塞
            loop = asyncio.get_event_loop()
            link, title, length, thumbnail = await loop.run_in_executor(executor=None, func=lambda: get_url(url))

        # 創建embed來傳送資訊
        try:
            embed = create_info_embed(title, url, length, thumbnail, ctx.author)
            current_playing[ctx.guild.id] = {
                'title': title, 
                'length': length, 
                'thumbnail': thumbnail, 
                'video_url': url,
                'audio_url': link,
            }

            # Button and View
            view = ButtonView(bot=bot)

            await message.edit(content=None, embed=embed, view=view)
        except Exception as exception:
            await ctx.invoke(bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

        # 初始化played
        initialize_played(ctx, played)
        
        if not discord.opus.is_loaded():
            discord.opus.load_opus('libopus-0.dll')

        # 連接至使用者頻道
        if not ctx.guild.voice_client: # Bot 尚未連接頻道
            voice_client = await voice_channel.connect()
        else: # Bot 已經連接頻道
            voice_client = ctx.guild.voice_client

        voice_client.play(discord.FFmpegPCMAudio(link, **ffmpeg_options), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(bot, ctx), bot.loop))

async def machine_play(bot: commands.Bot, ctx, link, title, url, length, thumbnail):
    current_playing[ctx.guild.id] = {
        'title': title, 
        'length': length, 
        'thumbnail': thumbnail, 
        'video_url': url,
        'audio_url': link,
    }

    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus-0.dll')

    voice_client = ctx.guild.voice_client

    def after_playing(error):
        if error:
            print(f'Error occurred: {error}')
        coro = play_next(bot, ctx)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f'Error in after_playing: {str(e)}')

    voice_client.play(discord.FFmpegPCMAudio(link, **ffmpeg_options), after=after_playing)