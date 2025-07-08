'''some commands only for me'''

from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
import traceback
import typing
import os
from dotenv import load_dotenv
import asyncio

from core.classes import Cog_Extension
from core.functions import testing_guildID

# get env
load_dotenv()
embed_link = os.getenv('embed_default_link')
KeJCID = os.getenv('KeJC_ID')

async def load_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[Choice[str]]:
    files = [filename[:-3] for filename in os.listdir('./cmds') if filename.endswith('.py')]
    files.sort()

    if current:
        files = [filename for filename in files if current.lower().strip() in filename.lower()]

    # 限制最多回傳 25 個結果
    return [Choice(name=filename, value=filename) for filename in files[:25]]

class Load(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    #load command
    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    @app_commands.describe(extension = "選擇一個category")
    @app_commands.autocomplete(extension = load_autocomplete)
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def load(self, ctx, extension: str):
        '''只有克克能用的話  還需要幫助嗎:thinking:'''
        if str(ctx.author.id) != KeJCID: await ctx.send("你沒有權限使用該指令"); return
        
        await ctx.send(f'嘗試載入「{extension}」', ephemeral=True)
        try:
            await self.bot.load_extension(f'cmds.{extension}')
        except Exception as e:
            await ctx.send(f"「{extension}」 未被載入", ephemeral=True)
            print("出錯 when loading: ", e)
            return
        await ctx.send(f"「{extension}」 已被載入", ephemeral=True)

    #unload command
    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    @app_commands.describe(extension = "選擇一個category")
    @app_commands.autocomplete(extension = load_autocomplete)
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def unload(self, ctx, extension: str):
        '''只有克克能用的話  還需要幫助嗎:thinking:'''
        if str(ctx.author.id) != KeJCID: await ctx.send("你沒有權限使用該指令"); return

        await ctx.send(f'嘗試卸載「{extension}」', ephemeral=True)
        try:
            await self.bot.unload_extension(f'cmds.{extension}')
        except Exception as e:
            await ctx.send(f"「{extension}」 未被卸載", ephemeral=True)
            print("出錯 when unloading: ", e)
            return
        await ctx.send(f"「{extension}」 已被卸載", ephemeral=True)
        
    #reload command
    @commands.hybrid_command()
    @commands.has_permissions(administrator=True)
    @app_commands.describe(extension = "選擇一個category")
    @app_commands.autocomplete(extension = load_autocomplete)
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def reload(self, ctx: commands.Context, extension: str):
        '''只有克克能用的話  還需要幫助嗎:thinking:'''
        if str(ctx.author.id) != KeJCID: await ctx.send("你沒有權限使用該指令"); return
        
        message1 = await ctx.send(f'嘗試重載「{extension}」', ephemeral=True)
        try:
            await self.bot.reload_extension(f'cmds.{extension}')
        except Exception as e:
            message2 = await ctx.send(f"「{extension}」 未被重載", ephemeral=True)
            print("出錯 when reloading: ", e)
            return
        message2 = await ctx.send(f"「{extension}」 已被重載", ephemeral=True)

        await asyncio.sleep(30)
        try:
            await message1.delete()
            await message2.delete()
        except:...

    #reload all commands
    @commands.hybrid_command(name = "全部重載", description = "reload all commands, 重載全部commands, 不會回報載入成功, 可於後台看到錯誤。")
    @commands.has_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def reloadall(self, ctx):
        '''只有克克能用的話  還需要幫助嗎:thinking:'''
        if str(ctx.author.id) != KeJCID: await ctx.send("你沒有權限使用該指令"); return

        embed=discord.Embed(color=discord.Color.blue(), timestamp= datetime.now())
        embed.set_author(name="Reload All commands", icon_url=embed_link)
        message = await ctx.send(embed=embed, ephemeral=True)
        for filename in os.listdir('./cmds'):
            try:
                if filename.endswith('.py'):
                    await self.bot.reload_extension(f'cmds.{filename[:-3]}')
                    embed.add_field(name=f'重載cmds.{filename}', value=' ')
                    await message.edit(embed=embed)    
            except Exception as e:
                print(f'出錯 When reloading extension: {e}')

    #reload sync
    @commands.hybrid_command(name = "重載sync")
    @commands.has_permissions(administrator=True)
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def reloadsync(self, ctx):
        '''只有克克能用的話  還需要幫助嗎:thinking:'''
        if str(ctx.author.id) != KeJCID: await ctx.send("你沒有權限使用該指令", ephemeral=True); return

        await ctx.send("trying to reload sync", ephemeral=True)
        try:
            synced_bot = await self.bot.tree.sync()
            await ctx.send(f'Synced {len(synced_bot)} commands.', ephemeral=True)
        except Exception as e:
            print("出錯 when synced: ", e)

    # reload all commands ands sync them
    @commands.hybrid_command(name="reload_all", description = "重載全部指令並sync一遍")
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def reload_all_sync(self, ctx):
        '''只有克克能用的話  還需要幫助嗎:thinking:'''
        if str(ctx.author.id) != KeJCID: await ctx.send("你沒有權限使用該指令", ephemeral=True); return
        
        embed=discord.Embed(color=discord.Color.blue(), timestamp= datetime.now())
        embed.set_author(name="Reload All commands and Sync", icon_url=embed_link)
        message = await ctx.send(embed=embed, ephemeral=True)
    
        error = []

        for filename in os.listdir('./cmds'):
            try:
                if filename.endswith('.py'):
                    await self.bot.reload_extension(f'cmds.{filename[:-3]}')
                    if len(embed.fields) < 24:
                        embed.add_field(name=f'重載cmds.{filename}', value=' ')
                    await message.edit(embed=embed)
            except Exception as e:
                error.append(f"Error when reload_all and sync: {e}")
                print("Error when reload_all and sync: ", e)

        if error: 
            errors = '\n'.join(error)
            ed = discord.Embed(title='錯誤', description=errors, color=discord.Color.blue(), timestamp=datetime.now())
            await ctx.send(embed=ed, ephemeral=True)
        
        synced_bot = await self.bot.tree.sync()
        embed.add_field(name=f'Synced {len(synced_bot)} commands.', value=' ')
        # await ctx.send(f'Synced {len(synced_bot)} commands.')
        await message.edit(embed=embed)

    @commands.command(name='restart')
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def restart(self, ctx):
        if str(ctx.author.id) != KeJCID: return

        message = await ctx.send('嘗試重啟bot...')
        os.system('pm2 restart DiscordBot')
        await asyncio.sleep(10)
        try: await message.delete()
        except:...

    @commands.command(name='清除日誌')
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def clear(self, ctx):
        if str(ctx.author.id) != KeJCID: return

        await ctx.send('正在清除日誌')
        os.system('pm2 flush')

    @commands.command(name='系統指令')
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def system_command(self, ctx, * , command):
        if str(ctx.author.id) != KeJCID: return
        
        await ctx.send(f'Running command: {command}')
        try:
            os.system(command)
        except:
            string = traceback.format_exc()
            await ctx.send(string)

    @commands.command(name='del_msg')
    async def del_msg(self, ctx: commands.Context, msgID: int):
        '''
        IF YOU CLONE THSI PROJECT FROM GITHUB, MAKE SURE YOU DON'T USE THIS COMMAND CASUALLY.
        I did this because I'm not always sitting in front of the computer, and sometimes my bot sended some bad things.
        '''
        if str(ctx.author.id) != KeJCID: return
        if ctx.guild.me.guild_permissions.manage_messages:
            await ctx.message.delete()
        msg = await ctx.channel.fetch_message(msgID)
        content = msg.content.replace('`', '')
        name = msg.author.global_name or msg.author.name
        await msg.delete()
        await ctx.send('已刪除訊息\nMessage ID: `{}`\nMessage Content: ```{}```\nMessage Author: `{}`'.format(msgID, content, name))



async def setup(bot):
    await bot.add_cog(Load(bot))
