import discord
from discord.ext import commands
from core.classes import Cog_Extension
from datetime import datetime
import os
import json
from dotenv import load_dotenv

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


class Bot_Info_and_Help(Cog_Extension):
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    # bot info
    @commands.hybrid_command(name="bot資訊", description="bot info")
    async def botinfo(self, ctx):
        '''為什麼你需要幫助:thinking:'''
        指令類別 = ", ".join([cogname for cogname in self.bot.cogs])
        embed=discord.Embed(title=' ', description=" ", color=discord.Color.blue(), timestamp=datetime.now())
        embed.set_author(name="Bot資訊", url=None, icon_url=embed_link)
        embed.add_field(name="作者: ", value="克克 KeJC", inline=True)
        embed.add_field(name="已知指令類別", value=指令類別, inline=True)
        embed.add_field(name="Github連結:",value="[NotKeKe](https://github.com/NotKeKe)", inline=True)
        await ctx.send(embed=embed)

    # Commands help
    @commands.hybrid_command(aliases=['helping'], name="指令幫助", description="Commands help")
    async def choose(self, ctx:commands.Context):
        '''為什麼你需要幫助:thinking:'''
        try:
            # 第一個 View (讓使用者選擇cog)
            view = CogSelectView(self.bot)
            message = await ctx.send("Your option", view=view)

            await view.wait()

            # 如果cog name bug的話就return
            # if view.cogname is None: await ctx.send('你選的東西呢:thinking:', ephemeral=True); return

            # 第二個 View (在使用者選擇完cog後 裡面的指令們)
            view2 = CommandSelectView(self.bot, view.cogname)
            await message.edit(view=view2)
        except Exception as exception:
            await ctx.invoke(self.bot.get_command('errorresponse'), 檔案名稱=__name__, 指令名稱=ctx.command.name, exception=exception, user_send=False, ephemeral=False)


        

async def setup(bot):
    await bot.add_cog(Bot_Info_and_Help(bot))