import discord
from discord.ext import commands
from discord import app_commands
import traceback

from core.classes import Cog_Extension
from core.functions import create_basic_embed, thread_pool
from cmds.AIsTwo.others.func import translate

class Translator(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name='翻譯', description='Translate some text')
    @app_commands.describe(content='輸入你要翻譯的文字 Enter the text you wanna translate', 
                            target='選擇目標語言（你希望翻譯成哪種語言，預設為zh-TW） Select the language you want to translate into'  
                            )
    async def translate(self, ctx, content: str, target:str = 'zh-TW'):
        async with ctx.typing():
            think, translated = await thread_pool(translate, content, target)
            
            embed = create_basic_embed(功能='音汐', color=ctx.author.color)
            embed.add_field(name='**翻譯**', value=translated if translated else think, inline=False)
            embed.set_footer(text='Powered by qwen-3-32b')

            await ctx.send(embed=embed)




async def setup(bot):
    await bot.add_cog(Translator(bot))