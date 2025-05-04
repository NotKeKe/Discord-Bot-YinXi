import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timedelta
import asyncio
import re
from dotenv import load_dotenv
from cmds.skyblock_commands_foldor import skyblock_commands

# get env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KeJC_ID = int(os.getenv('KeJC_ID'))
embed_link = os.getenv('embed_default_link')
api_key = os.getenv('tmp_hypixel_api_key')

current_directory = os.getcwd()
with open(f"{current_directory}/setting.json", "r") as jfile:
    jdata = json.load(jfile)

sb = skyblock_commands.Skyblock(api_key=api_key)

def remove_color_codes(text): # 此段函式由Copliot生成
    return re.sub(r'§.', '', text)

# 刪除skyblock_events_channels中的指定channel
def remove_events_channel(channelID):
    # load JSON data from file
    with open(f"{current_directory}/cmds/data.json/skyblock_events_channels.json", 'r') as file:
        data = json.load(file)
    
    if str(channelID) not in data:
        return False

    # Removing the key
    del data[str(channelID)]

    # Write the updated json to json file
    with open(f"{current_directory}/cmds/data.json/skyblock_events_channels.json", 'w') as f:
        # write updated data
        json.dump(data,f,indent=4)

    return True

class skyblock_mayor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_embed_task.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    @commands.hybrid_command(aliases=['start_mayor'], name='開始mayor更新', description="Start Update Skyblock's mayor info.")
    @commands.has_permissions(administrator=True)
    async def start_mayor(self, ctx): # started embed
        '''
        [開始mayor更新 或是 [start_mayor
        開始取得skyblock的活動
        需要管理者權限
        '''
        
        # if isinstance(ctx.channel, discord.DMChannel):
        #     await ctx.send("我不在私訊中處理這項指令")
        #     return

        with open(f"{current_directory}/cmds/data.json/skyblock_events_channels.json", "r") as file: # 讀取events_channels
            events_channels = json.load(file)

        if str(ctx.channel.id) not in events_channels: # 如果該頻道沒有傳過mayor訊息
            try:
                mayor, minister, lastUpdated = sb.get_mayor()
                mayor_info = sb.get_mayor_information()
                minister_info = sb.get_minister_information()
                mayor_perks_info = sb.get_mayor_perks_description()
                minister_perk_info = sb.get_minister_perk_description()

                """下三行代碼為Copliot生成"""
                """清除mayor_perks_info中的 '§' 符號"""
                cleaned_mayor_perks_info = [remove_color_codes(info) for info in mayor_perks_info]
                combined_info = [f"{info}\n- {perk}" for info, perk in zip(mayor_info, cleaned_mayor_perks_info)]
                output = "\n".join(combined_info)

                """清除minister_perk_info中的cleaned_mayor_perks_info '§' 符號"""
                if minister is not None:
                    cleaned_minister_perks_info = remove_color_codes(minister_perk_info)

                embed=discord.Embed(title=mayor, description=output, color=discord.Color.blue(), timestamp=datetime.now())
                embed.set_author(name="取得現在的skyblock市長 以及副市長", url=None, icon_url=embed_link)
                # embed.set_thumbnail(url=f'https://mc-heads.net/avatar/{username}')
                if minister is not None:
                    embed.add_field(name=minister, value=f'{minister_info}\n- {cleaned_minister_perks_info}', inline=False)
                embed.set_footer(text=f"訊息更新時間: {lastUpdated}")

                msg = await ctx.send(embed=embed)
            except Exception as exception:
                await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=True)
                return
            
            with open(f"{current_directory}/cmds/data.json/skyblock_events_channels.json", "w") as file:
                events_channels[str(ctx.channel.id)] = {
                    'message_id': msg.id
                }
                json.dump(events_channels, file, indent=4)
        else:
            await ctx.send("此頻道已經有Mayor訊息了")
            return
        #
        await ctx.send("已開始更新 Mayor 訊息")

    @tasks.loop(hours=24)  # 每 24 小時執行一次
    async def update_embed_task(self):
        await self.wait_until_midnight()
        
        with open(f"{current_directory}/cmds/data.json/skyblock_events_channels.json", "r") as file: # 讀取events_channels
            events_channels = json.load(file)
        
        try:
            mayor, minister, lastUpdated = sb.get_mayor()
            mayor_info = sb.get_mayor_information()
            minister_info = sb.get_minister_information()
            mayor_perks_info = sb.get_mayor_perks_description()
            minister_perk_info = sb.get_minister_perk_description()

            """下三行代碼為Copliot生成"""
            """清除mayor_perks_info中的 '§' 符號"""
            cleaned_mayor_perks_info = [remove_color_codes(info) for info in mayor_perks_info]
            combined_info = [f"{info}\n- {perk}" for info, perk in zip(mayor_info, cleaned_mayor_perks_info)]
            output = "\n".join(combined_info)

            """清除minister_perk_info中的cleaned_mayor_perks_info '§' 符號"""
            if minister is not None:
                cleaned_minister_perks_info = remove_color_codes(minister_perk_info)

            embed=discord.Embed(title=mayor, description=output, color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name="取得現在的skyblock市長 以及副市長", url=None, icon_url=embed_link)
            # embed.set_thumbnail(url=f'https://mc-heads.net/avatar/{username}')
            if minister is not None:
                embed.add_field(name=minister, value=f'{minister_info}\n- {cleaned_minister_perks_info}', inline=False)
            embed.set_footer(text=f"訊息更新時間: {lastUpdated}")
        except Exception as e:
            print("Error from skyblock_mayor / tasksloop, update_embed_task: ", e)

        for cnl in events_channels:
            channel = self.bot.get_channel(int(cnl))
            message = await channel.fetch_message(int(events_channels[cnl]['message_id']))        
            await message.edit(embed=embed)

    @commands.hybrid_command(aliases=['stop_mayor'], name='停止mayor更新', description="Stop update Skyblock's mayor info")
    @commands.has_permissions(administrator=True)
    async def stop_mayor(self, ctx):
        '''
        [停止mayor更新 或是 [stop_mayor
        開始取得skyblock的活動
        需要管理者權限
        '''
        try:
            if remove_events_channel(ctx.channel.id) is False: # int
                await ctx.send("此頻道尚未設置mayor訊息")
                return
            await ctx.send("已停止更新 Mayor 訊息")
        except:
            pass

    @update_embed_task.before_loop
    async def before_update_embed_task(self):
        await self.bot.wait_until_ready()

    async def wait_until_midnight(self):
        now = datetime.now()
        target = datetime.combine(now + timedelta(days=1), datetime.min.time())
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

async def setup(bot):
    await bot.add_cog(skyblock_mayor(bot))