import discord
from discord.ext import commands, tasks
import httpx
from datetime import datetime, timezone, timedelta
import traceback
import asyncio
import random
from functools import partial

from cmds.cambridge.search import search 
from cmds.cambridge.config import USER_AGENT

from core.classes import Cog_Extension
from core.mongodb import MongoDB_DB
from core.functions import create_basic_embed

db = MongoDB_DB.cambrdige
channels = db['channels']

async def _get_random_test(user_id: int) -> tuple[str, list[str], str, str, list[dict[str, str | list]]] | None:
    datas = [d async for d in db[str(user_id)].find().sort('create_at', -1).limit(100)]
    if len(datas) <= 5: return

    data = random.choice(datas)

    word = data['word']
    meanings = data['meanings']
    examples = data['examples']

    # 取得例句
    example = random.choice(examples)

    eg_sentence = example['eg'].split()
    for i, w in enumerate(eg_sentence): # 遍歷每個單字
        if word.lower() in (w.lower(), w[:-1].lower()):
            eg_sentence[i] = '_' * len(w)
            break
    eg_sentence = ' '.join(eg_sentence)

    translate_sentence = example['translate']

    # 取得其他錯誤答案
    datas.remove(data)
    wrong_datas = random.sample(datas, 3) # 取不重複的

    return word, meanings, eg_sentence, translate_sentence, wrong_datas

async def gener_daily_test(user_id: int) -> tuple[discord.Embed, discord.ui.View, str]:
    tmp = await _get_random_test(user_id)
    if not tmp: return discord.Embed(), discord.ui.View(), ''

    word, meanings, eg_sentence, translate_sentence, wrong_datas = tmp

    options_dict = {
        'A': '',
        'B': '',
        'C': '',
        'D': ''
    }

    correct_index = random.randint(0, 3)
    options_dict[chr(ord('A') + correct_index)] = word

    wrong_datas = random.sample(wrong_datas, 3)
    tmp = []
    for k, v in options_dict.items():
        if v: continue

        popped = wrong_datas.pop(0)
        tmp.append(popped) # 因為之後還會用到
        options_dict[k] = str(popped['word'])

    wrong_datas = tmp

    description = f'''
### Answer the following question!
**{eg_sentence}**

{'\n'.join([ f'{k}. {v}' for k, v in options_dict.items() ])}
'''.strip()
    
    eb = create_basic_embed('Daily Test!!!', description, color=discord.Color.blue())
    
    view = discord.ui.View()
    for i, (k, v) in enumerate(options_dict.items()):
        button = discord.ui.Button(label=v or 'Unknown', style=discord.ButtonStyle.primary)

        # 顯示這個按鈕的資訊，以及正確/錯誤
        async def button_callback(button: discord.ui.Button, _k: str, _meanings: list[str], inter: discord.Interaction):
            await inter.response.defer(thinking=True)
            option = button.label

            if option == word:
                # see others meanings
                other_info_button = discord.ui.Button(label='See others meanings', style=discord.ButtonStyle.primary)
                async def other_info_button_callback(inter: discord.Interaction):
                    strings = [
                        f"**({list(options_dict.keys())[list(options_dict.values()).index(str(item['word']))]}) {item['word']}:**\n{'; '.join(item['meanings'])}"
                        for item in wrong_datas
                    ]
                    await inter.response.send_message('\n\n'.join(strings))
                other_info_button.callback = other_info_button_callback # type: ignore

                _view = discord.ui.View()
                _view.add_item(other_info_button)
                await inter.followup.send(f'**✅ Correct!**\nThe answer is **{word}**\n\nClick the button below to see others meanings', view=_view)
            else:
                eb = create_basic_embed(f'You are WRONG!!! Try again', f'## ({_k}) {option}\n### Meanings:\n{'; '.join(_meanings)}', color=discord.Color.red())
                await inter.followup.send(embed=eb)
                
        # find current index's meanings
        curr_meanings = []
        for item in wrong_datas:
            if item['word'] == v:
                curr_meanings: list[str] = list(item['meanings'])
                break
        
        # 因為非裝飾器定義的 button 不會傳入 button 這個 arg
        button.callback = partial(button_callback, button, k, meanings if i == correct_index else curr_meanings) # type: ignore
        view.add_item(button)

    return eb, view, description


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
        if content.startswith('[') or content.startswith('[! '): return
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
        
        # add to db
        await db[str(ctx.author.id)].find_one_and_update(
            {'word': content}, 
            {'$set': {
                'word': content,
                'meanings': list(meanings),
                'examples': [{'eg': e['eg'], 'translate': e['translate']} for item in results for e in item['examples']],
                'created_at': datetime.now(timezone.utc)
            }}, 
            upsert=True
        )

    @commands.hybrid_command(name='cambridge_channel', description='Open/Close Cambridge channel')
    async def cambridge_channel(self, ctx: commands.Context):
        await ctx.defer()
        item = await channels.find_one({'channel_id': ctx.channel.id})
        if item:
            await channels.delete_one({'channel_id': ctx.channel.id})
            await ctx.send('Cambridge channel closed')
        else:
            await channels.insert_one(
                {
                    'channel_id': ctx.channel.id,
                    'created_at': datetime.now(timezone.utc)
                }, 
            )
            await ctx.send('Cambridge channel set')

    @commands.hybrid_command(name='daily_test', description='To close/open daily test')
    async def _daily_test(self, ctx: commands.Context):
        await ctx.defer()
        cond = not (await db[str(ctx.author.id)].find_one({'type': 'meta'}) or {}).get('daily_test', True) # 預設為開啟
        await db[str(ctx.author.id)].find_one_and_update(
            {'type': 'meta'}, 
            {'$set': {
                'daily_test': cond,
            }}, 
            upsert=True
        )
        await ctx.send(f'Daily test {"Opened" if cond else "Closed"}')


    @commands.command()
    async def test_daily_test(self, ctx: commands.Context):
        await ctx.defer()
        try:
            embed, view, question = await gener_daily_test(ctx.author.id)
            await ctx.send(embed=embed, view=view)
        except:
            traceback.print_exc()
            await ctx.send('發生錯誤')

    @tasks.loop(seconds=15)
    async def check_used(self):
        if self.last_used is None or self._client is None: return
        if self._client and (datetime.now() - self.last_used).total_seconds() > 30: # 30 秒未被使用
            await self._client.aclose()
            self._client = None

    @tasks.loop(hours=24)
    async def daily_test(self):
        for col in (await db.list_collection_names()):
            if col == 'channels': continue
            user_id = int(col)
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
            embed, view, question = await gener_daily_test(user_id)

            try:
                await user.send(embed=embed, view=view)
            except discord.Forbidden:
                continue

            await db[str(user_id)].update_one(
                {'type': 'meta'}, 
                {
                    '$set': {
                        'last_daily_test': datetime.now(timezone.utc)
                    },
                    '$push': {
                        'questions': question
                    }
                }, 
                upsert=True
            )

            await asyncio.sleep(1)

    @daily_test.before_loop
    async def before_daily_test(self):
        utc_now = datetime.now(timezone.utc)
        now = utc_now.astimezone(timezone(timedelta(hours=8)))

        target = datetime.combine(now + timedelta(days=1), datetime.min.time())
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

async def setup(bot):
    await bot.add_cog(CambridgeChannel(bot))