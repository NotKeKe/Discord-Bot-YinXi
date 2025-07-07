from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import orjson
import uuid
from datetime import datetime
from openai import AsyncOpenAI
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
import traceback

from core.classes import Cog_Extension, bot
from core.functions import read_json, write_json, create_basic_embed, current_time, KeJCID
from core.translator import load_translated, locale_str
from cmds.AIsTwo.base_chat import base_url_options

ex_keepData = {
    'ctx.author.id': [
        {
            "When_to_send_str": "2025-05-13 22:00:00",
            "When_to_send_timestamp": 1747144800.0,
            "ChannelID": 1300024314518704210,
            "event": "HI",
            'uuid': "str(uuid.uuid4())"
        }, 
    ]
}

keepPATH = './cmds/data.json/keep.json'

class SaveKeep:
    keepData = None
    update = False

    @classmethod
    def initData(cls):
        if not cls.keepData:
            cls.keepData = read_json(keepPATH)

    @classmethod
    def save(cls, data=None):
        if data:
            cls.keepData = data
        cls.update = True

    @classmethod
    def write(cls):
        write_json(cls.keepData, keepPATH)
        cls.update = False

    @classmethod
    def deletekeepEvent(cls, userID: str, uuid: str):
        if cls.keepData is not None:
            for item in cls.keepData[userID]:
                if item['uuid'] == uuid:
                    cls.keepData[userID].remove(item)
                    break

            if not cls.keepData[userID]: del cls.keepData[userID]
            cls.save(cls.keepData)

class RunKeep:
    def __init__(self, time: str, event: str, ctx: commands.Context):
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
        self.model = 'qwen-3-32b'
        self.provider = 'cerebras'
        self.client = AsyncOpenAI(api_key=base_url_options[self.provider]['api_key'], base_url=base_url_options[self.provider]['base_url'])
        self.ctx = ctx
        self.interaction = ctx.interaction

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
            raise

    async def func(self, time: str, event: str):
        '''格式為'%Y-%m-%d %H:%M' '''
        SaveKeep.initData()
        data = SaveKeep.keepData
        ctx = self.ctx
        channelID = ctx.channel.id
        userID = str(ctx.author.id)

        '''i18n'''
        invalid_format = await self.interaction.translate('send_keep_invalid_format')
        time_passed = await self.interaction.translate('send_keep_time_passed')
        too_far = await self.interaction.translate('send_keep_too_far')
        ''''''

        try:        #如果使用者輸入錯誤的格式，則返回訊息並結束keep command
            keep_time = datetime.strptime(f'{time}', '%Y-%m-%d %H:%M')
        except Exception:
            await ctx.send(invalid_format, ephemeral=True)
            return
        
        now = datetime.now()
        delay = (keep_time - now).total_seconds()

        if delay <= 0:      #如果使用者輸入現在或過去的時間，則返回訊息並結束keep command
            await ctx.send(time_passed.format(ctx.author.mention))
            return
        
        if delay > 31557600000:
            await ctx.send(too_far)
            return

        u = str(uuid.uuid4())
        if userID not in data:
            data[userID] = [
                {
                    'When_to_send_str': str(keep_time),
                    'When_to_send_timestamp': keep_time.timestamp(),
                    'ChannelID': channelID,
                    "event": event,
                    'uuid': u
                }
            ]
        else:
            data[userID].append(
                {
                    'When_to_send_str': str(keep_time),
                    'When_to_send_timestamp': keep_time.timestamp(),
                    'ChannelID': channelID,
                    "event": event,
                    'uuid': u
                }
            )
        '''i18n'''
        embed_translated = await self.interaction.translate('embed_keep_提醒事件')
        embed_translated: dict = (load_translated(embed_translated))[0]

        title = embed_translated.get('title')
        field_1 = (embed_translated.get('field'))[0]
        ''''''
        embed = create_basic_embed(title=title, description=f'**{event}**', color=ctx.author.color, time=False)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
        embed.add_field(name=field_1.get('name'), value=field_1.get('value'), inline=True)
        embed.set_footer(text=f'時間: {keep_time}')
        embed.set_footer(text=embed_translated.get('footer').format(keep_time=keep_time))

        await ctx.send(embed=embed)

        SaveKeep.save(data)
        bot.loop.create_task(self.keepMessage(ctx.channel, ctx.author, event, delay, u))

    @staticmethod
    async def keepMessage(channel, user, event, delay, uuid: str):
        await asyncio.sleep(delay)
        await channel.send(f'{user.mention}, 你需要做 {event}')
        SaveKeep.deletekeepEvent(str(user.id), uuid)

    @classmethod
    async def create_KeepTask(cls):
        '''This is a function for creating a keep task at bot ready. It will send a message to the user at the specified time.'''
        try:
            SaveKeep.initData()
            data = SaveKeep.keepData
            if not data: return
            count = 0
            for userID in data:
                for item in data[userID]:
                    delaySecond = item['When_to_send_timestamp']
                    delaySecond = (datetime.fromtimestamp(delaySecond) - datetime.now()).total_seconds()
                    if delaySecond <= 0: delaySecond = 1
                    channelID = item['ChannelID']
                    event = item['event']
                    u = item['uuid']

                    user = await bot.fetch_user(int(userID))
                    channel = await bot.fetch_channel(int(channelID))

                    bot.loop.create_task(cls.keepMessage(channel, user, event, delaySecond, u)) 
                    count += 1
            print(f'已新增 {count} 個 keep 任務')
        except: traceback.print_exc()


class Keep(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.write_keep_data.start()
        await self.bot.wait_until_ready()
        await RunKeep.create_KeepTask()

    # Create a Keep
    @commands.hybrid_command()
    @app_commands.describe(time=locale_str('keep_time'))
    async def keep(self, ctx:commands.Context, time: str, * , event: str):
        '''[keep time(會使用AI作分析) event: str'''
        async with ctx.typing():
            await RunKeep(time, event, ctx).run()

    @commands.command(name='check_keepdata')
    async def check_keepdata(self, ctx: commands.Context):
        if str(ctx.author.id) != KeJCID: return
        await ctx.send(f'{SaveKeep.keepData=}\n{SaveKeep.update=}')

    @tasks.loop(minutes=1)
    async def write_keep_data(self):
        try:
            if not SaveKeep.update: return
            SaveKeep.write()
        except: traceback.print_exc()

    @write_keep_data.before_loop
    async def write_keep_data_before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Keep(bot))