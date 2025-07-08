import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiofiles
import orjson
import os
import time
import traceback

from core.classes import Cog_Extension
from core.translator import locale_str, load_translated

PATH = './data/temp'

class ChannelHistories:
    def __init__(self, ctx: commands.Context, count: int, file_type: str, reverse: bool):
        self.file_type = file_type
        self.ctx = ctx
        self.count = count
        self.reverse = reverse
        self.ls = None
        self.channelID = ctx.channel.id
        self.file_path = None

    async def get_histories(self) -> list:
        ctx = self.ctx
        count = self.count
        ls = [{
            'channel': {'id': ctx.channel.id, 'name': ctx.channel.name}, 
            **({'guild': {'id': ctx.guild.id, 'name': ctx.guild.name}} if ctx.guild else {})
        }]
        async for m in ctx.channel.history(limit=count):
            if m.content == m.attachments == m.embeds == None: continue

            ls.append({
                'author': {
                    'id': m.author.id,
                    'name': m.author.global_name or m.author.name,
                    'avatar_url': m.author.avatar.url
                },
                'content': m.content,
                'timestamp': m.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'attachments': [a.url for a in m.attachments] if m.attachments else None,
                'embeds': [
                    {
                        'title': e.title, 
                        'description': e.description,
                        'fields': [{'name': f.name, 'value': f.value, 'inline': f.inline} for f in e.fields],
                        'image': e.image.url if e.image else None,

                    }
                    for e in m.embeds
                ] if m.embeds else None
            })

        self.ls = ls
        return ls
    
    async def type_process(self):
        if self.reverse:
            self.ls.reverse()

        if self.file_type == 'json':
            self.file_path = f'{PATH}/channel_history_{self.channelID}.json'
            async with aiofiles.open(f'{PATH}/channel_history_{self.channelID}.json', mode='w') as f:
                await f.write(orjson.dumps(self.ls, option=orjson.OPT_INDENT_2).decode())
        else:
            self.file_path = f'{PATH}/channel_history_{self.channelID}.txt'
            result = []
            for m in self.ls:
                i18n_data = await self.ctx.interaction.translate('send_channel_history_file_template')
                i18n_data = load_translated(i18n_data)[0]
                
                author_str = i18n_data.get('author', '作者')
                avatar_url_str = i18n_data.get('avatar_url', '頭像連結')
                time_str = i18n_data.get('time', '時間')
                content_str = i18n_data.get('content', '內容')
                none_str = i18n_data.get('none', '無')
                attachments_str = i18n_data.get('attachments', '附件')
                embed_str = i18n_data.get('embed', '嵌入訊息 (embed)')
                embed_title_str = i18n_data.get('embed_title', '嵌入標題')
                embed_description_str = i18n_data.get('embed_description', '嵌入描述')
                embed_fields_str = i18n_data.get('embed_fields', '嵌入欄位')
                embed_image_str = i18n_data.get('embed_image', '嵌入圖片')

                message_str = f"{author_str}: {m['author']['name']} ({m['author']['id']})\n" \
                              f"{avatar_url_str}: {m['author']['avatar_url'] or none_str}\n" \
                              f"{time_str}: {m['timestamp']}\n" \
                              f"{content_str}: {m['content'] or none_str}\n"

                if m['attachments'] is not None:
                    message_str += f"{attachments_str}: {', '.join(m['attachments'])}\n"
                
                if m['embeds'] is not None:
                    for embed in m['embeds']:
                        message_str += f"{embed_str}:\n"
                        if embed['title'] is not None and embed['title'] != none_str:
                            message_str += f"  {embed_title_str}: {embed['title']}\n"
                        if embed['description'] is not None and embed['description'] != none_str:
                            message_str += f"  {embed_description_str}: {embed['description']}\n"
                        if embed['fields']:
                            message_str += f"  {embed_fields_str}:\n"
                            for field in embed['fields']:
                                message_str += f"    - {field['name']}: {field['value']}\n"
                        if embed['image'] is not None:
                            message_str += f"  {embed_image_str}: {embed['image']}\n"
                
                message_str += "-" * 30 + "\n"
                result.append(message_str)

            async with aiofiles.open(f'{PATH}/channel_history_{self.channelID}.txt', mode='w', encoding='utf-8') as f:
                await f.write("".join(result))

    async def run(self):
        try:
            await self.get_histories()
            await self.type_process()
            return self.file_path
        except: traceback.print_exc()

class ChannelHistory(Cog_Extension):
    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        os.makedirs(PATH, exist_ok=True)
        self.rm_file.start()

    @commands.hybrid_command(name=locale_str('output_chat_history'), description=locale_str('output_chat_history'))
    @app_commands.choices(file_type=[app_commands.Choice(name=t, value=t) for t in ('json', 'txt')])
    @app_commands.describe(count=locale_str('output_chat_history_count'), file_type=locale_str('output_chat_history_file_type'), reverse=locale_str('output_chat_history_reverse'))
    async def output_chat_history(self, ctx: commands.Context, count: int = 10, file_type: str = 'json', reverse: bool = False):
        async with ctx.typing():
            if not ctx.channel.permissions_for(ctx.author).read_messages or not ctx.channel.permissions_for(ctx.author).read_message_history:
                return await ctx.send(await ctx.interaction.translate('send_output_chat_history_no_read_permission'))
            if not ctx.channel.permissions_for(ctx.me).read_message_history:
                return await ctx.send(await ctx.interaction.translate('send_output_chat_history_bot_no_read_permission'))

            ch = ChannelHistories(ctx, count, file_type, reverse)
            file_path = await ch.run()
            
            file = discord.File(file_path, f'channel_history_{ctx.channel.id}.{file_type}')

            await ctx.send(file=file)

    @tasks.loop(minutes=1)
    async def rm_file(self):
        for filename in os.listdir(PATH):
            file_path = os.path.join(PATH, filename)
            if not filename.startswith('channel_history_'): continue
            
            if os.path.isfile(file_path):
                try:
                    if time.time() - os.path.getctime(file_path) > 180: # 超過3分鐘則刪除
                        os.remove(file_path)
                except Exception as e:
                    print(f'刪除檔案 {file_path} 時發生錯誤: {e}')

async def setup(bot):
    await bot.add_cog(ChannelHistory(bot))
