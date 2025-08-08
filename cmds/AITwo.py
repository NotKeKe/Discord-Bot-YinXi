import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks
import traceback
import os
import re
import aiohttp
import random
from collections import defaultdict

from cmds.AIsTwo.base_chat import *
from cmds.AIsTwo.others.func import image_generate, video_generate
from cmds.AIsTwo.others.decide import save_to_knowledge_base, Preference
from cmds.AIsTwo.info import HistoryData, get_history, create_result_embed, chat_autocomplete
from cmds.AIsTwo.utils import image_url_to_base64, select_moduels_auto_complete
from cmds.AIsTwo.vector import chat_human as vt_chat_human
from vector_data import vector

from core.functions import KeJCID, thread_pool, create_basic_embed, UnixNow, download_image, translate, testing_guildID, OLLAMA_IP

save_to_preferences = Preference.save_to_preferences

numbers = defaultdict(lambda: defaultdict(list))

class AITwo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.weather_task.start()

    async def get_weather_llm(self, location: str) -> discord.Embed:
        think, result = await thread_pool(base_zhipu_chat, f'請你幫我從搜尋{location}今天整天的完整天氣預報 以及整周的完整天氣預報 (須包含溫度 降雨機率 體感溫度 濕度 以及總結)',
                          system_prompt = '請根據使用者給出的地點 利用搜尋功能 回傳使用者的需求。\n以條列式進行輸出 在總結時必須使用顏文字(如: (つ´ω`)つ)。' + 
                                            '如果tools沒有輸出的話 就輸出false' + 
                                            '請以公制單位做為輸出',
                                            top_p=0.9)
        eb = create_basic_embed(location, result or think, discord.Color.random(), '天氣預報')
        eb.set_footer(text='更新時間')
        return eb

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        await safe_get_ollama_models()

    # @commands.hybrid_command(name='chat_two', description='Chat with AI model')
    # @app_commands.autocomplete(model=select_moduels_auto_complete, 歷史紀錄=chat_autocomplete)
    # @app_commands.describe(model='預設為`qwen-3-32b`', 想法顯示='預設為`False`', 工具調用='預設為`True`')
    # async def _chat(self, ctx: commands.Context, * , 輸入文字: str, model:str = 'qwen-3-32b', 歷史紀錄:str = None, 想法顯示:bool = False, 文字檔案: discord.Attachment = None, 工具調用: bool = True, 系統提示詞: str = None):
    #     async with ctx.typing():
    #         try:
    #             HistoryData.initdata()
    #             history = get_history(ctx, 歷史紀錄)

    #             f_content = None
    #             if 文字檔案:
    #                 try:
    #                     f_content = (await 文字檔案.read()).decode('utf-8')
    #                 except:
    #                     await ctx.send('無法讀取文字檔案')

    #             try:
    #                 think, result, *_ = await thread_pool(base_openai_chat, 輸入文字, model, history=history, text_file_content=f_content, is_enable_tools=工具調用, system_prompt=系統提示詞)
    #             except: 
    #                 traceback.print_exc()
    #                 await ctx.send(f'您使用的model({model})出錯，因此此次用glm-4-flash代替，並且無法閱讀檔案')
    #                 model = 'glm-4-flash'
    #                 think, result, *_ = await thread_pool(base_zhipu_chat, 輸入文字, model, history=history)

    #             embed = create_result_embed(ctx, result, model)
    #             await ctx.send(embed=embed)

    #             if 想法顯示 and think:
    #                 await ctx.send(content=think, ephemeral=True)
            
    #             if result:
    #                 try: HistoryData.appendHistory(ctx.author.id, 輸入文字, result, 歷史紀錄, think)
    #                 except: traceback.print_exc()

    #             # await thread_pool(save_to_knowledge_base, ctx.message.content, result if result else think)
    #             # await thread_pool(save_to_preferences, ctx.author.id, (to_user_message(輸入文字) + to_assistant_message(result if result else think)))
    #         except:
    #             traceback.print_exc()
    #             await ctx.send('目前無法生成，請稍後再試')
    
    # @commands.hybrid_command(name='_圖片生成', description='Generate a image')
    # @app_commands.choices(
    #     model=[
    #         Choice(name='cogview-3-flash', value='cogview-3-flash')
    #     ]
    # )
    # async def _image_generate(self, ctx: commands.Context, * , 輸入文字: str, model:str ='cogview-3-flash'):
    #     try:
    #         async with ctx.typing():
    #             url, time = await thread_pool(image_generate, 輸入文字)
    #             embed = create_basic_embed(title='AI圖片生成', color=ctx.author.color)
    #             embed.set_image(url=url)
    #             embed.add_field(name='花費時間(秒)', value=int(time))
    #             embed.set_footer(text=f'Powered by {model}')
    #             await ctx.send(embed=embed)
    #     except:
    #         await ctx.send('生成失敗', ephemeral=True)

    # @commands.hybrid_command(name='_影片生成', description='Generate a video')
    # @app_commands.choices(
    #     model=[app_commands.Choice(name='cogvideox-flash', value='cogvideox-flash')],
    #     size = [
    #         Choice(name='720x480', value='720x480'),
    #         Choice(name='1024x1024', value='1024x1024'),
    #         Choice(name='1280x960', value='1280x960'),
    #         Choice(name='960x1280', value='960x1280'),
    #         Choice(name='1920x1080', value='1920x1080'),
    #         Choice(name='1080x1920', value='1080x1920'),
    #         Choice(name='2048x1080', value='2048x1080'),
    #         Choice(name='3840x2160', value='3840x2160')
    #     ],
    #     fps = [
    #         Choice(name=30, value=30),
    #         Choice(name=60, value=60)
    #     ],
    #     是否要聲音 = [
    #         Choice(name='要', value='要'),
    #         Choice(name='不要', value='不要')
    #     ]
    # )
    # @app_commands.describe(fps='預設為60，可選30 or 60', 影片時長='單位為秒, 預設為5, 最高為10')
    # async def _video_generate(self, ctx: commands.Context, * , 輸入文字: str, 圖片連結: str = None, size: str = None, fps: int = 60, 是否要聲音 = '要', 影片時長:int = 5, model:str = 'cogvideox-flash'):
    #     try:
    #         async with ctx.typing():
    #             if 影片時長 > 10:
    #                 await ctx.send(f'最高只能幫你生成10秒的圖片 要怪就怪{model}...', ephemeral=True) 
    #                 影片時長 = 10

    #             if fps not in (30, 60):
    #                 fps = 60

    #             if 是否要聲音 == '要':
    #                 是否要聲音 = True
    #             else:
    #                 是否要聲音 = False
    #             url = await thread_pool(video_generate, 輸入文字, 圖片連結, size, fps, 是否要聲音, 影片時長)
    #             string = f'影片生成 (Power by {model}) \n {url}'
    #             await ctx.send(string)
    #     except Exception as e:
    #         await ctx.send(f'生成失敗, reason: {e}', ephemeral=True)
    #         traceback.print_exc()

    # @commands.hybrid_command(name='image_to_base64', description='將圖片轉成base64')
    # async def to_base64(self, ctx:commands.Context, *, url: str):
    #     try:
    #         result = image_url_to_base64(url)
            
    #         if len(result) > 4000:
    #             path = f'./cmds/data.json/{(ctx.author.name).strip()}.txt'
    #             with open(path, mode='w', encoding="utf-8") as f:
    #                 f.write(result)
    #             file = discord.File(fp=path, filename=f'{(ctx.author.name).strip()}.txt')
    #             await ctx.send(file=file)
    #             os.remove(path)
    #         else: await ctx.send(result)
    #     except Exception as e:
    #         await ctx.send(f'轉換失敗, reason: {e}', ephemeral=True)

    @commands.hybrid_command(name='文字轉語音', description='利用ChatTTS來把文字轉成語音')
    @app_commands.guilds(discord.Object(id=testing_guildID))
    @app_commands.describe(text='在此輸入你要轉換的文字 (建議使用中文)', 
                           情感波動性='temperature，範圍在0~1，數字越大 波動性越高',
                           情感相關性='top_P，範圍在0.1~0.9，數字越大 相關性越高',
                           情感相似性='top_K，範圍在1~20，數字越小 相似性越高',
                           聲音種子碼='如果你有特殊需求的話再改這個 但不同種子碼會有不同聲音')
    async def text_to_speech(self, ctx:commands.Context, * , text, 情感波動性: float=0.62303, 情感相關性: float=0.7, 情感相似性: int=20, 聲音種子碼: int=9999):
        async with ctx.typing():
            text = translate(text, 'zh-TW', 'zh-CN')

            data = {
                "text": text.strip(),
                "prompt": "",
                "voice": "2222",
                "temperature": 情感波動性,
                "top_p": 情感相關性,
                "top_k": 情感相似性,
                "refine_max_new_token": "384",
                "infer_max_new_token": "2048",
                "skip_refine": 0,
                "is_split": 1,
                "custom_voice": 聲音種子碼
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(f"http://{OLLAMA_IP}:9966/tts", data=data) as resp:
                    if resp.status == 200:
                        j = await resp.json()
                    else: return await ctx.send('克克可能忘記開電腦了 這功能現在用不了:<')
            url = j['url']
            filename = f'textToSpeech{UnixNow()}_{ctx.author.id}.wav'
            await download_image(url, filename)
            file = discord.File(f'./cmds/data.json/{filename}', filename)

            await ctx.send(f'已將 **{text}** 轉換為音訊檔', file=file)
            os.remove(f'./cmds/data.json/{filename}')

    @commands.hybrid_command(name='weather', description='看天氣')
    async def _weather(self, ctx:commands.Context, 地名: str):
        async with ctx.typing():
            eb = await self.get_weather_llm(地名)
            await ctx.send(embed=eb)

    @commands.hybrid_command(name='weather_update', description='每日天氣更新(會每隔6小時更新一次bot發送的訊息)')
    @app_commands.describe(取消='刪除此頻道所有的weather update (幫我省省資源:D)')
    async def _weather_update(self, ctx:commands.Context, 地名: str = None, 取消: bool = False):
        async with ctx.typing():
            HistoryData.initdata()
            data = HistoryData.weather_messages

            if 取消: 
                count = 0
                for item in list(data.keys()):
                    if data[item]['channel'] == ctx.channel.id:
                        del data[item]
                        count += 1
                await ctx.send(f'已刪除此頻道所有的weather update (總計: {count}個)')
            else:
                if not 地名: return await ctx.send('請輸入地名')
                eb = await self.get_weather_llm(地名)
                message = await ctx.send(embed=eb)
                data[str(message.id)] = {'location': 地名, 'author': ctx.author.id, 'channel': ctx.channel.id}
                HistoryData.writeWeatherMessages(data)

    @commands.hybrid_command(name='猜數字')
    async def guess_num(self, ctx: commands.Context, range1: int, range2: int):
        num = random.randint(range1, range2)
        numbers[ctx.channel.id][ctx.author.id] = [range1, range2, num]
        await ctx.send(f'使用`[guess`來猜數字\n從{range1}~{range2}之間猜一個數字')
        await ctx.send(f'{num=}')

    @commands.command()
    async def guess(self, ctx: commands.Context, num: int):
        async with ctx.typing():
            if ctx.channel.id not in numbers: return await ctx.send('這個頻道沒有人在猜數字')
            if ctx.author.id not in numbers[ctx.channel.id]: return await ctx.send('你沒有再猜數字，先使用`/猜數字`來猜')

            range1, range2, target_num = numbers[ctx.channel.id][ctx.author.id]

            if not (range1 <= num <= range2): return await ctx.send('現在的範圍是{}~{}，請重新猜一次'.format(range1, range2))
            think, result = await thread_pool(base_openai_chat, f'我猜了{num}', 'qwen3:8b', no_extra_system_prompt=True, is_enable_tools=False, is_enable_thinking=True, system_prompt='''
你現在是一個給予使用者情緒價值的AI助手，你的任務是要看使用者有沒有猜對數字，如果使用者猜了錯誤的數字，你必須告訴使用者是太大還是太小，並且重新告訴他一個範圍。
正確數字為: `{target_num}`，而使用者現在猜了`{num}`
預設範圍為{range1} ~ {range2}
**不能告訴使用者正確數字**
範例:
    - (使用者猜錯了)使用者猜了5，但正確數字是10，預設範圍是`1~100`
    則輸出的時候比需要說出預設範圍改為6~100，並提供一些鼓勵的話，讓使用者繼續猜。
    - (使用者猜對了)使用者猜了10，且正確數字是10
    則直接告訴使用者他猜對了，並且像鼓勵小孩一樣鼓勵他很棒，並且不用告知範圍。
範例輸出:
    - 哇塞 你居然猜對了 太屌了吧 ٩(ˊᗜˋ*)و
    - 哎呀 你猜得有點太大了欸 再繼續挑戰看看吧～ (๑•̀ㅂ•́)و✧ (並且告知範圍)
多多使用換行來代替換句或標點符號
使用者名稱: {name}
'''.format(target_num=target_num, num=num, range1=range1, range2=range2, name=ctx.author.display_name)
    )
            solved = False
            if num > target_num: 
                numbers[ctx.channel.id][ctx.author.id][1] = num-1
            elif num < target_num:
                numbers[ctx.channel.id][ctx.author.id][0] = num+1
            else:
                solved = True
                del numbers[ctx.channel.id][ctx.author.id]
                if not numbers[ctx.channel.id]:
                    del numbers[ctx.channel.id]
            await ctx.send(result or think)
            if solved:
                await ctx.send('再次使用`/猜數字`來猜新的數字')

    @commands.hybrid_command(name='向量數據庫資料搜索', description='Vector database search')
    async def vector_search(self, ctx: commands.Context, query: str, limit: int = 3):
        async with ctx.typing():
            result = await vector.search(query, limit)
            await ctx.send('\n'.join(result))

    @commands.command('chat_human_vector_search')
    async def chatHumanVector_Search(self, ctx: commands.Context, query: str, top_k: int = 2):
        if str(ctx.author.id) != KeJCID: return
        async with ctx.typing(ephemeral=True):
            collection = vt_chat_human.create()
            items = await vt_chat_human.get(collection, query, top_k)
            await ctx.send('\n\n\n'.join(items), ephemeral=True)

    @commands.command('chat_human_vector_post_path')
    async def chatHumanVector_Post_path(self, ctx: commands.Context, file_path: str):
        if str(ctx.author.id) != KeJCID: return
        async with ctx.typing(ephemeral=True):
            collection = vt_chat_human.create()
            await vt_chat_human.add(collection, file_path)
            await ctx.send('Successfully Add {} to chat human database'.format(file_path), ephemeral=True)

    @commands.command('chat_human_vector_post_text')
    async def chatHumanVector_Post_text(self, ctx: commands.Context, single_text: str):
        if str(ctx.author.id) != KeJCID: return
        async with ctx.typing(ephemeral=True):
            collection = vt_chat_human.create()
            await vt_chat_human.add(collection, single_text)
            await ctx.send('Successfully Add {} to chat human database'.format(single_text), ephemeral=True)

    @commands.command('chat_human_vector_delete')
    async def chatHumanVector_Delete(self, ctx: commands.Context, text: str):
        if str(ctx.author.id) != KeJCID: return
        async with ctx.typing(ephemeral=True):
            if "~" in text:  # 處理範圍
                start, end = map(int, text.split("~"))
                ids = list(range(start, end + 1))
            else:  # 處理固定數字清單
                ids = list(map(int, re.split(r"[ ,]+", text)))

            collection = vt_chat_human.create()
            await vt_chat_human.delete(collection, ids)
            await ctx.send('Successfully Delete {} from chat human database'.format(text), ephemeral=True)


    @tasks.loop(hours=6)
    async def weather_task(self):
        HistoryData.initdata()
        data = HistoryData.weather_messages
        for messageID in data:
            location = data[messageID]["location"]
            channel = await self.bot.fetch_channel(data[messageID].get('channel'))
            message = await channel.fetch_message(int(messageID))
            eb = await self.get_weather_llm(location)
            await message.edit(embed=eb)

    @weather_task.before_loop
    async def weather_task_beforeloop(self):
        await self.bot.wait_until_ready()
        


async def setup(bot):
    await bot.add_cog(AITwo(bot))