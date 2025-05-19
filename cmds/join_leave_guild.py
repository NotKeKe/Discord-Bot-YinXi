import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import typing
import traceback

from core.classes import Cog_Extension
from core.functions import embed_link, read_json, write_json, create_basic_embed

PATH = './cmds/data.json/guild_join.json'

example = {
    'ctx.guild.id': {'joinChannel': 'ctx.guild.system_channel.id', 'leaveChannel': 'ctx.channel.id'}
}

async def channel_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    try:
        channels = interaction.guild.channels
        channels = [cn.name for cn in channels]

        if current:
            channels = [channel for channel in channels if current.lower().strip() in channel.lower()]

        return [app_commands.Choice(name=channel, value=channel) for channel in channels][:25]
    except: traceback.print_exc()

class OnJoinLeave(Cog_Extension):
    data = None

    @classmethod
    def init_data(cls):
        if cls.data is None:
            cls.data = read_json(PATH)

    @classmethod
    def write_data(cls, data=None):
        if data is not None:
            cls.data = data
        write_json(cls.data, PATH)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.init_data()

    #自己加入
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            channel = guild.system_channel if guild.system_channel.permissions_for(guild.me).send_messages else (channel for channel in guild.text_channels if channel.permissions_for(guild.me).send_messages)
            if channel is None: return
            embed=discord.Embed(title="我的自我介紹!",  color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name="Hello", icon_url=embed_link)
            embed.set_author(name="Bot資訊", url=None, icon_url=embed_link)
            embed.add_field(name="作者: ", value="克克 KeJC", inline=True)
            embed.add_field(name="Github連結:",value="[NotKeKe](https://github.com/NotKeKe)", inline=True)
            embed.add_field(name='注意事項:', value="目前這隻bot還在測試階段，不要給他任何的管理權限!\n不要給他任何的管理權限!\n不要給他任何的管理權限!", inline=False)
            await channel.send(embed=embed)
        except Exception as exception:
            print(f"Error: {exception}")

    #成員加入
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            self.init_data()
            data = self.__class__.data
            guildID = str(member.guild.id)
            if guildID not in data: return

            channelID = data[guildID]['joinChannel']
            chn = await self.bot.fetch_channel(channelID)

            if chn:
                await chn.send(f'「{member.name}」滑進了這個了伺服器!')
        except: traceback.print_exc()

    #成員離開
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            self.init_data()
            data = self.__class__.data
            guildID = str(member.guild.id)
            if guildID not in data: return

            channelID = data[guildID]['leaveChannel']
            chn = await self.bot.fetch_channel(channelID)

            if chn:
                await chn.send(f'「{member.name}」從進來的地方又出去了 （ ´☣///_ゝ///☣｀）')
        except: traceback.print_exc()

    @commands.hybrid_command(name='join_leave_message', description='在使用者加入伺服器時 發送訊息')
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(join_channel=channel_autocomplete, leave_channel=channel_autocomplete)
    async def set_join_leave_message(self, ctx: commands.Context, join_channel: str=None, leave_channel: str=None):
        self.init_data()
        data = self.__class__.data
        guildID = str(ctx.guild.id)

        if guildID in data: 
            view = discord.ui.View()
            check_button = discord.ui.Button(label='✅')
            refuse_button = discord.ui.Button(label='❌')

            def disabled_button():
                check_button.disabled = True
                refuse_button.disabled = True
                return

            async def check_callback(interation: discord.Interaction):
                await interation.response.send_message('已取消操作', ephemeral=True)
                disabled_button()
            async def refuse_callback(interation: discord.Interaction):
                del data[guildID]
                await interation.response.send_message(f'已為 {interation.guild.name} 刪除此功能')
                self.write_data(data)
                disabled_button()
            
            check_button.callback = check_callback
            refuse_button.callback = refuse_callback

            view.add_item(check_button)
            view.add_item(refuse_button)

            embed = create_basic_embed('你確定不讓Bot在使用者加入及退出伺服器時 發送訊息嗎?', '✅表示繼續讓Bot發送 ❌表示**不**讓Bot繼續發送',
                                       time=False)

            await ctx.send(embed=embed, view=view)
        else:
            if join_channel == leave_channel == ctx.guild.system_channel == None: return await ctx.send('請輸入頻道')
            joinCh = None
            leaveCh = None
            if not join_channel: joinCh = ctx.guild.system_channel
            if not leave_channel: leaveCh = ctx.guild.system_channel

            if not (joinCh == leaveCh == ctx.guild.system_channel):
                for channel in ctx.guild.channels:
                    if not channel.name: continue
                    if channel.name == join_channel:
                        joinCh = channel
                    if channel.name == leave_channel:
                        leaveCh = channel
                    if type(join_channel) == type(leave_channel) == discord.channel.TextChannel:
                        break
            if not joinCh:
                return await ctx.send("請輸入加入頻道")
            elif not leaveCh:
                return await ctx.send("請輸入離開頻道") 
            
            if not joinCh.permissions_for(joinCh.guild.me).send_messages: return await ctx.send('請選取能讓我發送訊息的頻道')
            if not leaveCh.permissions_for(leaveCh.guild.me).send_messages: return await ctx.send('請選取能讓我發送訊息的頻道')

            data[guildID] = {'joinChannel': joinCh.id, 'leaveChannel': leaveCh.id}
            self.write_data(data)
            embed = create_basic_embed(f'已為 {ctx.guild.name} 新增此功能', f'(加入頻道: {joinCh.name} 離開頻道: {leaveCh.name})')
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(OnJoinLeave(bot))