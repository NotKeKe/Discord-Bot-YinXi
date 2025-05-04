import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import random
import os 
from dotenv import load_dotenv

from core.functions import read_json, write_json
from core.classes import Cog_Extension

load_dotenv()
embed_link = os.getenv('embed_default_link')

path = './cmds/data.json/giveaway.json'

# {
#     "Message_id": {
#         "Channel_id": 132456,
#         "Hosted_by": 123456,
#         "Prize": "nothing",
#         "EndTime": "2025-01-19 22:01:18.972283",
#         "WinnersTotal": 1,
#         "Participants": []
#     }
# }

async def start(data, message_id):
    # 重新追蹤button
    bot = Giveaway.bot

    channel_id = data[message_id]['Channel_id']
    message_id = int(message_id)

    channel = await bot.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id)

    button = discord.ui.Button(label='🎉')
    button.callback = button_callback

    view = discord.ui.View()
    view.add_item(button)

    message = await message.edit(view=view)
    print('已重新開始追蹤Giveaway')
    
    # 計算等待時間並等待
    end_time = data[message_id]['EndTime']
    keep_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')

    now = datetime.now()
    delay = (keep_time - now).total_seconds()
    await asyncio.sleep(delay)

    # 等待完畢
    data = read_json(path)

    # 取得 winner
    winners = data[str(message_id)]['Participants']
    if not winners:
        value = '沒有winner'
    else:
        winner_id = random.sample(winners, data[message_id]['WinnerTotal'] if len(winners) >= data[message_id]['WinnerTotal'] else len(winners))
        winner = [await bot.fetch_user(winner) for winner in winner_id]
        value = ", ".join([user.mention for user in winner])

    # 取得當前參加giveaway人數
    count = embed.fields[1].value 

    # 取得發送訊息的user
    author = await bot.fetch_user(data[message_id]['Hosted_by'])

    # Embed
    embed=discord.Embed(title=data[message_id]['Prize'], color=author.color, timestamp=datetime.now())
    embed.add_field(name="獲獎者", value=value, inline=False)
    embed.set_footer(text=f"預設獲獎人數: {data[message_id]['WinnersTotal']} | 參加人數: {count}")
    await message.edit(content=f'🎉 **GIVEAWAY 已結束** 🎉\n{author.mention}\n{value}', embed=embed, view=None)

    del data[str(message.id)]

    write_json(data, path)
    
async def button_callback(interaction: discord.Interaction):
    data = read_json(path)

    # 獲取Embed訊息
    embed = interaction.message.embeds[0]
    # 取得當前參加giveaway人數
    count = int(embed.fields[1].value)     

    if interaction.user.id in data[str(interaction.message.id)]['Participants']:
        # 更改json
        data[str(interaction.message.id)]['Participants'].remove(interaction.user.id)
        # 更改embed
        count -= 1
        #傳送取消訊息給user
        await interaction.response.send_message(content='已取消參加Giveaway', ephemeral=True)
    else:
        # 更改json
        data[str(interaction.message.id)]['Participants'].append(interaction.user.id)
        # 更改embed
        count += 1
        # 傳送取消訊息給user
        await interaction.response.send_message(content='已參加Giveaway', ephemeral=True)

    # 更新Embed
    embed.set_field_at(1, name="目前參加人數", value=str(count), inline=False)
    await interaction.message.edit(embed=embed)

    write_json(data, path)

class Giveaway(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        data = read_json(path)
        if not data: return
        for message_id in data:
            await start(data, message_id)

    @commands.hybrid_command(name='giveaway', description='Giveaway')
    @app_commands.describe(獎品='輸入你要讓別人獲得的獎品', 中獎人數='輸入一個「數字」', date = "格式:年-月-日", time = "時:分 (請使用24小時制)")
    async def giveaway(self, ctx: commands.Context, 中獎人數: int, 獎品: str, date: str, time: str):
        '''[giveaway 中獎人數 獎品 date(日期, 格式:年-月-日) time(日期, 格式: 時:分)
        順便說一下 現在這功能如果遇到我重啟bot的話，還不確定能不能正常運作'''
        try:        #如果使用者輸入錯誤的格式，則返回訊息並結束keep command
            keep_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        except Exception:
            await ctx.send('你輸入了錯誤的格式', ephemeral=True)
            return
        try:
            now = datetime.now()
            delay = (keep_time - now).total_seconds()

            if delay <= 0:      #如果使用者輸入現在或過去的時間，則返回訊息並結束keep command
                await ctx.send(f'{ctx.author.mention}, 你指定的時間已經過去了，請選擇一個未來的時間。', ephemeral=True)
                return
            if delay > 31557600000:
                await ctx.send('你設置了1000年後的時間??\n 我都活不到那時候你憑什麼:sob:')
                return
            
            # Embed
            embed=discord.Embed(title=f'**{獎品}**', color=ctx.author.color, timestamp=keep_time)
            embed.set_author(name='Giveaway', icon_url=ctx.author.avatar.url)
            embed.add_field(name="中獎人數:", value=中獎人數, inline=False)
            embed.add_field(name='目前參加人數:', value=0, inline=False)
            embed.add_field(name='注意事項', value='如果點擊按鈕後 bot沒有傳送任何訊息給你，就代表你尚未參加這個活動')
            embed.set_footer(text="結束時間")

            # Button
            button = discord.ui.Button(label="🎉")
            button.callback = button_callback
            
            # View
            view = discord.ui.View()
            view.add_item(button)

            message = await ctx.send(embed=embed, view=view)

            # 寫入抽獎資訊
            data = read_json(path)

            data[str(message.id)] = {
                "Channel_id": ctx.channel.id,
                "Hosted_by": ctx.author.id,
                "Prize": 獎品,
                "EndTime": str(keep_time),
                "WinnersTotal": 中獎人數,
                "Participants": []
            }

            write_json(data, path)

            # 等待中獎
            await asyncio.sleep(delay)

            data = read_json(path)

            winners = data[str(message.id)]['Participants']
            if not winners:
                value = '沒有winner'
            else:
                winner_id = random.sample(winners, 中獎人數 if len(winners) >= 中獎人數 else len(winners))
                winner = [await self.bot.fetch_user(winner) for winner in winner_id]
                value = ", ".join([user.mention for user in winner])
        
            # 取得當前參加giveaway人數
            count = int(embed.fields[1].value)

            # Embed
            embed=discord.Embed(title=獎品, color=ctx.author.color, timestamp=datetime.now())
            embed.add_field(name="獲獎者", value=value, inline=False)
            embed.set_footer(text=f'預設獲獎人數: {中獎人數} | 參加人數: {count}')
            await message.edit(content=f'🎉 **GIVEAWAY 已結束** 🎉\n{ctx.author.mention}\n{value}', embed=embed, view=None)

            del data[str(message.id)]

            write_json(data, path)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)


    



async def setup(bot):
    await bot.add_cog(Giveaway(bot))