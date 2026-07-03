from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timezone

from core.functions import settings
from core.mongodb import MongoDB_DB
from core.translator import locale_str, get_translate

logger = logging.getLogger(__name__)

CHANNEL_ID = None
try:    
    CHANNEL_ID = settings.get('suggest_report_channel') # type: ignore
except Exception:
    pass

if CHANNEL_ID is None:
    logger.warning('`suggest_report_channel` is not set in settings.json, suggest report will not work.')

class SuggestReport(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.DB = MongoDB_DB.suggest_report
        self.CHANNEL = None

        self.SUGGEST_COLL = self.DB.suggest
        self.REPORT_COLL = self.DB.report

    async def cog_load(self):
        print(f'已載入「{__name__}」')

        if CHANNEL_ID is not None and self.CHANNEL is None:
            self.CHANNEL = await self.bot.fetch_channel(CHANNEL_ID)

    @commands.hybrid_command(name=locale_str('suggest'), description=locale_str('suggest'))
    @app_commands.describe(text=locale_str('suggest_text'))
    async def suggest(self, ctx: commands.Context, * , text: str):
        await self.SUGGEST_COLL.insert_one({
            'user_global_name': ctx.author.global_name,
            'user_id': ctx.author.id,
            'text': text,
            'create_time': datetime.now().astimezone(timezone.utc).isoformat()
        })

        try:
            if self.CHANNEL is not None:
                await self.CHANNEL.send(f'💡 `{ctx.author.global_name} ({ctx.author.id})` 建議: \n```\n{text}\n```') # type: ignore
            await ctx.send((await get_translate('send_suggest_succeeded', ctx)).format(suggestion=text), ephemeral=True)
        except Exception:
            logger.error("Suggest cannot send to channel.", exc_info=True)
            await ctx.send(await get_translate('send_suggest_failed', ctx))


    @commands.hybrid_command(name=locale_str('report'), description=locale_str('report'), aliases=['error'])
    @app_commands.describe(text=locale_str('report_text'))
    async def report(self, ctx: commands.Context, * , text: str):
        await self.REPORT_COLL.insert_one({
            'user_global_name': ctx.author.global_name,
            'user_id': ctx.author.id,
            'text': text,
            'create_time': datetime.now().astimezone(timezone.utc).isoformat()
        })

        try:
            if self.CHANNEL is not None:
                await self.CHANNEL.send(f'🐛 `{ctx.author.global_name} ({ctx.author.id})` 回報了錯誤: \n```\n{text}\n```') # type: ignore
            await ctx.send((await get_translate('send_report_succeeded', ctx)).format(error=text), ephemeral=True)
        except Exception:
            logger.error("Error report cannot send to channel.", exc_info=True)
            await ctx.send(await get_translate('send_report_failed', ctx))


async def setup(bot: commands.Bot):
    await bot.add_cog(SuggestReport(bot))