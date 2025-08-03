import discord
from discord import app_commands
from discord.ext import commands
import logging

from core.functions import testing_guildID, is_testing_guild
from core.classes import Cog_Extension
from cmds.ai_chat.chat.chat import Chat
from cmds.ai_chat.utils import model

# dev
from cmds.ai_chat.utils.config import *

logger = logging.getLogger(__name__)

class AIChat(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        await model.fetch_models()

    @commands.hybrid_command(name='agent')
    @app_commands.guilds(discord.Object(testing_guildID))
    async def agent(self, ctx: commands.Context, prompt: str):
        try:
            async with ctx.typing():
                client = Chat(
                    ctx=ctx,
                    model='qwen-3-32b'
                )

                think, result = await client.chat(prompt)
                await ctx.send(result)
        except:
            logger.error('Erorr accured at agent command', exc_info=True)



async def setup(bot):
    await bot.add_cog(AIChat(bot))