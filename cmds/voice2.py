import asyncio
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import itertools

from core.classes import Cog_Extension
from core.functions import read_json, create_basic_embed
from cmds.music_bot.play2.default import save, init, personal_list_path
from cmds.music_bot.play2.button import ButtonView, PaginatorView
from cmds.music_bot.play2.play2 import ID, is_youtube_url, is_audio_url, is_looping, ytSearch, get_yt_audio_url, play, is_in_channel, play_next, get_user_choice, create_info_embed, get_current_info

import os
from dotenv import load_dotenv

import traceback

load_dotenv()
KeJC_ID = os.getenv('KeJC_ID')
embed_link = os.getenv('embed_default_link')
po_token = os.getenv('YouTube_PoToken')
visitor_data = os.getenv('YouTube_visitorData')

async def youtubeUrlOrText(ctx: commands.Context, 輸入文字或連結, ispersonal=False):
    if is_youtube_url(輸入文字或連結):
        message = await ctx.send('Loading...')

        async with ctx.typing():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(executor=None, func=lambda: get_yt_audio_url(ctx,輸入文字或連結, ispersonal))
    else:
        message = await get_user_choice(ctx, 輸入文字或連結, ispersonal)

    return message

class Voice(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        save.personal_list = read_json(personal_list_path)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, discord.errors.ClientException): print(f"錯誤: {error}"); return
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
                        await channel.guild.voice_client.disconnect()
                            
                        await channel.send("已經5分鐘沒人了，所以我就滑出去了（ ´☣///_ゝ///☣｀）", silent=True)
        except Exception as e:
            print('from voice.py task: ' + e)


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
        try:
            # 判斷使用者是否在頻道當中
            if not await is_in_channel(ctx): return

            message = await youtubeUrlOrText(ctx, 輸入文字或連結)
                
            queue = save.queues[ctx.guild.id][0]
            audio_url = queue['audio_url']
            embed, view = get_current_info(self.bot, ctx)

            await message.edit(content=None, embed=embed, view=view)

            # 開始播放音樂
            if not discord.opus.is_loaded():
                discord.opus.load_opus('libopus-0.dll')

            # 連接至使用者頻道
            if not ctx.guild.voice_client: # Bot 尚未連接頻道
                voice_client = await ctx.author.voice.channel.connect()
            else: # Bot 已經連接頻道
                voice_client = ctx.guild.voice_client

            save.current_playing_index[ctx.guild.id] = 0
            play(self.bot, ctx, voice_client, audio_url)
        except Exception as e:
            traceback.print_exc()

    @commands.hybrid_command(aliases=['queue'], name="新增列隊", description='Add a song to queue')
    async def queue(self, ctx:commands.Context, 輸入文字或連結):
        if not await is_in_channel(ctx): return
        if not save.queues[ctx.guild.id] or not ctx.guild.voice_client: await ctx.send(content="先使用[p 增加音樂吧!", ephemeral=True); return

        message = await youtubeUrlOrText(ctx, 輸入文字或連結)

        await ctx.send(content="成功將歌曲加入列隊", ephemeral=True)

    @commands.hybrid_command(aliases=['current', 'now', 'playing'], name='正在播放', description='Display what song is playing')
    async def now_playing(self, ctx:commands.Context):
        try:
            if not await is_in_channel(ctx): return

            index = save.current_playing_index[ctx.guild.id]
            embed, view = get_current_info(self.bot, ctx, index)
            await ctx.send(embed=embed, view=view)
        except:
            traceback.print_exc()


    @commands.hybrid_command(aliases=['clear', 'clear_queue'], name="清除列隊", description='Clear the queue')
    async def clear_queue(self, ctx: commands.Context):
        if ctx.guild.id in save.queues:
            del save.queues[ctx.guild.id]
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
            if ctx.guild.id in save.queues:
                del save.queues[ctx.guild.id]
            await ctx.send(content='已停止音樂', ephemeral=True)
        except Exception as e:
            print(e)

    @commands.hybrid_command(aliases=['循環', 'loop'], name='循環音樂', description='Loop the current song')
    async def loop(self, ctx: commands.Context):
        if ctx.guild.id not in save.current_playing_index:
            await ctx.send(content='沒有正在播放的音樂', ephemeral=True)
            return

        if ctx.guild.id not in save.looping:
            save.looping.append(ctx.guild.id)
            await ctx.send('已開始循環播放')
        else:
            save.looping.remove(ctx.guild.id)
            await ctx.send('已停止循環播放')

    @commands.hybrid_command(aliases=['pre'], name='上一首', description='Play the previous song')
    async def pervious_callback(self, ctx: commands.Context):
        if save.current_playing_index[ctx.guild.id]-1 < 0: return

        from cmds.music_bot.play2.play2 import play_button, is_looping

        ctx.guild.voice_client.stop()
        if not is_looping(ctx):
            save.current_playing_index[ctx.guild.id] -= 2
        else: 
            save.current_playing_index[ctx.guild.id] -= 1

        await ctx.send('已開始播放上一首歌')
        await play_button(self.bot, ctx)


    @commands.hybrid_command(aliases=['list', '列表'], name='播放列表', description='Display the song list')
    async def list(self, ctx: commands.Context):
        try:
            if not await is_in_channel(ctx): return

            if ctx.guild.id not in save.current_playing_index: await ctx.send('沒有正在播放的歌曲', ephemeral=True); return

            embed = discord.Embed(title='🎵 LIST 🎵', color=ctx.author.color, timestamp=datetime.now())
            embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)
            embed.set_author(name='歌曲列表 (最多顯示10項)', icon_url=embed_link)
            if ctx.guild.id in save.queues:
                # 顯示最多9項 (for迴圈中)
                queues = save.queues
                index = save.current_playing_index[ctx.guild.id]
                for song in itertools.islice(queues[ctx.guild.id], index, index + 10):
                    embed.add_field(name=f'{queues[ctx.guild.id].index(song)+1}. ', value=f'[{song["title"]}]({song["video_url"]})  時長: {song["length"]}', inline=True)
            embed.add_field(name='循環狀態', value='開啟' if ctx.guild.id in save.looping else '關閉', inline=True)
            await ctx.send(embed=embed)
        except:
            traceback.print_exc()

    @commands.hybrid_command(aliases=['next'], name='下一首', description='Play the next song')
    async def next(self, ctx):
        if save.current_playing_index[ctx.guild.id]+1 >= len(save.queues[ctx.guild.id]): return

        from cmds.music_bot.play2.play2 import play_button, is_looping

        ctx.guild.voice_client.stop()
        if is_looping(ctx):
            save.current_playing_index[ctx.guild.id] += 1        

        await ctx.send('已開始播放下一首歌')
        await play_button(self.bot, ctx)

    @commands.hybrid_command(aliases=['selfplay'], name='播放個人清單', description='Play your personal list!')
    async def selfplay(self, ctx):
        try:
            if str(ctx.author.id) not in save.personal_list: await ctx.send('先使用[selflist 新增歌曲吧'); return
            if not await is_in_channel(ctx): return

            if not discord.opus.is_loaded():
                discord.opus.load_opus('libopus-0.dll')

            queue = save.personal_list[str(ctx.author.id)][0]
            audio_url = queue['audio_url']
            embed, view = get_current_info(self.bot, ctx, ispersonal=True)

            await ctx.send(embed=embed, view=view)

            # 連接至使用者頻道
            if not ctx.guild.voice_client: # Bot 尚未連接頻道
                voice_client = await ctx.author.voice.channel.connect()
            else: # Bot 已經連接頻道
                voice_client = ctx.guild.voice_client

            save.current_playing_index[ctx.guild.id] = 0
            play(self.bot, ctx, voice_client, audio_url, True)
        except: 
            traceback.print_exc()

    @commands.hybrid_command(aliases=['addselflist'], name='新增個人播放清單', description='Add a song to your personal list!')
    async def addpersonallist(self, ctx, 輸入文字或連結):
        try:
            message = await youtubeUrlOrText(ctx, 輸入文字或連結, True)

            await message.edit(content="成功將歌曲加入個人播放清單")
        except:
            traceback.print_exc()

    @commands.hybrid_command(aliases=['selflist', '個人列表', '個人播放列表',  'personallist'], name='個人播放清單', description='Display your song list')
    async def selflist(self, ctx: commands.Context):
        try:
            embed = discord.Embed(title='🎵 LIST 🎵', color=ctx.author.color, timestamp=datetime.now())
            embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)
            embed.set_author(name='歌曲列表 (最多顯示10項)', icon_url=embed_link)
            if str(ctx.author.id) in save.personal_list:
                # 顯示最多9項 (for迴圈中)
                user_id = str(ctx.author.id)
                list = save.personal_list
                index = save.current_playing_index[ctx.guild.id] if ctx.guild.id in save.current_playing_index else 0
                for song in itertools.islice(list[user_id], index, index + 10):
                    embed.add_field(name=f'{list[user_id].index(song)+1}. ', value=f'[{song["title"]}]({song["video_url"]})  時長: {song["length"]}', inline=True)
                if ctx.guild.id in save.current_playing_index:
                    embed.add_field(name='循環狀態', value='開啟' if ctx.guild.id in save.looping else '關閉', inline=True)
            else:
                embed.add_field(name='你尚未新增任何歌曲至你的個人播放清單中', value='', inline=True)
            await ctx.send(embed=embed)
        except:
            traceback.print_exc()

    @commands.hybrid_command(aliases=['dselflist', 'deleteselflist', 'dpersonallist', 'deletepersonallist'], name='刪除個人播放清單', description='Delete the song you selected')
    async def deletepersonallist(self, ctx: commands.Context):
        try:
            if str(ctx.author.id) not in save.personal_list: await ctx.send('你尚未新增任何歌曲', ephemeral=True); return

            embed:discord.Embed = create_basic_embed(title='🎵 LIST 🎵', color=ctx.author.color, 功能='刪除列表中的歌曲')
            embed.set_footer(text=ctx.author.name, icon_url=ctx.author.avatar.url)
            # 顯示最多9項 (for迴圈中)
            user_id = str(ctx.author.id)
            list = save.personal_list
            for song in itertools.islice(list[user_id], 0, 10):
                embed.add_field(name=f'{list[user_id].index(song)+1}. ', value=f'[{song["title"]}]({song["video_url"]})  時長: {song["length"]}', inline=True)

            async def select_callback(interaction: discord.Interaction):
                values = interaction.values
                deleted = []
                for value in values:
                    value = int(value) - 1
                    deleted.append(save.delete_info_for_personal_list(user_id, value)['title'])

                string = '\n'.join(deleted)
                embed = create_basic_embed(title='已刪除以下歌曲', description=string, color=interaction.user.color)
                embed.set_footer(text=interaction.user.name, icon_url=interaction.user.avatar.url)
                await interaction.response.send_message(embed=embed)

            範圍 = 10 if len(save.personal_list[str(ctx.author.id)]) >= 10 else len(save.personal_list[str(ctx.author.id)])
            option範圍 = [i for i in range(範圍)]

            select = discord.ui.Select(placeholder='選擇你要刪除第幾首', max_values=10, min_values=1,
                                       options=[discord.SelectOption(label=i+1) for i in option範圍])
            select.callback = select_callback

            view = discord.ui.View()
            view.add_item(select)

            await ctx.send(embed=embed, view=view)
        except:
            traceback.print_exc()

    @commands.command(name='voicedata')
    async def data(self, ctx):
        if str(ctx.author.id) != KeJC_ID: return

        select = discord.ui.Select(placeholder='選擇一個選項', min_values=1, max_values=1,
                                    options=[
                                        discord.SelectOption(label='items', value=1),
                                        discord.SelectOption(label='personal_list', value=2),
                                        discord.SelectOption(label='queues', value=3),
                                        discord.SelectOption(label='current_playing_index', value=4),
                                        discord.SelectOption(label='looping', value=5)
                                    ])

        async def select_callback(interaction: discord.Interaction):
            value = int(select.values[0])
            if value == 1: result = save.items
            elif value == 2: result = save.personal_list[str(interaction.user.id)]
            elif value == 3: result = save.queues[interaction.guild.id]
            elif value == 4: result = save.current_playing_index[interaction.guild.id]
            elif value == 5: result = '開啟' if interaction.guild.id in save.looping else '關閉'

            await interaction.response.send_message(str(result)[:2000])

        select.callback = select_callback
        view = discord.ui.View()
        view.add_item(select)
        await ctx.send(view=view)




# async def setup(bot):
#     await bot.add_cog(Voice(bot))