from discord.ext import commands
from discord import (
    app_commands, 
    Interaction, 
    errors as dc_errors
)
from discord.app_commands import Choice
import asyncio
import orjson
import uuid
from datetime import datetime
from typing import List
from openai import AsyncOpenAI
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
import traceback
from motor.motor_asyncio import AsyncIOMotorCollection
from textwrap import dedent
import logging

from core.classes import Cog_Extension, get_bot
from core.functions import create_basic_embed, current_time, is_testing_guild, mongo_db_client, UnixToReadable
from core.translator import load_translated, locale_str

from cmds.ai_chat.utils.config import base_url_options

reminder_tasks = {}
bot = get_bot()
logger = logging.getLogger(__name__)

DB_KEY = 'keep'
DB = mongo_db_client[DB_KEY]

PROVIDER = 'cerebras'
MODEL = 'qwen-3-32b'
OPENAI_CLIENT = AsyncOpenAI(api_key=base_url_options[PROVIDER]['api_key'], base_url=base_url_options[PROVIDER]['base_url'])

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
        response = await self.client.chat.completions.create(
            model=self.model, 
            messages=messages,
            tools=self.tool_descrip,
            tool_choice='required'
        )
        if not response.choices: raise ValueError('AI沒有回應')
        if not response.choices[0].message.tool_calls: raise ValueError('AI沒有調用工具')

        tool_call = response.choices[0].message.tool_calls[0]
        return tool_call

    async def run(self):
        try:
            tool_call = await self.chat()
            tool_name = tool_call.function.name
            arguments = tool_call.function.arguments
            args = orjson.loads(arguments) if type(arguments) != dict else arguments
            print(f'{tool_name}: {args}')
            await self.func(**args)
        except: 
            traceback.print_exc()

    async def func(self, time: str, event: str):
        '''格式為'%Y-%m-%d %H:%M' '''
        inter = self.inter
        channelID = inter.channel.id

        '''i18n'''
        invalid_format = await self.inter.translate('send_keep_invalid_format')
        time_passed = await self.inter.translate('send_keep_time_passed')
        too_far = await self.inter.translate('send_keep_too_far')
        ''''''

        try:        #如果使用者輸入錯誤的格式，則返回訊息並結束keep command
            keep_time = datetime.strptime(f'{time}', '%Y-%m-%d %H:%M')
        except Exception:
            await inter.followup.send(invalid_format, ephemeral=True)
            return
        
        now = datetime.now()
        delay = (keep_time - now).total_seconds()

        if delay <= 0:      #如果使用者輸入現在或過去的時間，則返回訊息並結束keep command
            await inter.followup.send(time_passed.format(inter.user.mention))
            return
        
        if delay > 31557600000:
            await inter.followup.send(too_far)
            return

        u = str(uuid.uuid4())
        self.collection.insert_one({
            'createAt': datetime.now().timestamp(),
            'sendAt': keep_time.timestamp(),
            'channelID': channelID,
            'event': event,
            'uuid': u
        })

        '''i18n'''
        embed_translated = await self.inter.translate('embed_keep_created')
        embed_translated: dict = (load_translated(embed_translated))[0]

        title = embed_translated.get('title')
        field_1 = (embed_translated.get('field'))[0]
        ''''''
        embed = create_basic_embed(title=title, description=f'**{event}**', color=inter.user.color, time=False)
        embed.set_author(name=inter.user.name, icon_url=inter.user.avatar.url)
        embed.add_field(name=field_1.get('name'), value=field_1.get('value'), inline=True)
        embed.set_footer(text=embed_translated.get('footer').format(keep_time=keep_time))

        await inter.followup.send(embed=embed)

        task = bot.loop.create_task(keepMessage(self.collection, inter.channel, inter.user, event, delay, u))
        reminder_tasks[u] = task


async def keepMessage(collection: AsyncIOMotorCollection, channel, user, event: str, delay: float, uuid: str):
    await asyncio.sleep(delay)

    try:
        await channel.send((await bot.tree.translator.get_translate('send_keep_remind')).format(mention=user.mention, event=event))
    except dc_errors.Forbidden:
        try:
            await user.send((await bot.tree.translator.get_translate('send_keep_remind')).format(mention=user.mention, event=event))
        except dc_errors.Forbidden:
            ...
        except Exception as e:
            logger.error(f'Cannot send keep message with DM: {e}', exc_info=True)
    except Exception as e:
        logger.error(f'Cannot send keep message with channel: {e}', exc_info=True)

    reminder_tasks.pop(uuid)

    collection.find_one_and_delete({
        'uuid': uuid,
        'channelID': channel.id
    })        

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
                delaySecond = e['sendAt'] - datetime.now().timestamp()
                if delaySecond <= 0: delaySecond = 1
                channelID = e['channelID']
                event = e['event']
                u = e['uuid']

                try:
                    channel = bot.get_channel(int(channelID)) or await bot.fetch_channel(int(channelID))
                except dc_errors.NotFound: # 找不到
                    await collection.delete_one({
                        'uuid': u,
                        'channelID': channelID
                    })
                    continue
                except Exception as e:
                    logger.error(f'Unexpected error: {str(e)}', exc_info=True)
                    continue

                task = bot.loop.create_task(keepMessage(collection, channel, user, event, delaySecond, u)) 
                
                reminder_tasks[u] = task
                count += 1

        print(f'已新增 {count} 個 keep 任務')
    except: traceback.print_exc()


async def keep_event_autocomplete(interaction: Interaction, current: str) -> List[Choice[str]]:
    userID = str(interaction.user.id)
    collection = DB[userID]

    result = [
        (
            f"{item.get('event', '')} | {datetime.fromtimestamp(item.get('sendAt', 0))} | {(bot.get_channel(item.get('channelID', 0))).name} | {(bot.get_channel(item.get('channelID', 0))).guild.name}" ,
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

    @app_commands.command(name=locale_str('del_keep'), description=locale_str('del_keep'))
    @app_commands.autocomplete(keep_event=keep_event_autocomplete)
    async def del_keep(self, inter: Interaction, keep_event: str):
        await inter.response.defer(ephemeral=True, thinking=True)

        collection = DB[str(inter.user.id)]

        try:
            keep_event = orjson.loads(keep_event)
        except:
            return await inter.followup.send(await inter.translate('send_del_keep_please_use_slash_command'), ephemeral=True)
        
        uuid = keep_event[0]
        channelID = keep_event[1]

        doc = await collection.find_one_and_delete({
            'uuid': uuid,
            'channelID': channelID
        })

        task = reminder_tasks.pop(uuid)
        task.cancel()

        await inter.followup.send( (await inter.translate('send_del_keep_cancel_success') ).format(
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
        sendAt_text = await inter.translate('send_show_keep_sendAt_text')
        event_text = await inter.translate('send_show_keep_event_text')
        channel_text = await inter.translate('send_show_keep_channel_text')
        ''''''

        data = ['## Events:']
        index = 1

        async for e in collection.find().sort('sendAt', -1):
            sendAt = UnixToReadable(e.get('sendAt', 0))
            event = e.get('event', '')
            channel = self.bot.get_channel(e.get('channelID', 0))
            channelName = channel.name
            guildName = channel.guild.name
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
        await ctx.send(str(reminder_tasks))

async def setup(bot):
    await bot.add_cog(Keep(bot))