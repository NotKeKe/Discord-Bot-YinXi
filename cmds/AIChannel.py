import discord
from discord import app_commands
from discord.ext import commands, tasks
import traceback
import typing
from datetime import datetime
import asyncio
import random
import parsedatetime

# from cmds.AIs.info import HistoryData
# from cmds.AIs.zhipu import response
# from cmds.AIs.hugging import available_models as hugging_moduels_and_provider
# from cmds.AIs.hugging import chat as chat_hugging
# from cmds.AIs.ollama import available_ollama_models as ollama_moduels
# from cmds.AIs.ollama import chat_ollama
# from cmds.AIs.openrouter import openrouter_moduels
# from cmds.AIs.openrouter import chat_openrouter, summarize

from cmds.AIsTwo.info import HistoryData
from cmds.AIsTwo.base_chat import zhipu_moduels, openrouter_moduels, ollama_modules, gemini_moduels, base_zhipu_chat, base_openai_chat, to_assistant_message, to_user_message, stop_flag
from cmds.AIsTwo.human.base import chat_human, processing, style_train
from cmds.AIsTwo.others.func import summarize
from cmds.AIsTwo.others.decide import is_talking_with_me, save_to_knowledge_base, ActivitySelector, Preference
from cmds.AIsTwo.utils import choice_model, halfToFull, select_moduels_auto_complete

from core.functions import thread_pool, create_basic_embed, current_time, KeJCID, current_time, get_attachment, admins

save_to_preferences = Preference.save_to_preferences

resting = False # 每隔一段時間就讓bot休息不讀訊息(模擬人類下線)

cal = parsedatetime.Calendar()
reminder_tasks = []

class AIChannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.overTenHistoryTask.start()
        self.rest.start()
        self.timed_history_save.start()

    async def schedule_reminder(user, channel, delay, text):
        await asyncio.sleep(delay)
        await channel.send(f"{user.mention} 嘿啦啦時間到囉：{text} (ﾉ>ω<)ﾉ")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.on_AIChannelSend(message)
        await self.on_ReplyOrTag(message)
        await self.chatWithHuman(message)
        await self.trainStyle(message)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        HistoryData.initdata()

    # Chat with human(由AI假扮)
    async def chatWithHuman(self, message: discord.Message):
        try:
            if resting: return

            HistoryData.initdata()
            channelID = str(message.channel.id)
            userID = message.author.id
            data = HistoryData.chat_human

            if message.author.bot: return
            if message.content.startswith('['): return
            if message.content == '': return
            if channelID in HistoryData.channel: return
            if message.guild and channelID not in HistoryData.chat_human: return

            if channelID not in data: data[channelID] = [] # 對私訊

            
            if message.guild:
                isTalkToMe = await thread_pool(is_talking_with_me, message.content, HistoryData.chat_human[channelID])
                if not isTalkToMe:
                    if (self.bot.user not in message.mentions and not message.reference and '尖峰' not in message.content): 
                        data[channelID][-1] += to_user_message(f'「使用者ID: {message.author.id}，使用者名稱: {message.author.global_name}」說了: `{message.content}`」\n' , userID)
                        HistoryData.writeChatHuman(data)
                        return
                    
            if message.content.startswith('提醒我'): return await ctx.send('我幹嘛提醒你 我是人欸')

            is_stop = False
            if channelID in processing:
                if userID in processing[channelID]: # 如果正在生成 就stop flag
                    is_stop = True
                    # await message.channel.send('Stop')
                    if channelID in stop_flag: stop_flag[channelID].append(userID)
                    else: stop_flag[channelID] = [userID]
                    await asyncio.sleep(0.1)
            
            ctx = await self.bot.get_context(message)
            async with ctx.typing():
                think, result = await thread_pool(chat_human, ctx)
                if not result and not is_stop: await ctx.send('你說啥 再說一次'); return # 如果是因為使用者打斷對話 就不用傳送這個訊息
                await ctx.send(halfToFull(result))

            data[channelID] += (
                to_user_message(f'「使用者ID: {message.author.id}，使用者名稱: {message.author.global_name}」說了: `{message.content}`」' 
                                if message.guild else message.content, userID, time=current_time()) + 
                to_assistant_message(result, think)
            )
            HistoryData.writeChatHuman(data)
            # await thread_pool(save_to_knowledge_base, message.content, result if result else think)
            # await thread_pool(save_to_preferences, userID, data[channelID][-2:])
        except:
            traceback.print_exc()

    # AI channel
    async def on_AIChannelSend(self, message: discord.Message):
        try:
            HistoryData.initdata()
            channelID = str(message.channel.id)
            data = HistoryData.channel

            if message.author.bot: return
            if channelID not in data: return
            if message.content.startswith('['): return
            if message.content == '': return

            if message.content.startswith('提醒') or message.content.startswith("remind"): 
                # 嘗試用 parsedatetime 解析
                time_struct, parse_status = cal.parse(message.content)

                if parse_status == 0:
                    await message.channel.send("我不知道你要什麼時候提醒欸 (*´・ｖ・)")
                    return

                when = datetime(*time_struct[:6])
                now = datetime.now()
                delta = (when - now).total_seconds()

                if delta <= 0:
                    await message.channel.send("那個時間已經過了你知道嗎靠北 (¬_¬)")
                    return

                reminder_text = message.content.replace("提醒我", "").replace("提醒", "")
                await message.channel.send(f"好喔，我會在 `{when.strftime('%Y-%m-%d %H:%M:%S')}` 提醒你：{reminder_text.strip()} (｀・ω・´)")

                task = asyncio.create_task(self.schedule_reminder(message.author, message.channel, delta, reminder_text.strip()))
                reminder_tasks.append(task)


            ctx = await self.bot.get_context(message)
            async with ctx.typing():
                try:
                    model = HistoryData.channel_model_select[channelID]
                except:
                    model = 'glm-4-flash'
                    
                輸入文字 = f'「使用者ID: {message.author.id}，使用者名稱: {message.author.global_name}」說了: `{message.content}`」'
                history = data[channelID]
                attachments = get_attachment(message)

                try:
                    think, result, *_ = await thread_pool(base_openai_chat, 輸入文字, model, 0.7, history, userID=str(ctx.author.id), url=attachments)
                    if think == result == '': print(f'{model}沒給輸出 time: {current_time()}'); raise ValueError
                except:
                    await ctx.send(f'由於你使用的{model}抱錯 本次回答由 **glm-4-flash** 代替')
                    model = 'glm-4-flash'
                    think, result, *_ = await thread_pool(base_zhipu_chat, 輸入文字, model, 0.7, history, userID=str(ctx.author.id))

                output = result if result != '' else think
                if len(output) >= 2000:
                    await ctx.send('bot輸出了超過2000字的訊息...')
                await ctx.send(output[-1999:])

            HistoryData.appendHistoryForChannel(channelID, f'{ctx.author.id}: {輸入文字}', result, think, message.author.id, attachments)
            # await thread_pool(save_to_knowledge_base, message.content, result if result else think)
            # await thread_pool(save_to_preferences, message.author.id, data[channelID][-2:])
        except Exception as e:
            traceback.print_exc()
            await ctx.send(f"目前無法使用此功能，請稍後再試 (model={model}) {'bot沒有輸出' if think == result == '' else ''}\n {current_time()}")
            print(f'{think=}, {result=}')

    # on reply or on tag Bot
    async def on_ReplyOrTag(self, message: discord.Message):
        if message.author.bot: return    
        if not message.guild: return # 在DM中 交給self.chatWithHuman處理
        if self.bot.user not in message.mentions and not message.reference: return
        if message.reference: # 確保是bot被回覆
            replied_message = await message.channel.fetch_message(message.reference.message_id)
            if replied_message.author != self.bot.user: return
        if str(message.channel.id) in HistoryData.channel: return
        if str(message.channel.id) in HistoryData.chat_human: return

        string = ''
        try:
            if message.reference:
                string = f'身為一個discord bot，你剛剛說了{replied_message.content}。而現在「使用者ID: {message.author.id}，使用者名稱: {message.author.global_name}」說了: `'
            string += f'{message.content}`'

            ctx = await self.bot.get_context(message)
            await ctx.invoke(self.bot.get_command('chat'), 輸入文字=string)
        except:
            traceback.print_exc()

    async def trainStyle(self, message:discord.Message):
        try:
            channelID = str(message.channel.id)
            if message.author == self.bot.user: return
            if channelID != str(1357662478795935824): return
            if message.content == '': return
            if message.content.startswith('['): return
            HistoryData.initdata()
            if channelID in (HistoryData.channel, HistoryData.chat_human): return

            ctx = await self.bot.get_context(message)
            async with ctx.typing():
                think, result = await thread_pool(style_train, ctx)
                if result in (None, '') and think in (None, ''): await ctx.send('生成失敗'); return
                await ctx.send(result if result not in ('', None) else think); return
        except: traceback.print_exc()

    @commands.hybrid_command(name='ai頻道', description='設定此頻道為AI channel')
    @commands.has_permissions(administrator=True)
    @app_commands.describe(模型='預設為glm-4-flash，或者可使用[更換ai_channel模型 來為此頻道更換回覆的模型')
    @app_commands.autocomplete(模型=select_moduels_auto_complete)
    async def ai_channel(self, ctx, 模型: str = 'glm-4-flash'):
        HistoryData.initdata()
        data = HistoryData.channel
        channelID = str(ctx.channel.id)

        if channelID in HistoryData.channel and channelID in HistoryData.chat_human:
            await ctx.send(f"此頻道已經是{'AI channel' if channelID in HistoryData.channel else 'chatHuman'}，無法使用此功能")
            return

        if channelID not in data:
            data[channelID] = []
            embed = create_basic_embed(title=f'已設定此頻道為AI channel (模型: {模型})')
            embed.add_field(name='注意事項', value='接下來在此頻道的每個訊息 (除了指令和圖片以外)都會被AI看到，所以不建議你透露太多個人資訊', inline=False)
            embed.add_field(name='如果不希望繼續讓ai自動回覆你的訊息的話，可以使用 [取消ai頻道', value=' ')
            await ctx.send(embed=embed)
            HistoryData.writeChannel(data)
            HistoryData.writeChannelSelectModel(ctx, 模型)
        else:
            await ctx.send('此頻道已經是AI channel')

    @commands.hybrid_command(name='取消ai頻道', description='取消AI channel')
    @commands.has_permissions(administrator=True)
    async def cancel_aiChannel(self, ctx: commands.Context):
        HistoryData.initdata()
        data = HistoryData.channel
        channelID = str(ctx.channel.id)

        if channelID not in data: await ctx.send('此頻道沒設置過AI channel', ephemeral=True); return

        embed = create_basic_embed(title='是否確定取消ai channel', description='注意: 此功能會刪除這個頻道之前的所有聊天紀錄', color=ctx.author.color)
        embed.set_footer(text=ctx.author.global_name, icon_url=ctx.author.avatar.url)

        button = discord.ui.Button(
            label = "✅",
            style = discord.ButtonStyle.blurple
        )
        button1 = discord.ui.Button(
            label='❌',
            style=discord.ButtonStyle.blurple
        )

        async def button_callback(interaction: discord.Interaction):
            del data[channelID]
            HistoryData.writeChannel(data)
            await interaction.response.edit_message(content='已取消AI channel', view=None)
        async def button1_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content='已取消動作 (未刪除AI channel)', view=None)
        
        button.callback = button_callback
        button1.callback = button1_callback
        
        view = discord.ui.View()
        view.add_item(button)
        view.add_item(button1)

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name='更換ai_channel模型', description="Change AI channel's model")
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(模型=select_moduels_auto_complete)
    async def change_aiChannelModel(self, ctx: commands.Context, 模型: str):
        HistoryData.initdata()
        channelID = str(ctx.channel.id)
        if channelID not in HistoryData.channel: await ctx.send('你尚未在此頻道設置AI channel', ephemeral=True); return

        HistoryData.writeChannelSelectModel(ctx, 模型)
        await ctx.send(f'已成功將 {ctx.channel.name} 的AI模型更換成 {模型}')
        if 模型 in openrouter_moduels:
            await ctx.send('Powered by OpenRouter.\n (OpenRouter可能會把對話拿去訓練模型)')

    @commands.hybrid_command(name='訊息想法顯示', description='Show previous message assistant reasoning')
    async def _pre_reasoning_show(self, ctx: commands.Context):
        HistoryData.initdata()
        channelID = str(ctx.channel.id)
        if channelID not in HistoryData.channel: await ctx.send('此頻道沒有設置AI channel', ephemeral=True); return
        try:
            reasoning = HistoryData.channel[channelID][-1]['reasoning']
        except:
            reasoning = '剛剛的對話沒有Reasoning'
        await ctx.send(reasoning)

    @commands.command(aliases=['model_show', 'model_select', 'modelshow'], description='顯示當前AI channel所使用的模型')
    async def modelShow(self, ctx):
        HistoryData.initdata()
        if str(ctx.channel.id) not in HistoryData.channel: return await ctx.send('此頻道尚未設置AI channel')
        model_select = HistoryData.channel_model_select.get(str(ctx.channel.id))
        await ctx.send(f"此頻道選擇的回覆模型是: **{model_select if model_select else ''}**")

    @commands.hybrid_command(name='人類對話', description='跟AI對話，但他會假裝成人類')
    async def chat(self, ctx: commands.Context):
        channelID = str(ctx.channel.id)
        if channelID in HistoryData.channel and channelID in HistoryData.chat_human:
            await ctx.send(f"此頻道已經是{'AI channel' if channelID in HistoryData.channel else 'chatHuman'}，無法使用此功能")
            return
        data = HistoryData.chat_human
        if channelID in data: await ctx.send('此頻道已經chat with human，無法使用此功能'); return
    
        embed = create_basic_embed(title='已設定此頻道為AI channel')
        embed.add_field(name='注意事項', value='接下來在此頻道的每個訊息 (除了指令和圖片以外)都會被AI看到，所以不建議你透露太多個人資訊', inline=False)
        embed.add_field(name='如果不希望繼續讓ai自動回覆你的訊息的話，可以使用 [取消ai頻道', value=' ')
        await ctx.send(embed=embed)
        data['chatting_with_human'].append(ctx.channel.id)
        HistoryData.writeChatHuman(data)

    @commands.hybrid_command(name='取消人類對話', description='取消跟AI偽裝的人類對話')
    async def cancel_chatHuman(self, ctx: commands.Context):
        channelID = str(ctx.channel.id)
        data = HistoryData.chat_human
        if channelID not in data: await ctx.send('此頻道沒設置過chat with human', ephemeral=True); return

        embed = create_basic_embed(title='是否確定取消chat with human', description='注意: 沒啥可注意的', color=ctx.author.color)
        embed.set_footer(text=ctx.author.global_name, icon_url=ctx.author.avatar.url)

        button = discord.ui.Button(
            label = "✅",
            style = discord.ButtonStyle.blurple
        )
        button1 = discord.ui.Button(
            label='❌',
            style=discord.ButtonStyle.blurple
        )

        async def button_callback(interaction: discord.Interaction):
            data['chatting_with_human'].remove(channelID)
            HistoryData.writeChatHuman(data)
            await interaction.response.edit_message(content='已取消chat with human', view=None)
        async def button1_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content='已取消動作 (未刪除chat with human)', view=None)
        
        button.callback = button_callback
        button1.callback = button1_callback
        
        view = discord.ui.View()
        view.add_item(button)
        view.add_item(button1)

        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name='ai_personality', description='設定AI的personality 讓他以這個個性跟你說話', aliases=['ai_personal'])
    async def set_personality(self, ctx: commands.Context, personality: str=None):
        HistoryData.initdata()
        data = HistoryData.personality
        userID = str(ctx.author.id)
        original = None
        if userID in data: original = data[userID]

        if personality:
            data[userID] = personality
            HistoryData.writePersonality(data)
            await ctx.send(f'已經你的AI的個性設定設定為**{personality}**' + (f'(原本為 {original})' if original else ''))
        else:
            if userID in data: del data[userID]
            await ctx.send('已刪除AI的個性' + (f'原本為: ({original})' if original else ''))


    @tasks.loop(minutes=5)
    async def overTenHistoryTask(self):
        try:
            channel = await self.bot.fetch_channel(1336967311747321876)
            await channel.send(f'聊天對話整理中 {current_time()}')
            count = 0

            HistoryData.initdata()
            userHistorydata = HistoryData.user
            channelHistoryData = HistoryData.channel
            chatHuman = HistoryData.chat_human

            for channelID in channelHistoryData:
                conversation1 = channelHistoryData[channelID]
                if len(conversation1) > 10:
                    history = conversation1[:-4]
                    summarized = await thread_pool(summarize, history)
                    channelHistoryData[channelID][:-4] = [{
                        'role': 'user',
                        'content': summarized
                    }]

                    HistoryData.writeChannel(channelHistoryData)
                    count += 1
            
            for userID in userHistorydata:
                for title in userHistorydata[userID]:
                    if title == '': continue
                    if type(title) == int:
                        print(f'Error\n{userID=}, {title=}')
                    conversation2 = userHistorydata[userID][title]
                    if len(conversation2) > 10:
                        history = conversation2[:-4]
                        summarized = await thread_pool(summarize, history)
                        userHistorydata[userID][title][:-4] = [{
                            'role': 'user',
                            'content': summarized
                        }]
                        
                        HistoryData.writeUser(userHistorydata)
                        count += 1

            for aID in chatHuman:
                conversation3 = chatHuman[aID]
                if not conversation3: continue
                if len(conversation3) > 10:
                    history = conversation3[:-4]
                    summarized = await thread_pool(summarize, history)
                    chatHuman[aID][:-4] = [{
                        'role': 'user',
                        'content': summarized
                    }]

                    HistoryData.writeChatHuman(chatHuman)
                    count += 1

            await channel.send(f'聊天對話整理完畢 {current_time()} 整理次數={count}')
        except:
            traceback.print_exc()

    @tasks.loop(minutes=5)
    async def rest(self): # 取 1~150 讓bot休息 (此段期間 human_chat 不運作)
        try:
            if_run_this_func = random.uniform(0, 1) < 0.5
            if not if_run_this_func: return

            second = random.randint(1, 120)
            global resting
            resting = True
            await self.bot.change_presence(status=discord.Status.idle)
            await asyncio.sleep(second)
            resting = False
            activity = await thread_pool(ActivitySelector.activity_select)
            await self.bot.change_presence(status=discord.Status.online, activity=activity)
        except: traceback.print_exc()

    @tasks.loop(minutes=1)
    async def timed_history_save(self):
        HistoryData.timed_storage()

    @overTenHistoryTask.before_loop
    async def before_task(self):
        await self.bot.wait_until_ready()

    @rest.before_loop
    async def before_rest(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(600)
    
    @timed_history_save.before_loop
    async def before_timed_history_save(self):
        await self.bot.wait_until_ready()
        

    @commands.command(name='force_output')
    async def force_processing_stop_flag_output(self, ctx):
        if str(ctx.author.id) != KeJCID: return
        await ctx.send(f'{processing=}\n{stop_flag=}\n{resting=}')

    @commands.command(name='force_history')
    async def force_save_history(self, ctx):
        if str(ctx.author.id) != KeJCID: return
        HistoryData.timed_storage()
        await ctx.send('已將對話記錄存入')

    @commands.command(name='force_online')
    async def force_online(self, ctx):
        if str(ctx.author.id) not in admins: return
        async with ctx.typing():
            global resting
            resting = False
            activity = await thread_pool(ActivitySelector.activity_select())
            await self.bot.change_presence(status=discord.Status.online, activity=activity)
            await ctx.send('Bot 已從閒置模式轉為Online')

async def setup(bot):
    await bot.add_cog(AIChannel(bot))