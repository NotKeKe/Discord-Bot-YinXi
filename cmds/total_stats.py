'''
這是用來記錄各種數據的 Cog，最終會將資料存在 MongoDB
'''

import discord
from discord import app_commands, Interaction
from discord.ext import commands
import logging
from datetime import datetime

from core.classes import Cog_Extension
from core.functions import mongo_db_client, is_KeJC, create_basic_embed
from core.translator import locale_str, load_translated

logger = logging.getLogger(__name__)

db_key = 'bot_collect_stats'
db = mongo_db_client[db_key]
collection = db['stats']

class BotStats(Cog_Extension):
    async def cog_load(self):
        print(f'已載入「{__name__}」')

        if not (await collection.find_one({'type': 'TOP_STATS'})):
            await collection.insert_one(
                {
                    'type': 'TOP_STATS',
                    'start_time': datetime.now().timestamp()
                }
            )

    @commands.Cog.listener()
    async def on_ready(self):
        await collection.find_one_and_update(
            {'type': 'on_ready'},
            {'$inc': {'bot_online_times': 1}},
            upsert=True
        )

    # command
    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        await collection.find_one_and_update(
            {'type': 'on_command'},
            {
                '$inc': {
                    'total_times': 1,
                    f'commands.{ctx.command.name}': 1,
                }
            },
            upsert=True
        )

        await collection.find_one_and_update(
            {'type': 'on_command_user_times'},
            {
                '$inc': {
                    str(ctx.author.id): 1
                }
            },
            upsert=True
        )

        if not ctx.guild: return 
        await collection.find_one_and_update(
            {'type': 'on_command_guild_times'},
            {
                '$inc': {
                    str(ctx.guild.id): 1
                }
            },
            upsert=True
        )

    async def on_any_command_completion(self, ctx: commands.Context):
        await collection.find_one_and_update(
            {'type': 'on_command_completion'},
            {
                '$inc': {
                    'total_times': 1,
                    f'commands.{ctx.command.name}': 1
                }
            },
            upsert=True
        )

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        await self.on_any_command_completion(ctx)

    @commands.Cog.listener()
    async def on_app_command_completion(self, inter: Interaction, command: app_commands.Command):
        await self.on_any_command_completion((await self.bot.get_context(inter)))

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if not ctx.command: return
        await collection.find_one_and_update(
            {'type': 'on_command_error'},
            {
                '$inc': {
                    'total_times': 1,
                    f'commands.{ctx.command.name}': 1
                }
            },
            upsert=True
        )

    @app_commands.command(name=locale_str('bot_stats'), description=locale_str('bot_stats'))
    async def stats(self, inter: Interaction):
        await inter.response.defer(thinking=True)

        start_time = (await collection.find_one({'type': 'TOP_STATS'})) or {}
        on_ready = (await collection.find_one({'type': 'on_ready'})) or {}
        on_command = (await collection.find_one({'type': 'on_command'})) or {}
        on_command_completion = (await collection.find_one({'type': 'on_command_completion'})) or {}
        on_command_error = (await collection.find_one({'type': 'on_command_error'})) or {}
        
        '''i18n'''
        eb_obj = load_translated(await inter.translate('embed_bot_stats'))[0]
        author = eb_obj.get('author')
        fields = eb_obj.get('fields')
        start_time_text = fields[0].get('name')
        start_count_text = fields[1].get('name')
        command_call_text = fields[2].get('name')
        command_complete_text = fields[3].get('name')
        command_error_text = fields[4].get('name')
        footer = eb_obj.get('footer')
        ''''''

        eb = create_basic_embed(功能=author, time=False)
        eb.add_field(name=start_count_text, value=on_ready.get('bot_online_times'))
        eb.add_field(name=command_call_text, value=on_command.get('total_times'))
        eb.add_field(name=command_complete_text, value=on_command_completion.get('total_times'))
        eb.add_field(name=command_error_text, value=on_command_error.get('total_times'))

        eb.set_footer(text=footer)
        eb.timestamp = datetime.fromtimestamp(start_time.get('start_time'))

        await inter.followup.send(embed=eb)


async def setup(bot):
    await bot.add_cog(BotStats(bot))