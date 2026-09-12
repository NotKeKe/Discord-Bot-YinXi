from discord.ext import commands
from discord import (
    app_commands, 
    Interaction, 
    errors as dc_errors,
    Guild
)
from discord.app_commands import Choice
import asyncio
import orjson
import uuid
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, cast
from openai import AsyncOpenAI
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
import traceback
from motor.motor_asyncio import AsyncIOMotorCollection
from textwrap import dedent
import logging

from core.classes import Cog_Extension, get_bot
from core.functions import create_basic_embed, current_time, is_testing_guild, mongo_db_client, UnixToReadable, is_KeJC
from core.translator import load_translated, locale_str, get_translate

from cmds.ai_chat.utils.config import base_url_options

reminder_tasks = {}
bot = get_bot()
logger = logging.getLogger(__name__)

DB_KEY = 'keep'
DB = mongo_db_client[DB_KEY]

PROVIDER = 'zhipu'
MODEL = 'glm-4.5-flash'
OPENAI_CLIENT = AsyncOpenAI(api_key=base_url_options[PROVIDER]['api_key'], base_url=base_url_options[PROVIDER]['base_url'])

class _KeepUtils:
    @staticmethod
    async def call_ai(messages: list[dict[str, str]], tools: list[dict]) -> ChatCompletionMessageToolCall:
        response = await OPENAI_CLIENT.chat.completions.create(
            model=MODEL,
            messages=messages, # type: ignore
            tools=tools, # type: ignore
            tool_choice='required'
        )
        if not response.choices: raise ValueError('AI沒有回應')
        if not response.choices[0].message.tool_calls: raise ValueError('AI沒有調用工具')
        return response.choices[0].message.tool_calls[0]

    @staticmethod
    async def create(collection, inter, event, raw_time, freq_str=None, freq_int=None):
        invalid_format = await get_translate('send_keep_invalid_format', inter)
        time_passed = await get_translate('send_keep_time_passed', inter)
        too_far = await get_translate('send_keep_too_far', inter)

        try:
            keep_time = datetime.strptime(f'{raw_time}', '%Y-%m-%d %H:%M')
        except Exception:
            await inter.followup.send(invalid_format, ephemeral=True)
            return

        delay = (keep_time - datetime.now()).total_seconds()

        if delay <= 0:
            await inter.followup.send(time_passed.format(inter.user.mention))
            return

        if delay > 31557600000:
            await inter.followup.send(too_far)
            return

        if freq_str:
            if not isinstance(freq_int, int) or freq_int <= 0:
                await inter.followup.send(invalid_format, ephemeral=True)
                return
            if freq_str == 'yearly' and freq_int * 31557600 > 31557600000:
                await inter.followup.send(too_far)
                return
            try:
                _KeepUtils.next_send_at(keep_time, freq_str, freq_int)
            except OverflowError:
                await inter.followup.send(too_far)
                return

        dm_forbidden = await get_translate('send_keep_dm_forbidden', inter)

        if freq_str:
            dm_check = (await get_translate('send_keep_dm_check_freq', inter)).format(
                event=event,
                freq_int=freq_int,
                freq_label=await get_translate(f'keep_frequency_{freq_str}', inter),
                keep_time=keep_time.strftime('%Y-%m-%d %H:%M')
            )
        else:
            dm_check = (await get_translate('send_keep_dm_check', inter)).format(
                event=event,
                keep_time=keep_time.strftime('%Y-%m-%d %H:%M')
            )

        try:
            await inter.user.send(dm_check)
        except dc_errors.Forbidden:
            await inter.followup.send(dm_forbidden, ephemeral=True)
            return
        except Exception as e:
            logger.error(f'Unexpected error while checking DM: {e}', exc_info=True)

        u = str(uuid.uuid4())
        doc = {
            'createAt': datetime.now().timestamp(),
            'sendAt': keep_time.timestamp(),
            'channelID': inter.channel.id if inter.channel else -1,
            'event': event,
            'uuid': u
        }
        if freq_str:
            doc |= {'freq_str': freq_str, 'freq_int': freq_int}
        await collection.insert_one(doc)

        embed_key = 'embed_keep_frequency_created' if freq_str else 'embed_keep_created'
        embed_translated: dict = (load_translated(await get_translate(embed_key, inter)))[0]

        title = embed_translated.get('title')
        field_1 = (embed_translated.get('field'))[0] # type: ignore

        embed = create_basic_embed(title=title, description=f'**{event}**', color=inter.user.color, time=False)
        embed.set_author(name=inter.user.name, icon_url=inter.user.avatar.url if inter.user.avatar else None)
        embed.add_field(name=field_1.get('name'), value=field_1.get('value'), inline=True)

        footer = embed_translated.get('footer')
        if freq_str:
            freq_label = await get_translate(f'keep_frequency_{freq_str}', inter)
            embed.set_footer(text=str(footer).format(keep_time=keep_time, freq_label=freq_label, freq_int=freq_int))
        else:
            embed.set_footer(text=str(footer).format(keep_time=keep_time))

        await inter.followup.send(embed=embed)

        _KeepUtils.schedule(collection, inter.channel, inter.user, event, keep_time, u, freq_str, freq_int)

    @staticmethod
    def schedule(collection, channel, user, event, keep_time, u, freq_str=None, freq_int=None):
        if u in reminder_tasks and not reminder_tasks[u].done():
            return
        delay = (keep_time - datetime.now()).total_seconds()
        if delay <= 0: delay = 1
        if freq_str:
            task = bot.loop.create_task(keepFrequencyMessage(collection, channel, user, event, delay, u, freq_str, freq_int, keep_time)) # type: ignore
        else:
            task = bot.loop.create_task(keepMessage(collection, channel, user, event, delay, u))
        reminder_tasks[u] = task

    @staticmethod
    async def send_reminder(channel, user, event):
        lang_code = None
        if channel and channel.guild:
            lang_code = channel.guild.preferred_locale.value if channel.guild.preferred_locale else None

        bot = get_bot()
        try:
            await user.send((bot.tree.translator.get_translate('send_keep_remind', lang_code)).format(mention=user.mention, event=event)) # type: ignore
        except Exception as e:
            logger.error(f'Cannot send keep message with DM: {e}', exc_info=True)

    @staticmethod
    def next_send_at(current, freq_str, freq_int):
        if freq_str == 'minutely': return current + timedelta(minutes=freq_int)
        if freq_str == 'hourly': return current + timedelta(hours=freq_int)
        if freq_str == 'daily': return current + timedelta(days=freq_int)
        if freq_str == 'weekly': return current + timedelta(weeks=freq_int)
        if freq_str == 'monthly': return current + relativedelta(months=freq_int)
        if freq_str == 'yearly': return current + relativedelta(years=freq_int)
        raise ValueError(f'unknown freq_str: {freq_str}')

