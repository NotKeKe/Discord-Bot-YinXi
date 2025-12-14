'''You need to download `FFmpeg` to use these commands.'''
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks
import traceback
import copy

from cmds.music_bot.play4.player import Player, loop_option
from cmds.music_bot.play4.utils import send_info_embed, check_and_get_player
from cmds.music_bot.play4 import utils
from cmds.music_bot.play4.lyrics import search_lyrics
from cmds.music_bot.play4.buttons import VolumeControlButtons
from cmds.music_bot.play4.play_list import add_to_custom_list, CustomListPlayer, del_custom_list, get_custom_list
from cmds.music_bot.play4.autocomplete import *

from core.classes import Cog_Extension
from core.functions import KeJCID, create_basic_embed
from core.translator import locale_str, load_translated

players: dict[int, Player] = {}
custom_list_players: dict[int, CustomListPlayer] = {}
join_channel_time: dict[int, datetime] = {}

class Music(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)

    async def cog_load(self):
        print(f'已載入「{__name__}」')
        self.check_left_channel.start()

    async def cog_unload(self):
        self.check_left_channel.cancel()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, exception: commands.errors.CommandError):
        if isinstance(exception, commands.CommandInvokeError):
            if isinstance(exception.original, discord.Forbidden):
                try:
                    u = self.bot.get_user(ctx.author.id)
                    return await u.send("I'm missing some permissions:((")
                except:
                    ...
        if not ctx.cog: return
        if ctx.cog.__cog_name__ != 'Music': return
        await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        '''用於檢測 bot 加入語音頻道，並紀錄時間'''
        guild_id = member.guild.id
        if member.id == self.bot.user.id:
            if before.channel is None and after.channel is not None: # 加入語音頻道
                join_channel_time[guild_id] = datetime.now()
            elif before.channel is not None and after.channel is None: # 離開語音頻道
                if guild_id in join_channel_time:
                    del join_channel_time[guild_id]
                if guild_id in players:
                    del players[guild_id]
                if guild_id in custom_list_players:
                    del custom_list_players[guild_id]
            elif before.channel is not None and after.channel is not None: # 切換語音頻道
                join_channel_time[guild_id] = datetime.now()
        else: # 普通使用者 or 其他 bot
            if member.bot: return
            just_self_deafened = not before.self_deaf and after.self_deaf
            just_deafened_by_server = not before.deaf and after.deaf

            if not (just_self_deafened or just_deafened_by_server): # 如果不是 (使用者開啟拒聽 or 使用者被伺服器拒聽)
                return
            
            if guild_id in join_channel_time: # 如果確定 bot 在語音頻道，再更新
                join_channel_time[guild_id] = datetime.now()

    @commands.hybrid_command(name=locale_str('play'), description=locale_str('play'), aliases=['p', '播放'])
    @app_commands.describe(query=locale_str('play_query'))
    @app_commands.autocomplete(query=play_query_autocomplete)
    async def _play(self, ctx: commands.Context, *, query: str = None):
        try:
            async with ctx.typing():
                member = ctx.guild.get_member(ctx.author.id) or await ctx.guild.fetch_member(ctx.author.id) if ctx.guild else None
                if not member:
                    return await ctx.send(await ctx.interaction.translate('send_play_not_in_guild'))

                if not member.voice: return await ctx.send(await ctx.interaction.translate('send_play_not_in_voice'))
                if not ctx.voice_client:
                    await member.voice.channel.connect()

                if ctx.voice_client.is_paused(): return await ctx.invoke(self.bot.get_command('resume'))
                elif not query: return await ctx.send(await ctx.interaction.translate('send_play_no_query'))
                if players.get(ctx.guild.id): return await ctx.invoke(self.bot.get_command('add'), query=query)

                player = Player(ctx)
                players[ctx.guild.id] = player
                data = await player.add(query, ctx)
                await player.play()
                await send_info_embed(player, ctx)
        except:
            traceback.print_exc()
            await ctx.send(await ctx.interaction.translate('send_play_error'))
            if ctx.guild.id in players:
                del players[ctx.guild.id]

    @commands.hybrid_command(name=locale_str('add'), description=locale_str('add'))
    @app_commands.describe(query=locale_str('add_query'))
    @app_commands.autocomplete(query=play_query_autocomplete)
    async def _add(self, ctx: commands.Context, *, query: str):
        async with ctx.typing():
            member = ctx.guild.get_member(ctx.author.id) or await ctx.guild.fetch_member(ctx.author.id) if ctx.guild else None
            if not member:
                return await ctx.send(await ctx.interaction.translate('send_play_not_in_guild'))

            if not member.voice: return await ctx.send(await ctx.interaction.translate('send_add_not_in_voice'))
            if not ctx.voice_client: return await ctx.send(await ctx.interaction.translate('send_add_use_play_first'))
            if member.voice.channel != ctx.voice_client.channel: return await ctx.send((await ctx.interaction.translate('send_add_not_in_same_channel')).format(channel_mention=ctx.guild.voice_client.channel.mention))

            try:
                player: Player = players.get(ctx.guild.id)
                if not player: return await ctx.send(await ctx.interaction.translate('send_add_player_crashed'))

                data = await player.add(query, ctx)
                size = data[0]

                await send_info_embed(player, ctx, size-1)
                await ctx.send((await ctx.interaction.translate('send_add_success')).format(size=size), ephemeral=True)
            except:
                traceback.print_exc()

    @commands.hybrid_command(name=locale_str('skip'), description=locale_str('skip'), aliases=['s'])
    async def _skip(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            if not (await player.skip()): return await ctx.send(await ctx.interaction.translate('send_skip_no_more_songs'))

            await send_info_embed(player, ctx)

    @commands.hybrid_command(name=locale_str('back'), description=locale_str('back'))
    async def _back(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return
            
            if not (await player.back()): return await ctx.send(await ctx.interaction.translate('send_back_no_more_songs'))

            await send_info_embed(player, ctx)

    @commands.hybrid_command(name=locale_str('pause'), description=locale_str('pause'), aliases=['ps', '暫停'])
    async def _pause(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            await player.pause(ctx)
    
    @commands.hybrid_command(name=locale_str('resume'), description=locale_str('resume'), aliases=['rs'])
    async def resume(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            # 修正邏輯：當暫停時才恢復播放
            await player.resume(ctx)

    @commands.hybrid_command(name=locale_str('stop'), description=locale_str('stop'))
    async def _stop(self, ctx: commands.Context):
        async with ctx.typing():
            member = ctx.guild.get_member(ctx.author.id) or await ctx.guild.fetch_member(ctx.author.id) if ctx.guild else None
            if not member:
                return await ctx.send(await ctx.interaction.translate('send_play_not_in_guild'))
            
            if not (member.voice and ctx.voice_client): return await ctx.send(await ctx.interaction.translate('send_stop_not_in_voice'))
            if member.voice.channel != ctx.voice_client.channel: return await ctx.send(await ctx.interaction.translate('send_stop_not_in_same_channel'))
            channel = ctx.voice_client.channel
            await utils.leave(ctx)
            await ctx.send((await ctx.interaction.translate('send_stop_success')).format(channel_mention=channel.mention))

    @commands.hybrid_command(name=locale_str('loop'), description=locale_str('loop'))
    @app_commands.choices(loop_type = [Choice(name=item, value=item) for item in loop_option])
    @app_commands.describe(loop_type=locale_str('loop_loop_type'))
    async def _loop(self, ctx: commands.Context, loop_type: str = None):
        async with ctx.typing():
            loop_option_str = ', '.join(loop_option)
            if loop_type not in loop_option and loop_type is not None: return await ctx.send((await ctx.interaction.translate('send_loop_invalid_type')).format(loop_option_str=loop_option_str))

            player, status = await check_and_get_player(ctx)
            if not status: return

            if loop_type is not None:
                player.loop(loop_type)
            else:
                loop_type = player.turn_loop()

            await ctx.send((await ctx.interaction.translate('send_loop_success')).format(loop_type=loop_type))

    @commands.hybrid_command(name=locale_str('nowplaying'), description=locale_str('nowplaying'), aliases=['np', '當前播放', 'now'])
    async def current_playing(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx, check_user_in_channel=False)
            if not status: return

            await send_info_embed(player, ctx)

    @commands.hybrid_command(name=locale_str('queue'), description=locale_str('queue'), aliases=['q', '清單'])
    async def _list(self, ctx: commands.Context):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx, check_user_in_channel=False)
            if not status: return

            eb = await player.show_list()

            await ctx.send(embed=eb)

    @commands.hybrid_command(name=locale_str('remove'), description=locale_str('remove'), aliases=['rm', '刪除'])
    @app_commands.describe(number=locale_str('remove_number'))
    async def delete_song(self, ctx: commands.Context, number: int):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            item = player.delete_song(number - 1)

            await ctx.send((await ctx.interaction.translate('send_remove_success')).format(title=item.get('title'), user_name=item.get('user').global_name))

    @commands.hybrid_command(name=locale_str('clear'), description=locale_str('clear'), aliases=['cq', '清除'])
    async def clear_queue(self, ctx: commands.Context):
        try:
            async with ctx.typing():
                player, status = await check_and_get_player(ctx)
                if not status: return
                if not player.list: return await ctx.send(await ctx.interaction.translate('send_clear_already_empty'))

                view = discord.ui.View(timeout=60)
                button_check = discord.ui.Button(emoji='✅', label=await ctx.interaction.translate('send_clear_confirm_button'), style=discord.ButtonStyle.green)
                async def clear_queue_callback(interaction: discord.Interaction):
                    player.clear_list()
                    button_reject.disabled = True
                    button_check.disabled = True
                    await interaction.response.edit_message(content=await interaction.translate('send_clear_success'), embed=None, view=None)
                button_check.callback = clear_queue_callback

                button_reject = discord.ui.Button(emoji='❌', label=await ctx.interaction.translate('send_clear_reject_button'), style=discord.ButtonStyle.red)
                async def button_reject_callback(interaction: discord.Interaction):
                    button_reject.disabled = True
                    button_check.disabled = True
                    await interaction.response.edit_message(content=await interaction.translate('send_clear_cancelled'), embed=None, view=None)
                button_reject.callback = button_reject_callback

                view.add_item(button_check)
                view.add_item(button_reject)

                '''i18n'''
                eb = load_translated((await ctx.interaction.translate('embed_clear_confirm')))[0]
                title = eb.get('title')
                ''''''

                eb = create_basic_embed(title, color=ctx.author.color)
                eb.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
                await ctx.send(embed=eb, view=view)
        except:
            traceback.print_exc()

    @commands.hybrid_command(name=locale_str('leave'), description=locale_str('leave'))
    async def _leave(self, ctx: commands.Context):
        await ctx.invoke(self.bot.get_command('stop'))

    @commands.hybrid_command(name=locale_str('lyrics'), description=locale_str('lyrics'))
    @app_commands.describe(query=locale_str('lyrics_query'), artist=locale_str('lyrics_artist'), lrc=locale_str('lyrics_lrc'))
    async def lyrics_search(self, ctx: commands.Context, query: str, artist: str = None, lrc: bool = False):
        async with ctx.typing():
            result = await search_lyrics(query, artist, lrc)
            await ctx.send(result if result else await ctx.interaction.translate('send_lyrics_not_found'))

            if not isinstance(result, str): return

            if len(result.splitlines()) < 10: await ctx.send(await ctx.interaction.translate('send_lyrics_too_short_tip'), ephemeral=True)

    @commands.hybrid_command(name=locale_str('volume'), description=locale_str('volume'))
    @app_commands.describe(volume=locale_str('volume_volume'))
    async def volume_adjust(self, ctx: commands.Context, volume: int = None):
        async with ctx.typing():
            player, status = await check_and_get_player(ctx)
            if not status: return

            if volume:
                await player.volume_adjust(volume=volume / 100)

            await ctx.send(await ctx.interaction.translate('send_volume_buttons_title'), view=VolumeControlButtons(player))

    @commands.hybrid_command(name=locale_str('play_custom_list'), description=locale_str('play_custom_list'))
    @app_commands.autocomplete(list_name=custom_play_list_autocomplete)
    async def play_custom_list(self, ctx: commands.Context, list_name: str):
        async with ctx.typing():
            member = ctx.guild.get_member(ctx.author.id) or await ctx.guild.fetch_member(ctx.author.id) if ctx.guild else None
            if not member:
                return await ctx.send(await ctx.interaction.translate('send_play_not_in_guild'))

            if not member.voice: return await ctx.send(await ctx.interaction.translate('send_play_not_in_voice'))
            if players.get(ctx.guild.id): # 不讓使用者同時播放兩個 list，或是自訂歌曲 + 自訂歌單
                return await ctx.send(await ctx.interaction.translate('send_play_custom_list_already_playing_left_first'))
            if not ctx.voice_client:
                await member.voice.channel.connect()

            if ctx.voice_client.is_paused(): return await ctx.invoke(self.bot.get_command('resume'))
            if players.get(ctx.guild.id): return # 如果 player 已經存在，則不再建立
            
            # 取得 player
            custom_list_player = CustomListPlayer(ctx, list_name)
            player = await custom_list_player.run()
            players[ctx.guild.id] = player
            custom_list_players[ctx.guild.id] = custom_list_player

            # 播放
            await player.play()
            await send_info_embed(player, ctx)
            
    @commands.hybrid_command(name=locale_str('add_custom_list'), description=locale_str('add_custom_list'))
    @app_commands.autocomplete(list_name=custom_play_list_autocomplete)
    @app_commands.describe(list_name=locale_str('add_custom_list_list_name'))
    async def add_custom_list(self, ctx: commands.Context, url: str, list_name: str):
        async with ctx.typing():
            result = await add_to_custom_list(url, list_name, ctx.author.id)
            await ctx.send(result if result is not True else (await ctx.interaction.translate('send_add_to_custom_list_success')).format(list_name=list_name))

    @commands.hybrid_command(name=locale_str('show_custom_list'), description=locale_str('show_custom_list'))
    @app_commands.autocomplete(list_name=custom_play_list_autocomplete)
    async def show_custom_list(self, ctx: commands.Context, list_name: str):
        async with ctx.typing():
            result = await get_custom_list(list_name, ctx.author.id)
            description = '\n'.join(f'{i+1}. [{song[0]}]({song[1]})' for i, song in enumerate(result))
            eb = create_basic_embed(description=description)
            await ctx.send(embed=eb)

    @commands.hybrid_command(name=locale_str('delete_custom_list'), description=locale_str('delete_custom_list'), aliases=['del_custom_list'])
    @app_commands.autocomplete(list_name=custom_play_list_autocomplete)
    async def delete_custom_list(self, ctx: commands.Context, list_name: str):
        async with ctx.typing():
            view = discord.ui.View(timeout=60)
            button_check = discord.ui.Button(emoji='✅', label='Yes', style=discord.ButtonStyle.green)
            async def button_check_callback(interaction: discord.Interaction):
                button_reject.disabled = True
                button_check.disabled = True

                await del_custom_list(list_name, interaction.user.id)

                await interaction.response.edit_message(content=await interaction.translate('send_delete_custom_list_success'), embed=None, view=None)
            button_check.callback = button_check_callback

            button_reject = discord.ui.Button(emoji='❌', label='No', style=discord.ButtonStyle.red)
            async def button_reject_callback(interaction: discord.Interaction):
                button_reject.disabled = True
                button_check.disabled = True
                await interaction.response.edit_message(content=await interaction.translate('send_delete_custom_list_cancelled'), embed=None, view=None)
            button_reject.callback = button_reject_callback

            view.add_item(button_check)
            view.add_item(button_reject)

            '''i18n'''
            eb = load_translated((await ctx.interaction.translate('embed_clear_confirm')))[0]
            title = eb.get('title')
            ''''''

            eb = create_basic_embed(title, color=ctx.author.color)
            eb.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
            await ctx.send(embed=eb, view=view)

    @commands.command(name='show_players')
    async def show_players(self, ctx: commands.Context):
        if str(ctx.author.id) != KeJCID: return

        guilds_count = sum(1 for guild in self.bot.guilds if guild.voice_client is not None)

        await ctx.send(f'目前共有 {str(len(players))} (players) 個伺服器正在播放音樂\n音汐正在 {guilds_count} 個頻道裡面\nServers: {", ".join([self.bot.get_guild(id).name for id in players.keys()])}')
        player: Player = players.get(ctx.guild.id)
        if not player: return
        await send_info_embed(player, ctx)

    @commands.command(name='curr_player')
    async def curr_player(self, ctx: commands.Context):
        if str(ctx.author.id) != KeJCID: return
        player: Player = players.get(ctx.guild.id)
        if not player: return await ctx.send('no player', ephemeral=True)
        
        from pathlib import Path
        with open(Path(__file__).parent / 'test.txt', 'r', encoding='utf-8') as f:
            f.write(player.__dict__)
        await ctx.send('Done')

    @commands.command(name='clear_players')
    async def clear_players(self, ctx: commands.Context):
        if str(ctx.author.id) != KeJCID: return
        global players
        players = {}
        await ctx.send('已清除players', ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_left_channel(self):
        for guild_id, time in copy.deepcopy(join_channel_time).items(): # 使用 deepcopy，避免迴圈途中被進行修改
            guild = self.bot.get_guild(guild_id) or await self.bot.fetch_guild(guild_id)
            if not guild:
                try: del join_channel_time[guild_id]
                except: ... # 可能在操作途中 使用者就把 bot 退掉了
                continue
            
            voice_client = guild.voice_client
            if not voice_client:
                try: del join_channel_time[guild_id]
                except: ... # 可能在操作途中 使用者就把 bot 退掉了
                continue
            channel = voice_client.channel

            curr_time = datetime.now()
            passed_time = (curr_time - time).total_seconds()

            if passed_time <= 120: continue # 只檢測超過 2 分鐘的 voice_client

            # 檢測 channel 裡面有沒有活人
            is_alive = False
            for member in channel.members:
                assert isinstance(member, discord.Member)
                if member.id == self.bot.user.id: continue
                voice_state = member.voice
                
                afk = voice_state.afk
                deaf = voice_state.deaf
                self_deaf = voice_state.self_deaf

                if not (afk or deaf or self_deaf):
                    is_alive = True
                    break

            if is_alive: 
                if guild_id in join_channel_time:
                    join_channel_time[guild_id] = datetime.now() # 2 分鐘後再判斷，避免短時間內重複判斷
                continue

            successful_run = True # 因為可能遇到途中就已經被刪掉，True 代表過程中完全沒被刪掉
            # 先清除其他變數中的 guild_id，因為 disconnect 會觸發刪除 join_channel_id
            try: del players[guild_id]
            except: successful_run = False
            try: del custom_list_players[guild_id]
            except: ...
            try: del join_channel_time[guild_id]
            except: successful_run = False
            try: await voice_client.disconnect()
            except: successful_run = False


            # 想想還是算了，因為 voice channel 那裡有個白點看著挺煩的:)
            # if successful_run: 
            #     sent_message = await self.bot.tree.translator.get_translate('send_check_left_channel_disconnect_success', guild.preferred_locale.value)
            #     await channel.send(sent_message, silent=True)

    @check_left_channel.before_loop
    async def check_left_channel_before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Music(bot))
