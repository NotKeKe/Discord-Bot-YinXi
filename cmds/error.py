import discord
from discord.ext import commands
from dotenv import load_dotenv
from core.classes import Cog_Extension
from core.translator import locale_str
import os
import traceback, logging

# get env
load_dotenv()
my_id = int(os.getenv('KeJC_ID'))

logging.getLogger(__name__)

class ErrorHandler(Cog_Extension):
    @commands.command(hidden=True)
    async def errorresponse(self, ctx:commands.Context, 檔案名稱, 指令名稱, exception=None, user_send = False, ephemeral=False):
        user = await self.bot.fetch_user(my_id)
        if traceback.format_exc() != 'NoneType: None\n':
            error = traceback.format_exc()
        else: error = exception
        string = f'有個在「{檔案名稱} {指令名稱}」的錯誤: 「{error}」'
        logging.error(string, exc_info=True)
        await ctx.send(content=await ctx.interaction.translate('send_error_occurred'), ephemeral=ephemeral)
        if user_send:
            await user.send(string)

async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
        
if __name__ == '__main__':
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix='!', intents=intents)
    ErrorHandler(bot).response('error.py', 'test', 'test')