import discord
from discord.ext import commands
import re
from pytubefix import Search
from datetime import timedelta
import urllib.parse
from concurrent.futures import ProcessPoolExecutor
import os
from typing import TYPE_CHECKING
from asyncio import Semaphore
import httpx

from core.functions import create_basic_embed
from core.translator import load_translated

if TYPE_CHECKING:
    from .player import Player

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af "volume=0.25"',
}

Semaphore_multi_processing_pool = Semaphore(os.cpu_count())

# YTDL_OPTIONS = {
#     'format': 'bestaudio/best',
#     'forceurl': True,
#     'skip_download': True,
#     'quiet': True,
#     'no_warnings': True,
#     'default_search': 'auto',
#     'noplaylist': True,
#     'restrictfilenames': True,
#     'no_check_certificate': True,
#     'source_address': '0.0.0.0',
# }

YTDL_OPTIONS = {
    # === 基本設定 ===
    "quiet": True,                # 安靜模式（減少輸出）
    "no_warnings": True,          # 隱藏警告
    "color": 'never',             # 禁用顏色輸出

    # === 格式選擇 ===
    "format": "bestaudio/best",   # 獲取最佳音訊品質
    "prefer_free_formats": True,  # 優先選擇開放格式（如 webm）

    # === 下載控制 ===
    "skip_download": True,        # 跳過實際下載
    "simulate": False,            # 禁用模擬模式（需完整解析）
    "dump_single_json": True,     # 直接輸出 JSON 資料

    # === 資訊提取 ===
    "writeinfojson": True,        # 寫入完整資訊（含標題、連結）
    "writethumbnail": True,      # 獲取封面連結

    # === 網路優化 ===
    "socket_timeout": 30,         # 縮短超時時間
    "retries": 1,                 # 減少重試次數
    "fragment_retries": 1,

    # === 快取設定（Linux）===
    "cachedir": "/tmp/yt-dlp-cache",  # 使用 RAM Disk 加速
    "rm_cachedir": False,

    # === 其他優化 ===
    "no_check_certificate": True,         # 避免 SSL 握手延遲（僅限可信環境）
    "call_home": False,                   # 禁用外部請求
    'ignore_no_formats_error': True
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
        
def is_url(query: str) -> bool:
    pattern = r'(https?://)?(www\.|music\.)?(youtube\.com|youtu\.be)'
    return bool(re.match(pattern, query))

def get_video_id(url: str):
    parsed = urllib.parse.urlparse(url)

    if parsed.netloc == "youtu.be": # 因為連結中可能包含 ?t=...
        video_id = parsed.path.lstrip("/")
    else: # 處理 youtube.com or other urls
        query = urllib.parse.parse_qs(parsed.query)
        video_id = query.get("v", [None])[0]

    return video_id

def convert_to_short_url(url: str) -> str:
    video_id = get_video_id(url)
    if not video_id: return
    return f'https://youtu.be/{video_id}'

async def check_audio_url_alive(audio_url: str) -> bool:
    try:
        client = httpx.AsyncClient()
        resp = await client.head(audio_url, timeout=5)
        return resp.status_code == 200
    except:
        return False
    finally:
        await client.aclose()

def query_search(query: str) -> tuple:
    '''return (title, video_url, length: str)'''
    search = Search(query, 'WEB')
    videos = search.videos
    if videos:
        video = videos[0]
        title = video.title
        video_url = video.watch_url
        length = str(timedelta(seconds=video.length))
        return (title, video_url, length)
    else: return None

async def leave(ctx: commands.Context):
    '''leave the voice channel and delete the player object from players dict'''
    if not ctx.author.voice or not ctx.guild.voice_client: await ctx.send('疑? 是你還是我不在語音頻道裡面啊'); return False
    if ctx.author.voice.channel != ctx.guild.voice_client.channel: await ctx.send('疑? 我們好像在不同的頻道裡面欸'); return False
    from cmds.play4 import players, custom_list_players, join_channel_time
    await ctx.guild.voice_client.disconnect()
    if ctx.guild.id in players:
        del players[ctx.guild.id]
    if ctx.guild.id in custom_list_players:
        del custom_list_players[ctx.guild.id]
    if ctx.guild.id in join_channel_time:
        del join_channel_time[ctx.guild.id]

async def send(ctx: commands.Context | discord.Interaction, text: str = None, embed: discord.Embed = None, view: discord.ui.View = None, ephemeral: bool = False):
    '''Same as discord.py send function but support interaction'''
    if isinstance(ctx, commands.Context):
        await ctx.send(text, embed=embed, view=view, ephemeral=ephemeral)
    elif isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(text, embed=embed, view=view, ephemeral=ephemeral)
    else: raise ValueError('Invalid context type')

async def send_info_embed(player: 'Player', ctx: commands.Context | discord.Interaction, index: int = None, if_send: bool = True):
    '''Ensure index is index not id of song'''
    from cmds.music_bot.play4.player import Player
    from cmds.music_bot.play4.buttons import MusicControlButtons

    player: Player = player
    
    index = index or player.current_index
    if not (0 <= index < len(player.list)): return await send(ctx, (await player.translator.get_translate('send_player_not_found_song', player.locale)).format(index=index+1), ephemeral=True)

    title = player.list[index]['title']
    video_url = player.list[index]['video_url']
    duration = player.list[index]['duration']
    user = (player.list[index]).get('user')
    thumbnail_url = player.list[index]['thumbnail_url']
    loop_status = player.loop_status
    is_current = index == player.current_index

    '''i18n'''
    i18n_info_str = await player.translator.get_translate('embed_music_info', player.locale)
    i18n_info_data = load_translated(i18n_info_str)[0]
    ''''''

    eb = create_basic_embed(f'{i18n_info_data['title'] if is_current else '已新增 '}`{title}`', color=user.color, 功能='音樂播放')
    eb.set_image(url=thumbnail_url)

    field_names = i18n_info_data['field']
    field_values = [
        f'[url]({video_url})',
        duration,
        loop_status,
        f'{player.volume * 100}%',
        player.progress_bar
    ]

    for i, field in enumerate(field_names):
        eb.add_field(name=field['name'], value=field_values[i], inline=field.get('inline', True))

    footer_text = i18n_info_data['footer'].format(user_name=user.global_name)
    eb.set_footer(text=footer_text, icon_url=user.avatar.url if user.avatar else None)

    view = MusicControlButtons(player)
    if if_send:
        await send(ctx, embed=eb, view=view)
    return eb, view

async def check_and_get_player(ctx: commands.Context, *, check_user_in_channel=True):
    '''Return current Player object, and a status of this command.'''
    from cmds.play4 import players
    from cmds.music_bot.play4.player import Player
    
    if check_user_in_channel:
        if not ctx.author.voice:
            return await ctx.send(await ctx.bot.tree.translator.get_translate('send_check_not_in_voice', ctx.interaction.locale.value)), False
    if not ctx.voice_client:
        return await ctx.send(await ctx.bot.tree.translator.get_translate('send_check_bot_not_in_voice', ctx.interaction.locale.value)), False

    player: Player = players.get(ctx.guild.id)

    if not player:
        return await ctx.send(await ctx.bot.tree.translator.get_translate('send_add_player_crashed', ctx.interaction.locale.value)), False
    return player, True


if __name__ == '__main__':
    a = query_search('D/N/A')
    print(a)