import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks

import aiohttp
from pprint import pp
import traceback
from datetime import datetime
from deep_translator import GoogleTranslator
import typing
import os
import asyncio
import time
import base64
from PIL import Image
import io
import re
import aiofiles
from urllib.parse import urlparse, urljoin

from core.functions import thread_pool, read_json, create_basic_embed, download_image, secondToReadable
from core.translator import locale_str, load_translated
from core.functions import nasaApiKEY, NewsApiKEY, unsplashKEY, GIPHYKEY, testing_guildID
from core.playwright import get_context, get_page
from core.classes import Cog_Extension

youtube_download_base_url = None

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

    @staticmethod
    async def langs_for_gifs(_, interaction: discord.Interaction, current: str) -> typing.List[Choice[str]]:
        try:
            langs = {
                "Arabic": "ar", "Bengali": "bn", "Chinese Simplified": "zh-CN", "Chinese Traditional": "zh-TW",
                "Czech": "cs", "Danish": "da", "Dutch": "nl", "English": "en", "Farsi": "fa",
                "Filipino": "tl", "Finnish": "fi", "French": "fr", "German": "de", "Hebrew": "he",
                "Hindi": "hi", "Hungarian": "hu", "Indonesian": "id", "Italian": "it", "Japanese": "ja",
                "Korean": "ko", "Malay": "ms", "Norwegian": "no", "Polish": "pl", "Portuguese": "pt",
                "Romanian": "ro", "Russian": "ru", "Spanish": "es", "Swedish": "sv", "Thai": "th",
                "Turkish": "tr", "Ukrainian": "uk", "Vietnamese": "vi"
            }

            items = list(langs.items())

            if current:
                return [Choice(name=lang, value=code) for lang, code in items if lang in current.lower().strip()][:25]
            else:
                return [Choice(name=lang, value=code) for lang, code in items][:25]

        except: traceback.print_exc()



