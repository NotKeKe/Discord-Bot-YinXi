import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from datetime import datetime
import os
import json
from dotenv import load_dotenv
import typing
import traceback

from core.classes import Cog_Extension, bot
from core.functions import create_basic_embed

# get env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KeJC_ID = int(os.getenv('KeJC_ID'))
embed_link = os.getenv('embed_default_link')

with open('setting.json', "r") as f:
    jdata = json.load(f)

class CommandSelectView(discord.ui.View):
    def __init__(self, bot: commands.Bot, cogname: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.cogname = cogname
        if not cogname: return
        options = [discord.SelectOption(label=command.name) for command in bot.get_cog(cogname).get_commands()]
        self.children[0].options = options[:25]

    @discord.ui.select(placeholder='選擇一個command', min_values=1, max_values=1)
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            await interaction.response.defer()
            
            value = select.values[0]

            cmd = self.bot.get_command(value)
            docstring = cmd.callback.__doc__ or cmd.description or "該指令沒有敘述"

            embed=discord.Embed(title=value, description=docstring, color=interaction.user.color, timestamp=datetime.now())

            await interaction.message.edit(embed=embed, view=self)
        except Exception as e:
            await interaction.response.send_message(content=f'This command accurs a bug from CommandSelectView「{e}」 , pls report this bug to me.', ephemeral=True)

class CogSelectView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__(timeout=300)
        options = [discord.SelectOption(label=filename) for filename in bot.cogs][:25]
        options.sort(key=lambda o: o.label)
        self.children[0].options = options

        self.cogname = None

    @discord.ui.select(
            placeholder = "選擇", 
            min_values=1, 
            max_values=1
            )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select) :
        try:
            # Cog name
            value = select.values[0] 
            self.cogname = value
            
            # 取得該項類別中的指令名稱
            if not self.bot.get_cog(value).get_commands(): await interaction.response.send_message('該類別沒有指令', ephemeral=True); return
            commands_list = [command.name for command in self.bot.get_cog(value).get_commands()]
            commands_list.sort()

            # 更改Select
            self.children[0].disabled = True

            # Embed
            embed = discord.Embed(title='指令列表', color=discord.Color.blue(), timestamp=datetime.now())
            for command in commands_list[:24]:
                embed.add_field(name=f'**{command}**', value=' ')
            
            if len(commands_list) > 25:
                await interaction.message.reply(f'尚有其他從{value}的指令無法顯示')
                
            # Send Embed and stop self
            await interaction.message.edit(embed=embed, view=self)
            await interaction.response.defer()
            self.stop()
        except Exception as e:
            await interaction.response.send_message(content=f'This command accurs a bug from CogSelectView 「{e}」 , pls report this bug to me.', ephemeral=True)

async def cogName_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[Choice[str]]:
    try:
        cogs = list(bot.cogs.keys())

        if current:
            cogs = [c for c in cogs if current.lower().strip() in c.lower()]

        cogs.sort()

        # 限制最多回傳 25 個結果
        return [Choice(name=c, value=c) for c in cogs[:25]]
    except: traceback.print_exc()
    
async def cmdName_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[Choice[str]]:
    cogName = interaction.namespace.cog_name

    if cogName:
        cmds = bot.get_cog(cogName).get_commands()
    else:
        cmds = bot.commands
        
    cmds = [c.name for c in cmds]

    if current:
        cmds = [c for c in cmds if current.lower().strip() in c.lower()]

    cmds.sort()

    return [Choice(name=c, value=c) for c in cmds[:25]]


