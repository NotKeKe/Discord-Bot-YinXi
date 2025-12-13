import discord
from discord import app_commands
from discord.ext import commands
from playwright.async_api import async_playwright
import os

from core.classes import Cog_Extension
from core.functions import testing_guildID
from core.translator import locale_str

AUTH_FILE = "auth.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/118.0.0.0 Safari/537.36"
)
# TARGET_USERNAME = "codm_link"

async def fetch(url: str):
    """
    使用 Playwright 啟動瀏覽器，處理登入狀態，並抓取 Instagram 頁面圖片。
    """
    async with async_playwright() as p:
        # 啟動 Chromium 瀏覽器，headless=False 會顯示瀏覽器 UI
        browser = await p.chromium.launch(headless=True)

        # 檢查是否存在已儲存的登入狀態
        if os.path.exists(AUTH_FILE):
            print(f"找到驗證檔案 '{AUTH_FILE}'，正在載入狀態...")
            context = await browser.new_context(
                storage_state=AUTH_FILE, user_agent=USER_AGENT
            )
        else:
            # 如果沒有，則引導使用者手動登入一次
            print(f"未找到驗證檔案 '{AUTH_FILE}'。")
            print("將會開啟瀏覽器，請手動登入一次以儲存登入狀態。")
            context = await browser.new_context(user_agent=USER_AGENT)
            page_for_login = await context.new_page()
            await page_for_login.goto("https://www.instagram.com/accounts/login/")
            
            print("-----------------------------------------------------------")
            print("請在彈出的瀏覽器視窗中登入您的 Instagram 帳號。")
            print("登入成功並看到 Instagram 主頁後，請不要關閉瀏覽器。")
            print("回到此終端機視窗，然後按下 Enter 鍵繼續...")
            print("-----------------------------------------------------------")
            input()  # 等待使用者按下 Enter

            # 儲存登入狀態
            await context.storage_state(path=AUTH_FILE)
            print(f"驗證狀態已成功儲存至 '{AUTH_FILE}'。")
            await page_for_login.close()

        # 使用已驗證的 context 開啟新分頁
        page = await context.new_page()

        print(f"正在前往目標頁面: {url}")
        # 使用 'load' 確保頁面資源都已載入，比 'domcontentloaded' 更可靠
        await page.goto(url, wait_until="load")
        print(f"已載入頁面: {await page.title()}")

        # --- 處理可能出現的 "開啟通知" 彈出視窗 ---
        try:
            # Instagram 常會彈出通知視窗，按鈕文字可能是 "Not Now"
            not_now_button = page.get_by_role("button", name="Not Now", exact=True)
            print("偵測到 'Not Now' 按鈕，正在點擊...")
            await not_now_button.click(timeout=2000) # 設定短超時，因為它不一定會出現
        except Exception:
            print("未找到 'Not Now' 按鈕，或已處理。")

        # --- 抓取大頭貼 ---
        print("正在擷取大頭貼 URL...")
        # 大頭貼是在 header 區塊中，位於 <a> 標籤內的 <img>，以和限時動態精選做區分
        profile_pic_locator = page.locator('header a img')
        try:
            # 增加等待時間到 10 秒，給予頁面更充裕的渲染時間
            await profile_pic_locator.wait_for(timeout=10000)
            profile_pic_url = await profile_pic_locator.get_attribute("src")
            if profile_pic_url:
                print(f"✅ 成功找到大頭貼 URL: {profile_pic_url}")
                return profile_pic_url
        except Exception as e:
            error_message = f"❌ 錯誤：找不到大頭貼。可能是頁面結構已變更、載入失敗或被彈出視窗遮擋。\n詳細錯誤: {e}"
            print(error_message)
            return error_message

class Instagram_fecher(Cog_Extension):
    @commands.hybrid_command(name=locale_str('ig_fetch'))
    @app_commands.guilds(discord.Object(id=testing_guildID))
    async def ig_fetch(self, ctx, ig_url: str):
        async with ctx.typing():
            url = await fetch(ig_url)
            await ctx.send(url)

async def setup(bot):
    await bot.add_cog(Instagram_fecher(bot))