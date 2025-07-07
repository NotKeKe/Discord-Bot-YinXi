from discord.ext import commands
from discord import app_commands

from core.classes import Cog_Extension
from core.functions import create_basic_embed, thread_pool
from core.translator import load_translated, locale_str
from cmds.AIsTwo.others.func import translate

class Translator(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name=locale_str('translate'), description=locale_str('translate'))
    @app_commands.describe(content=locale_str('translate_content'), target=locale_str('translate_target'))
    async def translate(self, ctx: commands.Context, content: str, target:str = 'zh-TW'):
        async with ctx.typing():
            '''i18n'''
            yinxi_translated = await ctx.interaction.translate('yin_xi')
            eb = await ctx.interaction.translate('embed_translate_translated')
            eb: dict = (load_translated(eb))[0]
            field_1: dict = (eb.get('field'))[0]
            translate_name = field_1.get('name')
            ''''''
            think, translated = await thread_pool(translate, content, target, ctx.interaction.locale.value)
            
            embed = create_basic_embed(功能=yinxi_translated, color=ctx.author.color)
            embed.add_field(name=translate_name, value=translated if translated else think, inline=False)
            embed.set_footer(text='Powered by qwen-3-32b')

            await ctx.send(embed=embed)




async def setup(bot):
    await bot.add_cog(Translator(bot))