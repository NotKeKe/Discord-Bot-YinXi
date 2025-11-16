# 基本上小功能的，需要用到 playwright 的，都在這裡管理
# 此處變數於 newbot2.py 的 bot.event 管理
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright, Page
from typing import Optional, Literal, Any
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
import orjson
import asyncio
import logging

from core.functions import yinxi_base_url

logger = logging.getLogger(__name__)

p: Optional[Playwright] = None
browser: Optional[Browser] = None

contexts: dict[BrowserContext, dict[str, Any]] = {}

UA_TYPE = Literal['normal', 'yinxi']

class UserAgent:
    normal = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36 OPR/70.0.3728.119'
    yinxi = f"YinXiBOT ({yinxi_base_url})"

def get_ua(ua_type: UA_TYPE) -> str:
    if hasattr(UserAgent, ua_type):
        return getattr(UserAgent, ua_type)
    else:
        return UserAgent.yinxi

async def _get_p() -> Playwright:
    global p
    if not p:
        p = await async_playwright().start()
    return p

async def _get_browser() -> Browser:
    global browser
    if not browser:
        p = await _get_p()
        browser = await p.chromium.launch(headless=True)
    return browser

async def get_context(ua_type: UA_TYPE = 'yinxi', cookie_file: str | Path = '', purpose: str = 'Unknown') -> BrowserContext:
    browser = await _get_browser()

    # 先檢查有沒有相同 purpose 的 context
    for context, data in contexts.items():
        if data['purpose'] == purpose:
            contexts[context]['last_used'] = datetime.now()
            return context

    # 沒有則創建新的 context
    context = await browser.new_context(
        user_agent=get_ua(ua_type)
    )

    # add cookie
    if cookie_file:
        async with aiofiles.open(cookie_file, 'rb') as f:
            cookies = orjson.loads(await f.read())
        if cookies:
            await context.add_cookies(cookies)

    logger.info('Got a context')

    contexts[context] = {
        'ua_type': ua_type,
        'create_at': datetime.now(),
        'last_used': datetime.now(),
        'purpose': purpose # 用途
    }
    return context

async def get_page(context: BrowserContext, url: str) -> Page:
    if context not in contexts:
        raise ValueError('You are using a unmanaged context.')
    
    logger.info('Got a page.')

    contexts[context]['last_used'] = datetime.now()
    page = await context.new_page()
    await page.goto(url)
    return page

async def _close_context():
    try:
        global contexts
        while True:
            closed_count = 0
            for context, data in contexts.items():
                if data['last_used'] < datetime.now() - timedelta(minutes=5):
                    await context.close()
                    del contexts[context]
                    closed_count += 1

            if closed_count:
                logger.info(f'Closed {closed_count} contexts')

            await asyncio.sleep(60)
    except asyncio.CancelledError:
        pass

async def _close_browser():
    try:
        global browser, p
        while True:
            await asyncio.sleep(30)
            if not contexts:
                if browser:
                    await browser.close()
                    browser = None
                    logger.info('Closed global browser')

                if p:
                    await p.stop()
                    p = None
                    logger.info('Closed global playwright')
    except asyncio.CancelledError:
        pass

close_context_task = asyncio.create_task(_close_context())
close_browser_task = asyncio.create_task(_close_browser())