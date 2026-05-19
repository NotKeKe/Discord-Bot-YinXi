import discord
from discord.ext import commands
import asyncio
import re
from pytubefix import Search, YouTube
from datetime import datetime, timedelta
import traceback

from core.functions import read_json, write_json, create_basic_embed, embed_link
from cmds.music_bot.play2.default import save, init
from cmds.music_bot.play2.button import MyView, ButtonView


# FFmpeg Settings(給discord.ffmpeg的)
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"',
}

class ID:
    @staticmethod
    def return_user_id(obj) -> int:
        if type(obj) == commands.Context:
            return obj.author.id
        elif type(obj) == discord.Interaction:
            return obj.user.id
        
    @staticmethod
    def return_guild_id(obj) -> int:
        return obj.guild.id
    
    @staticmethod
    def return_user_color(obj):
        if type(obj) == commands.Context:
            return obj.auhor.color
        elif type(obj) == discord.Interaction:
            return obj.user.color
    
# 判斷連結類型 回傳bool
def is_youtube_url(string):
    youtube_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)')
    return bool(youtube_pattern.search(string))

def is_audio_url(url):
    pattern = r"https://rr\d+---sn-ipoxu-un5es\.googlevideo\.com/videoplayback\?expire="
    return re.match(pattern, url) is not None

def is_looping(ctx):
    if ID.return_guild_id(ctx) in save.looping:
        return True
    else:
        return False

def ytSearch(ctx, query: str) -> dict:
    search = Search(query, 'WEB')
    results = search.videos
    if results:
        # Embed
        embed = create_basic_embed(title="**音樂搜尋結果**", description="請選擇一首歌", color=ctx.author.color, 功能='播放音樂')
        embed.set_footer(text=f"搜尋用戶 「{ctx.author.name}」", icon_url=ctx.author.avatar.url)

        for index, video in enumerate(results[:5], start=1):
            title = video.title
            video_url = video.watch_url
            length = str(timedelta(seconds=video.length))
            embed.add_field(name=f'{index}.', value=f'[{title}]({video_url})\n時長: {length}', inline=True)

        return embed, results

def get_audio_streams(video):
    audio_streams = video.streams.filter(only_audio=True, abr='128kbps')
    return audio_streams

def save_info(ctx, ispersonal = False):
    '''
    先使用save.item()再使用這個
    將save class中的item加進save.queues or save.personal_list中
    '''
    if ispersonal:
        user_id = ID.return_user_id(ctx)
        init.initialize_personal_list(user_id)
        save.save_info_to_personal_list(user_id)
    else:
        guild_id = ID.return_guild_id(ctx)
        init.initialize_queues(guild_id)
        save.save_info_to_queues(guild_id)
    
def get_yt_audio_url(ctx, url, ispersonal = False):
    '''
    需傳入的是youtube url
    ispersonal 決定是否存入個人播放清單
    會先初始化個人list或queues
    '''
    yt = YouTube(url, 'WEB')
    # 獲取所有音訊
    audio = yt.streams.filter(only_audio=True, abr='128kbps').first()

    if audio:
        audio_url = audio.url
    else:
        audio2 = yt.streams.filter(only_audio=True).first()
        audio_url = audio2.url

    # 儲存info
    title = yt.title
    length = str(timedelta(seconds=yt.length))
    thumbnail = yt.thumbnail_url

    save.save_item(audio_url, title, length, thumbnail, url)
    save_info(ctx, ispersonal)
    
def play(bot: commands.Bot, ctx, voice_client, link, ispersonal=False):
    voice_client.play(discord.FFmpegPCMAudio(link, **ffmpeg_options), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(bot, ctx, ispersonal), bot.loop))

def create_info_embed(title, video_url, length, thumbnail, author: discord.member.Member):
    embed=discord.Embed(title=f'🎵 NOW PLAYING 🎵', description=f'[{title}]({video_url})', color=author.color, timestamp=datetime.now())
    embed.add_field(name='時長: ', value=length, inline=True)
    embed.add_field(name='循環狀態', value='開啟' if author.guild.id in save.looping else '關閉', inline=True)
    embed.set_author(name="音樂資訊", icon_url=embed_link)
    embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text=f"播放用戶 「{author.name}」", icon_url=author.avatar.url)

    return embed