class Bot_Info_and_Help(Cog_Extension):
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    # bot info
    @commands.hybrid_command(name="機器人資訊", description="Bot info")
    async def botinfo(self, ctx):
        '''為什麼你需要幫助:thinking:'''
        指令類別 = ", ".join(sorted([cogname for cogname in self.bot.cogs]))
        embed=discord.Embed(title=' ', description=" ", color=discord.Color.blue(), timestamp=datetime.now())
        embed.set_author(name="Bot資訊", url=None, icon_url=embed_link)
        embed.add_field(name='🤖 **名字**', value='音汐')
        embed.add_field(name="👨 **作者**", value="克克 KeJC", inline=True)
        embed.add_field(name="⚙️ **已知指令類別**", value=指令類別, inline=True)
        embed.add_field(name="🐙 **我的Github連結**",value="[NotKeKe](https://github.com/NotKeKe)", inline=True)
        embed.add_field(name='🔗 **此專案連結**', value=f'[音汐](https://github.com/NotKeKe/Discord-Bot-YinXi)')
        await ctx.send(embed=embed)

    # Commands help
    # @commands.hybrid_command(aliases=['helping'], name="指令幫助", description="Commands help")
    # async def choose(self, ctx:commands.Context):
    #     '''為什麼你需要幫助:thinking:'''
    #     try:
    #         # 第一個 View (讓使用者選擇cog)
    #         view = CogSelectView(self.bot)
    #         message = await ctx.send("Your option", view=view)

    #         await view.wait()

    #         # 如果cog name bug的話就return
    #         # if view.cogname is None: await ctx.send('你選的東西呢:thinking:', ephemeral=True); return

    #         # 第二個 View (在使用者選擇完cog後 裡面的指令們)
    #         view2 = CommandSelectView(self.bot, view.cogname)
    #         await message.edit(view=view2)
    #     except Exception as exception:
    #         await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)

    @commands.hybrid_command(name='help', description="指令幫助", aliases=['helping'])
    @app_commands.autocomplete(cog_name=cogName_autocomplete, cmd_name=cmdName_autocomplete)
    async def help_test(self, ctx: commands.Context, cog_name: str = None, cmd_name: str = None):
        if cog_name == cmd_name == None:
            eb = create_basic_embed(color=ctx.author.color, 功能='指令幫助')
            eb.add_field(
                name='**特點**', 
                value=
'''
✅ 與 AI 結合的 Discord Bot
✅ 提供許多實用小功能
''', 
                inline=False
            )
            eb.add_field(
                name='**使用方式**', 
                value=
'''
**🌟 AI 功能**
> `/chat` —— 與 AI 交流
> `/ai頻道` —— 設定 AI 頻道，**無需輸入指令**即可對話
> `/圖片生成` —— 使用 **AI 生成圖片** (cogview-3-flash)
**👥 伺服器功能**
> `/伺服器資訊` —— 快速取得這個**伺服器的資訊**
> `/世界頻道` —— 與其他設定該功能的使用者**跨伺服器**交流
> `/數數頻道` —— 與伺服器成員玩**數字接力**
> `/取得伺服器預設頻道` —— 如名
> `/avatar` —— 趁別人不注意的時候拿走別人的**頭像**w
**🔧 實用小功能**
> `[nasa` —— 獲取 NASA 提供的**每日圖片**
> `[cat` —— 獲得每日的**貓貓知識**🐱
> `/qrcode生成器` —— 轉換連結為 **QR Code**
> `/keep` —— 設定好時間後，會在同個頻道**提醒**你要做什麼!
> `/設定yt通知` —— 通知你追蹤的**YouTuber**更新了! (如果在youtuber欄位不輸入的話就會取消)
**🤫 一般人用不到的功能**
> `/convert_timestamp` 將**timestamp**轉換為可讀的時間
''', 
                inline=False
            )
            eb.add_field(
                name='其他:', 
                value='> 還有更多功能等著你去探索!',
                inline=False
            )
            return await ctx.send(embed=eb)

        if cmd_name:
            cmd = self.bot.get_command(cmd_name)
            docstring = cmd.callback.__doc__ or cmd.description or "該指令沒有敘述"

            embed = discord.Embed(title=f'{cmd_name} ({cmd.cog_name})', description=docstring, color=ctx.author.color, timestamp=datetime.now())
        else:
            cmds = self.bot.get_cog(cog_name).get_commands()
            total_cmds = len(cmds)
            embed = create_basic_embed(cog_name, f'指令數量: `{total_cmds}`', ctx.author.color)

            for c in cmds[:25]:
                docstring = c.callback.__doc__ or c.description or "該指令沒有敘述"
                embed.add_field(name=c.name, value=docstring)
        await ctx.send(embed=embed)


        

async def setup(bot):
    await bot.add_cog(Bot_Info_and_Help(bot))
