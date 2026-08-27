import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import asyncio
import random
import logging

from core.classes import Cog_Extension, get_bot
from core.translator import locale_str, load_translated, get_translate
from core.mongodb import MongoDB_DB

logger = logging.getLogger(__name__)

DB = MongoDB_DB.giveaway
COLL = DB['data']

class Utils:
    @staticmethod
    async def button_callback(interaction: discord.Interaction):
        if not interaction.message: return

        data = await COLL.find_one({
            'channel_id': interaction.message.channel.id,
            'message_id': interaction.message.id
        })
        if not data:
            await interaction.response.send_message(await get_translate('send_giveaway_not_exist', interaction), ephemeral=True); return

        # 避免使用者在結束後的計算過程中點擊按鈕
        if datetime.fromisoformat(data['end_time']) < datetime.now(timezone.utc):
            await interaction.response.send_message(await get_translate('send_giveaway_not_exist', interaction), ephemeral=True); return

        # 獲取Embed訊息
        embed = interaction.message.embeds[0]
        # 取得當前參加giveaway人數
        count = int(embed.fields[1].value)     

        if interaction.user.id in data.get('participant_ids', []):
            # 更改 data
            await COLL.update_one(
                {'channel_id': interaction.message.channel.id, 'message_id': interaction.message.id}, 
                {'$pull': {'participant_ids': interaction.user.id}}
            )

            # 更改embed
            count -= 1

            #傳送取消訊息給user
            await interaction.response.send_message(
                content=await get_translate('send_giveaway_left', interaction), 
                ephemeral=True
            )
        else:
            # 更改 data
            await COLL.update_one(
                {'channel_id': interaction.message.channel.id, 'message_id': interaction.message.id}, 
                {'$addToSet': {'participant_ids': interaction.user.id}}
            )

            # 更改embed
            count += 1

            # 傳送取消訊息給user
            await interaction.response.send_message(
                content=await get_translate('send_giveaway_joined', interaction), 
                ephemeral=True
            )

        # 更新Embed
        '''i18n'''
        eb_template = await get_translate('embed_giveaway_start', interaction)
        eb_data = load_translated(eb_template)[0]
        participants_field_name = eb_data.get('fields')[1].get('name')
        ''''''
        embed.set_field_at(1, name=participants_field_name, value=str(count), inline=False)
        await interaction.message.edit(embed=embed)

    @staticmethod
    async def write_giveaway_info(
        channel_id: int,
        message_id: int,
        hosted_user_id: int,
        prize: str,
        end_time: datetime,
        winners_total: int
    ):
        await COLL.insert_one({
            'channel_id': channel_id,
            'message_id': message_id,
            'hosted_user_id': hosted_user_id,
            'prize': prize,
            'end_time': end_time.astimezone(timezone(timedelta(hours=8))).isoformat(),
            'winners_total': winners_total, # 中獎人數
            'participant_ids': []
        })
        

    @staticmethod
    async def wait_task(
        delay: int | float, 
        channel_id: int,
        message_id: int
    ):
        await asyncio.sleep(delay)
        _bot = get_bot()
        assert _bot.tree.translator

        try:
            channel = _bot.get_channel(channel_id) or await _bot.fetch_channel(channel_id)
            if channel is None:
                raise Exception("Channel not found")
        except Exception:
            logger.info(f'Channel `{channel_id}` not found')
            return await COLL.delete_one({
                'channel_id': channel_id,
                'message_id': message_id
            })

        try:
            message = await channel.fetch_message(message_id)
        except Exception:
            logger.info(f'Message `{message_id}` not found | Channel:`{channel_id}`')
            return await COLL.delete_one({
                'channel_id': channel_id,
                'message_id': message_id
            })

        try:
            # 取得 data
            data = await COLL.find_one({
                'channel_id': channel_id,
                'message_id': message_id
            })

            if not data: return

            try:
                host_user = await _bot.fetch_user(data['hosted_user_id'])
            except Exception:
                host_user = message.author

            # 隨機選取中獎者
            winner_ids = random.sample(data['participant_ids'], min(data['winners_total'], len(data['participant_ids'])))

            # 將 winners 更新至 mongodb
            await COLL.update_one(
                {'channel_id': channel_id, 'message_id': message_id},
                {'$set': {
                    'winners': winner_ids
                }}
            )

            # 將 winners 轉為 user 物件
            winners = [
                await _bot.fetch_user(user_id) 
                for user_id in winner_ids
            ]

            # 檢查是否在 guild (for preferred_locale, i18n)
            try:
                if not hasattr(channel, 'guild') or channel.guild is None:
                    raise Exception("channel.guild not found")

                guild= channel.guild
                lang_code = guild.preferred_locale.value
            except Exception:
                lang_code = None

            '''i18n'''
            eb_template = _bot.tree.translator.get_translate("embed_giveaway_end", lang_code)
            eb_data = load_translated(eb_template)[0]
            winner_field_name = eb_data.get('fields')[0].get('name')
            footer_text = eb_data.get('footer')
            ''''''
            winner_field_value = ', '.join([user.mention for user in winners]) if winners else _bot.tree.translator.get_translate("send_giveaway_no_winner", lang_code)

            # send
            embed=discord.Embed(title=data['prize'], color=host_user.color, timestamp=datetime.now())
            embed.add_field(name=winner_field_name, value=winner_field_value, inline=False)
            embed.set_footer(text=footer_text.format(winners_total=data['winners_total'], count=len(data['participant_ids'])))
            await message.edit(
                content=(
                    _bot.tree.translator.get_translate('send_giveaway_ended_message', lang_code).format(
                        mention=host_user.mention, 
                        winner=winner_field_value
                    )
                ), 
                embed=embed, 
                view=None
            )

            await COLL.delete_one({
                'channel_id': channel_id,
                'message_id': message_id
            })
        except Exception:
            pass



