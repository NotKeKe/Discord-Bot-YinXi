import discord
from discord.ext import commands
from discord import app_commands
from deep_translator import GoogleTranslator, single_detection
import traceback
import typing

from core.classes import Cog_Extension
from core.functions import create_basic_embed

languages:dict = GoogleTranslator().get_supported_languages(as_dict=True)

async def translate_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    if not current:
        return [app_commands.Choice(name=lang.title(), value=code) for lang, code in list(languages.items())[:25]]

    return [app_commands.Choice(name=lang.title(), value=code) for lang, code in languages.items() if current.lower() in lang.title().lower()]


class Translator(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name='翻譯', description='Translate some text')
    @app_commands.describe(content='輸入你要翻譯的文字 Enter the text you wanna translate', 
                            source='選擇原始語言（你要翻譯的文字是什麼語言） Select the language of the text you want to translate',  
                            target='選擇目標語言（你希望翻譯成哪種語言） Select the language you want to translate into'  
                            )
    @app_commands.autocomplete(source=translate_autocomplete, target=translate_autocomplete)
    async def translate(self, ctx, content: str, source:str = None, target:str = None):
        if target is None:
            target = 'zh-TW'
        if source is None:
            source = 'auto'

        translator = GoogleTranslator(source=source, target=target)
        translated_text = translator.translate(content)
        
        embed = create_basic_embed(title=f"Your content: {content} (Lang: {source})", description=f'Translated to {target}: {translated_text}', 功能='翻譯', color=ctx.author.color)
        embed.set_footer(text='Python Module "deep-translator"')

        await ctx.send(embed=embed)




async def setup(bot):
    await bot.add_cog(Translator(bot))