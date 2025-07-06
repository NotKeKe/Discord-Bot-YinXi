import discord
from discord import app_commands
from discord.ext import commands
import time
from datetime import datetime, timedelta
import traceback

from core.classes import Cog_Extension
from core.functions import create_basic_embed, read_json, write_json

path = './cmds/data.json/world_channels.json'

bad_image_channel = 1338022304306954251

class WorldChat(Cog_Extension):
    channels = None

    @classmethod
    def initchannel(cls):
        if cls.channels is None:
            cls.channels = read_json(path)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.__class__.channels = read_json(path)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        '''
        如果使用者發送圖片，就不會再發送Embed
        '''
    
        if msg.author.bot: return
        self.initchannel()
        channels = self.__class__.channels
        if msg.channel.id not in channels['channels']: return

        # 使用者圖片
        attachments = [
            attachment.url
            for attachment in msg.attachments
            if attachment.content_type and attachment.content_type.startswith('image/')
        ]

        eb = create_basic_embed(color=msg.author.color)
        
        for cnl in channels['channels']:
            try:
                if msg.channel.id == cnl: continue
                channel = self.bot.get_channel(cnl)

                if attachments:
                    eb.add_field(name=f"**:speech_balloon: {msg.author.global_name}: **", value=f"User sended {len(attachments)} image{'s' if len(attachments) > 1 else ''}", inline=True)
                    await channel.send(embed=eb)
                    for a in attachments:
                        await channel.send(a)
                else:
                    eb.add_field(name=f"**:speech_balloon: {msg.author.global_name}: **", value=msg.content, inline=True)
                    await channel.send(embed=eb)
            except TypeError:
                ...
            except Exception as e:
                print(f'An error accured at world_chat: {e}')

        user_said = msg.content if not attachments else f"{f'{msg.content} | 'if msg.content else ''}{' '.join(attachments)}"
            
        time = datetime.now()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        channels['History'].append(f"{now} | {msg.author.global_name}: {user_said}")

        self.__class__.channels = channels
        write_json(channels, path)

    @commands.hybrid_command(name='世界頻道', description='Set a World Channel')
    @commands.has_permissions(administrator=True)
    @app_commands.choices(
        是否取消 = [
            discord.app_commands.Choice(name = "不取消 (可以不填這項)", value = 1),
            discord.app_commands.Choice(name = "取消", value = 2)
        ]
    )
    async def setworldchannel(self, ctx, 是否取消: discord.app_commands.Choice[int] = None):
        self.initchannel()
        channels = self.__class__.channels

        if 是否取消 is not None:
            取消 = False if 是否取消.value==1 else True
        else: 取消 = False

        channelID = ctx.channel.id

        if 取消:
            if channelID not in channels['channels']: await ctx.send('此頻道不是世界頻道', ephemeral=True); return
            channels['channels'].remove(channelID)
            await ctx.send('已取消世界頻道')
        else:
            if channelID in channels['channels']: await ctx.send('你已經設定了世界頻道'); return
            channels['channels'].append(channelID)
            await ctx.send('已設置此頻道為世界頻道')

        self.__class__.channels = channels
        write_json(channels, path)

    @commands.hybrid_command(name='不良圖片檢舉', description='Report whoever sended bad image to you')
    @app_commands.describe(author='輸入該使用者的名稱(不是你的 除非你想舉報你自己)', 舉報原因='說說為什麼你要舉報他，是因為他傳送了不良圖片嗎:thinking:')
    async def report(self, ctx, author, 舉報原因):
        channel = await self.bot.fetch_channel(bad_image_channel)
        now = time.strftime("%Y/%m/%d %H:%M:%S")
        await channel.send(f"{ctx.guild.name} | {ctx.author.global_name} 於 {now} 舉報了\n{author=}\n{舉報原因=}\n舉報人ID{ctx.author.id}")
        await ctx.send(f'已成功向我舉報{author}')


async def setup(bot):
    await bot.add_cog(WorldChat(bot))