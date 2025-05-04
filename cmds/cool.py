import discord
from discord import app_commands
from discord.ext import commands
import time, os
import traceback
# for keep
import asyncio
from datetime import datetime, timedelta
from typing import Optional
# for 簽到
import json

from core.classes import Cog_Extension
from core.functions import read_json, write_json, create_basic_embed, KeJCID, admins

ex_keepData = {
    'ctx.author.id': [
        {
            'When_to_send': '2025-02-21 12:00',
            'delay': 1234,
            'ChanelID': 123456789,
            "event": "你好"
        }, 
    ]
}

keepPATH = './cmds/data.json/keep.json'

class Cool(Cog_Extension):
    keepData = None

    @classmethod
    def initkeepData(cls):
        if cls.keepData is None:
            cls.keepData = read_json(keepPATH)

    @classmethod
    def savekeepData(cls, data):
        cls.keepData = data
        write_json(data, keepPATH)

    @classmethod
    def deletekeepEvent(cls, userlID: str):
        if cls.keepData is not None:
            cls.keepData[userlID].pop()
            cls.savekeepData(cls.keepData)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.initkeepData()
        await self.create_KeepTask()

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        try:
            if after.guild.id != 731034812336570399: return
            if after.bot and (after.id != self.bot.user.id): return

            channelID = 1367818599745454130
            channel = self.bot.get_channel(channelID) or await self.bot.fetch_channel(channelID)

            # await channel.send('on_presence_update')

            for m in after.guild.members:
                if m.id == after.id:
                    after = m

            before_activities_str = '\n'.join([(a.name + 
                ('(自定義狀態)' if isinstance(a, discord.CustomActivity) else '') + 
                ( (f' 細節: {a.details}' if a.details else '') if hasattr(a, 'details') else '') ) for a in before.activities]) if before.activities else 'None'
            after_activities_str = '\n'.join([(a.name + 
                ('(自定義狀態)' if isinstance(a, discord.CustomActivity) else '') + 
                ( (f' 細節: {a.details}' if a.details else '') if hasattr(a, 'details') else '') ) for a in after.activities]) if after.activities else 'None'

            if before_activities_str == after_activities_str and before.status == after.status: return
            
            eb = create_basic_embed(after.global_name or after.name, color=after.color)
            eb.add_field(name='**Before**', value=before_activities_str)
            eb.add_field(name="**After**", value=after_activities_str)
            eb.add_field(name='Status', value=f'{before.status} -> {after.status}')
            await channel.send(embed=eb)
        except:
            traceback.print_exc()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.content and not message.attachments: return
        
        日期 = time.strftime("%Y%m%d")
        attachments = [
            attachment.url
            for attachment in message.attachments
            if attachment.content_type and attachment.content_type.startswith('image/')
        ]
        if attachments: attachments.insert(0, 'url: '); attachments.append(0, 'content: ')
        attachments += [message.content]
        user_said = ' '.join(attachments)

        if message.guild:
            if message.author.bot: return
            # path1 = f'./chat_log/{message.guild.name}'
            path2 = f'./chat_log/server/{message.guild.name}/{message.channel.name}'
            
            os.makedirs(path2, exist_ok=True)  

            with open(f'{path2}/{日期}.txt', mode="at", encoding='utf8') as file:
                file.write(f'[{time.strftime("%Y/%m/%d %H:%M:%S")}]    {message.author.global_name} 說: {user_said}\n')
        else:
            path = f'./chat_log/DM/{message.author.id}'
            os.makedirs(path, exist_ok=True)  
            with open(f'{path}/{日期}.txt', 'at', encoding='utf8') as f:
                f.write(f'[{time.strftime("%Y/%m/%d %H:%M:%S")}]    {message.author.global_name} 說: {user_said}\n'
                        if not message.author.bot else 
                        f'[{time.strftime("%Y/%m/%d %H:%M:%S")}]    {self.bot.user.global_name} 說: {user_said}\n')

    async def keepMessage(self, channel, user, event, delay):
        await asyncio.sleep(delay)
        await channel.send(f'{user.mention}, 你需要做 {event}')
        self.deletekeepEvent(str(user.id))

    async def create_KeepTask(self):
        await self.bot.wait_until_ready()
        data = self.__class__.keepData
        for userID in data:
            delaySecond = data[userID]['delay']
            channelID = data[userID]['ChannelID']
            event = data[userID]['event']

            user = await self.bot.fetch_user(int(userID))
            channel = await self.bot.fetch_channel(int(channelID))

            self.bot.loop.create_task(self.keepMessage(channel, user, event, delaySecond))

    # Create a Keep
    @commands.hybrid_command()
    @discord.app_commands.describe(date = "格式:年-月-日", time = "時:分 (請使用24小時制)")
    async def keep(self, ctx:commands.Context, time: str, date: Optional[str] = None, * , event: str):
        '''[keep time(格式: 時:分) date(日期，格式: 年-月-日)'''
        self.initkeepData()
        data = self.__class__.keepData
        channelID = str(ctx.channel.id)
        userID = str(ctx.author.id)

        import time as tm
        
        if date == None:        #如果使用者未輸入，則預設為當天日期
            date = tm.strftime("%Y-%m-%d")

        try:        #如果使用者輸入錯誤的格式，則返回訊息並結束keep command
            keep_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        except Exception:
            await ctx.send('你輸入了錯誤的格式', ephemeral=True)
            return
        
        now = datetime.now()
        delay = (keep_time - now).total_seconds()

        if delay <= 0:      #如果使用者輸入現在或過去的時間，則返回訊息並結束keep command
            await ctx.send(f'{ctx.author.mention}, 你指定的時間已經過去了，請選擇一個未來的時間。')
            return
        
        if delay > 31557600000:
            await ctx.send('你設置了1000年後的時間??\n 我都活不到那時候你憑什麼:sob:')
            return

        if userID not in data:
            data[userID] = [
                {'When_to_send': str(keep_time),
                'delay': delay,
                'ChannelID': channelID,
                "event": event}
            ]
        else:
            data[userID].append(
                {'When_to_send': str(keep_time),
                'delay': delay,
                'ChannelID': channelID,
                "event": event}
            )

        embed = create_basic_embed(title='提醒事件:', description=f'**{event}**', color=ctx.author.color, time=False)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
        embed.add_field(name='', value='', inline=False)
        embed.add_field(name='注意事項: ', value='記得開啟此頻道的mentions通知 以免錯過提醒!', inline=True)
        embed.set_footer(text=f'時間: {keep_time}')

        await ctx.send(embed=embed)

        self.savekeepData(data)
        self.bot.loop.create_task(self.keepMessage(ctx.channel, ctx.author, event, delay))

    # 簽到
    @commands.hybrid_command(name = "每日簽到", description = "check in, 每日簽到")
    async def checkin(self, ctx):
        '''[每日簽到, 就只是簽到!'''
        userid = str(ctx.author.id)
        try:
            with open("./cmds/data.json/簽到.json", mode="r", encoding="utf8") as file:
                data_c = json.load(file)

            if(userid not in data_c):
                data_c[userid] = {
                    'times': 1,
                    'last_checkin': time.strftime("%Y/%m/%d")
                }
            else:
                if data_c[userid]['last_checkin'] == time.strftime("%Y/%m/%d"):
                    await ctx.send('你簽過了')
                    return
                
                data_c[userid]['times'] += 1
                data_c[userid]['last_checkin'] = time.strftime("%Y/%m/%d")

            with open("./cmds/data.json/簽到.json", mode="w", encoding="utf8") as file:
                json.dump(data_c, file, indent=4)
        
            await ctx.send(f"您已在「{time.strftime('%Y/%m/%d %H:%M:%S')}」時簽到, 目前簽到次數為: {data_c[userid]['times']}")
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False)

    @commands.hybrid_command(name="傳送私人訊息", description = "僅給克克使用")
    async def private_message(self, ctx, userid: str=None, username: discord.Member=None, *, prompt):
        '''只有克克能用的話  還需要幫助嗎:thinking:'''
        if str(ctx.author.id) != KeJCID: await ctx.send("你沒有權限使用該指令"); return
        if username is None and userid is None: await ctx.send("你未輸入使用者"); return
        if username is not None and userid is not None: await ctx.send("你輸入了兩個使用者"); return
        if not prompt: await ctx.send("你未輸入訊息"); return

        try:
            if username is not None: # 使用者輸入了username
                user = await self.bot.fetch_user(username.id)
            elif userid is not None: # 使用者輸入了userid
                userid = int(userid)
                user = await self.bot.fetch_user(userid)

            await user.send(prompt) # 如果此時使用者關閉私訊功能，則會出現discord.Forbidden

            await ctx.send("已傳送私人訊息")
        except discord.Forbidden: 
            await ctx.send("此使用者關閉了私訊功能")
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception)

    @app_commands.command(name="獲取id", description="Get the user's ID (User must in this guild)")
    async def get_id(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(member.id, ephemeral=True)
    
    @commands.hybrid_command(name="取得使用者狀態", description="Get the user's status (使用者必須在你使用指令的伺服器裡面)")
    async def get_user_status(self, ctx: commands.Context, user_id: str = None, member: discord.Member = None, ephemeral: bool = True):
        try:
            if user_id and member:
                return await ctx.send('請只選擇userID或是user做為輸入 (或者兩個都不輸入 來查看你自己的狀態)')
            elif user_id:
                try: int(user_id)
                except: return await ctx.send("請輸入有效的ID")

                try:
                    member = ctx.guild.get_member(user_id)
                    if not member:
                        member = await ctx.guild.fetch_member(user_id)
                except discord.NotFound:
                    return await ctx.send(f'沒有找到有關於該使用者的資訊 ({user_id=})')
                except Exception as e:
                    return await ctx.send(f'未取得該使用者的資訊 請稍後再試 reason: {str(e)}')
            elif member:
                pass
            else: # 取得ctx.author的狀態
                member = ctx.author
            
            for m in ctx.guild.members:
                if m.id == member.id:
                    member = m

            m_name = member.global_name or member.name
            eb = create_basic_embed(f'**{m_name}** ({member.status}): ', color=member.color)

            if member.activities:
                for a in member.activities:
                    eb.add_field(name=a.name + ('(自定義狀態)' if type(a) == discord.CustomActivity else ''), 
                                 value=(f'- 細節: {a.details}' if a.details else '') if hasattr(a, 'details') else '')
            else:
                eb.add_field(name='使用者沒有正在進行的活動', value=' ')

            await ctx.send(embed=eb, ephemeral=ephemeral)
        except: traceback.print_exc()

async def setup(bot):
    await bot.add_cog(Cool(bot))