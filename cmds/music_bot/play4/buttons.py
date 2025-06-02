from discord import Interaction, SelectOption
from discord.ui import View, button, select, Button

from cmds.music_bot.play4.player import Player
from cmds.music_bot.play4.utils import send_info_embed


class MusicControlButtons(View):
    def __init__(self, player: Player, timeout = 180):
        super().__init__(timeout=timeout)
        self.player = player
    
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
        
        if not interaction.user.voice.channel: return await interaction.response.send_message('你好像不在語音頻道裡面?')
        if not interaction.guild.voice_client: return await interaction.response.send_message('音汐不在語音頻道內欸:thinking:')

        player: Player = players.get(interaction.guild.id)
        user = interaction.user.global_name

        if not player: return await interaction.response.send_message('音汐剛剛好像不正常退出了呢:thinking:')
        del players[interaction.guild.id]

        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(f'( {user} ) 已經停止音樂囉~')

    @button(label='循環', emoji='🔁')
    async def loop_callback(self, interaction: Interaction, button: Button):
        msg = interaction.message
        self.player.turn_loop()
        eb, view = await send_info_embed(self.player, interaction, if_send=False)
        await msg.edit(embed=eb, view=view)
        await interaction.response.send_message(f'已將循環狀態改為 `{self.player.loop_status}`', ephemeral=True)
    
    @button(label='列表', emoji='📄')
    async def queue_callback(self, interaction: Interaction, button: Button):
        eb = self.player.show_list()
        await interaction.response.send_message(embed=eb)

    @button(label='刷新', emoji='🔄')
    async def refresh_callback(self, interaction: Interaction, button: Button):
        eb, view = await send_info_embed(self.player, interaction, if_send=False)
        await interaction.response.edit_message(embed=eb, view=view)