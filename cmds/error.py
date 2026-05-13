import discord
from discord.ext import commands
from core.classes import Cog_Extension
from core.functions import KeJCID
from core.translator import get_translate
import traceback, logging

logging.getLogger(__name__)

class ErrorHandler(Cog_Extension):
    @commands.command(hidden=True)
    async def errorresponse(self, ctx: commands.Context, 檔案名稱, 指令名稱, exception=None, user_send = False, ephemeral=False):
        user = await self.bot.fetch_user(int(KeJCID)) if KeJCID else None

        if traceback.format_exc().strip() not in ('NoneType: None', 'None'):
            error = traceback.format_exc()
        else: error = exception

        string = f'有個在「{檔案名稱} {指令名稱}」的錯誤: 「{error}」，{ctx.author.id} used `{ctx.args}` and `{ctx.kwargs}`'
        logging.error(string, exc_info=True)

        await ctx.send(content=await get_translate('send_error_occurred', ctx), ephemeral=ephemeral)

        if user and user_send:
            await user.send(string)

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))