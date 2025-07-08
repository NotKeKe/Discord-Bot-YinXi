from discord import Interaction, SelectOption, Message
from discord.ui import View, button, select, Button
import traceback

from cmds.music_bot.play4.player import Player
from cmds.music_bot.play4.utils import send_info_embed, create_basic_embed
from cmds.music_bot.play4.lyrics import search_lyrics


class MusicControlButtons(View):
    def __init__(self, player: Player, timeout = 180):
        super().__init__(timeout=timeout)
        self.player = player
        self.translator = player.translator
        self.locale = player.locale
    
    @button(label='上一首歌', emoji='⏮️')
    async def previous_callback(self, interaction: Interaction, button: Button):
        await self.player.back()
        await send_info_embed(self.player, interaction)

    @button(label='暫停/繼續', emoji='⏯️')
    async def pause_resume_callback(self, interaction: Interaction, button: Button):
        if self.player.paused:
            await self.player.resume()
        else:
            await self.player.pause()
        embed, view = await send_info_embed(self.player, interaction, if_send=False)
        await interaction.response.edit_message(embed=embed, view=view)

    @button(label='下一首歌', emoji='⏭️')
    async def next_callback(self, interaction: Interaction, button: Button):
        await self.player.skip()
        await send_info_embed(self.player, interaction)

    @button(label='停止播放', emoji='⏹️')
    async def stop_callback(self, interaction: Interaction, button: Button):
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

    @button(label='循環', emoji='🔁')
    async def loop_callback(self, interaction: Interaction, button: Button):
        msg = interaction.message
        self.player.turn_loop()
        eb, view = await send_info_embed(self.player, interaction, if_send=False)
        await msg.edit(embed=eb, view=view)
        await interaction.response.send_message((await self.translator.get_translate('send_button_loop_changed', self.locale)).format(loop_status=self.player.loop_status), ephemeral=True)
    
    @button(label='列表', emoji='📄')
    async def queue_callback(self, interaction: Interaction, button: Button):
        eb = await self.player.show_list()
        await interaction.response.send_message(embed=eb, ephemeral=True)

    @button(label='刷新', emoji='🔄')
    async def refresh_callback(self, interaction: Interaction, button: Button):
        eb, view = await send_info_embed(self.player, interaction, if_send=False)
        await interaction.response.edit_message(embed=eb, view=view)

    @button(label='歌詞搜尋', emoji='🔍')
    async def search_callback(self, interation: Interaction, button: Button):
        await interation.response.defer(ephemeral=True, thinking=True)
        result = await self.player.search_lyrics()
        await interation.followup.send(result, ephemeral=True)

    @button(label='音量調整', emoji='🔊')
    async def volume_callback(self, interaction: Interaction, button: Button):
        await interaction.response.send_message(view=VolumeControlButtons(self.player), ephemeral=True)

    @button(label='歌曲推薦')
    async def recommend_callback(self, interaction: Interaction, button: Button):
        from cmds.play4 import music_data
        item = music_data.data['recommend'].get(str(interaction.user.id))
        if not item: return await interaction.response.send_message(await self.translator.get_translate('send_button_recommend_not_enabled', self.locale))

        recommend: list = item.get('recommend')
        if not recommend: return await interaction.response.send_message(await self.translator.get_translate('send_button_no_recommendations', self.locale))

        eb = create_basic_embed(await self.translator.get_translate('embed_button_recommend_title', self.locale), color=interaction.user.color, 功能='音樂播放')
        eb.add_field(name='推薦歌曲', value='\n'.join( [ f'[{song[0]}]({song[3]}) - {song[1]}' for song in recommend ] ), inline=False)
        await interaction.response.send_message(embed=eb)

class VolumeControlButtons(View):
    def __init__(self, player: Player, timeout = 180):
        super().__init__(timeout=timeout)
        self.player = player

    @button(label='音量-50%', emoji='⏬')
    async def volume_down_50(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        await self.player.volume_adjust(reduce=0.5)

    @button(label='音量-10%', emoji='➖')
    async def volume_down_10(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        await self.player.volume_adjust(reduce=0.1)

    @button(label='正常音量', emoji='🔊')
    async def volume_normal(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        await self.player.volume_adjust(volume=1.0)

    @button(label='音量+10%', emoji='➕')
    async def volume_up_10(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        await self.player.volume_adjust(add=0.1)

    @button(label='音量+50%', emoji='🔼')
    async def volume_up_50(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        await self.player.volume_adjust(add=0.5)
