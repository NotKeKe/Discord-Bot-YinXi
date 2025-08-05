import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import io

from core.functions import MONGO_URL, create_basic_embed, UnixNow, current_time, get_attachment, is_testing_guild
from core.classes import Cog_Extension, get_bot
from core.translator import locale_str
from cmds.ai_chat.chat.chat import Chat
from cmds.ai_chat.utils import model, model_autocomplete, to_user_message, to_assistant_message

logger = logging.getLogger(__name__)

# db = db_client['ai_channel_chat_history']

async def to_history(channel: discord.TextChannel, limit: int = 10):
    histories = []
    messages = [m async for m in channel.history(limit=limit)]
    messages.reverse()
    pre = str()

    bot = get_bot()
    
    for m in messages:
        if m.author == bot.user:
            if m.content == '嘗試重啟bot...': continue
            if pre == 'bot':
                histories[-1]['content'] += m.content + '\n'
            else:
                histories.extend(to_assistant_message(m.content + '\n'))
            pre = 'bot'
        else:
            if m.content.startswith('['): continue
            content = '`user_ID: {userID}; user_name: {userName}; at: {time}` said: {mcontent}\n '.format(userID=m.author.id, userName=m.author.global_name, mcontent=m.content, time=m.created_at.strftime('%Y-%m-%d %H:%M:%S')) if not channel.guild else '`user_name: {userName}; at: {time}` said: {mcontent}'.format(userName=m.author.global_name, mcontent=m.content, time=m.created_at.strftime('%Y-%m-%d %H:%M:%S'))
            if pre == 'user':
                histories[-1]["content"] = content + '\n'
            else:
                attachment = get_attachment(m)
                histories.extend(to_user_message(content + '\n', time=current_time(), attachments=attachment))
            pre = 'user'

    return histories[-6:]

class AIChannelTwo(Cog_Extension):
    async def cog_load(self):
        logger.info(f'已載入{__name__}')

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        ...

    async def on_msg_chat_human(self, msg: discord.Message):
        ...

    async def on_msg_ai_channel(self, msg: discord.Message):
        ...

    @commands.hybrid_command(name=locale_str('set_ai_channel'), description=locale_str('set_ai_channel'))
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(model=model_autocomplete)
    async def set_ai_channel(self, ctx: commands.Context, model: str = 'qwen-3-32b'):
        ...

    @commands.hybrid_command(name=locale_str('cancel_ai_channel'), description=locale_str('cancel_ai_channel'))
    @commands.has_permissions(administrator=True)
    async def cancel_ai_channel(self, ctx: commands.Context):
        ...

    @commands.hybrid_command(name=locale_str('change_ai_channel_model'), description=locale_str('change_ai_channel_model'))
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(model=model_autocomplete)
    async def change_ai_channel_model(self, ctx: commands.Context, model: str):
        ...

    @commands.hybrid_command(name=locale_str('show_ai_channel_model'), description=locale_str('show_ai_channel_model'))
    async def model_show(self, ctx: commands.Context):
        ...

    @commands.hybrid_command(name=locale_str('set_chat_human'), description=locale_str('set_chat_human'))
    @commands.has_permissions(administrator=True)
    async def set_chat_human(self, ctx: commands.Context):
        ...

    @commands.hybrid_command(name=locale_str('cancel_chat_human'), description=locale_str('cancel_chat_human'))
    @commands.has_permissions(administrator=True)
    async def cancel_chat_human(self, ctx: commands.Context):
        ...

    @commands.command()
    @is_testing_guild()
    async def force_online(self, ctx: commands.Context):
        ...