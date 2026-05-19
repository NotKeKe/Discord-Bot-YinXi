import asyncio
import aiohttp
from pytubefix import YouTube, Search

def yt():
        # @commands.hybrid_command(aliases=['pause', '暫停'], name='暫停音樂', description='Pause the playing song!')
    # async def pause(self, ctx):
    #     voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
    #     if voice.is_playing():
    #         await ctx.send("已暫停播放音樂")
    #         voice.pause()
    #     else:
    #         await ctx.send("Currently no audio is playing")

    # @commands.hybrid_command(aliasese=['resume', '繼續', 'continue'], name='繼續音樂', description='Resume the stopped song!')
    # async def resume(self, ctx):
    #     voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
    #     if voice.is_paused():
    #         await ctx.send("已繼續播放音樂")
    #         voice.resume()
    #     else:
    #         await ctx.send("The audio is not pause")

    # @commands.hybrid_command(aliasese=['skip', '跳過'], name='跳過音樂', description='Skip the song!')
    # async def skip(self, ctx):
    #     voice = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        
    #     if voice.is_paused() or voice.is_playing():
    #         await ctx.send("已跳過此音樂")
    #         voice.stop()
    #     else:
    #         await ctx.send('沒有正在播放的音樂')

if __name__ == '__main__':
    # string = str(input())
    yt()
    asyncio.run(main())