class RunKeep:
    def __init__(self, time: str, event: str, inter: Interaction):
        self.system_prompt = '''你是一個專門記錄使用者設定提醒事項的AI，你必須使用你的function calling能力，呼叫keep函數，來協助使用者完成這件事，使用者會說他希望你提醒他完成某件事，在 `event` 變數中 一字不漏、不能修改的 傳入這件事，確保你的格式沒有任何錯誤。time部分，如果使用者沒有特別指定準確的小時與分鐘，就使用當前時間。**現在的時間為: {}**'''.format(current_time())
        self.tool_descrip = [
            {
                "type": "function",
                "function": {
                    "name": "keep",
                    "description": "此工具用來完成使用者的設定提醒事項。使用者可以使用此工具來記錄他們想要提醒的事項，並指定提醒時間。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time": {
                                "type": "string",
                                "description": "格式為 `%Y-%m-%d %H:%M`，例如 `2023-10-05 14:30`，表示在2023年10月5日的下午2點30分提醒。不要使用markdown格式，使用24小時制，另外注意凌晨24點(或0點)，需要表示為00:00。"
                            },
                            "event": {
                                "type": "string",
                                "description": "使用者需要提醒事項的內容"
                            }
                        },
                        "required": ["time", "event"]
                    }
                }
            }
        ]
        self.prompt = f'我想要在 `{time}` 的時候讓你提醒我完成 `{event}`'
        self.model = MODEL
        self.client = OPENAI_CLIENT
        self.collection = DB[str(inter.user.id)]
        self.inter = inter

    async def chat(self) -> ChatCompletionMessageToolCall:
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': self.prompt}
        ]
        return await _KeepUtils.call_ai(messages, self.tool_descrip)

    async def run(self):
        try:
            tool_call = await self.chat()
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments
            args = orjson.loads(arguments) if not isinstance(arguments, dict) else arguments
            print(f'{tool_name}: {args}')
            await self.func(**args)
        except: 
            traceback.print_exc()

    async def func(self, time: str, event: str):
        await _KeepUtils.create(self.collection, self.inter, event, time)


