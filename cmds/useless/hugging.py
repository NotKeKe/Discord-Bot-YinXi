import discord
from discord import app_commands
from discord.ext import commands, tasks
import typing
import traceback

from core.functions import thread_pool
from core.translator import locale_str

from cmds.AIsTwo.base_chat import huggingFace_modules, base_huggingFace_chat
from cmds.AIsTwo.info import HistoryData, chat_autocomplete, get_history, create_result_embed

async def moduels_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    module_keys = [module_dict['module'] for module_dict in huggingFace_modules]
    if current:
        module_keys = [module for module in module_keys if current.lower() in module.lower()]
    
    module_keys.sort()

    # 限制最多回傳 25 個結果
    return [app_commands.Choice(name=module, value=module) for module in module_keys[:25]]

class HuggingFaceAI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(name=locale_str('chat_hugging'), description=locale_str('chat_hugging'))
    @app_commands.describe(輸入文字=locale_str('chat_hugging_prompt'), model=locale_str('chat_hugging_model'), 歷史紀錄=locale_str('chat_hugging_history'), temperature=locale_str('chat_hugging_temperature'), 想法顯示=locale_str('chat_hugging_show_thoughts'))
    @app_commands.autocomplete(歷史紀錄=chat_autocomplete, model=moduels_autocomplete)
    async def chat(self, ctx: commands.Context, * , 輸入文字: str, model:str = 'deepseek-ai/DeepSeek-R1', 歷史紀錄:str = None, temperature:float = None, 想法顯示:bool = False):
        async with ctx.typing():
            try:
                HistoryData.initdata()
                history = get_history(ctx, 歷史紀錄)

                think, result, *_ = await thread_pool(base_huggingFace_chat, 輸入文字, model, temperature, history)

                embed = create_result_embed(ctx, result, model)
                await ctx.send(embed=embed)

                if 想法顯示 and think:
                    await ctx.send(content=think, ephemeral=True)
            
                if result:
                    HistoryData.appendHistory(ctx.author.id, 輸入文字, result, 歷史紀錄)
            except:
                traceback.print_exc()
                await ctx.send(await ctx.interaction.translate('send_chat_hugging_fail'))

async def setup(bot):
    await bot.add_cog(HuggingFaceAI(bot))