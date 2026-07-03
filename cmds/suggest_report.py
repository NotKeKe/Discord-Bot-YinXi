import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timezone
import uuid
from enum import Enum

from core.functions import settings, create_basic_embed
from core.mongodb import MongoDB_DB
from core.translator import locale_str, get_translate, load_translated

logger = logging.getLogger(__name__)


CHANNEL_ID = None
try:    
    CHANNEL_ID = settings.get('suggest_report_channel') # type: ignore
except Exception:
    pass

if CHANNEL_ID is None:
    logger.warning('`suggest_report_channel` is not set in settings.json, suggest report will not work.')


class ReportStatusType(Enum):
    PENDING = "pending" # 已接收，但開發者未看到
    CONFIRMED = "confirmed" # 已接收，開發者已看到
    IN_PROGRESS = "in_progress" # 修復中
    RESOLVED = "resolved" # 已修復，等待部署至正式環境
    CLOSED = "closed" # 已部署


class SuggestReport(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.DB = MongoDB_DB.suggest_report
        self.CHANNEL = None

        self.SUGGEST_COLL = self.DB.suggest
        self.REPORT_COLL = self.DB.report

    async def cog_load(self):
        print(f'已載入「{__name__}」')


    @commands.Cog.listener()
    async def on_ready(self):
        if CHANNEL_ID is not None and self.CHANNEL is None:
            self.CHANNEL = await self.bot.fetch_channel(CHANNEL_ID)

    @commands.hybrid_command(name=locale_str('suggest'), description=locale_str('suggest'))
    @app_commands.describe(text=locale_str('suggest_text'))
    async def suggest(self, ctx: commands.Context, *, text: str):
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
            await ctx.send(await get_translate('send_suggest_failed', ctx), ephemeral=True)
            

    @commands.hybrid_command(name=locale_str('report'), description=locale_str('report'), aliases=['error'])
    @app_commands.describe(text=locale_str('report_text'))
    async def report(self, ctx: commands.Context, *, text: str):
        _uuid = uuid.uuid4().hex
        await self.REPORT_COLL.insert_one({
            "uuid": _uuid,
            'user_global_name': ctx.author.global_name,
            'user_id': ctx.author.id,
            'text': text,
            'create_time': datetime.now().astimezone(timezone.utc).isoformat(),

            'status': ReportStatusType.PENDING.value,
            'reason': "PENDING",
            "closed_time": ""
        })

        """i18n"""
        report_eb_suc_text = await get_translate('embed_report_succeeded', ctx)
        report_eb_fail_text = await get_translate('embed_report_failed', ctx)

        report_eb_suc_d = load_translated(report_eb_suc_text)
        report_eb_fail_d = load_translated(report_eb_fail_text)

        title = report_eb_suc_d[0].get('title')

        suc_fields = report_eb_suc_d[0].get('field')
        fail_fields = report_eb_fail_d[0].get('field')

        suc_field_1 = suc_fields[0] # 回報內容
        suc_field_2 = suc_fields[1] # 系統訊息
        suc_field_3 = suc_fields[2] # UUID

        fail_field_1 = fail_fields[0] # 回報內容
        fail_field_2 = fail_fields[1] # 系統訊息
        fail_field_3 = fail_fields[2] # UUID
        """"""
        
        eb = create_basic_embed(
            title=title,
        )

        try:
            # send to own channel
            if self.CHANNEL is not None:
                await self.CHANNEL.send(f'🐛 `{ctx.author.global_name} ({ctx.author.id})` 回報了錯誤: \n```\n{text}\n```') # type: ignore

        
            eb.color = discord.Color.green()
            eb.add_field(name=suc_field_1.get('name'), value=text)
            eb.add_field(name=suc_field_2.get('name'), value=suc_field_2.get('value'))
            eb.add_field(name=suc_field_3.get('name'), value=suc_field_3.get('value'))
        except Exception:
            logger.error("Error report cannot send to channel.", exc_info=True)
            
            eb.color = discord.Color.orange()
            eb.add_field(name=fail_field_1.get('name'), value=text)
            eb.add_field(name=fail_field_2.get('name'), value=fail_field_2.get('value'))
            eb.add_field(name=fail_field_3.get('name'), value=fail_field_3.get('value'))

        # send to user channel
        await ctx.send(embed=eb, ephemeral=True)


    @commands.hybrid_command(name=locale_str('report_trace'), description=locale_str('report_trace'))
    async def report_trace(self, ctx: commands.Context, report_uuid: str):
        # check report uuid in DB
        data = await self.REPORT_COLL.find_one({'uuid': report_uuid})
        if not data:
            await ctx.send(await get_translate('send_report_trace_not_exist', ctx), ephemeral=True)
            return

        # send report trace
        """i18n"""
        trace_eb_text = await get_translate('embed_report_trace', ctx)
        trace_eb_d = load_translated(trace_eb_text)[0]

        title = trace_eb_d.get('title')
        fileds = trace_eb_d.get('field')

        field_1 = fileds[0] # 回報內容
        field_2 = fileds[1] # UUID
        field_3 = fileds[2] # 狀態
        """"""

        eb = create_basic_embed(
            title=title
        )

        eb.add_field(name=field_1.get('name'), value=data.get('text'))
        eb.add_field(name=field_2.get('name'), value=data.get('uuid'))
        eb.add_field(name=field_3.get('name'), value=f"{data.get('status').upper()}: `{data.get('reason')}`")

        await ctx.send(embed=eb, ephemeral=True)

    @commands.hybrid_command()
    @commands.is_owner()
    async def set_report_status(self, ctx: commands.Context, report_uuid: str, status: ReportStatusType, reason: str = ""):
        data = await self.REPORT_COLL.find_one({'uuid': report_uuid})
        if not data:
            await ctx.send(f"Report `{report_uuid}` not found.", ephemeral=True)
            return

        update_data = {
            'status': status.value,
            'reason': reason
        }
        if status == ReportStatusType.CLOSED:
            update_data['closed_time'] = datetime.now().astimezone(timezone.utc).isoformat()
        else:
            update_data['closed_time'] = ""

        await self.REPORT_COLL.update_one({'uuid': report_uuid}, {'$set': update_data})
        await ctx.send(f"Updated report `{report_uuid}` to `{status.value}`.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SuggestReport(bot))