class Giveaway2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not hasattr(self, '_resumed_message_ids'):
            self._resumed_message_ids = set()

        try:
            translator = self.bot.tree.translator
            assert translator

            async for doc in COLL.find({}):
                message_id = doc['message_id']
                if message_id in self._resumed_message_ids:
                    continue
                self._resumed_message_ids.add(message_id)

                try:
                    channel = self.bot.get_channel(doc['channel_id'])
                    if channel is None:
                        channel = await self.bot.fetch_channel(doc['channel_id'])
                    message = await channel.fetch_message(message_id)
                except Exception:
                    logger.error(f'Giveaway message `{message_id}` not found, removing record', exc_info=True)
                    await COLL.delete_one({'channel_id': doc['channel_id'], 'message_id': message_id})
                    continue

                try:
                    end_time = datetime.fromisoformat(doc['end_time'])
                    delay = (end_time - datetime.now(timezone.utc)).total_seconds()
                except Exception:
                    logger.error(f'Failed to parse end_time for giveaway message {message_id}', exc_info=True)
                    continue

                try:
                    lang_code = message.guild.preferred_locale.value if message.guild and message.guild.preferred_locale else None
                except Exception:
                    lang_code = None

                '''i18n'''
                eb_template = translator.get_translate('embed_giveaway_start', lang_code)
                eb_data = load_translated(eb_template)[0]
                author_text = eb_data.get('author')
                fields_data = eb_data.get('fields', [])
                winners_field_name = fields_data[0].get('name')
                participants_field_name = fields_data[1].get('name')
                note_field_name = fields_data[2].get('name')
                note_field_value = fields_data[2].get('value')
                footer_text = eb_data.get('footer')
                ''''''

                embed = discord.Embed(
                    title=f'**{doc["prize"]}**',
                    color=message.author.color,
                    timestamp=end_time
                )
                embed.set_author(name=author_text)
                embed.add_field(name=winners_field_name, value=doc['winners_total'], inline=False)
                embed.add_field(name=participants_field_name, value=str(len(doc['participant_ids'])), inline=False)
                embed.add_field(name=note_field_name, value=note_field_value, inline=False)
                embed.set_footer(text=footer_text)

                button = discord.ui.Button(label='🎉', custom_id=f'giveaway-{message_id}')
                button.callback = Utils.button_callback  # type: ignore

                view = discord.ui.View(timeout=None)
                view.add_item(button)

                try:
                    await message.edit(embed=embed, view=view)
                except Exception:
                    logger.error(f'Failed to edit giveaway message {message_id}', exc_info=True)
                    continue

                self.bot.loop.create_task(
                    Utils.wait_task(max(delay, 0), doc['channel_id'], message_id)
                )
        except Exception:
            logger.error('Giveaway on_ready recovery failed', exc_info=True)

    @commands.hybrid_command(name=locale_str('giveaway'), description=locale_str('giveaway'))
    @app_commands.describe(
        winners=locale_str('giveaway_winners_total'), 
        prize=locale_str('giveaway_prize'), 
        date=locale_str('giveaway_date'), 
        time=locale_str('giveaway_time')
    )
    async def giveaway(self, ctx: commands.Context, winners: int, prize: str, date: str, time: str):
        try:
            end_time_dt = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        except Exception:
            return await ctx.send(await get_translate('send_giveaway_invalid_format', ctx), ephemeral=True)

        try:
            now = datetime.now()
            delay = (end_time_dt - now).total_seconds()

            if delay <= 0: # 過去的時間
                await ctx.send((await get_translate('send_giveaway_time_passed', ctx)).format(mention=ctx.author.mention), ephemeral=True)
                return
            if delay > 31557600000:
                await ctx.send(await get_translate('send_giveaway_too_far', ctx))
                return
            
            '''i18n'''
            eb_template = await get_translate('embed_giveaway_start', ctx)
            eb_data = load_translated(eb_template)[0]
            
            author_text = eb_data.get('author')
            fields_data = eb_data.get('fields', [])
            winners_field_name = fields_data[0].get('name')
            participants_field_name = fields_data[1].get('name')
            participants_field_value = fields_data[1].get('value')
            note_field_name = fields_data[2].get('name')
            note_field_value = fields_data[2].get('value')
            footer_text = eb_data.get('footer')
            ''''''

            # Embed
            embed=discord.Embed(title=f'**{prize}**', color=ctx.author.color, timestamp=end_time_dt)
            embed.set_author(name=author_text, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            embed.add_field(name=winners_field_name, value=winners, inline=False)
            embed.add_field(name=participants_field_name, value=participants_field_value, inline=False)
            embed.add_field(name=note_field_name, value=note_field_value, inline=False)
            embed.set_footer(text=footer_text)

            # Button
            button = discord.ui.Button(label="🎉")
            button.callback = Utils.button_callback # type: ignore
            
            # View
            view = discord.ui.View(timeout=None)
            view.add_item(button)

            message = await ctx.send(embed=embed, view=view)

            # 寫入抽獎資訊
            await Utils.write_giveaway_info(
                channel_id=ctx.channel.id,
                message_id=message.id,
                hosted_user_id=ctx.author.id,
                prize=prize,
                end_time=end_time_dt,
                winners_total=winners
            )
        except Exception as e:
            pass # todo