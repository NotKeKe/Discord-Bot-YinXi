import discord
from discord.ext import commands
import re
from pytubefix import Search
from datetime import timedelta

from core.functions import create_basic_embed

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af "volume=0.25"',
}

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
    pattern = r'(https?://)?(www\.)?(youtube\.com|youtu\.be)'
    return (True if re.match(pattern, query) else False)

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
    from cmds.play4 import players
    await ctx.guild.voice_client.disconnect()
    del players[ctx.guild.id]

async def send(ctx: commands.Context | discord.Interaction, text: str = None, embed: discord.Embed = None, view: discord.ui.View = None, ephemeral: bool = False):
    if isinstance(ctx, commands.Context):
        await ctx.send(text, embed=embed, view=view, ephemeral=ephemeral)
    elif isinstance(ctx, discord.Interaction):
        await ctx.response.send_message(text, embed=embed, view=view, ephemeral=ephemeral)
    else: raise ValueError('Invalid context type')

async def send_info_embed(player, ctx: commands.Context | discord.Interaction, index: int = None, if_send: bool = True):
    '''Ensure index is index not id of song'''
    from cmds.music_bot.play4.player import Player
    from cmds.music_bot.play4.buttons import MusicControlButtons
    
    player: Player = player
    
    index = index or player.current_index
    if not (0 <= index < len(player.list)): return await send(ctx, f'找不到第{index+1}首歌曲')

    title = player.list[index]['title']
    video_url = player.list[index]['video_url']
    duration = player.list[index]['duration']
    user = (player.list[index]).get('user')
    thumbnail_url = player.list[index]['thumbnail_url']
    loop_status = player.loop_status
    is_current = index == player.current_index

    eb = create_basic_embed(f'{'▶️ 正在播放 ' if is_current else '以新增 '}`{title}`', color=user.color, 功能='音樂播放')
    eb.set_image(url=thumbnail_url)
    eb.add_field(name='🌐 Video url', value=f'[url]({video_url})')
    eb.add_field(name='⏱️ Duration', value=f'{duration}')
    eb.add_field(name='🔁 Loop status', value=loop_status)
    eb.add_field(name='Progress bar', value=player.progress_bar)
    eb.set_footer(text=f'Requested by {user.global_name}', icon_url=user.avatar.url if user.avatar else None)

    view = MusicControlButtons(player)
    if if_send:
        await send(ctx, embed=eb, view=view)
    return eb, view

async def check_and_get_player(ctx: commands.Context, *, check_user_in_channel=True):
    from cmds.play4 import players
    from cmds.music_bot.play4.player import Player
    
    if check_user_in_channel:
        if not ctx.author.voice: return await ctx.send('你好像不在語音頻道裡面?'), False
    if not ctx.voice_client: return await ctx.send('音汐不在語音頻道內欸:thinking:'), False

    player: Player = players.get(ctx.guild.id)

    if not player: return await ctx.send('音汐剛剛好像不正常退出了呢:thinking:'), False
    return player, True


if __name__ == '__main__':
    a = query_search('D/N/A')
    print(a)