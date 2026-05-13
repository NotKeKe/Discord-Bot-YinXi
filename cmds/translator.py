from discord.ext import commands
from discord import app_commands

from core.classes import Cog_Extension
from core.functions import create_basic_embed, thread_pool
from core.translator import load_translated, locale_str, get_translate
# from cmds.AIsTwo.others.func import translate
from cmds.ai_chat.chat.translate import translate

class Translator(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name=locale_str('translate'), description=locale_str('translate'))
    @app_commands.describe(content=locale_str('translate_content'), target=locale_str('translate_target'))
    async def translate(self, ctx: commands.Context, content: str, target:str = 'zh-TW'):
        async with ctx.typing():
            '''i18n'''
            yinxi_translated = await get_translate('yin_xi', ctx)
            ''''''

            user_lang_code = None
            if ctx.interaction:
                user_lang_code = ctx.interaction.locale.value
            else:
                if ctx.guild:
                    user_lang_code = ctx.guild.preferred_locale.value

            translated = await translate(
                prompt=content,
                to_lang=target, 
                ctx=ctx,
                **({'user_lang_code': user_lang_code} if user_lang_code else {})
                )
            
            embed = create_basic_embed(description=translated, 功能=yinxi_translated, color=ctx.author.color)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            embed.set_footer(text='Powered by qwen3-1.7b')

            await ctx.send(embed=embed)




async def setup(bot):
    await bot.add_cog(Translator(bot))