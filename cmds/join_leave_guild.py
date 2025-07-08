import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import typing
from typing import Optional, Union
import traceback

from core.classes import Cog_Extension
from core.functions import embed_link, read_json, write_json, create_basic_embed
from core.translator import locale_str, load_translated

PATH = './cmds/data.json/guild_join.json'

example = {
    'ctx.guild.id': {'joinChannel': 'ctx.guild.system_channel.id', 'leaveChannel': 'ctx.channel.id'}
}

async def channel_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    try:
        channels = interaction.guild.channels
        channels = [cn.name for cn in channels]

        if current:
            channels = [channel for channel in channels if current.lower().strip() in channel.lower()]

        return [app_commands.Choice(name=channel, value=channel) for channel in channels][:25]
    except: traceback.print_exc()

class OnJoinLeave(Cog_Extension):
    data = None

    @classmethod
    def init_data(cls):
        if cls.data is None:
            cls.data = read_json(PATH)

    @classmethod
    def write_data(cls, data=None):
        if data is not None:
            cls.data = data
        write_json(cls.data, PATH)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.init_data()

    #自己加入
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            channel = guild.system_channel if guild.system_channel.permissions_for(guild.me).send_messages else (channel for channel in guild.text_channels if channel.permissions_for(guild.me).send_messages)
            if channel is None: return
            '''i18n'''
            locale = guild.preferred_locale.value if guild.preferred_locale else 'zh-TW'
            translations = self.bot.tree.translator.translations.get(locale, self.bot.tree.translator.translations.get('zh-TW', {}))
            eb_template_str = translations.get('components', {}).get('embed_on_guild_join', '[{}]')
            eb_data = load_translated(eb_template_str)[0]
            ''''''
            
            embed=discord.Embed(title=eb_data.get('title'),  color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=eb_data.get('author'), icon_url=embed_link)
            for field in eb_data.get('fields', []):
                embed.add_field(name=field.get('name'), value=field.get('value'), inline=field.get('inline', False))
            await channel.send(embed=embed)
        except Exception as exception:
            print(f"Error: {exception}")

    #成員加入
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            self.init_data()
            data = self.__class__.data
            guildID = str(member.guild.id)
            if guildID not in data: return

            channelID = data[guildID]['joinChannel']
            chn = await self.bot.fetch_channel(channelID)

            if chn:
                locale = chn.guild.preferred_locale.value if chn.guild else 'zh-TW'
                translations = self.bot.tree.translator.translations.get(locale, self.bot.tree.translator.translations.get('zh-TW', {}))
                send_str = translations.get('components', {}).get('send_on_member_join', '{member_name}')
                await chn.send(send_str.format(member_name=member.name))
        except: traceback.print_exc()

    #成員離開
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            self.init_data()
            data = self.__class__.data
            guildID = str(member.guild.id)
            if guildID not in data: return

            channelID = data[guildID]['leaveChannel']
            chn = await self.bot.fetch_channel(channelID)

            if chn:
                locale = chn.guild.preferred_locale.value if chn.guild else 'zh-TW'
                translations = self.bot.tree.translator.translations.get(locale, self.bot.tree.translator.translations.get('zh-TW', {}))
                send_str = translations.get('components', {}).get('send_on_member_remove', '{member_name}')
                await chn.send(send_str.format(member_name=member.name))
        except: traceback.print_exc()

    @commands.hybrid_command(name=locale_str('join_leave_message'), description=locale_str('join_leave_message'))
    @app_commands.describe(join_channel=locale_str('join_leave_message_join_channel'), leave_channel=locale_str('join_leave_message_leave_channel'))
    @commands.has_permissions(administrator=True)
    @app_commands.autocomplete(join_channel=channel_autocomplete, leave_channel=channel_autocomplete)
    async def set_join_leave_message(self, ctx: commands.Context, join_channel: str=None, leave_channel: str=None):
        self.init_data()
        data = self.__class__.data
        guildID = str(ctx.guild.id)

        if guildID in data: 
            view = discord.ui.View()
            check_button = discord.ui.Button(label='✅')
            refuse_button = discord.ui.Button(label='❌')

            def disabled_button():
                check_button.disabled = True
                refuse_button.disabled = True
                return

            async def check_callback(interation: discord.Interaction):
                await interation.response.send_message(await interation.translate('send_join_leave_message_cancel_success'), ephemeral=True)
                disabled_button()
            async def refuse_callback(interation: discord.Interaction):
                del data[guildID]
                await interation.response.send_message((await interation.translate('send_join_leave_message_delete_success')).format(guild_name=interation.guild.name))
                self.write_data(data)
                disabled_button()
            
            check_button.callback = check_callback
            refuse_button.callback = refuse_callback

            view.add_item(check_button)
            view.add_item(refuse_button)

            '''i18n'''
            eb_template = await ctx.interaction.translate('embed_join_leave_message_confirm_delete')
            eb_data = load_translated(eb_template)[0]
            ''''''
            embed = create_basic_embed(eb_data.get('title'), eb_data.get('description'), time=False)

            await ctx.send(embed=embed, view=view)
        else:
            if join_channel == leave_channel == ctx.guild.system_channel == None: return await ctx.send(await ctx.interaction.translate('send_join_leave_message_no_channel_input'))
            joinCh = None
            leaveCh = None
            if not join_channel: joinCh = ctx.guild.system_channel
            if not leave_channel: leaveCh = ctx.guild.system_channel

            if not (joinCh == leaveCh == ctx.guild.system_channel):
                for channel in ctx.guild.channels:
                    if not channel.name: continue
                    if channel.name == join_channel:
                        joinCh = channel
                    if channel.name == leave_channel:
                        leaveCh = channel
                    if type(join_channel) == type(leave_channel) == discord.channel.TextChannel:
                        break
            if not joinCh:
                return await ctx.send(await ctx.interaction.translate('send_join_leave_message_no_join_channel'))
            elif not leaveCh:
                return await ctx.send(await ctx.interaction.translate('send_join_leave_message_no_leave_channel'))
            
            if not joinCh.permissions_for(joinCh.guild.me).send_messages: return await ctx.send(await ctx.interaction.translate('send_join_leave_message_no_permission'))
            if not leaveCh.permissions_for(leaveCh.guild.me).send_messages: return await ctx.send(await ctx.interaction.translate('send_join_leave_message_no_permission'))

            data[guildID] = {'joinChannel': joinCh.id, 'leaveChannel': leaveCh.id}
            self.write_data(data)
            '''i18n'''
            eb_template = await ctx.interaction.translate('embed_join_leave_message_set_success')
            eb_data = load_translated(eb_template)[0]
            title = eb_data.get('title').format(guild_name=ctx.guild.name)
            description = eb_data.get('description').format(join_channel_name=joinCh.name, leave_channel_name=leaveCh.name)
            ''''''
            embed = create_basic_embed(title, description)
            await ctx.send(embed=embed)

    @commands.hybrid_command(name=locale_str('delete_spam_messages'), description=locale_str('delete_spam_messages'))
    @app_commands.describe(hours=locale_str('delete_spam_messages_hours'), user=locale_str('delete_spam_messages_user'))
    @commands.has_permissions(administrator=True)
    async def delete_spam_messages(self, ctx: commands.Context, hours: int, user: discord.User):
        async with ctx.typing(ephemeral=True):
            try:
                if not ctx.guild.me.guild_permissions.manage_messages: return await ctx.send(await ctx.interaction.translate('send_delete_spam_messages_no_permission'), ephemeral=True)

                count = 0
                cant_delete_m: list[discord.Message] = []
                cant_delete_c = []
                now = datetime.now()
                time = now - timedelta(hours=hours)

                if isinstance(user, str):
                    userID = int(user)
                else:
                    userID = user.id

                for c in ctx.guild.text_channels:
                    if not hasattr(c, 'history') or not c.permissions_for(ctx.guild.me).view_channel: continue
                    if not c.permissions_for(ctx.guild.me).read_message_history:
                        cant_delete_c.append(c)
                        continue
                    async for m in c.history(after=time):
                        if m.author.id == userID: 
                            if not c.permissions_for(ctx.guild.me).manage_messages:
                                cant_delete_m.append(m)
                                continue

                            await m.delete()
                            count += 1

                '''i18n'''
                eb_template = await ctx.interaction.translate('embed_delete_spam_messages')
                eb_data = load_translated(eb_template)[0]
                title = eb_data.get('title')
                fields = eb_data.get('fields')
                count_field_name = fields[0].get('name')
                cant_delete_msg_field_name = fields[1].get('name')
                cant_delete_msg_field_value = fields[1].get('value')
                cant_delete_channel_field_name = fields[2].get('name')
                cant_delete_channel_field_value = fields[2].get('value')
                ''''''

                embed = create_basic_embed(功能=title, color=discord.Color.red())
                embed.add_field(name=count_field_name, value=f'`{count}`', inline=False)
                embed.set_footer(text=f'{userID=}')
                if cant_delete_m:
                    embed.add_field(
                        name=cant_delete_msg_field_name,
                        value=cant_delete_msg_field_value.format(
                            count=len(cant_delete_m),
                            messages='\n'.join([f"- Content: {m.content}; Time: {m.created_at.strftime('%Y-%m-%d %H:%M:%S')}" for m in cant_delete_m])
                        ),
                        inline=False
                    )
                if cant_delete_c:
                    embed.add_field(
                        name=cant_delete_channel_field_name,
                        value=cant_delete_channel_field_value.format(
                            count=len(cant_delete_c),
                            channels='\n'.join([c.name for c in cant_delete_c])
                        ),
                        inline=False
                    )

                await ctx.send(embed=embed)
            except: traceback.print_exc()

async def setup(bot):
    await bot.add_cog(OnJoinLeave(bot))