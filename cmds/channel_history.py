import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiofiles
import orjson
import os
import time
import traceback

from core.classes import Cog_Extension

PATH = './data/temp'

class ChannelHistories:
    def __init__(self, ctx: commands.Context, count: int, file_type: str):
        self.file_type = file_type
        self.ctx = ctx
        self.count = count
        self.ls = None
        self.channelID = ctx.channel.id
        self.file_path = None

    async def get_histories(self) -> list:
        ctx = self.ctx
        count = self.count
        ls = []
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
        if self.file_type == 'json':
            self.file_path = f'{PATH}/channel_history_{self.channelID}.json'
            async with aiofiles.open(f'{PATH}/channel_history_{self.channelID}.json', mode='w') as f:
                await f.write(orjson.dumps(self.ls, option=orjson.OPT_INDENT_2).decode())
        else:
            self.file_path = f'{PATH}/channel_history_{self.channelID}.txt'
            result = []
            for m in self.ls:
                message_str = f"作者: {m['author']['name']} ({m['author']['id']})\n" \
                              f"頭像連結: {m['author']['avatar_url'] or '無'}\n" \
                              f"時間: {m['timestamp']}\n" \
                              f"內容: {m['content'] or '無'}\n"

                if m['attachments'] is not None:
                    message_str += f"附件: {', '.join(m['attachments'])}\n"
                
                if m['embeds'] is not None:
                    for embed in m['embeds']:
                        message_str += "嵌入訊息 (embed):\n"
                        if embed['title'] is not None and embed['title'] != '無':
                            message_str += f"  嵌入標題: {embed['title']}\n"
                        if embed['description'] is not None and embed['description'] != '無':
                            message_str += f"  嵌入描述: {embed['description']}\n"
                        if embed['fields']:
                            message_str += "  嵌入欄位:\n"
                            for field in embed['fields']:
                                message_str += f"    - {field['name']}: {field['value']}\n"
                        if embed['image'] is not None:
                            message_str += f"  嵌入圖片: {embed['image']}\n"
                
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

    @commands.hybrid_command(name='輸出聊天紀錄', description='Return a file that contains the chat history of the channel')
    @app_commands.choices(file_type=[app_commands.Choice(name=t, value=t) for t in ('json', 'txt')])
    async def output_chat_history(self, ctx: commands.Context, count: int = 10, file_type: str = 'json', ephemeral: bool = False):
        async with ctx.typing():
            if not ctx.channel.permissions_for(ctx.author).read_messages:
                return await ctx.send('你沒有權限讀取聊天紀錄')
            if not ctx.channel.permissions_for(ctx.me).read_message_history:
                return await ctx.send('我沒有權限讀取聊天紀錄')

            ch = ChannelHistories(ctx, count, file_type)
            file_path = await ch.run()
            
            file = discord.File(file_path, f'channel_history_{ctx.channel.id}.{file_type}')

            await ctx.send(file=file, ephemeral=ephemeral)

    @tasks.loop(minutes=1)
    async def rm_file(self):
        for path in os.listdir(PATH):
            if not path.startswith('channel_history_'): continue
            if time.time() - os.path.getctime(path) < 180: # 3分鐘後自動刪除
                os.remove(f'{PATH}/{path}')


async def setup(bot):
    await bot.add_cog(ChannelHistory(bot))
