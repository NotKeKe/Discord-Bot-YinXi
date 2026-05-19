import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, urllib.request, re

from core.classes import Cog_Extension


queues = {}
voice_clients = {}
youtube_base_url = 'https://www.youtube.com/'
youtube_results_url = youtube_base_url + 'results?'
youtube_watch_url = youtube_base_url + 'watch?v='
yt_dl_options = {"format": "bestaudio/best"}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

async def play_next(bot: commands.Bot, ctx):
    if queues[ctx.guild.id] != []:
        link = queues[ctx.guild.id].pop(0)
        # await play(ctx, link=link)
        await ctx.invoke(bot.get_command('play'), link=link)

class TVoice(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name="play")
    async def play(self, ctx, *, link):
        try:
            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(f'1 {e}')

        try:

            # if youtube_base_url not in link:
            #     query_string = urllib.parse.urlencode({
            #         'search_query': link
            #     })

            #     content = urllib.request.urlopen(
            #         youtube_results_url + query_string
            #     )

            #     search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())

            #     link = youtube_watch_url + search_results[0]
            #     print(link)

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            
            song = data['url']

            if not discord.opus.is_loaded():
                discord.opus.load_opus('libopus-0.dll')

            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)

            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(self.bot, ctx), self.bot.loop))
        except Exception as e:
            print(f'2 {e}')

    @commands.hybrid_command(name="clear_queue")
    async def clear_queue(self, ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Queue cleared!")
        else:
            await ctx.send("There is no queue to clear")

    @commands.hybrid_command(name="pause")
    async def pause(self, ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    @commands.hybrid_command(name="resume")
    async def resume(self, ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    @commands.hybrid_command(name="stop")
    async def stop(self, ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
        except Exception as e:
            print(e)

    @commands.hybrid_command(name="queue")
    async def queue(self, ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue!")

# async def setup(bot):
#     await bot.add_cog(TVoice(bot))
