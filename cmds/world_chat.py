import discord
from discord import app_commands
from discord.ext import commands
import time
from datetime import datetime, timedelta
import traceback

from core.classes import Cog_Extension
from core.functions import create_basic_embed, read_json, write_json
from core.translator import locale_str, load_translated

path = './cmds/data.json/world_channels.json'

bad_image_channel = 1338022304306954251

class WorldChat(Cog_Extension):
    channels = None

    @classmethod
    def initchannel(cls):
        if cls.channels is None:
            cls.channels = read_json(path)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        self.__class__.channels = read_json(path)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        '''
        如果使用者發送圖片，就不會再發送Embed
        '''
    
        if msg.author.bot: return
        self.initchannel()
        channels = self.__class__.channels
        if msg.channel.id not in channels['channels']: return

        # 使用者圖片
        attachments = [
            attachment.url
            for attachment in msg.attachments
            if attachment.content_type and attachment.content_type.startswith('image/')
        ]

        eb = create_basic_embed(color=msg.author.color)
        
        for cnl in channels['channels']:
            try:
                if msg.channel.id == cnl: continue
                channel = self.bot.get_channel(cnl)

                if attachments:
                    '''i18n'''
                    locale = channel.guild.preferred_locale.value if channel.guild else 'zh-TW'
                    translations = self.bot.tree.translator.translations.get(locale, self.bot.tree.translator.translations.get('zh-TW', {}))
                    eb_template_str = translations.get('components', {}).get('embed_world_chat', '[{}]')
                    eb_data = load_translated(eb_template_str)[0]
                    field = eb_data['field'][0]
                    field_name_template = field['name']
                    field_value_template = field.get('value', '')
                    ''''''
                    field_name = field_name_template.format(author_name=msg.author.global_name)
                    if attachments:
                        eb.add_field(name=field_name, value=field_value_template.format(count=len(attachments)), inline=True)
                        await channel.send(embed=eb)
                        for a in attachments:
                            await channel.send(a)
                    else:
                        eb.add_field(name=field_name, value=msg.content, inline=True)
                        await channel.send(embed=eb)
            except TypeError:
                ...
            except Exception as e:
                print(f'An error accured at world_chat: {e}')

        user_said = msg.content if not attachments else f"{f'{msg.content} | 'if msg.content else ''}{' '.join(attachments)}"
            
        time = datetime.now()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        channels['History'].append(f"{now} | {msg.author.global_name}: {user_said}")

        self.__class__.channels = channels
        write_json(channels, path)

    @commands.hybrid_command(name=locale_str('world_chat'), description=locale_str('world_chat'))
    @app_commands.describe(是否取消=locale_str('world_chat_cancel'))
    @app_commands.choices(
        是否取消 = [
            discord.app_commands.Choice(name=locale_str('choice_world_chat_cancel_no'), value=1),
            discord.app_commands.Choice(name=locale_str('choice_world_chat_cancel_yes'), value=2)
        ]
    )
    @commands.has_permissions(administrator=True)
    async def setworldchannel(self, ctx: commands.Context, 是否取消: discord.app_commands.Choice[int] = None):
        self.initchannel()
        channels = self.__class__.channels

        if 是否取消 is not None:
            取消 = False if 是否取消.value==1 else True
        else: 取消 = False

        channelID = ctx.channel.id

        if 取消:
            if channelID not in channels['channels']: await ctx.send(await ctx.interaction.translate('send_world_chat_not_world_channel'), ephemeral=True); return
            channels['channels'].remove(channelID)
            await ctx.send(await ctx.interaction.translate('send_world_chat_cancelled'))
        else:
            if channelID in channels['channels']: await ctx.send(await ctx.interaction.translate('send_world_chat_already_set')); return
            channels['channels'].append(channelID)
            await ctx.send(await ctx.interaction.translate('send_world_chat_set_success'))

        self.__class__.channels = channels
        write_json(channels, path)

    @commands.hybrid_command(name=locale_str('report_bad_image'), description=locale_str('report_bad_image'))
    @app_commands.describe(author=locale_str('report_bad_image_author'), 舉報原因=locale_str('report_bad_image_reason'))
    async def report(self, ctx: commands.Context, author: str, 舉報原因: str):
        channel = await self.bot.fetch_channel(bad_image_channel)
        now = time.strftime("%Y/%m/%d %H:%M:%S")
        '''i18n'''
        log_message_template = await self.bot.tree.translator.translate(locale_str('send_report_bad_image_log'), channel.guild.preferred_locale, None)
        ''''''
        log_message = log_message_template.format(
            guild_name=ctx.guild.name,
            reporter_name=ctx.author.global_name,
            now=now,
            author=author,
            reason=舉報原因,
            reporter_id=ctx.author.id
        )
        await channel.send(log_message)
        await ctx.send((await ctx.interaction.translate('send_report_bad_image_success')).format(author=author))


async def setup(bot):
    await bot.add_cog(WorldChat(bot))