import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import time
import typing
import traceback
from dotenv import load_dotenv

from cmds.skyblock_commands_foldor import skyblock_commands
from core.functions import create_basic_embed, read_json, write_json, thread_pool
from so_func import c_function

# get env
load_dotenv()
KeJC_ID = int(os.getenv('KeJC_ID'))
embed_link = os.getenv('embed_default_link')
api_key = os.getenv('tmp_hypixel_api_key')

sb = skyblock_commands.Skyblock(api_key=api_key)

auction_item_tracker_itemPATH = './cmds/data.json/skyblock_auction_item_tracker.json'
bazaar_item_tracker_itemPATH = './cmds/data.json/skyblock_bazaar_item_tracker.json'


def format_string(input_string:str) -> str:
    words = input_string.lower().split('_')
    formatted_words = [word.capitalize() for word in words]
    formatted_string = ' '.join(formatted_words)
    return formatted_string

async def bazaar_tracker_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    class_bazaar = SkyblockItemTracker.bazaar
    bazaar = class_bazaar if class_bazaar is not None else sb.get_bazaar_data()
    if bazaar is None: return [app_commands.Choice(name='目前無法使用此指令，請稍後在試', value=1)]
    if not bazaar['success']: return [app_commands.Choice(name='API目前無法使用，請稍後再試或連繫我', value=1)]

    items = [name for name in bazaar['products']]

    if not current:
        return [app_commands.Choice(name=format_string(fruit), value=fruit) for fruit in items[:25]]

    return [app_commands.Choice(name=format_string(name), value=name) for name in items if current.lower() in name.lower()]

async def auction_tracker_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    class_auction = SkyblockItemTracker.auctions
    auction = class_auction if class_auction is not None else sb.get_auctions()
    if auction is None: return [app_commands.Choice(name='目前無法使用此指令，請稍後在試', value=1)]
    if not auction['success']: return [app_commands.Choice(name='API目前無法使用，請稍後再試或連繫我', value=1)]

    items = [item['item_name'] for item in auction['auctions']]

    if not current:
        return [app_commands.Choice(name=fruit, value=fruit) for fruit in items[:25]]

    return [app_commands.Choice(name=name, value=name) for name in items if current.lower() in name.lower()]

def bz_embed(obj, products, embed):
    '''obj: data[ctx.guild.id], products: bazaar['products'], embed: discord.Embed'''
    for item in obj['items']:
        products[item]
        sellprice = products[item]['quick_status']['sellPrice']
        F_sellprice = sb.format_price(sellprice)
        buyprice = products[item]['quick_status']['buyPrice']
        F_buyprice = sb.format_price(buyprice)
        embed.add_field(name=item, value=f"Sell Price: {F_sellprice}\nBuy price: {F_buyprice}", inline=False)
    return embed

# def ac_string(obj, ac_data, channelID):
#     '''obj: data[ctx.channel.id], ac_data: auctions['auctions'], channelID:int =ctx.channel.id'''
#     string = ''

#     for item in obj['items']:
#         string += f'### {item}\n'
#         for ac_item in ac_data:
#             if ac_item['item_name'].endswith(item) and ac_item['bin'] and not ac_item['claimed'] and ac_item['item_uuid'] not in SkyblockItemTracker.tracked_item[channelID]:
#                 string += f"From {sb.get_username_from_uuid(ac_item['auctioneer'])}: {sb.format_price(ac_item['starting_bid'])}\n"
#                 SkyblockItemTracker.tracked_item[channelID].append(item)
#         if string.endswith(f'### {item}\n'): string = string[:-len(f'### {item}\n')]
#     return string

def ac_string(obj, ac_data, channelID):
    return c_function.ac_string(SkyblockItemTracker, sb, obj, ac_data, channelID)

class ChannelSelect(discord.ui.View):
    def __init__(self, channels, user, page=0):
        super().__init__()
        self.channels = channels
        self.user = user
        self.page = page

        # 分頁：每頁最多 25 個頻道
        self.page_count = (len(channels) - 1) // 25 + 1
        start = self.page * 25
        end = start + 25
        options = [
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in channels[start:end]
        ]

        self.select = discord.ui.Select(placeholder="選擇一個頻道", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

        # 上一頁按鈕
        self.prev_button = discord.ui.Button(label="⬅️ 上一頁", style=discord.ButtonStyle.blurple)
        self.prev_button.callback = self.prev_page
        self.add_item(self.prev_button)

        # 下一頁按鈕
        self.next_button = discord.ui.Button(label="➡️ 下一頁", style=discord.ButtonStyle.blurple)
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)

        # 根據當前頁面啟用/禁用按鈕
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= self.page_count - 1

    async def select_callback(self, interaction: discord.Interaction):
        """當使用者選擇頻道時"""
        if interaction.user != self.user:
            return await interaction.response.send_message("這不是你的選單！", ephemeral=True)

        selected_channel = interaction.guild.get_channel(int(self.select.values[0]))
        SkyblockItemTracker.ac_user[str(selected_channel.id)] = SkyblockItemTracker.ac_user[str(interaction.channel.id)]
        del SkyblockItemTracker.ac_user[str(interaction.channel.id)]
        await interaction.response.send_message(f"你選擇將頻道更改至 {selected_channel.mention}", ephemeral=True)

    async def prev_page(self, interaction: discord.Interaction):
        """上一頁"""
        if interaction.user != self.user:
            return await interaction.response.send_message("這不是你的選單！", ephemeral=True)

        self.page -= 1
        await interaction.message.edit(view=ChannelSelect(self.channels, self.user, self.page))

    async def next_page(self, interaction: discord.Interaction):
        """下一頁"""
        if interaction.user != self.user:
            return await interaction.response.send_message("這不是你的選單！", ephemeral=True)

        self.page += 1
        await interaction.message.edit(view=ChannelSelect(self.channels, self.user, self.page))