class RunKeepFrequency:
    def __init__(self, time: str, event: str, inter: Interaction, freq_str: str, freq_int: int):
        self.system_prompt = '''你是一個專門解析使用者第一次提醒時間的AI，你必須使用你的function calling能力，呼叫keep_frequency_time函數，來協助使用者完成這件事。time部分，如果使用者沒有特別指定準確的小時與分鐘，就使用當前時間。**現在的時間為: {}**'''.format(current_time())
        self.tool_descrip = [
            {
                "type": "function",
                "function": {
                    "name": "keep_frequency_time",
                    "description": "此工具用來記錄使用者第一次提醒的時間。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time": {
                                "type": "string",
                                "description": "格式為 `%Y-%m-%d %H:%M`，例如 `2023-10-05 14:30`，表示在2023年10月5日的下午2點30分提醒。不要使用markdown格式，使用24小時制，另外注意凌晨24點(或0點)，需要表示為00:00。"
                            }
                        },
                        "required": ["time"]
                    }
                }
            }
        ]
        self.prompt = f'我想要設定一個每 {freq_int} {freq_str} 的週期性提醒，內容是 `{event}`，第一次提醒時間是 `{time}`'
        self.freq_str = freq_str
        self.freq_int = freq_int
        self.event = event
        self.collection = DB[str(inter.user.id)]
        self.inter = inter

    async def chat(self) -> ChatCompletionMessageToolCall:
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': self.prompt}
        ]
        return await _KeepUtils.call_ai(messages, self.tool_descrip)

    async def run(self):
        try:
            tool_call = await self.chat()
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments
            args = orjson.loads(arguments) if not isinstance(arguments, dict) else arguments
            print(f'{tool_name}: {args}')
            await self.func(args['time'], self.event)
        except:
            traceback.print_exc()

    async def func(self, time: str, event: str):
        await _KeepUtils.create(self.collection, self.inter, event, time, self.freq_str, self.freq_int)


async def keepMessage(collection: AsyncIOMotorCollection, channel, user, event: str, delay: float, uuid: str):
    await asyncio.sleep(delay)

    await _KeepUtils.send_reminder(channel, user, event)

    reminder_tasks.pop(uuid)

    await collection.find_one_and_delete({
        'uuid': uuid,
        'channelID': channel.id
    })

