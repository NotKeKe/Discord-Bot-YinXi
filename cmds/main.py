import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
import json
from datetime import datetime
import random
import os
from dotenv import load_dotenv
import uuid
import asyncio
import aiosqlite
import io

from cmds.AIsTwo.others.func import image_read
from cmds.AIsTwo.utils import image_url_to_base64

from core.classes import Cog_Extension
from core.functions import thread_pool, admins, KeJCID, write_json, create_basic_embed, UnixToReadable, download_image, UnixNow, testing_guildID, image_to_base64
from core.translator import locale_str, load_translated

# get env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
KeJC_ID = int(os.getenv('KeJC_ID'))
embed_link = os.getenv('embed_default_link')


#setting.json
with open('setting.json', 'r', encoding = 'utf8') as jfile:
        #(檔名，mode=read)
    jdata = json.load(jfile)


class Main(Cog_Extension):

    async def cog_load(self):
        print(f'已載入「{__name__}」')

    #Owner ID回覆
    @commands.hybrid_command(name=locale_str("owner_id"), description=locale_str("owner_id"), aliases=['ownerid'])
    async def ownerid(self, ctx: commands.Context):
        '''
        [管理員id回覆
        會傳個訊息跟你說這群的群主名字 跟他的ID
        '''
        async with ctx.typing():
            '''i18n'''
            eb_template = await ctx.interaction.translate('embed_owner_id')
            eb_data = load_translated(eb_template)[0]
            author_name = eb_data.get('author')
            title = eb_data.get('title')
            field_name = eb_data.get('field').get('name')
            ''''''
            guild_owner = await self.bot.fetch_user(int(ctx.guild.owner_id))
            embed=discord.Embed(title=title.format(owner_mention=guild_owner.mention), color=discord.Color.blue(), timestamp=datetime.now())
            embed.set_author(name=author_name, icon_url=embed_link)
            embed.add_field(name=field_name, value=ctx.guild.owner_id, inline=False)
            await ctx.send(embed=embed)

    #取得延遲
    @commands.hybrid_command(name=locale_str("ping"), description=locale_str("ping"))
    async def ping(self, ctx: commands.Context):
        '''
        [ping
        傳送延遲(我也不知道這延遲是怎麼來的)
        '''
        async with ctx.typing():
            '''i18n'''
            eb_template = await ctx.interaction.translate('embed_ping')
            eb_data = load_translated(eb_template)[0]
            title = eb_data.get('title')
            description = eb_data.get('description').format(latency=round(self.bot.latency*1000))
            ''''''
            embed = discord.Embed(
                color=discord.Color.red(),
                title=title,
                description=description,
                timestamp=datetime.now()
            )
            await ctx.send(embed = embed)

    #重複我說的話
    @commands.hybrid_command(name=locale_str("repeat"), description=locale_str("repeat"))
    @app_commands.describe(arg=locale_str('repeat_text'))
    async def test(self, ctx: commands.Context, *, arg: str):
        '''
        [重複你說的話 arg(然後打你要的字)
        沒啥用的功能，如果你想要bot重複你說的話就用吧
        '''
        await ctx.send(arg)

    #我在哪
    @commands.hybrid_command(name=locale_str("where_am_i"), description=locale_str("where_am_i"))
    async def whereAmI(self, ctx: commands.Context):
        '''
        [我在哪裡
        說出你在哪 會有伺服器名稱跟頻道的名稱
        '''
        async with ctx.typing():
            '''i18n'''
            eb_template = await ctx.interaction.translate('embed_where_am_i')
            eb_data = load_translated(eb_template)[0]
            title = eb_data.get('title')
            description = eb_data.get('description').format(guild_name=ctx.guild.name, channel_mention=ctx.channel.mention)
            ''''''
            embed = discord.Embed(
                color=discord.Color.blue(),
                title=title,
                description=description,
                timestamp=datetime.now()
            )
            await ctx.send(embed=embed)

    #回傳使用者頭貼
    @commands.hybrid_command(name=locale_str("avatar"), description=locale_str("avatar"))
    @app_commands.describe(member=locale_str('avatar_member'))
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        '''
        [avatar member
        member的話能tag人，或是都沒輸入的話就回傳你自己的頭貼
        '''
        async with ctx.typing():
            if member is None:
                member = ctx.author

            try:
                embed=discord.Embed(title=member, color=member.color).set_image(url=member.avatar.url)
            except:
                await ctx.send((await ctx.interaction.translate('send_avatar_no_avatar')).format(member_name=member.display_name))
                return
            
            await ctx.send(embed=embed)
    
    #獲得該guild的system channel
    @commands.hybrid_command(name=locale_str('get_system_channel'), description=locale_str('get_system_channel'))
    async def systemChannel(self, ctx: commands.Context):
        async with ctx.typing():
            channel = ctx.guild.system_channel
            if channel is None:
                await ctx.send(await ctx.interaction.translate('send_get_system_channel_no_system_channel'))
            else:
                await ctx.send(channel.mention)

    @commands.command(name='add_admin')
    async def add_admin(self, ctx: commands.Context, userID: int = None):
        if str(ctx.author.id) != KeJCID: return

        global admins
        if not userID: userID = ctx.author.id
        userName = (await self.bot.fetch_user(userID)).global_name

        if userID in admins: return await ctx.send(f'{userName} ({userID=}) 已經是管理員了', ephemeral=True)
        admins.append(userID)
        data = {'admins': admins}
        write_json(data, './cmds/data.json/admins.json')
        await ctx.send(f'已將 {userName} ({userID=}) 加入管理員', ephemeral=True)

    @commands.hybrid_command(name=locale_str('server_info'), description=locale_str('server_info'))
    async def get_server_info(self, ctx: commands.Context):
        async with ctx.typing():
            if not ctx.guild: return await ctx.send(await ctx.interaction.translate('send_server_info_not_in_guild'))

            name = ctx.guild.name
            id = ctx.guild.id
            total_member_counts = len(ctx.guild.members)
            true_member_counts = len([m for m in ctx.guild.members if not m.bot])
            bot_counts = total_member_counts - true_member_counts
            channel_counts = len(ctx.guild.channels)
            owner = ctx.guild.owner.global_name
            ownerID = ctx.guild.owner.id
            online_member_counts = len([m for m in ctx.guild.members if m.status not in (discord.Status.offline, discord.Status.invisible)])
            system_channel = ctx.guild.system_channel or 'None'

            '''i18n'''
            eb_template = await ctx.interaction.translate('embed_server_info')
            eb_data = load_translated(eb_template)[0]
            title = eb_data.get('title').format(guild_name=name)
            fields = eb_data.get('fields')
            ''''''
            eb = create_basic_embed(title, color=ctx.author.color)
            
            values = [name, id, total_member_counts, true_member_counts, bot_counts, channel_counts, owner, ownerID, online_member_counts, system_channel.mention]
            for i, field in enumerate(fields):
                eb.add_field(name=field.get('name'), value=values[i])
            await ctx.send(embed=eb)

    @commands.hybrid_command(name=locale_str('convert_timestamp'), description=locale_str('convert_timestamp'))
    @app_commands.describe(unix_second=locale_str('convert_timestamp_timestamp'))
    async def unixSecondToReadalbe(self, ctx: commands.Context, unix_second: str):
        async with ctx.typing():
            try: unix_second = float(unix_second)
            except: return await ctx.send(await ctx.interaction.translate('send_convert_timestamp_invalid_number'))
            readable = UnixToReadable(unix_second)
            await ctx.send(readable)

    @commands.hybrid_command(name=locale_str('tw_high_school_score_calculator'), description=locale_str('tw_high_school_score_calculator'))
    @app_commands.guilds(discord.Object(testing_guildID))
    @app_commands.describe(image=locale_str('tw_high_school_score_calculator_image'), prompt=locale_str('tw_high_school_score_calculator_prompt'))
    async def high_school_totalScore_calculate(self, ctx: commands.Context, 國文: float = 0.0, 英文: float = 0.0, 數學: float = 0.0, 化學: float = 0.0, 生物: float = 0.0, 物理: float = 0.0, 歷史: float = 0.0, 地理: float = 0.0, 公民: float = 0.0, 體育: float = 0.0, image: discord.Attachment = None, prompt: str = None):
        async with ctx.typing():
            '''i18n'''
            eb_template = await ctx.interaction.translate('embed_tw_high_school_score_calculator')
            eb_data = load_translated(eb_template)[0]
            title = eb_data.get('title')
            fields = eb_data.get('fields')
            weighted_field_name = fields[0].get('name')
            unweighted_field_name = fields[1].get('name')
            ai_response_field_name = fields[2].get('name')
            ''''''
            eb = create_basic_embed(功能=title, color=ctx.author.color, time=False)

            if not image:
                weight_total = (國文 + 數學 + 英文) * 4 + (化學 + 生物 + 物理 + 歷史 + 地理 + 公民 + 體育) * 2
                total = 國文 + 數學 + 英文 + 化學 + 生物 + 物理 + 歷史 + 地理 + 公民 + 體育
                eb.add_field(name=weighted_field_name, value=f'`{weight_total}`')
                eb.add_field(name=unweighted_field_name, value=f'`{total}`')
                await ctx.send(embed=eb)
            else:
                if not prompt: return await ctx.send(await ctx.interaction.translate('send_tw_high_school_score_calculator_no_prompt'), ephemeral=True)
                os.makedirs('./data/upload', exist_ok=True)
                path = f'./data/upload/{ctx.author.id}_{UnixNow()}_{uuid.uuid4()}.jpg'
                absolute_path = os.path.abspath(path)
                final_url = f'https://yinxi.keketw.dpdns.org/api/image/?path={absolute_path}'
                await ctx.send(final_url)

                await download_image(image.url, path=path)

                result = await thread_pool(image_read, prompt, final_url)
                eb.add_field(name=ai_response_field_name, value=result)
                eb.set_footer(text='Powered by glm-4v-flash')
                await ctx.send(embed=eb)

                await asyncio.sleep(300)
                os.remove(path)

    @commands.hybrid_command(name=locale_str("random_number"), description=locale_str("random_number"))
    @app_commands.describe(range1=locale_str('random_number_start'), range2=locale_str('random_number_end'), times=locale_str('random_number_times'))
    async def random_number(self, ctx: commands.Context, range1: int, range2: int, times:int = None):
        async with ctx.typing():
            if times is None:
                times = 1

            if range1 > range2: # 如果使用者輸入將起始跟終止順序寫反了
                range1, range2 = range2, range1

            if times > range2-range1+1:
                await ctx.send((await ctx.interaction.translate('send_random_number_too_many')).format(range1=range1, range2=range2, times=times))
                return

            def for_loop(times, range1, range2):
                result = []
                for _ in range(times):
                    while True:
                        num = random.randint(range1, range2)
                        if num not in result:
                            result.append(num)
                            break
                return result
            
            result = await thread_pool(for_loop, times, range1, range2)

            resultStr = ', '.join(map(str, result))
            await ctx.send(resultStr)

    @commands.hybrid_command(name=locale_str('lang'), description=locale_str('lang'))
    @app_commands.describe(lang=locale_str('lang_lang'))
    @app_commands.choices(lang=[app_commands.Choice(name=l, value=l) for l in ('en-US', 'zh-TW', 'zh-CN')])
    async def _lang(self, ctx: commands.Context, lang: str):
        async with ctx.typing():
            if lang not in ('en-US', 'zh-TW', 'zh-CN'):
                return await ctx.send(await ctx.interaction.translate('send_lang_invalid_lang'))
            
            async with aiosqlite.connect('./data/user_lang.db') as db:
                cursor = await db.execute('SELECT lang FROM users WHERE user_id = ?', (ctx.author.id,))
                result = await cursor.fetchone()
                if result: pre = result[0]
                else: pre = None
                if pre == lang: return await ctx.send((await ctx.interaction.translate('send_lang_same_lang')).format(lang=lang))

                await db.execute('''INSERT INTO users (user_id, lang)
                                    VALUES (?, ?)
                                    ON CONFLICT(user_id) DO UPDATE SET
                                        lang = excluded.lang
                                ''', (ctx.author.id, lang))
                await db.commit()

            await ctx.send((await ctx.interaction.translate('send_lang_success')).format(lang=lang), ephemeral=True)

    @commands.hybrid_command(name=locale_str('image_to_base64'), description=locale_str('image_to_base64'))
    async def _to_base64(self, ctx: commands.Context, image_url: str):
        async with ctx.typing():
            base64_str = await image_to_base64(image_url)
            
            bytes_io = io.BytesIO(base64_str.encode())
            file = discord.File(bytes_io, 'base64.txt')

            await ctx.send(file=file)

    @commands.hybrid_command(name=locale_str('random_uuid'), description=locale_str('random_uuid'))
    async def _random_uuid(self, ctx: commands.Context):
        async with ctx.typing():
            await ctx.send(str(uuid.uuid4()))

async def setup(bot):
    await bot.add_cog(Main(bot))
