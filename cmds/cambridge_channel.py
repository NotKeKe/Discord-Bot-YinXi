import discord
from discord.ext import commands, tasks
import httpx
from datetime import datetime, timezone
import traceback

from cmds.cambridge.search import search 
from cmds.cambridge.config import USER_AGENT

from core.classes import Cog_Extension
from core.mongodb import MongoDB_DB

db = MongoDB_DB.cambrdige
channels = db['channels']

class CambridgeChannel(Cog_Extension):
    def __init__(self, bot: commands.Bot):
        super().__init__(bot)

        self._client: httpx.AsyncClient | None = None
        self.last_used: datetime | None = None

    def get_client(self):
        if not self._client:
            limit = httpx.Limits(
                max_connections=20,            # 整體同時連線上限
                max_keepalive_connections=10,  # 允許的 keep‑alive 空閒連線
                keepalive_expiry=30.0          # 30 秒內不會自動關閉
            )
            self._client = httpx.AsyncClient(headers={'User-Agent': USER_AGENT}, limits=limit)

        self.last_used = datetime.now()
        return self._client

    async def cog_load(self):
        self.get_client()
        self.check_used.start()

    async def cog_unload(self):
        if self._client is None: return
        await self._client.aclose()
        self.check_used.stop()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        content = msg.content
        if not content: return
        if msg.author.bot: return
        if not (await channels.find_one({'channel_id': msg.channel.id})): return

        ctx = await self.bot.get_context(msg)
        async with ctx.typing():
            self.last_used = datetime.now()

            try:
                results = await search(content, self.get_client())
            except:
                traceback.print_exc()
                return

            詞性 = set()
            meanings = set()
            examples = []
            for r in results:
                splited_word = r['word'].split()
                if len(splited_word) > 0:
                    詞性.add(splited_word[1])

                for m in r['meaning']: meanings.add(m)
                
                for e in r['examples']: 
                    if len(examples) >= 3: continue
                    examples.append(f'英: {e["eg"]}\n中: {e["translate"]}')

#             message = f'''  
# ### 詞性:   
# `{';'.join(詞性).strip()}`  

# ### 意義:   
# `{';'.join(meanings).strip()}`  

# ### 例句:   
# {'\n'.join([f'`{i+1}. {item}`' for i, item in enumerate(examples)])}  
# '''.strip()
            meanings_str = '; '.join(meanings).strip()

            message = f'''
{content} ||{meanings_str}||

例句:
{'\n'.join([f'{i+1}.\n||{item}||' for i, item in enumerate(examples)])}
'''

            await msg.reply(message if meanings_str else '找不到詞性或意義')

    @commands.hybrid_command(name='set_cambridge_channel', description='Set Cambridge channel')
    async def cambridge_channel(self, ctx: commands.Context):
        await ctx.defer()
        await channels.update_one(
            {'channel_id': ctx.channel.id}, 
            {'$set': {
                'channel_id': ctx.channel.id,
                'created_at': datetime.now(timezone.utc)
            }}, 
            upsert=True
        )
        await ctx.send('Cambridge channel set')

    @commands.hybrid_command(name='cancel_cambridge_channel', description='Cancel Cambridge channel')
    async def cancel_cambridge_channel(self, ctx: commands.Context):
        await ctx.defer()
        item = await channels.find_one_and_delete({'channel_id': ctx.channel.id})
        if item:
            await ctx.send('Cambridge channel canceled')

    @tasks.loop(seconds=15)
    async def check_used(self):
        if self._client and (datetime.now() - self.last_used).total_seconds() > 30: # 30 秒未被使用
            await self._client.aclose()
            self._client = None

async def setup(bot):
    await bot.add_cog(CambridgeChannel(bot))