import discord
from discord.ext import commands
from discord import app_commands, SelectOption
from discord.app_commands import Choice
from discord.ui import Select, View
from core.classes import Cog_Extension
import json
import os
import time
from datetime import datetime
import random
import typing
from typing import Optional
import asyncio
import traceback
from dotenv import load_dotenv
import aiohttp
import motor.motor_asyncio

from core.functions import read_json, thread_pool, KeJCID, create_basic_embed, MONGO_URL, split_str_by_len_and_backtick

# get env
load_dotenv()

with open("setting.json", 'r', encoding='utf8') as jfile:
    jdata = json.load(jfile)

async def on_select(interaction: discord.Interaction):
    result = interaction.data["values"][0]
    await interaction.response.send_message(result)

class PersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Green', style=discord.ButtonStyle.green, custom_id='persistent_view:green')
    async def green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('This is green.', ephemeral=True)

    @discord.ui.button(label='Red', style=discord.ButtonStyle.red, custom_id='persistent_view:red')
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('This is red.', ephemeral=True)

    @discord.ui.button(label='Grey', style=discord.ButtonStyle.grey, custom_id='persistent_view:grey')
    async def grey(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('This is grey.', ephemeral=True)

def promision_check(interaction: discord.Interaction,):
    return str(interaction.user.id) == KeJCID

class TestTemp(Cog_Extension):
    def __init__(self, bot):
        super().__init__(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

        
    @commands.command()
    async def testtemp(self, ctx):
        await ctx.send("hello, this is testtemp", ephemeral=True)

    @commands.hybrid_command(name='取得所有指令名稱')
    async def get_all_commands(self, ctx: commands.Context):
        await ctx.send((', '.join(sorted(list(self.bot.all_commands)))) + f'\n共有 `{len(self.bot.all_commands)}` 個指令')

    @commands.command()
    async def embedtest(self, ctx):
        try:
            embed=discord.Embed(title="title", description="description", color=0xff0000, timestamp=datetime.now())
            embed.set_author(name="name", url="https://discord.gg/MhtxWJu")
            embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/584213384409382953/4438fe5d2f91ddd873407e759ff23116.png?size=512")
            embed.add_field(name="field", value="- value", inline=False)
            embed.set_footer(text="footer")
            await ctx.send(embed=embed)
        except Exception as e:
            print("Error: ", e)

    @commands.command()
    async def get_cog_name(self, ctx):
        lst = [filename for filename in self.bot.cogs]
        await ctx.send(lst)

    @commands.command()
    async def get_command_name(self, ctx):
        try:
            lst = [command.name for command in self.bot.get_cog('TestTemp').get_commands()]
            await ctx.send(lst)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

    @commands.command()
    async def errortest(self, ctx):
        try:
            raise Exception("testing")
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=True)
            
    @commands.command()
    async def systemchannel(self, ctx):
        if str(ctx.author.id) != KeJCID: return

        channel = ctx.guild.system_channel
        if channel is None:
            await ctx.send('這個伺服器沒有system channel')
        else:
            await ctx.send('have')
            if not channel.permissions_for(ctx.guild.me).send_messages: await ctx.send('預設頻道沒有權限讓我發送訊息'); return
            await channel.send("hi")

    @commands.command()
    async def fromidtoname(self, ctx, id):
        '''
        從user id 獲得名字
        '''
        user = await self.bot.fetch_user(id)
        await ctx.send(content=user.name, ephemeral=True)

    @commands.command()
    async def getguildid(self, ctx: commands.Context):
        await ctx.send(ctx.guild.id)

    @commands.command()
    async def buttontest(self, ctx):
        view = PersistentView()
        await ctx.send("請選擇一個按鈕", view=view)

    @commands.command()
    async def cmd(self, ctx):
        if str(ctx.author.id) != KeJCID: return
        print('hello\n')

    @commands.command()
    async def membernametest(self, ctx):
        member = ctx.author
        await ctx.send('name' + member.name)
        await ctx.send('global name' + member.global_name)
        await ctx.send('display name' + member.display_name)
        await ctx.send('str(member)' + str(member))

    @commands.command()
    async def getchannels(self, ctx):
        guild = ctx.guild
        channels = [channel.name for channel in guild.channels if str(channel.type) == 'text']
        await ctx.send(', '.join(channels))

    @commands.command()
    async def mongo_test(self, ctx: commands.Context):
        try:
            async with ctx.typing():
                client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
                db = client['test']
                collection = db[str(ctx.author.id)]

                await collection.insert_one({
                    'title': 'abcdefg',
                    'user': ctx.author.id,
                    'messages': [
                        {'role': 'user', 'content': 'prompt'},
                        {'role': 'assistant', 'content': 'wdym'}
                    ],
                    'createAt': datetime.now().timestamp()
                })

                await ctx.send(f"現在伺服器上的資料庫: {await client.list_database_names()}")
                await ctx.send(f"在 'test' 中的 collections: {await db.list_collection_names()}")
                await ctx.send(f'找到 {await collection.find_one({'user': ctx.author.id})}')
                async for d in collection.find({'user': ctx.author.id}):
                    await ctx.send(f'找到一項數據: {d}')
                await collection.update_one({
                    'title': 'abcdefg'
                },
                {
                    '$set': {
                        'messages': [
                            {'role': 'user', 'content': 'prompt2'},
                            {'role': 'assistant', 'content': 'wdym2'}
                        ]
                    }
                }
                )
        finally:
            if client:
                # client.drop_database('test')
                client.close()


async def setup(bot):
    await bot.add_cog(TestTemp(bot))