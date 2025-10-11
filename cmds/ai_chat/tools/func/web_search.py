from aiohttp import ClientSession, TCPConnector
import asyncio
from bs4 import BeautifulSoup

from core.functions import DEVICE_IP

NOT_AVAILABLE = 'web_search is not available'

searching_sem = asyncio.Semaphore(40)
headers = {"User-Agent": 'Mozilla/5.0'}

async def web_search(keywords: str, time_range: str = 'year', language: str = 'zh-TW') -> str:
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

    async def scrape_page(session: ClientSession, url) -> tuple[str, str, str]:
        try:
            async with searching_sem:
                async with session.get(url, headers=headers, timeout=5) as resp:
                    if resp.status != 200: return None, None, None
                    text = await resp.text()

                soup = BeautifulSoup(text, "html.parser")
                titleObj = soup.find("title")

                if titleObj is None: return None, None, None

                title = titleObj.text
                paragraphs = [p.text for p in soup.find_all("p")]
                content = "\n".join(paragraphs)

                return title, content, url
        except Exception as e:
            print(f"爬取失敗: {url}, 錯誤: {e}")
            return None, None, None

    async with ClientSession() as session:
        tasks = [scrape_page(session, url) for url in urls if not url.endswith('.pdf')]
        task_results = await asyncio.gather(*tasks)

    for title, content, url in task_results:
        if title is None and content is None: continue
        result.append(f"標題: {title}\n內容: {content[:400]}...\n連結: {url}\n\n")  # 只顯示前200字

    if not result: return "web_search didn't find any answer."

    return '\n'.join(result)