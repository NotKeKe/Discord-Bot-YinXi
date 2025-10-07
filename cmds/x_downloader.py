from discord.ext import commands
from playwright.async_api import async_playwright, Route, Request, Browser, BrowserContext, Playwright, Page
import os
import orjson
import asyncio
from pathlib import Path
import httpx
import traceback
import aiofiles
from typing import Literal

from core.classes import Cog_Extension

VIDEO_EXTENSIONS = [".mp4", ".webm", ".mov", ".mkv", ".m3u8"]
VIDEO_MIMES = ["video/mp4", "video/webm", "application/x-mpegurl", "video/quicktime"]

COOKIE_FILE_PATH = Path('./data/cookies/x.json')
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'

class Donwloader:
    def __init__(self):
        self.playwright: Playwright = None
        self.broswer: Browser = None
        self.context: BrowserContext = None

    async def init_broswer(self):
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)

        cookie_or_status = await self.get_cookie()

        if isinstance(cookie_or_status, bool) and cookie_or_status is False:
            context = await browser.new_context(
                user_agent=USER_AGENT,
                storage_state=COOKIE_FILE_PATH
            )
        elif isinstance(cookie_or_status, list):
            context = await browser.new_context(
                user_agent=USER_AGENT,
            )
            await context.add_cookies((await self.get_cookie()))
        else:
            raise ValueError('Unknown cookie file')
        
        self.broswer = browser
        self.context = context

    async def clean_broswer(self):
        if self.context:
            await self.context.close()
        if self.broswer:
            await self.broswer.close()
        if self.playwright:
            await self.playwright.stop()

    def is_video_request(self, request: Request):
        url = request.url.lower()
        mime = request.headers.get("content-type", "").lower()
        return any(ext in url for ext in VIDEO_EXTENSIONS) or any(m in mime for m in VIDEO_MIMES)

    async def download_video(self, url: str, download_dir: str = "videos"):
        os.makedirs(download_dir, exist_ok=True)
        filename = os.path.join(download_dir, url.split("/")[-1].split("?")[0])

        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(filename, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            print(f"✅ Downloaded: {filename}")
        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")

    async def get_cookie(self) -> list | bool:
        async with aiofiles.open(COOKIE_FILE_PATH, "rb") as f:
            raw_cookies = orjson.loads((await f.read()))
            if not isinstance(raw_cookies, list): # playwright 存回去之後就會變這樣，變為使用 storage_state
                return False

        # 轉換格式
        playwright_cookies = []
        for c in raw_cookies:
            cookie = {
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
                "secure": c.get("secure", False),
                "httpOnly": c.get("httpOnly", False),
                "sameSite": c.get("sameSite", 'None'),
                "expires": int(c.get("expirationDate", 0))  # Playwright expects seconds
            }
            playwright_cookies.append(cookie)
        return playwright_cookies
    
    async def write_cookie(self, cookie: list):
        async with aiofiles.open(COOKIE_FILE_PATH, 'wb') as f:
            await f.write(orjson.dumps(cookie, option=orjson.OPT_INDENT_2))

    async def get_video(self, url: str, page: Page):
        final_url = 'No Result'
        async def handle_route(route: Route):
            req = route.request
            if self.is_video_request(req):
                nonlocal final_url
                final_url = req.url
                # await self.download_video(req.url, download_dir)
            await route.continue_()

        await page.route("**/*", handle_route)
        await page.goto(url)
        await page.wait_for_selector("video")
        return final_url
    
    async def get_image(self, url: str, page: Page):
        final_url = 'No Result'
        selector = 'article[tabindex="-1"] >> img.css-9pa8cd[alt]:not([alt=""])'
        srcs = []

        await page.goto(url)
        await page.wait_for_selector(selector)

        imgs = await page.query_selector_all(selector)
        for i, img in enumerate(imgs):
            src = await img.get_attribute("src")
            srcs.append(src) if src else None

        return '\n'.join(srcs) or final_url

    async def run(self, url: str, type: Literal['image', 'video'] = 'image', download_dir="videos") -> str:
        try:
            try:
                page = await self.context.new_page()
            except:
                page = None
                raise

            if type == 'video':
                final_url = await self.get_video(url, page)
            else:
                final_url = await self.get_image(url, page)

            cookie = await self.context.storage_state()
            asyncio.create_task(self.write_cookie(cookie))

            return final_url
        except:
            traceback.print_exc()
        finally:
            if page:
                await page.close()

x_downloader = Donwloader()

class XDownloader(Cog_Extension):
    async def cog_load(self):
        print(f'已載入「{__name__}」')
        await x_downloader.init_broswer()

    async def cog_unload(self):
        await x_downloader.clean_broswer()

    @commands.hybrid_command()
    async def x_download(self, ctx: commands.Context, url: str, type: Literal['image', 'video']):
        async with ctx.typing():
            if not url.startswith('https://x.com/'): return await ctx.send('Invalid URL. Please provide a valid URL starting with https://x.com/')
            url = await x_downloader.run(url.strip(), type)
        
            await ctx.send(url)

async def setup(bot):
    await bot.add_cog(XDownloader(bot))