class SkyblockItemTracker(commands.Cog):
    bz_user = None
    ac_user = None
    auctions = None
    bazaar = None

    tracked_item = {}

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ac_item_tracker.start()
        self.bz_item_tracker.start()
    
    @classmethod
    def initbzuser(cls):
        if cls.bz_user is None:
            cls.bz_user = read_json(bazaar_item_tracker_itemPATH)
    
    @classmethod
    def initacuser(cls):
        if cls.ac_user is None:
            cls.ac_user = read_json(auction_item_tracker_itemPATH)

    @classmethod
    def inittrackeditem(cls, channelID: int):
        if channelID not in cls.tracked_item:
            cls.tracked_item[channelID] = []

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        def get_data():
            bz_user = read_json(bazaar_item_tracker_itemPATH)
            bazaar = sb.get_bazaar_data()
            ac_user = read_json(auction_item_tracker_itemPATH)
            auctions = sb.get_auctions()
            return bz_user, bazaar, ac_user, auctions
        self.__class__.bz_user, self.__class__.bazaar, self.__class__.ac_user, self.__class__.auctions = await thread_pool(get_data)
        

    @commands.hybrid_command(aliases=['bztracker', 'bzt'], name='追蹤bazaar物品價錢', description="Track the price of items in bazaar.")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(item='選擇一個item，如果你在下次使用指令時選擇他 就會取消', 是否重新傳送訊息='選擇要True的話就只會更新bot新傳的訊息，舊的訊息就不會再管他')
    @app_commands.choices(是否重新傳送訊息=[app_commands.Choice(name='True', value=1), app_commands.Choice(name="False", value=2)])
    @app_commands.autocomplete(item=bazaar_tracker_autocomplete)
    async def start_item_check(self, ctx, item: str = None, 是否重新傳送訊息: app_commands.Choice[int] = None): # started embed
        name = item

        self.initbzuser()

        if name is None and 是否重新傳送訊息 is None:
            await ctx.send('你什麼都沒輸入幹嘛用這指令:<')
            return


        if 是否重新傳送訊息 is None: 
            是否重新傳送訊息 == 2
        if_NewMessage = 2 if 是否重新傳送訊息 is None else 是否重新傳送訊息.value

        data = self.__class__.bz_user

        if str(ctx.guild.id) in data:
            if name is not None:
                if name in data[str(ctx.guild.id)]['items']:
                    data[str(ctx.guild.id)]['items'].remove(name)
                    message = await ctx.send(f"已關閉對{name}的追蹤")
                else:
                    data[str(ctx.guild.id)]['items'].append(name)
                    message = await ctx.send(f"已開啟對{name}的追蹤")
            else: message = await ctx.send('Loading...')
            if if_NewMessage == 1:
                data[str(ctx.guild.id)]['channelID'] = ctx.channel.id
                data[str(ctx.guild.id)]["messageID"] = message.id
                embed = bz_embed(data[str(ctx.guild.id)], 
                            self.__class__.bazaar['products'], 
                            create_basic_embed(title=ctx.guild.name, 功能='BZ價格追蹤'))

                await message.edit(content=None, embed=embed)
        else:
            message = await ctx.send(f"已開啟對{name}的追蹤")
            data[str(ctx.guild.id)] = {
                "channelID": ctx.channel.id,
                "messageID": message.id,
                "items": [name]
            }

            embed = bz_embed(data[str(ctx.guild.id)], 
                            self.__class__.bazaar['products'], 
                            create_basic_embed(title=ctx.guild.name, 功能='BZ價格追蹤'))

            await message.edit(embed=embed)

        if not data[str(ctx.guild.id)]['items']: del data[str(ctx.guild.id)]

        self.__class__.bz_user = data
        write_json(self.__class__.bz_user, bazaar_item_tracker_itemPATH)

    @commands.hybrid_command(name='查看正在追蹤的auction物品', description='See the items bot are tracking')
    async def check_auction_user_data(self, ctx):
        ac_user = self.__class__.ac_user
        if not ac_user: await ctx.send('資料錯誤，請使用 /錯誤回報 回報此Bug')
        if str(ctx.channel.id) in ac_user:
            items = ac_user[str(ctx.channel.id)]['items']
            if items:
                view = discord.ui.View()
                select = discord.ui.Select(placeholder='選擇你要取消追蹤的物品', min_values=1, max_values=1, 
                                           options=[discord.SelectOption(label=item) for item in items[:25]])
                
                async def select_callback(interaction: discord.Interaction):
                    value = interaction.data['values'][0]
                    self.__class__.ac_user[str(interaction.channel.id)]['items'].remove(value)
                    write_json(self.__class__.ac_user, auction_item_tracker_itemPATH)
                    await interaction.response.send_message(f'已刪除{value}')

                select.callback = select_callback
                view.add_item(select)

                await ctx.send(content=f"目前正在追蹤的物品:\n{', '.join(items)}", view=view)
            else:
                await ctx.send('此頻道未設置任何auction物品追蹤')
        else:
            await ctx.send('此頻道未設置任何auction物品追蹤')

    @commands.hybrid_command(aliases=['actrakcer'], name='追蹤auction物品價錢', description="Track the price of items in auction.")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(item='選擇一個item，如果你在下次使用指令時選擇他 就會取消', 是否更換發送頻道='選擇要True的話就會彈出視窗，需要你手動輸入 頻道名稱 來切換要更改到哪個頻道')
    @app_commands.choices(是否更換發送頻道=[app_commands.Choice(name='True', value=1), app_commands.Choice(name="False", value=2)])
    @app_commands.autocomplete(item=auction_tracker_autocomplete)
    async def start_acitem_check(self, ctx: commands.Context, item: str = None, 是否更換發送頻道: app_commands.Choice[int] = None): # started embed
        try:
            if 是否更換發送頻道 is None: 
                是否更換發送頻道 == 2
            if_NewMessage = 2 if 是否更換發送頻道 is None else 是否更換發送頻道.value

            self.initacuser()
            self.inittrackeditem(ctx.channel.id)  
            data = self.__class__.ac_user

            if if_NewMessage == 1 and str(ctx.channel.id) in data:
                channels = [
                    channel for channel in ctx.guild.text_channels 
                    if channel.permissions_for(ctx.author).view_channel 
                        and str(channel.type) == 'text'
                ]
                view = ChannelSelect(channels, ctx.author)

                await ctx.send(view=view)
            elif item is None:
                await ctx.send('你沒有輸入item :<', ephemeral=True)
                return  
            
            if item is not None:
                if str(ctx.channel.id) in data:
                    if item in data[str(ctx.channel.id)]['items']:
                        data[str(ctx.channel.id)]['items'].remove(item)
                        message = await ctx.send(f"已關閉對{item}的追蹤")
                    else:
                        data[str(ctx.channel.id)]['items'].append(item)
                        message = await ctx.send(f"已開啟對{item}的追蹤")
                else:
                    message = await ctx.send(f"已開啟對{item}的追蹤")
                    data[str(ctx.channel.id)] = {
                        "guild": ctx.guild.id,
                        "items": [item]
                    }

                    string = ac_string(data[str(ctx.channel.id)], 
                                    self.__class__.auctions['auctions'],
                                    ctx.channel.id)
                    if string is not None:
                        await message.edit(content=string)
                    else:
                        await message.edit('目前尚無對此物品的價錢')

            if not data[str(ctx.channel.id)]['items']: del data[str(ctx.channel.id)]

            self.__class__.ac_user = data
            write_json(self.__class__.ac_user, auction_item_tracker_itemPATH)
        except:
            traceback.print_exc()


    @tasks.loop(minutes=2)
    async def ac_item_tracker(self):
        try:
            # 每隔5分鐘更新一次bazaar資訊
            self.__class__.auctions = await thread_pool(sb.get_auctions)
            auctions = self.__class__.auctions
            sended = self.__class__.ac_user
            self.initacuser()
            if not sended: return
            if not auctions['success']: return

            items = auctions["auctions"]

            for cnl in sended:
                try:
                    obj = sended[cnl]
                    channel = await self.bot.fetch_channel(int(cnl))

                    string = ac_string(obj, items, int(cnl))
                    if string is not None:
                        await channel.send(content=string)
                except: pass
        except:
            traceback.print_exc()

    @tasks.loop(minutes=5)
    async def bz_item_tracker(self):
        try:
            # 每隔5分鐘更新一次bazaar資訊
            try:
                self.__class__.bazaar = await thread_pool(sb.get_bazaar_data)
            except: ...
            bazaar = self.__class__.bazaar
            self.initbzuser()
            if not bazaar['success']: return

            products = bazaar["products"]
            sended = self.__class__.bz_user

            for guild in sended:
                try:
                    obj = sended[guild]
                    channel = await self.bot.fetch_channel(obj['channelID'])
                    message = await channel.fetch_message(obj['messageID'])
                    guild = self.bot.get_guild(int(guild))
                    embed = create_basic_embed(title=guild.name, 功能='BZ價格追蹤')

                    embed = bz_embed(obj, products, embed)
                    
                    await message.edit(content=None, embed=embed)
                except: pass
        except:
            traceback.print_exc()

async def setup(bot):
    await bot.add_cog(SkyblockItemTracker(bot))