import discord
from discord.ext import commands
import itertools
from datetime import datetime
import traceback
import asyncio

from cmds.music_bot.play2.default import save
from core.functions import embed_link

# Select view
class MyView(discord.ui.View):
    def __init__(self, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.value = None
        

    @discord.ui.select(
        placeholder="選擇一首歌!", min_values=1, max_values=1,
            options=[
                discord.SelectOption(label=1),
                discord.SelectOption(label=2),
                discord.SelectOption(label=3),
                discord.SelectOption(label=4),
                discord.SelectOption(label=5),
            ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.value = select.values
        self.stop()

# ⏯️⏭️⏹️🔂📄
class ButtonView(discord.ui.View):
    def __init__(self, bot:commands.Bot, timeout = 300):
        super().__init__(timeout=timeout)
        self.bot = bot

    @discord.ui.button(label='⏮️上一首歌')
    async def pervious_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if save.current_playing_index[interaction.guild.id]-1 < 0: return

        from cmds.music_bot.play2.play2 import play_next, is_looping

        interaction.guild.voice_client.stop()
        if not is_looping(interaction):
            save.current_playing_index[interaction.guild.id] -= 2
        else: 
            save.current_playing_index[interaction.guild.id] -= 1

        if not str(interaction.user.id) in save.personal_list:
            save.current_playing_index[interaction.guild.id] -= 1

        await interaction.response.send_message('已開始播放上一首歌')
        await play_next(self.bot, interaction, True if str(interaction.user.id) in save.personal_list else False)

    @discord.ui.button(label='⏯️')
    async def pause_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message('已暫停播放音樂')
        elif interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message('已繼續播放音樂')
    
    @discord.ui.button(label='⏭️下一首歌')
    async def skip_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.guild.id not in save.current_playing_index: return
            
            if interaction.guild.id in save.queues:
                condition1 = save.current_playing_index[interaction.guild.id]+1 >= len(save.queues[interaction.guild.id])
                if condition1: return
                ispersonal = False
            elif str(interaction.user.id) in save.personal_list:
                condition2 = save.current_playing_index[interaction.guild.id]+1 >= len(save.personal_list[str(interaction.user.id)])
                if condition2: return
                ispersonal = True
            
            from cmds.music_bot.play2.play2 import play_next, is_looping

            interaction.guild.voice_client.stop()
            if is_looping(interaction):
                save.current_playing_index[interaction.guild.id] += 1        

            await interaction.response.send_message('已開始播放下一首歌')
            await play_next(self.bot, interaction, ispersonal)
        except:
            traceback.print_exc()

    @discord.ui.button(label='⏹️停止播放')
    async def stop_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        interaction.guild.voice_client.stop()
        await interaction.guild.voice_client.disconnect()
        if interaction.guild.id in save.queues:
            del save.queues[interaction.guild.id]
        await interaction.response.send_message(content='已停止音樂')

    @discord.ui.button(label='🔂單曲循環')
    async def loop_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.id not in save.current_playing_index: return

        if interaction.guild.id not in save.looping:
            save.looping.append(interaction.guild.id)
            await interaction.response.send_message('已開始循環播放')
        else:
            save.looping.remove(interaction.guild.id)
            await interaction.response.send_message('已停止循環播放')

    @discord.ui.button(label='📄列表')
    async def queue_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title='🎵 LIST 🎵', color=interaction.user.color, timestamp=datetime.now())
        embed.set_footer(text=interaction.user.name, icon_url=interaction.user.avatar.url)
        embed.set_author(name='歌曲列表 (最多顯示10項)', icon_url=embed_link)
        
        if interaction.guild.id in save.queues:
            # 顯示最多9項 (for迴圈中)
            queues = save.queues
            index = save.current_playing_index[interaction.guild.id]
            for song in itertools.islice(queues[interaction.guild.id], index, index + 10):
                embed.add_field(name=f'{queues[interaction.guild.id].index(song)+1}. ', value=f'[{song["title"]}]({song["video_url"]})  時長: {song["length"]}', inline=True)
        elif str(interaction.user.id) in save.personal_list:
            user_id = str(interaction.user.id)
            list = save.personal_list
            index = save.current_playing_index[interaction.guild.id] if interaction.guild.id in save.current_playing_index else 0
            for song in itertools.islice(list[user_id], index, index + 10):
                embed.add_field(name=f'{list[user_id].index(song)+1}. ', value=f'[{song["title"]}]({song["video_url"]})  時長: {song["length"]}', inline=True)
        else: return
        embed.add_field(name='循環狀態', value='開啟' if interaction.guild.id in save.looping else '關閉', inline=True)
        await interaction.response.send_message(embed=embed)

class PaginatorView(discord.ui.View):
    def __init__(self, pages):
        super().__init__()
        self.pages = pages
        self.current_page = 0
        options = [discord.SelectOption(label=page['title'], value=str(i)) for i, page in enumerate(self.pages)]
        self.children[0].options = options

    def get_options(self):
        return [discord.SelectOption(label=page['title'], value=str(i)) for i, page in enumerate(self.pages)]

    def get_output(self) -> str:
        content = self.pages
        
        data = [{'title': f"{content[i]['title']}"} for i in range(len(self.pages))]  # 假設有 20 項資料

        # 將資料每 10 項分為一個列表，並格式化每個項目的標題
        chunks = [['\n'.join([f"{j+1 + i}: {item['title']}" for j, item in enumerate(data[i:i + 10]) if 'title' in item])] for i in range(0, len(data), 10)]
        return ''.join(chunks[self.current_page])

    @discord.ui.select(placeholder="選擇你要刪除哪一首")
    async def select_page(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            value = int(select.values[0])
            item = save.delete_info_for_personal_list(str(interaction.user.id), value)
            self.pages = save.personal_list[str(interaction.user.id)]
            self.children[0].options = self.get_options()  # 更新選擇器的選項
            await interaction.response.edit_message(content=self.get_output(), view=self)
            await interaction.followup.send(content=f"已刪除{item['title']}", ephemeral=True)
        except:
            traceback.print_exc()

    @discord.ui.button(label="上一頁", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.select.options = self.get_options()  # 更新選擇器的選項
            await interaction.response.edit_message(content=self.get_output(), view=self)

    @discord.ui.button(label="下一頁", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.select.options = self.get_options()  # 更新選擇器的選項
            await interaction.response.edit_message(content=self.get_output(), view=self)