def get_current_info(bot:commands.Bot, ctx, index=0, ispersonal=False):
    if ispersonal:
        queue = save.personal_list[str(ID.return_user_id(ctx))][index]
    else:
        queue = save.queues[ID.return_guild_id(ctx)][index]

    title = queue['title']
    length = queue['length']
    thumbnail = queue['thumbnail']
    video_url = queue['video_url']

    embed = create_info_embed(title, video_url, length, thumbnail, ctx.author)
    view = ButtonView(bot=bot)
    
    return embed, view

async def is_in_channel(ctx):
    '''
    確定使用者是否在頻道中
    不在的話會回傳false
    '''
    if type(ctx) == commands.Context:
        if not ctx.author.voice: await ctx.send("你不在任何頻道裡面", ephemeral=True); return False
    elif type(ctx) == discord.Interaction:
        if not ctx.user.voice: await ctx.response.send_message('你不再任何頻道裡面', ephemeral=True); return False

    return True

async def get_user_choice(ctx: commands.Context, input, ispersonal = False):
    '''
    如果使用者輸入的是文字才會跑來這裡
    會往queues儲存資訊
    '''
    message = await ctx.send('搜尋中...')
    
    async with ctx.typing():
        loop = asyncio.get_event_loop()
        embed, options = await loop.run_in_executor(executor=None, func=lambda: ytSearch(ctx, input))

    view = MyView()

    message = await message.edit(content=None, embed=embed, view=view)
    await view.wait()

    # 取得選擇的值
    if view.value is None: await ctx.send('There is no value'); return
    value = int(view.value[0])-1

    search_result = options[value]

    video_url = search_result.watch_url
    title = search_result.title
    message = await message.edit(content=f'你選擇了第{view.value[0]}首歌\n歌名: {title}\nLoading...', embed=None, view=None)

    async with ctx.typing():
        loop = asyncio.get_event_loop()
        audio_streams = await loop.run_in_executor(executor=None, func=lambda: get_audio_streams(search_result))

    audio_url = audio_streams[0].url

    duration = search_result.length
    length = timedelta(seconds=duration)
    thumbnail = search_result.thumbnail_url

    save.save_item(audio_url, title, length, thumbnail, video_url)
    save_info(ctx, ispersonal)

    return message
    
async def play_next(bot:commands.Bot, ctx, ispersonal=False):
    '''
    盡量能讓ctx跟interaction都能跑，不然要改play()
    '''
    try:
        id = str(ID.return_user_id(ctx)) if ispersonal else ID.return_guild_id(ctx)

        if not is_looping(ctx):
            save.current_playing_index[ctx.guild.id] += 1

        index = save.current_playing_index[ctx.guild.id]

        if ispersonal:
            print(ispersonal)
            if index < len(save.personal_list[id]):
                print(index)
                audio_url = save.personal_list[id][index]['audio_url']
            else: return
        elif index < len(save.queues[id]):
            audio_url = save.queues[id][index]['audio_url']
        else: return

        voice_client = ctx.guild.voice_client
        play(bot, ctx, voice_client, audio_url, ispersonal)
    except:
        traceback.print_exc()

async def play_button(bot: commands.Bot, ctx, ispersonal=False):
    try:
        id = ID.return_user_id(ctx) if ispersonal else ID.return_guild_id(ctx)

        index = save.current_playing_index[ctx.guild.id]

        if ispersonal and index < len(save.personal_list[str(id)]):
            audio_url = save.personal_list[str(id)][index]['audio_url']
        elif not ispersonal and index < len(save.queues[id]):
            audio_url = save.queues[id][index]['audio_url']
        else: return

        voice_client = ctx.guild.voice_client
        play(bot, ctx, voice_client, audio_url, ispersonal)
    except discord.errors.ClientException:
        pass
    except:
        traceback.print_exc()