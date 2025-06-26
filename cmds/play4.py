'''You need to download `FFmpeg` to use these commands.'''
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks
import traceback
import asyncio

from cmds.music_bot.play4.player import Player, loop_option
from cmds.music_bot.play4.utils import send_info_embed, check_and_get_player
from cmds.music_bot.play4 import utils
from cmds.music_bot.play4.music_data import MusicData, Recommend
from cmds.music_bot.play4.lyrics import search_lyrics
from cmds.music_bot.play4.buttons import VolumeControlButtons

from core.classes import Cog_Extension
from core.functions import KeJCID, create_basic_embed

players = {}

music_data = None

class Music(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)
        global music_data
        music_data = MusicData()
        self.data = music_data
        self.recommend = Recommend(self.data)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.update_music_data.start()
        self.update_recommendations.start()

    @commands.hybrid_command(name='play', description='播放音樂', aliases=['p', '播放'])
    async def _play(self, ctx: commands.Context, *, query: str = None):
        try:
            async with ctx.typing():
                if not ctx.author.voice: return await ctx.send('你好像不在語音頻道裡面? 先加一個吧')
                if not ctx.voice_client:
                    await ctx.author.voice.channel.connect()

                if ctx.voice_client.is_paused(): return await ctx.invoke(self.bot.get_command('resume'))
                elif not query: return await ctx.send('我沒有接收到你的關鍵字欸... 記得輸入 `query`')
                if players.get(ctx.guild.id): return await ctx.invoke(self.bot.get_command('add'), query=query)

                player = Player(ctx)
                players[ctx.guild.id] = player
                data = await player.add(query, ctx)
                self.recommend.record_data(data, str(ctx.author.id))
                await player.play()
                await send_info_embed(player, ctx)
        except: 
            traceback.print_exc()
            await ctx.send('疑? 好像出錯了 要不換個 `query` 試試看?')
            del players[ctx.guild.id]

    @commands.hybrid_command(name='add', description='添加歌曲到播放清單')
    async def _add(self, ctx: commands.Context, *, query: str):
        async with ctx.typing():
            if not ctx.author.voice: return await ctx.send('你好像不在語音頻道裡面? 先加一個吧')
            if not ctx.voice_client: return await ctx.send('使用 `/play` 來點播音樂吧~')
            if ctx.author.voice.channel != ctx.voice_client.channel: return await ctx.send(f'你跟我不在同一個頻道裡欸... 先跟加到 {ctx.guild.voice_client.channel.mention}')

            player: Player = players.get(ctx.guild.id)
            if not player: return await ctx.send('音汐剛剛好像不正常退出了欸... 要不讓我重新加入看看?')

            data = await player.add(query, ctx)
            size = data[0]
            self.recommend.record_data(data, str(ctx.author.id))

            await send_info_embed(player, ctx, size-1)
            await ctx.send(f'已成功添加歌曲到播放清單中! 你現在有 {size} 首歌在播放清單裡了！', ephemeral=True)

    @commands.hybrid_command(name='skip', description='跳過當前歌曲', aliases=['s'])
    async def _skip(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            if not (await player.skip()): return await ctx.send('先加入一首歌吧~ 播放清單裡沒有更多的歌了')

            await send_info_embed(player, ctx)

    @commands.hybrid_command(name='back', description='播放上一首歌曲')
    async def _back(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return
            
            if not (await player.back()): return await ctx.send('先加入一首歌吧~ 播放清單裡沒有更多的歌了')

            await send_info_embed(player, ctx)

    @commands.hybrid_command(name='pause', description='暫停播放音樂', aliases=['ps', '暫停'])
    async def _pause(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            await player.pause()
    
    @commands.hybrid_command(name='resume', description='恢復播放音樂', aliases=['rs'])
    async def resume(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            # 修正邏輯：當暫停時才恢復播放
            await player.resume()

    @commands.hybrid_command(name="stop", description='Clear the queue and leave channel')
    async def _stop(self, ctx: commands.Context):
        async with ctx.typing():
            if not (ctx.author.voice and ctx.voice_client): return await ctx.send('疑? 是你還是我不在語音頻道裡面啊')
            if ctx.author.voice.channel != ctx.voice_client.channel: return await ctx.send('疑? 我們好像在不同的頻道裡面欸')
            channel = ctx.voice_client.channel
            await utils.leave(ctx)
            await ctx.send(f'已經停止音樂 並離開 {channel.mention} 囉~')

    @commands.hybrid_command(name='loop', description='設置循環播放模式')
    @app_commands.choices(loop_type = [Choice(name=item, value=item) for item in loop_option])
    async def _loop(self, ctx: commands.Context, loop_type: str):
        async with ctx.typing():
            loop_option_str = ', '.join(loop_option)
            if loop_type not in loop_option: return await ctx.send(f'你給了我錯誤的循環類型欸，可用的循環類型有`{loop_option_str}`\n再試一次吧~')

            player, status = await check_and_get_player(ctx)
            if not status: return

            player.loop(loop_type)
            await ctx.send(f'已將音樂循環模式設為 `{loop_type}`')

    @commands.hybrid_command(name='current_playing', description='顯示當前播放的歌曲', aliases=['np', '當前播放', 'now'])
    async def current_playing(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx, check_user_in_channel=False)
            if not status: return

            await send_info_embed(player, ctx)

    @commands.hybrid_command(name='list', description='顯示播放清單', aliases=['q', '清單', 'queue'])
    async def _list(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx, check_user_in_channel=False)
            if not status: return

            eb = player.show_list()

            await ctx.send(embed=eb)

    @commands.hybrid_command(name='delete_song', description='刪除播放清單中的歌曲', aliases=['rm', '刪除'])
    @app_commands.describe(number='輸入你要刪除第幾首歌')
    async def delete_song(self, ctx: commands.Context, number: int):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            item = player.delete_song(number - 1)

            await ctx.send(f"已刪除 `{item.get('title')}`，點播人: `{item.get('user').global_name}`")

    @commands.hybrid_command(name='clear_queue', description='清除整個播放清單', aliases=['cq', '清除', 'clear'])
    async def clear_queue(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return
            if not player.list: return await ctx.send('播放清單本來就是空的窩~')

            view = discord.ui.View(timeout=60)
            button_check = discord.ui.Button(emoji='✅', label='確認', style=discord.ButtonStyle.green)
            async def clear_queue_callback(interaction: discord.Interaction):
                player.clear_list()
                button_reject.disabled = True
                button_check.disabled = True
                await interaction.response.edit_message(content="✅ 已刪除播放清單", embed=None, view=None)
            button_check.callback = clear_queue_callback

            button_reject = discord.ui.Button(emoji='❌', label='取消', style=discord.ButtonStyle.red)
            async def button_reject_callback(interaction: discord.Interaction):
                button_reject.disabled = True
                button_check.disabled = True
                await interaction.response.edit_message(content="❌ 已取消", embed=None, view=None)
            button_reject.callback = button_reject_callback

            view.add_item(button_check)
            view.add_item(button_reject)

            eb = create_basic_embed('確定要刪除播放列表嗎?', color=ctx.author.color)
            eb.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
            await ctx.send(embed=eb, view=view)

    @commands.hybrid_command(name='leave', description='離開語音頻道')
    async def _leave(self, ctx: commands.Context):
        await ctx.invoke(self.bot.get_command('stop'))

    @commands.hybrid_command(name='音樂推薦', description='使用此指令來啟用音樂推薦，音汐將會開始記錄你的點播紀錄')
    async def music_recommendation(self, ctx: commands.Context):
        async with ctx.typing(ephemeral=True):
            if str(ctx.author.id) != KeJCID: return await ctx.send('此功能尚未開放')
            data = self.data.data['recommend']
            users = data.keys()
            userID = str(ctx.author.id)

            def create_eb():
                eb = create_basic_embed(f'當前狀態: {'啟用' if userID in users else '未啟用'}', description='使用此功能即代表你**同意音汐收集你的音樂點播**紀錄，並且最後**使用AI**來推薦你喜歡的音樂。', color=discord.Color.blue())
                eb.add_field(name='按鈕說明', value='1. 點擊啟用: 啟用音樂推薦功能，並同意音汐收集你的音樂點播紀錄。\n\n2. 點擊取消: 取消音樂推薦功能，如果你本來就沒開啟的話，則無效。\n\n3. 查看當前選擇狀態')
                return eb

            async def button_callback(interaction: discord.Interaction):
                if userID in users: return await interaction.response.send_message('你已經啟用過音樂推薦了', ephemeral=True)

                data[userID] = {
                    'song': [],
                    'recommend': [],
                    'update_time': ''
                }

                self.data.save()
                msg = interaction.message
                await interaction.response.send_message('已為你啟用音樂推薦功能', ephemeral=True)
                await msg.edit(view = None)
                
            async def button1_callback(interaction: discord.Interaction):
                del data[userID]

                self.data.save()
                msg = interaction.message
                await interaction.response.send_message('已為你取消音樂推薦功能', ephemeral=True)
                await msg.edit(view = None)

            async def button2_callback(interaction: discord.Interaction):
                eb = create_eb()
                await interaction.response.send_message(embed=eb, view=view, ephemeral=True)

            button = discord.ui.Button(label="啟用音樂推薦", style=discord.ButtonStyle.green)
            button1 = discord.ui.Button(label="取消音樂推薦", style=discord.ButtonStyle.red)
            button2 = discord.ui.Button(label="查看當前狀態", style=discord.ButtonStyle.gray)
            button.callback = button_callback
            button1.callback = button1_callback
            button2.callback = button2_callback

            view = discord.ui.View(timeout=60)
            view.add_item(button)
            view.add_item(button1)
            view.add_item(button2)

            await ctx.send(view=view, embed=create_eb(), ephemeral=True)

    @commands.hybrid_command(name='歌詞搜尋', description='Search lyrics with LrcApi (https://github.com/HisAtri/LrcApi)')
    @app_commands.describe(lrc='是否顯示 LRC 格式 (帶有時間) 的歌詞，預設為 False')
    async def lyrics_search(self, ctx: commands.Context, query: str, artist: str = None, lrc: bool = False):
        async with ctx.typing():
            result = await search_lyrics(query, artist, lrc)
            await ctx.send(result if result else '找不到這首歌的歌詞欸... 要不考慮換個關鍵字試試?')

            if len(result.splitlines()) < 10: await ctx.send('如果歌詞看起來太短的話 可以試試把 `lrc` 設為 `True` 窩w', ephemeral=True)

    @commands.hybrid_command(name='音量調整', description='Adjust the volume of the bot')
    @app_commands.describe(volume='0~100 (單位為 `%` )，如果不輸入的話 可以用按鈕點')
    async def volume_adjust(self, ctx: commands.Context, volume: int = None):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            if volume:
                await player.volume_adjust(volume=volume / 100)

            await ctx.send('音量大小按鈕', view=VolumeControlButtons(player))

    @commands.command(name='show_players')
    async def show_players(self, ctx: commands.Context):
        await ctx.send(f'目前共有 {str(len(players))} 個伺服器正在播放音樂\nServers: {", ".join([self.bot.get_guild(id) for id in players.keys()])}')
        player: Player = players.get(ctx.guild.id)
        if not player: return
        await send_info_embed(player, ctx)

    @commands.command(name='clear_players')
    async def clear_players(self, ctx: commands.Context):
        if str(ctx.author.id) != KeJCID: return
        global players
        players = {}
        await ctx.send('已清除players', ephemeral=True)

    @tasks.loop(minutes=1)
    async def update_music_data(self):
        self.data.write()

    @tasks.loop(hours=10)
    async def update_recommendations(self):
        # TODO: 完成此處邏輯以及其他部分
        recommend = self.recommend
        userIDs = self.data.data['recommend'].keys()
        for id in userIDs:
            await recommend.gener_recommendations(id)
            await asyncio.sleep(1)

    @update_music_data.before_loop
    async def before_update_music_data(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Music(bot))