class ApiCog(Cog_Extension):
    class utils:
        @staticmethod
        def stringToDatetime(string: str) -> datetime:
            '''datetime.strptime(string, "%Y-%m-%d T%H:%M:%SZ")'''
            converted_datetime = datetime.strptime(string, "%Y-%m-%dT%H:%M:%SZ")
            return converted_datetime
        
    async def cog_load(self):
        print(f'已載入「{__name__}」')
        self.update_alive.start()

    async def cog_unload(self):
        self.update_alive.stop()
    
    @commands.hybrid_command(name=locale_str('joke'), description=locale_str('joke'), aliases=['jokes'])
    async def joke(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://sv443.net/jokeapi/v2/joke/Any') as response:
                    if response.status != 200:
                        return await ctx.send(await ctx.interaction.translate('send_api_request_failed'), ephemeral=True)
                    data = await response.json()
                    if data['error']:
                        return await ctx.send(await ctx.interaction.translate('send_api_error_retry'), ephemeral=True)
                    
                    joke_text = data['setup']
                    answer_text = data['delivery']

            translated_joke = await thread_pool(GoogleTranslator(source='auto', target='zh-TW').translate, joke_text)
            translated_answer = await thread_pool(GoogleTranslator(source='auto', target='zh-TW').translate, answer_text)
            
            '''i18n'''
            template = await ctx.interaction.translate('send_joke_template')
            ''''''

            await ctx.send(template.format(
                joke=joke_text,
                answer=answer_text,
                translated_joke=translated_joke,
                translated_answer=translated_answer
            ))

    @commands.hybrid_command(name=locale_str('news'), description=locale_str('news'), aliases=['新聞'])
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
    @app_commands.describe(
        options=locale_str('news_options'),
        question=locale_str('news_question'),
        language=locale_str('news_language'),
        country=locale_str('news_country'),
        輸出數量=locale_str('news_count')
    )
    async def news(self, ctx: commands.Context, options: int, question: str=None, language: str = 'zh', country: str='tw', 輸出數量: int=3):
        try:
            async with ctx.typing():
                if 輸出數量 > 5:
                    '''i18n'''
                    confirm_msg_template = await ctx.interaction.translate('send_news_too_many_confirm')
                    cancel_msg = await ctx.interaction.translate('send_news_confirm_cancelled')
                    ''''''
                    
                    view = discord.ui.View()
                    button1 = discord.ui.Button(label = "✅", style = discord.ButtonStyle.blurple)
                    button2 = discord.ui.Button(label='❌', style=discord.ButtonStyle.blurple)

                    async def button1_callback(interaction: discord.Interaction):
                        await interaction.response.defer()
                    async def button2_callback(interaction: discord.Interaction):
                        await interaction.response.send_message(cancel_msg, ephemeral=True)
                        return

                    button1.callback = button1_callback
                    button2.callback = button2_callback
                    view.add_item(button1)
                    view.add_item(button2)
                    await ctx.send(confirm_msg_template.format(count=輸出數量), view=view, ephemeral=True)
                    await view.wait()

                if options == 1:
                    if not question:
                        return await ctx.send(await ctx.interaction.translate('send_news_question_required'), ephemeral=True)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://newsapi.org/v2/everything?q={question}&language={language}&apiKey={NewsApiKEY}') as response:
                            data = await response.json()
                elif options == 2:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://newsapi.org/v2/top-headlines?country={country}&apiKey={NewsApiKEY}') as response:
                            data = await response.json()

                if data['status'] != 'ok':
                    return await ctx.send((await ctx.interaction.translate('send_news_api_error')).format(reason=data.get('code', 'N/A')))
                
                result_count = data['totalResults']
                
                '''i18n'''
                embed_template_str = await ctx.interaction.translate('embed_news_search_results')
                embed_template = load_translated(embed_template_str)[0]
                article_template_str = await ctx.interaction.translate('embed_news_article')
                article_template = load_translated(article_template_str)[0]
                ''''''
                
                eb = create_basic_embed(title=embed_template['title'], color=ctx.author.color)
                eb.add_field(name=embed_template['field'][0]['name'], value=embed_template['field'][0]['value'].format(count=result_count))
                await ctx.send(embed=eb)

                for result in data["articles"][:輸出數量]:                    
                    eb = create_basic_embed(title=result["title"], description=result.get("content"), time=False)
                    eb.set_author(name=result["source"]['name'], url=result["url"])
                    eb.set_footer(text=article_template['footer'])
                    eb.set_image(url=result["urlToImage"])
                    eb.timestamp = self.utils.stringToDatetime(result["publishedAt"])
                    await ctx.send(embed=eb)
        except:
            traceback.print_exc()

    @commands.hybrid_command(name=locale_str('cat_fact'), description=locale_str('cat_fact'), aliases=['貓貓冷知識', 'cat', 'catfact'])
    async def cat_fact(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://catfact.ninja/fact?max_length=2000') as response:
                    result = await response.json()
            source = result['fact']
            translated = await thread_pool(GoogleTranslator(source='auto', target='zh-TW').translate, source)
            
            '''i18n'''
            template = await ctx.interaction.translate('send_cat_fact_template')
            ''''''
            
            await ctx.send(template.format(translated_fact=translated, original_fact=source))

    @commands.hybrid_command(name=locale_str('nasa'), description=locale_str('nasa'), aliases=['nasa每日圖片'])
    async def nasa(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.nasa.gov/planetary/apod?api_key={nasaApiKEY}') as response:
                    data = await response.json()
            
            title = data['title']
            url = data['url']
            date = data["date"]
            explanation = data["explanation"]
            translated_explanation = await thread_pool(GoogleTranslator(source='auto', target='zh-TW').translate, explanation)

            await download_image(url, 'nasa_apod.jpg')
            file = discord.File(fp='./cmds/data.json/nasa_apod.jpg', filename='nasa_apod.png')
            os.remove('./cmds/data.json/nasa_apod.jpg')
            
            '''i18n'''
            embed_template_str = await ctx.interaction.translate('embed_nasa_apod')
            embed_template = load_translated(embed_template_str)[0]
            desc_template = await ctx.interaction.translate('send_nasa_explanation_template')
            ''''''

            eb = create_basic_embed(title=title, description=desc_template.format(translated_explanation=translated_explanation, original_explanation=explanation), time=False)
            eb.set_image(url='attachment://nasa_apod.png')
            eb.set_footer(text=embed_template['footer'].format(date=date))
            await ctx.send(file=file, embed=eb)

    @commands.hybrid_command(name=locale_str('number_history'), description=locale_str('number_history'), aliases=['num_history', 'n_history'])
    @app_commands.describe(number=locale_str('number_history_number'))
    async def number_history(self, ctx: commands.Context, number: int):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://numbersapi.com/{number}?json') as response:
                    data = await response.json()
            if not data['found']:
                return await ctx.send((await ctx.interaction.translate('send_number_history_not_found')).format(number=number))
            
            text = data["text"]
            translated = await thread_pool(GoogleTranslator(source='auto', target='zh-TW').translate, text)
            
            '''i18n'''
            template = await ctx.interaction.translate('send_number_history_template')
            ''''''
            
            await ctx.send(template.format(number=number, translated_text=translated, original_text=text))

    @commands.hybrid_command(name=locale_str('unsplash_image'), description=locale_str('unsplash_image'), aliases=['photo', 'image', '看圖'])
    @app_commands.describe(query=locale_str('unsplash_image_query'), num=locale_str('unsplash_image_num'))
    async def unsplash_image(self, ctx: commands.Context, query: str=None, num: int=1):
        async with ctx.typing():
            urls = []
            async with aiohttp.ClientSession() as session:
                if query:
                    async with session.get(f'https://api.unsplash.com/search/photos?query={query}&client_id={unsplashKEY}') as response:
                        data = await response.json()
                        for index, photo in enumerate(data['results'][:num]):
                            urls.append(f"作者: [{photo['user']['username']}](<{photo['user']['links']['html']}>)")
                            urls.append(f"[圖片連結{index+1}]({photo['urls']['regular']})")
                else:
                    async with session.get(f'https://api.unsplash.com/photos/random?client_id={unsplashKEY}') as response:
                        data = await response.json()
                        urls.append(f"作者: [{data['user']['username']}](<{data['user']['links']['html']}>)")
                        urls.append(f"[圖片連結]({data['urls']['regular']})")
            
            result = '\n'.join(urls)
            if not result:
                result = await ctx.interaction.translate('send_unsplash_no_results')
            await ctx.send(result)

    @commands.hybrid_command(name=locale_str('get_gifs'), description=locale_str('get_gifs'), aliases=['gif'])
    @app_commands.describe(query=locale_str('get_gifs_query'), num=locale_str('get_gifs_num'), lang=locale_str('get_gifs_lang'))
    @app_commands.autocomplete(lang = select_autocomplete.langs_for_gifs)
    async def get_gifs(self, ctx: commands.Context, query: str=None, num: int=1, lang: str = None):
        async with ctx.typing():
            if num > 50:
                return await ctx.send(await ctx.interaction.translate('send_gif_too_many'), ephemeral=True) 

            search_url = 'https://api.giphy.com/v1/gifs/search'
            random_url = 'https://api.giphy.com/v1/gifs/random'
            results = []

            async with aiohttp.ClientSession() as session:
                if query:
                    params = {'api_key': GIPHYKEY, 'q': query, 'limit': num}
                    if lang:
                        params['lang'] = lang
                    async with session.get(search_url, params=params) as resp:
                        data = await resp.json()
                        for item in data['data']:
                            results.append((item['title'], item['images']['original']['url']))
                else:
                    async with session.get(random_url, params={'api_key': GIPHYKEY}) as resp:
                        data = await resp.json()
                        results.append((data['data']['title'], data['data']['images']['original']['url']))
            
            if not results:
                return await ctx.send(await ctx.interaction.translate('send_gif_no_results'))

            def strip_title(title: str) -> str:
                if isinstance(title, str): return title.strip()
                return None

            await ctx.send('\n'.join([
                    f'[{strip_title(title) if strip_title(title) else "gif"}]({url})' for title, url in results
                    ])
                )

    @commands.hybrid_command(name=locale_str('tiangou'), description=locale_str('tiangou'), aliases=['舔狗'])
    async def tiangou(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as sess:
                async with sess.get('https://api.zxki.cn/api/tgrj') as resp:
                    if resp.status != 200:
                        return await ctx.send(await ctx.interaction.translate('send_tiangou_api_error'), ephemeral=True)
                    text = await resp.text()
                    translated_text = await thread_pool(GoogleTranslator(source='auto', target='zh-TW').translate, text)
                    await ctx.send(translated_text)

    @commands.hybrid_command(name=locale_str('minecraft_server_status'), description=locale_str('minecraft_server_status'), aliases=['mc_status'])
    @app_commands.choices(edition=[Choice(name=edit, value=edit) for edit in ('java', 'bedrock')])
    @app_commands.describe(address=locale_str('minecraft_server_status_address'), edition=locale_str('minecraft_server_status_edition'))
    async def minecraft_server_status(self, ctx: commands.Context, address: str, edition: str = 'java'):
        try:
            if edition not in ('java', 'bedrock'): return await ctx.send(await ctx.interaction.translate('send_mc_status_invalid_edition'))
            async with ctx.typing():
                async with aiohttp.ClientSession() as sess:
                    url = f'https://api.mcsrvstat.us/3/{address}' if edition == 'java' else f'https://api.mcsrvstat.us/bedrock/3/{address}'
                    async with sess.get(url) as resp:
                        if resp.status != 200: return await ctx.send(await ctx.interaction.translate('send_mc_status_api_error'), ephemeral=True)
                        data = await resp.json()
                
                    ip = data.get('ip', 'None')
                    port = data.get('port', 'None')
                    hostname = data.get('hostname', 'None')

                    icon = data.get('icon', 'None')
                    gamemode = data.get('gamemode', 'None')
                    players = data.get('players', 'None') # dict
                    version = data.get('version', 'None')
                    plugins = data.get('plugins', 'None') # list
                    mods = data.get('mods', 'None') # list
                    online = None
                    max_player = None
                    file = None

                    if players != 'None':
                        online = players.get('online')
                        max_player = players.get('max')
                    if icon != 'None':
                        # 使用正則表達式去掉開頭的識別字串
                        base64_pattern = r"^data:image\/png;base64,"
                        clean_base64_data = re.sub(base64_pattern, "", icon)
                        if clean_base64_data:
                            # 解碼 Base64 並轉換為 PIL 圖像
                            image_bytes = base64.b64decode(clean_base64_data)
                            image = Image.open(io.BytesIO(image_bytes))

                            # 轉換為 Discord 可用的文件物件
                            image_buffer = io.BytesIO()
                            image.save(image_buffer, format="PNG")
                            image_buffer.seek(0)

                            # 建立 Discord Embed 並設定圖片
                            file = discord.File(image_buffer, filename="icon.png")

                '''i18n'''
                eb_template = await ctx.interaction.translate('embed_mc_server_status')
                eb_template = load_translated(eb_template)[0]
                title_str = eb_template['title']
                field = eb_template['fields']
                online_str = field[0]['name']
                ip_str = field[1]['name']
                host_name_str = field[2]['name']
                gamemode_str = field[3]['name']
                online_player_str = field[4]['name']
                max_player_str = field[5]['name']
                version_str = field[6]['name']
                plugins_str = field[7]['name']
                mods_str = field[8]['name']

                button_str = await ctx.interaction.translate('button_mc_status_show_details')
                ''''''

                eb = create_basic_embed(功能=title_str, color=ctx.author.color)
                view = discord.ui.View()

                eb.add_field(name=online_str, value=str(data.get('online')))
                eb.add_field(name=ip_str, value=f"{ip}:{port}")
                eb.add_field(name=host_name_str, value=hostname)
                eb.add_field(name=gamemode_str, value=gamemode)
                eb.add_field(name=online_player_str, value=online)
                eb.add_field(name=max_player_str, value=max_player)
                eb.add_field(name=version_str, value=version)
                def format_list_field(items, limit=1020):
                    if isinstance(items, list):
                        joined = ', '.join(item['name'] for item in items)
                        return (joined[:limit - 3] + '...') if len(joined) > limit else joined
                    return items
                eb.add_field(name=plugins_str, value=format_list_field(plugins))
                eb.add_field(name=mods_str, value=format_list_field(mods))
                eb.set_image(url="attachment://icon.png" if file else file)
                eb.set_footer(text=url)

                if 'None' in (mods, plugins) and ( isinstance(mods, list) or isinstance(plugins, list) ):
                    button = discord.ui.Button(label=button_str.format(type=mods_str if mods != 'None' else plugins_str), style=discord.ButtonStyle.blurple)
                    async def button_callback(interaction: discord.Interaction, *args):
                        text = '\n'.join([f"{item['name']} - {item['version']}" for item in (mods if mods != 'None' else plugins)])
                        path = './data/temp'
                        new_path = f'{path}/minecraft_server_status_{ctx.author.id}.txt'

                        async with aiofiles.open(new_path, mode='w', encoding='utf-8') as f:
                            await f.write(text)

                        file = discord.File(new_path, f'minecraft_server_status_{ctx.author.id}.txt')

                        await interaction.response.send_message(file=file)
                        await asyncio.sleep(300)
                        
                        try: os.remove(new_path)
                        except: ...
                    button.callback = button_callback
                    view.add_item(button)

                await ctx.send(embed=eb, file=file, view=view)
        except Exception as e:
            traceback.print_exc()
            return await ctx.send((await ctx.interaction.translate('send_mc_status_error')).format(reason=e))
        
    @commands.hybrid_command(name=locale_str('yiyan'), description=locale_str('yiyan'), aliases=['一言'])
    async def yiyan(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://v1.hitokoto.cn/?c=d&c=e&c=f&encode=text') as resp:
                    if not resp.status == 200:
                        return await ctx.send(await ctx.interaction.translate('send_yiyan_api_error'), ephemeral=True)
                    data = await resp.text()
            
            translated_text = await thread_pool(GoogleTranslator(source='auto', target='zh-TW').translate, data)
            await ctx.send(translated_text)

    @commands.hybrid_command(name=locale_str('toxic_jacket_soup'), description=locale_str('toxic_jacket_soup'), aliases=['毒雞湯'])
    async def toxic_jacket_soup(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.btstu.cn/yan/api.php?charset=utf-8&encode=text') as resp:
                    if resp.status != 200:
                        return await ctx.send(await ctx.interaction.translate('send_toxic_soup_api_error'), ephemeral=True)
                    text = await resp.text()
            
            translated_text = await thread_pool(GoogleTranslator(source='auto', target='zh-TW').translate, text)
            await ctx.send(translated_text)

    @commands.hybrid_command(name=locale_str('lovelive'), description=locale_str('lovelive'), aliases=['love'])
    async def lovelive(self, ctx: commands.Context):
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.lovelive.tools/api/SweetNothings') as resp:
                    if resp.status != 200:
                        return await ctx.send(await ctx.interaction.translate('send_lovelive_api_error'), ephemeral=True)
                    text = await resp.text()
            await ctx.send(text)

    @commands.hybrid_command(name=locale_str('yt_downloader'), description=locale_str('yt_downloader'), aliases=['yt_download', 'ytdownload', '影片下載'])
    @app_commands.guilds(discord.Object(testing_guildID))
    @app_commands.choices(
        type = [Choice(name=s, value=s) for s in ('mp4', 'mp3')],
        quality = [Choice(name=s, value=s) for s in ('high', 'medium', 'low')]
    )
    @app_commands.describe(
        url=locale_str('yt_downloader_url'),
        type=locale_str('yt_downloader_type'),
        quality=locale_str('yt_downloader_quality')
    )
    async def yt_downloader(self, ctx: commands.Context, url: str, type: str = 'mp3', quality: str = None):
        try:
            async with ctx.typing():
                data = {
                    "url": url, 
                    "media_type": type,
                    "quality": quality
                }

                async with aiohttp.ClientSession() as sess:
                    async with sess.post(f'{youtube_download_base_url}/api/download', json=data) as resp:
                        if resp.status == 404:
                            return await ctx.send(await ctx.interaction.translate('send_yt_download_api_offline'))
                        resp_json = await resp.json()
                        task_id = resp_json.get('task_id')

                await ctx.send((await ctx.interaction.translate('send_yt_download_tracking')).format(task_id=task_id))

                for _ in range(10):
                    await asyncio.sleep(3)

                    async with aiohttp.ClientSession() as sess:
                        async with sess.get(f'{youtube_download_base_url}/api/status/{task_id}') as resp:
                            resp_json = await resp.json()
                            status = resp_json.get('status')
                            if status == 'error': 
                                reason = resp_json.get('message')
                                if 'NSFW' in reason:
                                    return await ctx.send(await ctx.interaction.translate('send_yt_download_nsfw_error'))
                                else:
                                    return await ctx.send((await ctx.interaction.translate('send_yt_download_error')).format(reason=reason))
                            if status == 'started': continue
                            
                            info = resp_json.get('info')
                            
                            '''i18n'''
                            embed_template_str = await ctx.interaction.translate('embed_yt_downloader')
                            embed_template = load_translated(embed_template_str)[0]
                            ''''''
                            
                            eb = create_basic_embed(embed_template['title'].format(type=type.upper()), color=ctx.author.color)

                            fields = embed_template['fields']
                            eb.add_field(name=fields[0]['name'], value=f"[{fields[0]['name']}]({resp_json.get('source_url')})")
                            eb.add_field(name=fields[1]['name'], value=secondToReadable(info.get('duration')))
                            eb.add_field(name=fields[2]['name'], value=int(resp_json.get('process_time')))
                            
                            eb.set_image(url=info.get('thumbnail'))
                            eb.set_footer(text=embed_template['footer'])

                            await ctx.send(f"[下載連結]({resp_json.get('download_url')})", embed=eb)
                            return
                
                await ctx.send(await ctx.interaction.translate('send_yt_download_tracking_failed'))
        except Exception as e: 
            await ctx.send((await ctx.interaction.translate('send_mc_status_error')).format(reason=str(e)))
            traceback.print_exc()

    @commands.hybrid_command(name=locale_str('codlin_meme'), description=locale_str('codlin_meme'), aliases=['meme', 'codlin'])
    async def codlin_meme(self, ctx: commands.Context, *, text: str = '', count: int = 1):
        await ctx.defer()

        base_url = 'https://codlin.me/'
        context = await get_context(purpose='codlin_meme')
        page = await get_page(context, urljoin(base_url, 'aquarium/meme-cache/'))

        await page.wait_for_selector('input')
        locator = page.locator('input')
        
        await locator.fill(text)

        await page.wait_for_load_state('networkidle')
        
        img_locator = page.locator('img')
        img_count = await img_locator.count()

        async def fetch(i):
            try:
                img = await img_locator.nth(i).get_attribute('src', timeout=300)
                img_url = urljoin(base_url, img)
                return img_url
            except Exception as e:
                print(f'Cannot fetch image at {i}, error: {e}')
        
        tasks = []
        for i in range(min(count, img_count)):
            tasks.append(fetch(i))

        urls = await asyncio.gather(*tasks)

        await ctx.send('\n'.join(urls) or 'No Results')

        await page.close()


    @tasks.loop(minutes=1)
    async def update_alive(self):
        global alive
        alive = time.time()

async def setup(bot):
    await bot.add_cog(ApiCog(bot))
