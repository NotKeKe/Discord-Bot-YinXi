import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from datetime import datetime
from typing import Optional
import traceback

from core.classes import Cog_Extension, bot
from core.functions import create_basic_embed
from core.translator import locale_str, load_translated, get_translate

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
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            '''i18n'''
            cog_no_commands_str = await get_translate('send_bot_info_help_cog_no_commands', interaction)
            eb_template = await get_translate('embed_help_cog', interaction)
            eb_data = load_translated(eb_template)[0]
            embed_title_str = eb_data.get('title')
            more_commands_str = await get_translate('send_bot_info_help_more_commands_cannot_display', interaction)
            error_str = await get_translate('send_bot_info_help_view_error', interaction)
            ''''''

            # Cog name
            value = select.values[0] 
            self.cogname = value
            
            # 取得該項類別中的指令名稱
            cog = self.bot.get_cog(value)
            if not cog: return
            if not cog.get_commands(): await interaction.response.send_message(cog_no_commands_str, ephemeral=True); return
            commands_list = [command.name for command in cog.get_commands()]
            commands_list.sort()

            # 更改Select
            self.children[0].disabled = True # type: ignore

            # Embed
            embed = discord.Embed(title=embed_title_str, color=discord.Color.blue(), timestamp=datetime.now())
            for command in commands_list[:24]:
                embed.add_field(name=f'**{command}**', value=' ', inline=True)
            
            if len(commands_list) > 25:
                if interaction.message:
                    await interaction.message.reply(more_commands_str.format(value=value))
                
            # Send Embed and stop self
            if interaction.message:
                await interaction.message.edit(embed=embed, view=self)
            await interaction.response.defer()
            self.stop()
        except Exception as e:
            await interaction.response.send_message(content=error_str.format(e=e), ephemeral=True)

async def cogName_autocomplete(interaction: discord.Interaction, current: str) -> list[Choice[str]]:
    try:
        cogs = list(bot.cogs.keys())

        if current:
            cogs = [c for c in cogs if current.lower().strip() in c.lower()]

        cogs.sort()

        # 限制最多回傳 25 個結果
        return [Choice(name=c, value=c) for c in cogs[:25]]
    except: 
        traceback.print_exc()
        return []
    
async def cmdName_autocomplete(interaction: discord.Interaction, current: str) -> list[Choice[str]]:
    cogName = interaction.namespace.cog_name

    if cogName:
        cog = bot.get_cog(cogName)
        if not cog: return []
        cmds = cog.get_commands()
    else:
        cmds = bot.commands
        
    cmds = [c.name for c in cmds]

    if current:
        cmds = [c for c in cmds if current.lower().strip() in c.lower()]

    cmds.sort()

    return [Choice(name=c, value=c) for c in cmds[:25]]


class BotInfoAndHelp(Cog_Extension):
    
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')

    # bot info
    @commands.hybrid_command(name=locale_str("botinfo"), description=locale_str("botinfo"))
    async def botinfo(self, ctx: commands.Context):
        '''為什麼你需要幫助:thinking:'''
        async with ctx.typing():
            '''i18n'''
            eb_data = await get_translate('embed_botinfo_info', ctx)
            eb_data = load_translated(eb_data)[0]
            button_label = await get_translate('button_botinfo_command_intro_label', ctx)
            ''''''

            cogs_list = ", ".join(sorted([cogname for cogname in self.bot.cogs]))

            embed = discord.Embed(title=' ', description=" ", color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=eb_data.get('author'), url=None)
            
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
            button.callback = button_callback # type: ignore
            view.add_item(button)

            await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name=locale_str('help'), description=locale_str('help'), aliases=['helping'])
    @app_commands.describe(cog_name=locale_str('help_cog_name'), cmd_name=locale_str('help_cmd_name'))
    @app_commands.autocomplete(cog_name=cogName_autocomplete, cmd_name=cmdName_autocomplete)
    async def help_test(self, ctx: commands.Context, cog_name: Optional[str] = None, cmd_name: Optional[str] = None):
        async with ctx.typing():
            '''i18n'''
            no_desc_str = await get_translate('send_bot_info_help_command_no_description', ctx)
            ''''''

            if cog_name == cmd_name == None:
                eb_data = await get_translate('embed_help_main', ctx)
                eb_data = load_translated(eb_data)[0]
                
                eb = create_basic_embed(color=ctx.author.color, 功能=eb_data.get('author'))
                for field in eb_data.get('fields', []):
                    eb.add_field(name=field.get('name'), value=field.get('value'), inline=False)
                
                return await ctx.send(embed=eb)

            if cmd_name:
                cmd = self.bot.get_command(cmd_name)
                if not cmd:
                    return await ctx.send(no_desc_str, ephemeral=True)

                docstring = cmd.callback.__doc__ or cmd.description or no_desc_str
                embed = discord.Embed(title=f'{cmd_name} ({cmd.cog_name})', description=docstring, color=ctx.author.color, timestamp=datetime.now())
            else:
                if not cog_name:
                    return await ctx.send(no_desc_str, ephemeral=True)
                cog = self.bot.get_cog(cog_name)
                if not cog:
                    return await ctx.send(no_desc_str, ephemeral=True)
                cmds = cog.get_commands()
                total_cmds = len(cmds)
                
                '''i18n'''
                eb_template = await get_translate('embed_help_cog', ctx)
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
    await bot.add_cog(BotInfoAndHelp(bot))
