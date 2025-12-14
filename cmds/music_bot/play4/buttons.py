from discord import Interaction, SelectOption, Message, errors, File, ButtonStyle
from discord.ui import View, button, select, Button
import traceback
import io

from cmds.music_bot.play4.player import Player
from cmds.music_bot.play4.utils import send_info_embed, create_basic_embed
from cmds.music_bot.play4.lyrics import search_lyrics
from core.classes import get_bot
from core.functions import yinxi_base_url


class MusicControlButtons(View):
    def __init__(self, player: Player, timeout = 180):
        super().__init__(timeout=timeout)
        self.player = player
        self.translator = player.translator
        self.locale = player.locale

        url_button = Button(label='URL', emoji='🔗', style=ButtonStyle.link, url=f'{yinxi_base_url}/player/{player.guild.id}_{player._uuid}')
        self.add_item(url_button)

    async def button_error(self, inter: Interaction, exception):
        if isinstance(exception, errors.Forbidden):
            try:
                bot = get_bot()
                u = bot.get_user(inter.user.id)
                await u.send("I'm missing some permissions:((")
            finally:
                return
        traceback.print_exc()
    
    @button(label='上一首歌', emoji='⏮️')
    async def previous_callback(self, interaction: Interaction, button: Button):
        try:
            await self.player.back()
            await send_info_embed(self.player, interaction)
        except Exception as e:
            await self.button_error(interaction, e)

    @button(label='暫停/繼續', emoji='⏯️')
    async def pause_resume_callback(self, interaction: Interaction, button: Button):
        try:
            if self.player.paused:
                await self.player.resume()
            else:
                await self.player.pause()
            embed, view = await send_info_embed(self.player, interaction, if_send=False)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            await self.button_error(interaction, e)

    @button(label='下一首歌', emoji='⏭️')
    async def next_callback(self, interaction: Interaction, button: Button):
        try:
            await self.player.skip()
            await send_info_embed(self.player, interaction)
        except Exception as e:
            await self.button_error(interaction, e)

    @button(label='停止播放', emoji='⏹️')
    async def stop_callback(self, interaction: Interaction, button: Button):
        try:
            from cmds.play4 import players
            
            if not interaction.user.voice.channel: return await interaction.response.send_message(await self.translator.get_translate('send_button_not_in_voice', self.locale))
            if not interaction.guild.voice_client: return await interaction.response.send_message(await self.translator.get_translate('send_button_bot_not_in_voice', self.locale))

            player: Player = players.get(interaction.guild.id)
            user = interaction.user.global_name

            if not player: return await interaction.response.send_message(await self.translator.get_translate('send_button_player_crashed', self.locale))
            del players[interaction.guild.id]

            channel = interaction.guild.voice_client.channel

            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message((await self.translator.get_translate('send_button_stopped_music', self.locale)).format(user=user, channel_mention=channel.mention))
        except Exception as e:
            await self.button_error(interaction, e)

    @button(label='循環', emoji='🔁')
    async def loop_callback(self, interaction: Interaction, button: Button):
        try:
            msg = interaction.message
            self.player.turn_loop()
            eb, view = await send_info_embed(self.player, interaction, if_send=False)
            await msg.edit(embed=eb, view=view)
            new_msg = await interaction.response.send_message((await self.translator.get_translate('send_button_loop_changed', self.locale)).format(loop_status=self.player.loop_status), ephemeral=True)
            await new_msg.resource.delete(delay=30)
        except Exception as e:
            await self.button_error(interaction, e)
    
    @button(label='列表', emoji='📄')
    async def queue_callback(self, interaction: Interaction, button: Button):
        try:
            eb = await self.player.show_list()
            await interaction.response.send_message(embed=eb, ephemeral=True)
        except Exception as e:
            await self.button_error(interaction, e)

    @button(label='刷新', emoji='🔄')
    async def refresh_callback(self, interaction: Interaction, button: Button):
        try:
            eb, view = await send_info_embed(self.player, interaction, if_send=False)
            await interaction.response.edit_message(embed=eb, view=view)
        except Exception as e:
            await self.button_error(interaction, e)

    @button(label='歌詞搜尋', emoji='🔍')
    async def search_callback(self, interation: Interaction, button: Button):
        try:
            await interation.response.defer(ephemeral=True, thinking=True)
            result = await self.player.search_lyrics()

            if len(result) > 2000:
                file = File(io.BytesIO(result.encode()), filename='lyrics.txt')
                result = result[:1996] + '...'
            else:
                file = None

            await interation.followup.send(result, **({'file': file} if file else {}), ephemeral=True)
        except Exception as e:
            await self.button_error(interation, e)

    @button(label='音量調整', emoji='🔊')
    async def volume_callback(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.send_message(view=VolumeControlButtons(self.player), ephemeral=True)
        except Exception as e:
            await self.button_error(interaction, e)

    # @button(label='歌曲推薦')
    # async def recommend_callback(self, interaction: Interaction, button: Button):
    #     try:
    #         from cmds.play4 import music_data
    #         item = music_data.data['recommend'].get(str(interaction.user.id))
    #         if not item: return await interaction.response.send_message(await self.translator.get_translate('send_button_recommend_not_enabled', self.locale))

    #         recommend: list = item.get('recommend')
    #         if not recommend: return await interaction.response.send_message(await self.translator.get_translate('send_button_no_recommendations', self.locale))

    #         eb = create_basic_embed(await self.translator.get_translate('embed_button_recommend_title', self.locale), color=interaction.user.color, 功能='音樂播放')
    #         eb.add_field(name='推薦歌曲', value='\n'.join( [ f'[{song[0]}]({song[3]}) - {song[1]}' for song in recommend ] ), inline=False)
    #         await interaction.response.send_message(embed=eb)
    #     except Exception as e:
    #         await self.button_error(interaction, e)

class VolumeControlButtons(View):
    def __init__(self, player: Player, timeout = 180):
        super().__init__(timeout=timeout)
        self.player = player

    @button(label='音量-50%', emoji='⏬')
    async def volume_down_50(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.defer()
            await self.player.volume_adjust(reduce=0.5)
        except Exception as e:
            traceback.print_exc()

    @button(label='音量-10%', emoji='➖')
    async def volume_down_10(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.defer()
            await self.player.volume_adjust(reduce=0.1)
        except Exception as e:
            traceback.print_exc()

    @button(label='正常音量', emoji='🔊')
    async def volume_normal(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.defer()
            await self.player.volume_adjust(volume=1.0)
        except Exception as e:
            traceback.print_exc()

    @button(label='音量+10%', emoji='➕')
    async def volume_up_10(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.defer()
            await self.player.volume_adjust(add=0.1)
        except Exception as e:
            traceback.print_exc()

    @button(label='音量+50%', emoji='🔼')
    async def volume_up_50(self, interaction: Interaction, button: Button):
        try:
            await interaction.response.defer()
            await self.player.volume_adjust(add=0.5)
        except Exception as e:
            traceback.print_exc()
