from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import aiohttp
from pprint import pp
import traceback
from datetime import datetime
from deep_translator import GoogleTranslator
import typing
import os
import xml.etree.ElementTree as ET
import asyncio

from core.classes import Cog_Extension
from core.functions import thread_pool, read_json, create_basic_embed, download_image, translate, secondToReadable, strToDatetime
from core.functions import nasaApiKEY, NewsApiKEY, unsplashKEY

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head>
            <title>Discord Bot</title>
        </head>
        <body>
            <h1>Discord Bot is online.</h1>
        </body>
    </html>
    """

@app.get('/api/llm/tools')
async def get_tools():
    data = read_json('./cmds/AIsTwo/data/tools_descrip.json')
    return data

@app.get('/log', response_class=HTMLResponse)
async def get_log():
    with open("./nas_log/error.log", "rb") as f:
        f.seek(-3000, 2)
        data_bytes = f.read()
        data = data_bytes.decode("utf-8")
    return '''
    <html>
       <head>
            <title>Discord Bot logs</title>
        </head>
        <body style="background-color: #003E3E;">
            <h1 style="color: white; font-family: Arial, Helvetica, sans-serif;">Bot error logs:</h1>
            <p style="color: white; font-family: 'Lucida Console', 'Courier New', monospace; font-size: 17px;">{data}</p>
        </body>
    </html>
    '''.format(data=data.replace('\n', '<br>'))

@app.get('/test', response_class=FileResponse)
async def test_file_return():
    return FileResponse('./hii.mp4')

class select_autocomplete:
    countries = read_json('./cmds/data.json/country.json')

    @staticmethod
    async def country(_, interaction: discord.Interaction, current: str) -> typing.List[Choice[str]]:
        try:
            return [
                Choice(name=name, value=code) 
                for code, name in select_autocomplete.countries.items()
                if current.lower().strip() in name.lower() or current.lower().strip() in code.lower()
            ][:25]
        except: traceback.print_exc()



class ApiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class utils:
        @staticmethod
        def stringToDatetime(string: str) -> datetime:
            '''datetime.strptime(string, "%Y-%m-%d T%H:%M:%SZ")'''
            converted_datetime = datetime.strptime(string, "%Y-%m-%dT%H:%M:%SZ")
            return converted_datetime

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'已載入「{__name__}」')
        try:
            await thread_pool(uvicorn.run, app, host="0.0.0.0", port=3000, log_level="warning")
        except Exception as e:
            print(f'An error accur while bind address 0.0.0.0:3000 reason: {e}')
    
    @commands.hybrid_command(name='joke', description='隨機抽一個笑話 (英文的)', aliases=['jokes'])
    async def _joke(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://sv443.net/jokeapi/v2/joke/Any') as response:
                    if response.status != 200: return await ctx.send('請稍後在試')
                    data = await response.json()
                    if data['error']: await ctx.send('Bug了:< 再重試一次')
                    joke = data['setup']
                    answer = data['delivery']
            await ctx.send(f'**英文版:**\n笑話: {joke}\n答案: ||{answer}||\n' + 
                           f'**中文版:**\n笑話: {translate(joke)}\n答案: ||{translate(answer)}||')

    @commands.hybrid_command(name='新聞', description='查詢最近的新聞(雖然我實測 他內文有時候會bug)', aliases=['news'])
    @app_commands.choices(options=[
        Choice(name='Everything', value=1),
        Choice(name='Top_Headlines', value=2),
    ], language=[
            app_commands.Choice(name="Arabic", value="ar"),
            app_commands.Choice(name="German", value="de"),
            app_commands.Choice(name="English", value="en"),
            app_commands.Choice(name="Spanish", value="es"),
            app_commands.Choice(name="French", value="fr"),
            app_commands.Choice(name="Hebrew", value="he"),
            app_commands.Choice(name="Italian", value="it"),
            app_commands.Choice(name="Dutch", value="nl"),
            app_commands.Choice(name="Norwegian", value="no"),
            app_commands.Choice(name="Portuguese", value="pt"),
            app_commands.Choice(name="Russian", value="ru"),
            app_commands.Choice(name="Swedish", value="sv"),
            app_commands.Choice(name="Urdu", value="ud"),
            app_commands.Choice(name="Chinese", value="zh"),
        ])
    @app_commands.autocomplete(country=select_autocomplete.country)
    @app_commands.describe(question='只有在你選擇Everything時才要輸入', language='只有在選擇Everything時才要輸入', country='只有在選擇Top_headlines時才要輸入')
    async def _news(self, ctx: commands.Context, options: int, question: str=None, language: str = 'zh', country: str='tw', 輸出數量: int=3):
        try:
            async with ctx.typing():
                if 輸出數量 > 5:
                    view = discord.ui.View()

                    button1 = discord.ui.Button(label = "✅", style = discord.ButtonStyle.blurple)
                    button2 = discord.ui.Button(label='❌', style=discord.ButtonStyle.blurple)

                    async def button1_callback(interaction: discord.Interaction):
                        await interaction.response.defer()
                    async def button2_callback(interaction: discord.Interaction):
                        await interaction.response.send_message('已取消輸出', ephemeral=True)
                        return

                    button1.callback = button1_callback
                    button2.callback = button2_callback
                    view.add_item(button1)
                    view.add_item(button2)
                    await ctx.send(f'你確定要輸出那麼多的新聞數量嗎:thinking:\n 醬會吵到別人欸 (因為他會分{輸出數量}次輸出)', view=view, ephemeral=True)
                    view.wait()


                if options == 1:
                    if not question:
                        await ctx.send('請輸入question (一個你要搜尋的問題)', ephemeral=True); return
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://newsapi.org/v2/everything?q={question}&language={language}&apiKey={NewsApiKEY}') as response:
                            data = await response.json()

                elif options == 2:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://newsapi.org/v2/top-headlines?country={country}&apiKey={NewsApiKEY}') as response:
                            data = await response.json()

                if data['status'] != 'ok': await ctx.send('Bug了:< 再重試一次' + f'reason: {data["code"]}')
                # pp(data)
                result_count = data['totalResults']
                eb = create_basic_embed(color=ctx.author.color, 功能='News')
                eb.add_field(name='搜尋到的總數: ', value=f'{result_count} (因為discord限制 所以不會全部顯示)\n每個文章的連結都在作者上面窩')
                await ctx.send(embed=eb)

                for result in data["articles"][:輸出數量]:                    
                    title = result["title"]
                    url = result["url"]
                    description = result["description"]
                    content = result.get("content")
                    publistAt = result["publishedAt"]
                    source = result["source"]['name']
                    image = result["urlToImage"]
                    
                    eb = create_basic_embed(title=title, description=content, time=False)
                    eb.set_author(name=source, url=url)
                    eb.set_footer(text='創建時間:')
                    eb.set_image(url=image)
                    eb.timestamp = self.utils.stringToDatetime(publistAt)
                    await ctx.send(embed=eb)
        except:
            traceback.print_exc()

    @commands.hybrid_command(name='貓貓冷知識', description='cat fact (https://catfact.ninja/)', aliases=['貓咪冷知識', 'cat', 'cat_fact', 'catfact'])
    async def cat_fact(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://catfact.ninja/fact?max_length=2000') as response:
                    result = await response.json()
            source = result['fact']
            translated = translate(source)
            await ctx.send(translated + f'\n原文: {source}')

    @commands.hybrid_command(name='nasa每日圖片', description='nasa daily image (NASA API)', aliases=['nasa'])
    async def _nasa(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.nasa.gov/planetary/apod?api_key={nasaApiKEY}') as response:
                    data = await response.json()
            
            title = data['title']
            url = data['url']
            date = data["date"]
            explanation = data["explanation"]
            translated_explanation = translate(explanation)

            await download_image(url, 'nasa_apod.jpg')
            file = discord.File(fp='./cmds/data.json/nasa_apod.jpg', filename='nasa_apod.png')
            os.remove('./cmds/data.json/nasa_apod.jpg')

            eb = create_basic_embed(title=title, description=translated_explanation + f'\n原文: {explanation}', time=False)
            eb.set_image(url='attachment://nasa_apod.jpg')
            eb.set_footer(text=f'NASA API | {date}')
            await ctx.send(file=file, embed=eb)

    @commands.hybrid_command(name='數字歷史', description="Show the number's history", aliases=['num_history', 'n_history'])
    @app_commands.describe(number = '輸入一個數字 然後你就能知道他的故事:D')
    async def number_history(self, ctx: commands.Context, number: int):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://numbersapi.com/{number}?json') as response:
                    data = await response.json()
            if not data['found']: await ctx.send(f'找不到有關於{number}的結果'); return
            text = data["text"]
            traslated = translate(text)
            await ctx.send(f"**{number}**的資訊: \n{traslated}\n原文: {text}")

    @commands.hybrid_command(name='看圖', description='Get some photo from unsplash', aliases=['photo', 'image'])
    @app_commands.describe(query='輸入你要搜尋的結果', num='輸入你要幾個結果 (如果你query沒輸入的話 輸入這個也沒用)')
    async def unsplash_image(self, ctx: commands.Context, query: str=None, num: int=3):
        async with ctx.typing():
            urls = []
            async with aiohttp.ClientSession() as session:
                if query:
                    async with session.get(f'https://api.unsplash.com/search/photos?query={query}&client_id={unsplashKEY}') as response:
                        data = await response.json()
                        for index, photo in enumerate(data['results'][:num]):
                            urls += [f"作者: [{photo['user']['username']}](<{photo['user']['links']['html']}>)"]
                            urls += [f"[圖片連結{index+1}]({photo['urls']['regular']})"]
                else:
                    async with session.get(f'https://api.unsplash.com/photos/random?client_id={unsplashKEY}') as response:
                        data = await response.json()
                        urls += [f"作者: [{data['user']['username']}](<{data['user']['links']['html']}>)"]
                        urls += [f"[圖片連結]({data['urls']['regular']})"]
            await ctx.send('\n'.join(urls))

    @commands.hybrid_command(name='影片下載', description='Download the video or audio by yt-dlp (from youtube twitter etc.)', aliases=['yt_downlaod', 'ytdownload'])
    @app_commands.choices(
        type = [Choice(name=s, value=s) for s in ('mp4', 'mp3')],
        quality = [Choice(name=s, value=s) for s in ('high', 'medium', 'low')]
    )
    @app_commands.describe(
        type = '選擇你要下載mp4還是mp3 (預設: mp3)',
        quality = '(僅在選擇mp4時 這個選項才有效) high-高，medium-中，low-低'
    )
    async def yt_downloader(self, ctx: commands.Context, url: str, type: str = 'mp3', quality: str = None):
        try:
            async with ctx.typing():
                data = {
                    "url": url, 
                    "media_type": type, # 可以是 "mp4" 或 "mp3" 
                    "quality": quality # 僅在 media_type 為 mp4 時有效
                }

                async with aiohttp.ClientSession() as sess:
                    async with sess.post('http://192.168.31.99:6002/api/download', json=data) as resp:
                        if resp.status == 404: return await ctx.send('目前無法下載影片或音訊 (原因: 我也不知道 可能我壞掉了(?) )')
                        resp_json = await resp.json()
                        task_id = resp_json.get('task_id')

                await ctx.send(f'Tracking task id: {task_id}')

                for _ in range(10):
                    await asyncio.sleep(3)

                    async with aiohttp.ClientSession() as sess:
                        async with sess.get(f'http://192.168.31.99:6002/api/status/{task_id}') as resp:
                            resp_json = await resp.json()
                            status = resp_json.get('status')
                            if status == 'error': 
                                reason = resp_json.get('message')
                                return await ctx.send(f"出現了一個錯誤:< (原因: {'yt-dlp不讓我們下載好康的影片:<' if 'NSFW' in reason else reason})")
                            if status == 'started': continue
                            url = resp_json.get('download_url')
                            info = resp_json.get('info')
                                        
                    eb = create_basic_embed(info.get('title'), color=ctx.author.color, 功能=f'{type.upper()}下載')

                    eb.add_field(name='Source_url', value=f"[來源連結(SOURCE_URL)]({resp_json.get('source_url')})")
                    eb.add_field(name='Duration', value=secondToReadable(info.get('duration')))
                    eb.set_image(url=info.get('thumbnail'))
                    eb.add_field(name='花費時間(秒)', value=int(resp_json.get('process_time')))
                    eb.set_footer(text='不建議你把它拿去商業用途窩')

                    await ctx.send(f"[下載連結(DOWNLOAD_URL)]({resp_json.get('download_url')})", embed=eb)
                    return
                await ctx.send('Tracking failed')
        except Exception as e: 
            await ctx.send(f'有蟲蟲(Bug)出現了:< 請稍後再試 (reason: {str(e)})')
            traceback.print_exc()
            print(resp_json)


async def setup(bot):
    await bot.add_cog(ApiCog(bot))

