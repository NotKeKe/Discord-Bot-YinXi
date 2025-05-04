import asyncio
import discord
from discord.ext import commands, tasks
from pytubefix import YouTube, Search
from datetime import datetime, timedelta
import re
import itertools

from core.classes import Cog_Extension
from cmds.music_bot.play import queues, current_playing, looping, played, ButtonView, is_youtube_url, ytSearch, get_url, return_video_url, create_info_embed, human_play, machine_play

import os
from dotenv import load_dotenv

load_dotenv()
KeJC_ID = os.getenv('KeJC_ID')
embed_link = os.getenv('embed_default_link')
po_token = os.getenv('YouTube_PoToken')
visitor_data = os.getenv('YouTube_visitorData')

class Voice(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=error, user_send=False, ephemeral=False)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        try:
            if member.bot: return
        
            if before.channel is not None and after.channel is None:
                # 成員離開語音頻道
                # print(f"{member} 離開了語音頻道 {before.channel.name}")

                # 紀錄voice channel
                channel = before.channel

                if len(before.channel.members) == 1 or all(user.voice.self_deaf for user in channel.members if not member.bot):
                    await asyncio.sleep(300)  # 等待 5 分鐘
                    if len(channel.members) == 1 or all(user.voice.self_deaf for user in channel.members if not member.bot):
                        if channel.guild.id in current_playing:
                            del current_playing[channel.guild.id]
                        if channel.guild.id in queues:
                            del queues[channel.guild.id]
                        await channel.guild.voice_client.disconnect()
                            
                        await channel.send("已經5分鐘沒人了，所以我就滑出去了（ ´☣///_ゝ///☣｀）", silent=True)
        except Exception as e:
            print('from voice.py task: ' + e)

    # @commands.Cog.listener()
    # async def on_voice_state_update(self, member, before, after):
    #     if before.channel is None and after.channel is not None:
    #         # 成員加入語音頻道
    #         print(f"{member} 加入了語音頻道 {after.channel.name}")
    #     elif before.channel is not None and after.channel is None:
    #         # 成員離開語音頻道
    #         print(f"{member} 離開了語音頻道 {before.channel.name}")

    #         try:
    #             channel = before.channel
    #             await asyncio.sleep(3)
    #             print(len(channel.members))
    #         except Exception as e:
    #             print(e)

    #     elif before.channel != after.channel:
    #         # 成員從一個語音頻道移動到另一個語音頻道
            
    #         print(f"{member} 從 {before.channel.name} 移動到 {after.channel.name}")

    @commands.hybrid_command(aliases=['加入'], name = "join", description = "加入一個Voice channel")
    async def join(self, ctx):
        '''
        [join 或是 [加入
        加入一個語音頻道
        就醬
        '''
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            await ctx.send(f'我加入了「{ctx.author.voice.channel.mention}」')
        else:
            await ctx.send("你不在任何語音頻道當中")

    @commands.hybrid_command(aliases=['離開'], name = "leave", description = "離開所在的Voice channel")
    async def leave(self, ctx):
        '''
        [leave 或是 [離開
        離開一個語音頻道
        就醬
        '''
        if ctx.voice_client:
            await ctx.send(f'已退出「{ctx.voice_client.channel.mention}」')
            if ctx.guild.voice_client.is_playing():
                await ctx.invoke(self.bot.get_command('停止音樂'))
            await ctx.voice_client.disconnect()
        else:
            await ctx.send("我不在任何語音頻道當中", ephemeral=True)

    @commands.hybrid_command(aliases=['play', 'p', '播放', '音樂'], name='播放音樂', description='Play a song to you! (Put a url or some text in 輸入文字或連結)')
    async def play(self, ctx:commands.Context, 輸入文字或連結):
        await human_play(self.bot, ctx, 輸入文字或連結)

    @commands.hybrid_command(aliases=['queue'], name="新增列隊", description='Add a song to queue')
    async def queue(self, ctx:commands.Context, 輸入文字或連結):
        if not ctx.voice_client: await ctx.send(content="我不在任何語音頻道當中", ephemeral=True); return
        if ctx.guild.id not in current_playing: await ctx.send(content="先使用[p 增加音樂吧!", ephemeral=True); return

        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []

        # 如果不是連結，先讓使用者搜尋
        if not is_youtube_url(輸入文字或連結):
            video_url, message = await return_video_url(ctx, 輸入文字或連結)
        else: 
            video_url = 輸入文字或連結
            message = await ctx.send('Loading')

        async with ctx.typing():
            # 使用 asyncio 來避免阻塞
            loop = asyncio.get_event_loop()
            link, title, length, thumbnail = await loop.run_in_executor(executor=None, func=lambda: get_url(video_url))

        queues[ctx.guild.id].append(
            {
                'audio_url': link, 
                'title': title, 
                'length': length, 
                'thumbnail': thumbnail, 
                'video_url': video_url,
                'message': message
            }
        )

        await ctx.send(content="成功將歌曲加入列隊", ephemeral=True)

    @commands.hybrid_command(aliases=['current', 'now', 'playing'], name='正在播放', description='Display what song is playing')
    async def now_playing(self, ctx:commands.Context):
        if not ctx.voice_client: 
            await ctx.send(content="我不在任何語音頻道當中", ephemeral=True); return
        else:
            if not ctx.voice_client.is_playing(): 
                await ctx.send(content="沒有正在播放的音樂", ephemeral=True); return

        data = current_playing[ctx.guild.id]

        title = data['title']
        length = data['length']
        thumbnail = data['thumbnail']
        video_url = data['video_url']
        # [NotKeKe](https://github.com/NotKeKe)

        # Embed
        embed = create_info_embed(title, video_url, length, thumbnail, ctx.author)

        # Button and View
        view = ButtonView(self.bot)

        await ctx.send(content=None, embed=embed, view=view)

    @commands.hybrid_command(aliases=['clear', 'clear_queue'], name="清除列隊", description='Clear the queue')
    async def clear_queue(self, ctx: commands.Context):
        if ctx.guild.id in queues:
            del queues[ctx.guild.id]
            del current_playing[ctx.guild.id]
            await ctx.send(content="已清除列隊", ephemeral=True)
        else:
            await ctx.send(content="你們尚未點任何歌", ephemeral=True)

    @commands.hybrid_command(aliases=['pause', '暫停'], name='暫停音樂', description='Pause the playing song!')
    async def pause(self, ctx):
        try:
            if ctx.guild.voice_client:
                if ctx.guild.voice_client.is_playing():
                    ctx.guild.voice_client.pause()
                    await ctx.send('已暫停播放音樂')
                else:
                    await ctx.send('沒有正在播放的音樂')
            else:
                await ctx.send('我不在任何語音頻道當中')
        except Exception as e:
            print(e)

    @commands.hybrid_command(aliasese=['resume', '繼續', 'continue'], name='繼續音樂', description='Resume the stopped song!')
    async def resume(self, ctx):
        try:
            if ctx.guild.voice_client:
                if ctx.guild.voice_client.is_paused():
                    ctx.guild.voice_client.resume()
                    await ctx.send('已繼續播放音樂')
                else:
                    await ctx.send('沒有暫停的音樂')
            else:
                await ctx.send('我不在任何語音頻道當中')
        except Exception as e:
            print(e)

    @commands.hybrid_command(aliases=['stop', '停止'], name="停止音樂", description='Clear the queue and leave channel')
    async def stop(self, ctx: commands.Context):
        try:
            if not ctx.guild.voice_client:
                await ctx.send(content='我不在任何語音頻道當中', ephemeral=True)
                return

            ctx.guild.voice_client.stop()
            await ctx.guild.voice_client.disconnect()
            if ctx.guild.id in queues:
                del queues[ctx.guild.id]
            if ctx.guild.id in current_playing:
                del current_playing[ctx.guild.id]
            await ctx.send(content='已停止音樂', ephemeral=True)
        except Exception as e:
            print(e)

    @commands.hybrid_command(aliases=['循環', 'loop'], name='循環音樂', description='Loop the current song')
    async def loop(self, ctx: commands.Context):
        if ctx.guild.id not in current_playing:
            await ctx.send(content='沒有正在播放的音樂', ephemeral=True)
            return

        if ctx.guild.id not in looping:
            looping.append(ctx.guild.id)
            await ctx.send('已開始循環播放')
        else:
            looping.remove(ctx.guild.id)
            await ctx.send('已停止循環播放')

    @commands.hybrid_command(aliases=['pre'], name='上一首', description='Play the previous song')
    async def pervious_callback(self, ctx: commands.Context):
        if not ctx.guild.voice_client: await ctx.send('我尚未連接任何頻道', ephemeral=True); return
        if ctx.guild.id not in played: await ctx.send('沒上一首歌r 你在幹嘛s', ephemeral=True); return

        if ctx.guild.voice_client.is_playing(): await ctx.guild.voice_client.stop()

        # 給予played[ctx.guild.id]['pre'] = True讓play_next知道要播上一首
        played[ctx.guild.id]['pre'] = True

        link = played[ctx.guild.id][-1]['audio_url']
        title = played[ctx.guild.id][-1]['title']
        url = played[ctx.guild.id][-1]['video_url']
        length = played[ctx.guild.id][-1]['length']
        thumbnail = played[ctx.guild.id][-1]['thumbnail']

        await ctx.send('已開始準備播放上一首歌')
        await machine_play(self.bot, ctx, link, title, url, length, thumbnail)

    @commands.hybrid_command(aliases=['list', '列表'], name='播放列表', description='Display the song list')
    async def queue_callback(self, ctx: commands.Context):
        if not ctx.guild.voice_client: await ctx.send('我不在任何頻道中', ephemeral=True); return
        if ctx.guild.id not in queues or not queues[ctx.guild.id]: await ctx.send('沒有歌曲在列隊中 (或使用[正在播放 查看正在播放的音樂)', ephemeral=True); return

        embed = discord.Embed(title='🎵 LIST 🎵', color=ctx.author.color, timestamp=datetime.now())
        embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)
        embed.set_author(name='歌曲列表 (最多顯示10項)', icon_url=embed_link)
        embed.add_field(name='1. ', value=f"[{current_playing[ctx.guild.id]['title']}]({current_playing[ctx.guild.id]['video_url']})    時長: {current_playing[ctx.guild.id]['length']}", inline=True)
        if ctx.guild.id in queues:
            # 顯示最多9項 (for迴圈中)
            for song in itertools.islice(queues[ctx.guild.id], 9):
                embed.add_field(name=f"{queues[ctx.guild.id].index(song)+2}. ', value=f'[{song["title"]}]({song["video_url"]})  時長: {song['length']}", inline=True)
        embed.add_field(name='循環狀態', value='開啟' if ctx.guild.id in looping else '關閉', inline=True)
        await ctx.send(embed=embed)


    





# async def setup(bot):
#     await bot.add_cog(Voice(bot))