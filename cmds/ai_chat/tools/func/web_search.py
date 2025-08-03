from aiohttp import ClientSession
import orjson
from bs4 import BeautifulSoup

from core.functions import DEVICE_IP

NOT_AVAILABLE = 'web_search is not available'

async def web_search(keywords: str, time_range: str = 'year', language: str = 'zh-TW') -> str:
    # 先查資料庫中有沒有對應的資料 再進行搜尋
    # sql_data = knowledge_base_search(keywords)
    # result = [sql_data] if sql_data else []
    result = []
    time_range = ('day' if time_range.lower().strip() not in ('year', 'monuth', 'week', 'day') else time_range.lower().strip()) if time_range else None

    url = f'http://{DEVICE_IP}:8080'
    params = {
        'q': keywords,
        'format': 'json',
        'safesearch': 2,
        'language': language,
        **({'time_range': time_range} if time_range is not None and time_range != '' else {}),
    }

    async with ClientSession() as session:
        async with session.get(f'http://{DEVICE_IP}:8080', params=params) as resp:
            if resp.status != 200:
                return NOT_AVAILABLE
            
            try:
                data = await resp.json()
            except Exception as e:
                print(f'Error while calling web_search: {e}')
                return NOT_AVAILABLE
                
            
    urls = [item['url'] for item in data['results']][:10]

    async def scrape_page(url) -> str:
        headers = {"User-Agent": 'Mozilla/5.0'}

        async with ClientSession() as session:
            async with session.get(url, headers=headers, timeout=5) as resp:
                if resp.status != 200: return 'None', 'None'
                text = await resp.text()

        soup = BeautifulSoup(text, "html.parser")
        titleObj = soup.find("title")

        if titleObj is None: return None, None

        title = titleObj.text
        paragraphs = [p.text for p in soup.find_all("p")]
        content = "\n".join(paragraphs)

        return title, content

    
    for url in urls:
        try:
            if url.endswith('.pdf'): continue
            title, content = await scrape_page(url)
            if title is None and content is None: continue
            result.append(f"標題: {title}\n內容: {content[:400]}...\n連結: {url}\n")  # 只顯示前200字
        except Exception as e:
            print(f"爬取失敗: {url}, 錯誤: {e}")

    if not result: return "web_search didn't find any answer."

    return '\n'.join(result)