import markdown
from bs4 import BeautifulSoup
import asyncio
from pathlib import Path
import base64
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# 假設字體檔名 (請根據您下載的檔案名稱修改)
font_file_path = Path('./assests/fonts/Iansui-Regular.ttf')
with open(font_file_path, "rb") as f:
    font_base64 = base64.b64encode(f.read()).decode("utf-8")

css_style = f"""
<style>
    @font-face {{
        font-family: 'Iansui';
        src: url(data:font/ttf;base64,{font_base64}) format('truetype');
        font-display: swap; 
    }}
    body {{ 
        font-family: 'Iansui', 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
        padding: 30px; 
        background-color: #f8f8f8;
        text-align: center; /* **新增：讓內聯區塊 (.table-container) 水平居中** */
    }}
    .table-container {{
        padding: 20px;
        background-color: white;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        border-radius: 12px;
        /* 保持 inline-block */
        display: inline-block; 
        margin: 0; /* 移除 margin: auto 的需求 */
        /* 移除 overflow-x: auto; */
    }}
    .table-title {{
        margin-top: 30px;
        margin-bottom: 10px;
        color: #34495e;
        border-bottom: 2px solid #3498db;
        padding-bottom: 5px;
    }}
    .styled-markdown-table {{ 
        border-collapse: collapse; 
        /* **關鍵修改：移除 table-layout: fixed;** */
        /* 讓表格使用預設的 auto 佈局，隨著內容展開 */
        width: 100%; /* 讓表格充滿父容器 (table-container) */
        /* 移除 min-width: 800px; */
        margin: 0; /* 移除表格的 margin，避免多餘空間 */
        font-size: 14pt; 
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); 
        border-radius: 8px;
        overflow: hidden; 
    }}
    .spacer {{ height: 40px; }}
    .styled-markdown-table thead tr {{ background-color: #2c3e50; color: #ffffff; text-align: center; font-weight: bold; }}
    /* 調整 th/td 樣式：移除 word-break 和 max-width 限制，讓文字自由展開 */
    .styled-markdown-table th, .styled-markdown-table td {{ 
        padding: 15px 20px; 
        border: 1px solid #e0e0e0; 
        vertical-align: top; 
        line-height: 1.5; 
        text-align: left; 
        /* 移除強制斷行屬性 */
    }}
    .styled-markdown-table tbody tr:nth-of-type(even) {{ background-color: #fcfcfc; }}
    .styled-markdown-table tbody tr:hover {{ background-color: #e8f0fe; transition: background-color 0.3s ease; }}
</style>
"""

FULL_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>Multiple Tables Screenshot</title>
    {css_style}
</head>
<body>
    <div class="table-container">
        {html_content}
    </div>
</body>
</html>
"""

def _get_png(full_html: str) -> bytes:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage") 

    driver = webdriver.Chrome(options=options)
    try:
        driver.get("about:blank")
        driver.execute_script("document.write(arguments[0]);", full_html)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".table-container"))
        )
        driver.execute_script("document.body.style.overflow = 'hidden';")
        

        FINAL_WIDTH = driver.execute_script(
            "return Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);"
        )
        FINAL_HEIGHT = driver.execute_script(
            "return Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);"
        )

        FINAL_BUFFER = 40 
        
        FINAL_WIDTH += FINAL_BUFFER
        FINAL_HEIGHT += FINAL_BUFFER

        driver.execute_script("document.body.style.overflow = 'auto';")
        
        # 解析度設定
        driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
            "width": FINAL_WIDTH,
            "height": FINAL_HEIGHT,
            "deviceScaleFactor": 2,
            "mobile": False
        })

        # 調整視窗大小
        driver.set_window_rect(0, 0, FINAL_WIDTH, FINAL_HEIGHT)
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("""
            const sheets = [...document.styleSheets];
            return sheets.every(s => !s.href || s.cssRules.length > 0);
            """)
        )

        # 截圖
        screenshot = driver.execute_cdp_cmd("Page.captureScreenshot", {
            "format": "png",
            # "fromSurface": True
        })
        png_bytes = base64.b64decode(screenshot['data'])

    finally:
        driver.quit()

    return png_bytes

async def md_table_convert(text: str) -> bytes | None:
    # get full html
    text = text.strip()
    html = markdown.markdown(text, extensions=["tables"])
    if not html: return

    # find tables
    soup = BeautifulSoup(html, "html.parser")
    found_table = False
    tables = soup.find_all("table")
    for table in tables:
        table["class"] = table.get("class", []) + ["styled-markdown-table"]
        found_table = True
    if not found_table: return

    html_content = "".join([str(t) for t in tables])
    if not html_content: return
    full_html = FULL_HTML_TEMPLATE.format(css_style=css_style, html_content=html_content)

    # open selenium
    return await asyncio.to_thread(_get_png, full_html)