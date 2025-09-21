from aiohttp import ClientSession
from asyncio import Lock
from aiolimiter import AsyncLimiter
import logging

from core.functions import yinxi_base_url

logger = logging.getLogger(__name__)

NO_RESULT = '沒有找到結果'

headers = {
    "User-Agent": f"YinXiBOT ({yinxi_base_url})",
    "Accept-Encoding": "gzip"
}
base_url = "https://zh.wikipedia.org/w/api.php"
 
lock = Lock()
limiter = AsyncLimiter(5, 1) # 每秒 5 個請求

async def wiki_searh(query: str) -> str:
    try:
        # 先用 search 找到相關的頁面標題
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }

        async with limiter:
            async with lock:
                async with ClientSession() as session:
                    async with session.get(base_url, params=search_params, headers=headers) as resp:
                        search_data = await resp.json()

                    # 取得第一個搜尋結果的標題
                    if not search_data["query"]["search"]: return NO_RESULT
                    first_title = search_data["query"]["search"][0]["title"]

                    # 用 extracts 來獲取純文字內容
                    extract_params = {
                        "action": "query",
                        "prop": "extracts",
                        "explaintext": "",
                        "titles": first_title,
                        "format": "json"
                    }

                    async with session.get(base_url, params=extract_params, headers=headers) as resp:
                        extract_data = await resp.json()

        # pp(extract_data)

        # 提取純文字內容
        pages = extract_data["query"]["pages"]

        # print(len(pages)) # 1
        return '\n\n\n'.join([pages[page_id].get('extract', '') for page_id in pages])
    except Exception as e:
        logger.error(f'Error accured {str(e)}: ', exc_info=True)
        return NO_RESULT