async def keepFrequencyMessage(collection: AsyncIOMotorCollection, channel, user, event: str, delay: float, uuid: str, freq_str: str, freq_int: int, send_at: datetime):
    current = send_at
    try:
        while True:
            await asyncio.sleep(max(delay, 0))

            await _KeepUtils.send_reminder(channel, user, event)

            try:
                nxt = _KeepUtils.next_send_at(current, freq_str, freq_int)
            except Exception as e:
                logger.error(f'Cannot compute next send time for keep task: {e}', exc_info=True)
                break
            now = datetime.now()
            while nxt <= now:
                nxt = _KeepUtils.next_send_at(nxt, freq_str, freq_int)
            delay = (nxt - now).total_seconds()
            current = nxt

            await collection.update_one(
                {'uuid': uuid, 'channelID': channel.id},
                {'$set': {'sendAt': nxt.timestamp()}}
            )
    finally:
        reminder_tasks.pop(uuid, None)

async def create_KeepTask():
    ''' A init task for on_ready
    This is a function for creating a keep task at bot ready. It will send a message to the user at the specified time.
    '''
    try:
        ls_collection = await DB.list_collection_names()

        count = 0
        for userID in ls_collection:
            collection = DB[userID]
            user = await bot.fetch_user(int(userID))

            async for e in collection.find():
                channelID = e['channelID']
                event = e['event']
                u = e['uuid']

                try:
                    channel = bot.get_channel(int(channelID)) or await bot.fetch_channel(int(channelID))
                except (dc_errors.NotFound, dc_errors.Forbidden): # 找不到
                    await collection.delete_one({
                        'uuid': u,
                        'channelID': channelID
                    })
                    continue
                except Exception as e:
                    logger.error(f'Unexpected error: {str(e)}', exc_info=True)
                    continue

                keep_time = datetime.fromtimestamp(e['sendAt'])
                freq_str = e.get('freq_str')
                freq_int = e.get('freq_int')
                if freq_str and (not isinstance(freq_int, int) or freq_int <= 0):
                    freq_str = None
                _KeepUtils.schedule(collection, channel, user, event, keep_time, u, freq_str, freq_int)
                count += 1

        print(f'已新增 {count} 個 keep 任務')
    except: traceback.print_exc()


async def keep_event_autocomplete(interaction: Interaction, current: str) -> List[Choice[str]]:
    userID = str(interaction.user.id)
    collection = DB[userID]

    _get_channel_name = lambda channelID: (
        channel := bot.get_channel(channelID),
        str(channel.name) if hasattr(channel, 'name') else "Private Channel"
    )
    get_channel_name = lambda channelID: _get_channel_name(channelID)[1]

    _get_guild_name = lambda channelID: (
        channel := bot.get_channel(channelID),
        channel.guild.name if hasattr(channel, 'guild') and channel.guild and hasattr(channel.guild, 'name') else "Private Channel"
    )
    get_guild_name = lambda channelID: _get_guild_name(channelID)[1]

    label_once = await get_translate('keep_autocomplete_once', interaction)
    label_freq = await get_translate('keep_autocomplete_freq', interaction)

    result = [
        (
            f"{item.get('event', '')} | {datetime.fromtimestamp(item.get('sendAt', 0))} | {get_channel_name(item.get('channelID', 0))} | {get_guild_name(item.get('channelID', 0))} | {label_freq if item.get('freq_str') else label_once}",
            orjson.dumps((item.get('uuid', ''), item.get('channelID', ''))).decode('utf-8')
        )
        async for item in collection.find()
    ]

    if current:
        result = [item for item in result if current.lower() in item[0].lower()]
    
    return [Choice(name=item[0], value=item[1]) for item in result[:25]]

