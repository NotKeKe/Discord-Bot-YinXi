import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import random
import os 
from dotenv import load_dotenv

from core.functions import read_json, write_json
from core.classes import Cog_Extension, get_bot
from core.translator import locale_str, load_translated, get_translate

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
    bot = get_bot()

    channel_id = data[message_id]['Channel_id']
    message_id = int(message_id)

    channel = await bot.fetch_channel(channel_id)
    message = await channel.fetch_message(message_id) # type: ignore

    button = discord.ui.Button(label='🎉')
    button.callback = button_callback # type: ignore

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
    if not data:
        return

    # 取得 winner
    winners = data[str(message_id)]['Participants']
    if not winners:
        value = bot.tree.translator.get_translate('send_giveaway_no_winner', channel.guild.preferred_locale.value) # type: ignore
    else:
        winner_id = random.sample(winners, data[message_id]['WinnerTotal'] if len(winners) >= data[message_id]['WinnerTotal'] else len(winners))
        winner = [await bot.fetch_user(winner) for winner in winner_id]
        value = ", ".join([user.mention for user in winner])

    # 取得當前參加giveaway人數
    count = embed.fields[1].value 

    # 取得發送訊息的user
    author = await bot.fetch_user(data[message_id]['Hosted_by'])

    # Embed
    '''i18n'''
    eb_template = await get_translate('embed_giveaway_end', bot.get_user(bot.user.id))
    eb_data = load_translated(eb_template)[0]
    winner_field_name = eb_data.get('fields')[0].get('name')
    footer_text = eb_data.get('footer')
    ''''''

    embed=discord.Embed(title=data[message_id]['Prize'], color=author.color, timestamp=datetime.now())
    embed.add_field(name=winner_field_name, value=value, inline=False)
    embed.set_footer(text=footer_text.format(winners_total=data[message_id]['WinnersTotal'], count=count))
    await message.edit(content=(await get_translate('send_giveaway_ended_message', bot.get_user(bot.user.id))).format(mention=author.mention, winner=value), embed=embed, view=None)

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
        await interaction.response.send_message(content=await get_translate('send_giveaway_left', interaction), ephemeral=True)
    else:
        # 更改json
        data[str(interaction.message.id)]['Participants'].append(interaction.user.id)
        # 更改embed
        count += 1
        # 傳送取消訊息給user
        await interaction.response.send_message(content=await get_translate('send_giveaway_joined', interaction), ephemeral=True)

    # 更新Embed
    '''i18n'''
    eb_template = await get_translate('embed_giveaway_start', interaction)
    eb_data = load_translated(eb_template)[0]
    participants_field_name = eb_data.get('fields')[1].get('name')
    ''''''
    embed.set_field_at(1, name=participants_field_name, value=str(count), inline=False)
    await interaction.message.edit(embed=embed)

    write_json(data, path)

class Giveaway(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        data = read_json(path)
        if not data: return
        for message_id in data:
            await start(data, message_id)

    @commands.hybrid_command(name=locale_str('giveaway'), description=locale_str('giveaway'))
    @app_commands.describe(中獎人數=locale_str('giveaway_winners_total'), 獎品=locale_str('giveaway_prize'), date=locale_str('giveaway_date'), time=locale_str('giveaway_time'))
    async def giveaway(self, ctx: commands.Context, 中獎人數: int, 獎品: str, date: str, time: str):
        '''[giveaway 中獎人數 獎品 date(日期, 格式:年-月-日) time(日期, 格式: 時:分)
        順便說一下 現在這功能如果遇到我重啟bot的話，還不確定能不能正常運作'''
        try:        #如果使用者輸入錯誤的格式，則返回訊息並結束keep command
            keep_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        except Exception:
            await ctx.send(await get_translate('send_giveaway_invalid_format', ctx), ephemeral=True)
            return
        try:
            now = datetime.now()
            delay = (keep_time - now).total_seconds()

            if delay <= 0:      #如果使用者輸入現在或過去的時間，則返回訊息並結束keep command
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
            embed=discord.Embed(title=f'**{獎品}**', color=ctx.author.color, timestamp=keep_time)
            embed.set_author(name=author_text, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            embed.add_field(name=winners_field_name, value=中獎人數, inline=False)
            embed.add_field(name=participants_field_name, value=participants_field_value, inline=False)
            embed.add_field(name=note_field_name, value=note_field_value, inline=False)
            embed.set_footer(text=footer_text)

            # Button
            button = discord.ui.Button(label="🎉")
            button.callback = button_callback # type: ignore
            
            # View
            view = discord.ui.View()
            view.add_item(button)

            message = await ctx.send(embed=embed, view=view)

            # 寫入抽獎資訊
            data = read_json(path)
            if not data:
                data = {}

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
            if not data:
                data = {}

            winners = data.get(str(message.id), {}).get('Participants')
            if not winners:
                value = await get_translate('send_giveaway_no_winner', ctx)
            else:
                winner_id = random.sample(winners, 中獎人數 if len(winners) >= 中獎人數 else len(winners))
                winner = [await self.bot.fetch_user(winner) for winner in winner_id]
                value = ", ".join([user.mention for user in winner])
        
            # 取得當前參加giveaway人數
            count = int(embed.fields[1].value)

            '''i18n'''
            eb_template = await get_translate('embed_giveaway_end', ctx)
            eb_data = load_translated(eb_template)[0]
            winner_field_name = eb_data.get('fields')[0].get('name')
            footer_text = eb_data.get('footer')
            ''''''
            # Embed
            embed=discord.Embed(title=獎品, color=ctx.author.color, timestamp=datetime.now())
            embed.add_field(name=winner_field_name, value=value, inline=False)
            embed.set_footer(text=footer_text.format(winners_total=中獎人數, count=count))
            await message.edit(content=(await get_translate('send_giveaway_ended_message', ctx)).format(mention=ctx.author.mention, winner=value), embed=embed, view=None)

            del data[str(message.id)]

            write_json(data, path)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)


    



async def setup(bot):
    await bot.add_cog(Giveaway(bot))