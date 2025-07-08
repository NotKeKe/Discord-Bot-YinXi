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
from core.translator import locale_str, load_translated

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

    @discord.ui.select(placeholder=locale_str('select_bot_info_help_command_placeholder'), min_values=1, max_values=1)
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            await interaction.response.defer()
            
            '''i18n'''
            no_desc_str = await interaction.translate('send_bot_info_help_command_no_description')
            error_str = await interaction.translate('send_bot_info_help_view_error')
            ''''''
            
            value = select.values[0]

            cmd = self.bot.get_command(value)
            docstring = cmd.callback.__doc__ or cmd.description or no_desc_str

            embed=discord.Embed(title=value, description=docstring, color=interaction.user.color, timestamp=datetime.now())

            await interaction.message.edit(embed=embed, view=self)
        except Exception as e:
            await interaction.response.send_message(content=error_str.format(e=e), ephemeral=True)

class CogSelectView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__(timeout=300)
        options = [discord.SelectOption(label=filename) for filename in bot.cogs][:25]
        options.sort(key=lambda o: o.label)
        self.children[0].options = options

        self.cogname = None

    @discord.ui.select(
            placeholder = locale_str('select_bot_info_help_cog_placeholder'), 
            min_values=1, 
            max_values=1
            )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select) :
        try:
            '''i18n'''
            cog_no_commands_str = await interaction.translate('send_bot_info_help_cog_no_commands')
            eb_template = await interaction.translate('embed_help_cog')
            eb_data = load_translated(eb_template)[0]
            embed_title_str = eb_data.get('title')
            more_commands_str = await interaction.translate('send_bot_info_help_more_commands_cannot_display')
            error_str = await interaction.translate('send_bot_info_help_view_error')
            ''''''

            # Cog name
            value = select.values[0] 
            self.cogname = value
            
            # 取得該項類別中的指令名稱
            if not self.bot.get_cog(value).get_commands(): await interaction.response.send_message(cog_no_commands_str, ephemeral=True); return
            commands_list = [command.name for command in self.bot.get_cog(value).get_commands()]
            commands_list.sort()

            # 更改Select
            self.children[0].disabled = True

            # Embed
            embed = discord.Embed(title=embed_title_str, color=discord.Color.blue(), timestamp=datetime.now())
            for command in commands_list[:24]:
                embed.add_field(name=f'**{command}**', value=' ', inline=True)
            
            if len(commands_list) > 25:
                await interaction.message.reply(more_commands_str.format(value=value))
                
            # Send Embed and stop self
            await interaction.message.edit(embed=embed, view=self)
            await interaction.response.defer()
            self.stop()
        except Exception as e:
            await interaction.response.send_message(content=error_str.format(e=e), ephemeral=True)

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
    @commands.hybrid_command(name=locale_str("botinfo"), description=locale_str("botinfo"))
    async def botinfo(self, ctx: commands.Context):
        '''為什麼你需要幫助:thinking:'''
        async with ctx.typing():
            '''i18n'''
            eb_data = await ctx.interaction.translate('embed_botinfo_info')
            eb_data = load_translated(eb_data)[0]
            button_label = await ctx.interaction.translate('button_botinfo_command_intro_label')
            ''''''

            cogs_list = ", ".join(sorted([cogname for cogname in self.bot.cogs]))

            embed = discord.Embed(title=' ', description=" ", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=eb_data.get('author'), url=None, icon_url=embed_link)
            
            for field in eb_data.get('fields', []):
                name = field.get('name')
                value = field.get('value', '').format(cogs_list=cogs_list)
                inline = field.get('inline', True)
                embed.add_field(name=name, value=value, inline=inline)

            view = discord.ui.View()
            button = discord.ui.Button(label=button_label)
            async def button_callback(interaction: discord.Interaction):
                await ctx.invoke(self.bot.get_command('help'))
                await interaction.response.defer()
            button.callback = button_callback
            view.add_item(button)

            await ctx.send(embed=embed, view=view)

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

    @commands.hybrid_command(name=locale_str('help'), description=locale_str('help'), aliases=['helping'])
    @app_commands.describe(cog_name=locale_str('help_cog_name'), cmd_name=locale_str('help_cmd_name'))
    @app_commands.autocomplete(cog_name=cogName_autocomplete, cmd_name=cmdName_autocomplete)
    async def help_test(self, ctx: commands.Context, cog_name: str = None, cmd_name: str = None):
        async with ctx.typing():
            '''i18n'''
            no_desc_str = await ctx.interaction.translate('send_bot_info_help_command_no_description')
            ''''''

            if cog_name == cmd_name == None:
                eb_data = await ctx.interaction.translate('embed_help_main')
                eb_data = load_translated(eb_data)[0]
                
                eb = create_basic_embed(color=ctx.author.color, 功能=eb_data.get('author'))
                for field in eb_data.get('fields', []):
                    eb.add_field(name=field.get('name'), value=field.get('value'), inline=False)
                
                return await ctx.send(embed=eb)

            if cmd_name:
                cmd = self.bot.get_command(cmd_name)
                docstring = cmd.callback.__doc__ or cmd.description or no_desc_str
                embed = discord.Embed(title=f'{cmd_name} ({cmd.cog_name})', description=docstring, color=ctx.author.color, timestamp=datetime.now())
            else:
                cmds = self.bot.get_cog(cog_name).get_commands()
                total_cmds = len(cmds)
                
                '''i18n'''
                eb_template = await ctx.interaction.translate('embed_help_cog')
                eb_data = load_translated(eb_template)[0]
                desc_str = eb_data.get('description')
                field_template = eb_data.get('fields')[0]
                ''''''
                
                embed = create_basic_embed(cog_name, desc_str.format(total_cmds=total_cmds), ctx.author.color)

                for c in cmds[:25]:
                    docstring = c.callback.__doc__ or c.description or no_desc_str
                    field_name = field_template.get('name').format(command_name=c.name)
                    field_value = field_template.get('value').format(command_description=docstring)
                    embed.add_field(name=field_name, value=field_value, inline=True)
            await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Bot_Info_and_Help(bot))