class Keep(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        await create_KeepTask()

    # Create a Keep
    @app_commands.command(name=locale_str('keep'), description=locale_str('keep'))
    @app_commands.describe(time=locale_str('keep_time'), event=locale_str('keep_event'))
    async def keep(self, inter: Interaction, time: str, * , event: str):
        '''[keep time(會使用AI作分析) event: str'''
        await inter.response.defer(ephemeral=True, thinking=True)
        await RunKeep(time, event, inter).run()

    @app_commands.command(name=locale_str('keep_frequency'), description=locale_str('keep_frequency'))
    @app_commands.choices(freq_str=[
        Choice(name=locale_str('keep_frequency_minutely'), value='minutely'),
        Choice(name=locale_str('keep_frequency_hourly'), value='hourly'),
        Choice(name=locale_str('keep_frequency_daily'), value='daily'),
        Choice(name=locale_str('keep_frequency_weekly'), value='weekly'),
        Choice(name=locale_str('keep_frequency_monthly'), value='monthly'),
        Choice(name=locale_str('keep_frequency_yearly'), value='yearly'),
    ])
    @app_commands.describe(time=locale_str('keep_frequency_time'), freq_str=locale_str('keep_frequency_freq_str'), freq_int=locale_str('keep_frequency_freq_int'), event=locale_str('keep_frequency_event'))
    async def keep_frequency(self, inter: Interaction, time: str, freq_str: str, freq_int: int, *, event: str):
        await inter.response.defer(ephemeral=True, thinking=True)
        await RunKeepFrequency(time, event, inter, freq_str, freq_int).run()

    @app_commands.command(name=locale_str('del_keep'), description=locale_str('del_keep'))
    @app_commands.autocomplete(keep_event=keep_event_autocomplete)
    async def del_keep(self, inter: Interaction, keep_event: str):
        await inter.response.defer(ephemeral=True, thinking=True)

        collection = DB[str(inter.user.id)]

        try:
            keep_event = orjson.loads(keep_event)
        except:
            return await inter.followup.send(await get_translate('send_del_keep_please_use_slash_command', inter), ephemeral=True)
        
        uuid = keep_event[0]
        channelID = keep_event[1]

        doc = await collection.find_one_and_delete({
            'uuid': uuid,
            'channelID': channelID
        })

        task = reminder_tasks.pop(uuid, None)
        if task:
            task.cancel()

        await inter.followup.send( (await get_translate('send_del_keep_cancel_success', inter) ).format(
                event=doc.get('event', ''), 
                time=datetime.fromtimestamp(doc.get('sendAt', 0)).strftime('%Y-%m-%d %H:%M')
            ), 
            ephemeral=True
        )    

    @app_commands.command(name=locale_str('show_keep'), description=locale_str('show_keep'))
    async def show_keep(self, inter: Interaction):
        await inter.response.defer(ephemeral=True, thinking=True)

        collection = DB[str(inter.user.id)]

        '''i18n'''
        sendAt_text = await get_translate('send_show_keep_sendAt_text', inter)
        event_text = await get_translate('send_show_keep_event_text', inter)
        channel_text = await get_translate('send_show_keep_channel_text', inter)
        ''''''

        data = ['## Events:']
        index = 1

        async for e in collection.find().sort('sendAt', -1):
            sendAt = UnixToReadable(e.get('sendAt', 0))
            event = e.get('event', '')
            channel = self.bot.get_channel(e.get('channelID', 0))
            channelName = channel.name if hasattr(channel, 'name') else "Private Channel"
            guildName = channel.guild.name if hasattr(channel, 'guild') and channel.guild and hasattr(channel.guild, 'name') else "Private Channel"
            u = e.get('uuid')

            data.append(dedent(
                f'''
                ### {index}. {event}
                > **{sendAt_text}:** {sendAt}
                > **{event_text}:** {event}
                > **{channel_text}:** {channelName} ({guildName})
                > **event uuid:** {u}
                ''').strip()
            )
            index += 1

            if index > 10: break
        
        eb = create_basic_embed(description='\n'.join(data))
        await inter.followup.send(embed=eb, ephemeral=True)

    @commands.command()
    @is_testing_guild()
    async def check_keepdata(self, ctx: commands.Context):
        if not is_KeJC(ctx.author.id): return
        await ctx.send(str(reminder_tasks))

async def setup(bot):
    await bot.add_cog(Keep(bot))