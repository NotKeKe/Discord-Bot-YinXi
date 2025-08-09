import discord
from discord.ext import commands, voice_recv
import asyncio

from core.classes import Cog_Extension

class Recording(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.command()
    async def record(self, ctx: commands.Context, seconds: int = 10):
        if not ctx.author.voice.channel: return await ctx.send('請先加入頻道')
        
        voice_channel = ctx.author.voice.channel
        voice_client = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)
        voice_client.mode = 'xsalsa20_poly1305'

        output_file = f'./data/{ctx.author.id}.wav'
        sink = voice_recv.WaveSink(output_file)

        voice_client.listen(sink)

        await asyncio.sleep(seconds)

        voice_client.stop_listening()
        await voice_client.disconnect()

        await ctx.send('Done')

    @commands.command()  
    async def speaking(self, ctx: commands.Context, member: discord.Member = None):  
        """檢查成員是否正在說話"""  
        voice_channel = ctx.author.voice.channel
        voice_client = ctx.voice_client
        if not voice_channel: return await ctx.send('請先加入語音頻道')
        if not ctx.voice_client:
            voice_client = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)
        if not isinstance(voice_client, voice_recv, voice_recv.VoiceRecvClient):
            await voice_client.disconnect()
            voice_client = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)
            
        member = member or ctx.author  
        speaking_state = voice_client.get_speaking(member)  
        
        if speaking_state is None:  
            await ctx.send(f"{member.display_name} 不在語音頻道中")  
        elif speaking_state:  
            await ctx.send(f"{member.display_name} 正在說話")  
        else:  
            await ctx.send(f"{member.display_name} 沒有說話")


# async def setup(bot):
#     await bot.add_cog(Recording(bot))