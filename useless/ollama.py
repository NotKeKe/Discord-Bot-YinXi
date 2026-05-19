import discord
from discord import app_commands
from discord.ext import commands
import traceback
import typing

from core.classes import Cog_Extension
from core.functions import thread_pool, KeJCID
from cmds.AIs.ollama import chat_ollama, available_ollama_modules
from cmds.AIs.info import chat_autocomplete, HistoryData, get_history, create_result_embed

async def moduels_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    moduels = available_ollama_modules
    if current:
        moduels = [module for module in moduels if current.lower() in module.lower()]

    # 限制最多回傳 25 個結果
    return [app_commands.Choice(name=module, value=module) for module in moduels[:25]]

class Ollama(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name='chat_ollama')
    @app_commands.describe(model='預設為qwen2.5', 歷史紀錄='如果你不選的話 他就會自己創建一個新的歷史紀錄', 
                           temperature='預設為0.9', 想法顯示='僅限支援此功能的model(如deepseek)')
    @app_commands.autocomplete(model=moduels_autocomplete, 歷史紀錄=chat_autocomplete)
    async def chat(self, ctx: commands.Context, * , 輸入文字: str, model:str = 'qwen2.5:0.5b', 歷史紀錄:str = None, temperature:float = None, 想法顯示:bool = False):
        if str(ctx.author.id) != KeJCID: await ctx.send('此功能尚未開放', ephemeral=True); return
        async with ctx.typing():
            try:
                HistoryData.initdata()
                history = get_history(ctx, 歷史紀錄)
                think, result, *_ = await thread_pool(chat_ollama, 輸入文字, model, temperature, history)
                embed = create_result_embed(ctx, result, model)
                await ctx.send(embed=embed)

                if 想法顯示 and think:
                    await ctx.send(content=think, ephemeral=True)
            
                if result:
                    HistoryData.appendHistory(ctx.author.id, 輸入文字, result, 歷史紀錄)
            except:
                traceback.print_exc()
                await ctx.send('目前無法生成，請稍後再試')


async def setup(bot):
    await bot.add_cog(Ollama(bot))