from aiohttp import ClientSession

async def wiki_searh(query: str):
    # 先用 search 找到相關的頁面標題
    search_url = "https://zh.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json"
    }

    async with ClientSession() as session:
        async with session.get(search_url, params=search_params) as resp:
            search_data = await resp.json()

    # 取得第一個搜尋結果的標題
    if not search_data["query"]["search"]: return '沒有找到結果'
    first_title = search_data["query"]["search"][0]["title"]

    # 用 extracts 來獲取純文字內容
    extract_url = "https://zh.wikipedia.org/w/api.php"
    extract_params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": True,
        "titles": first_title,
        "format": "json"
    }

    async with ClientSession() as session:
        async with session.get(extract_url, params=extract_params) as resp:
            extract_data = await resp.json()

    # pp(extract_data)

    # 提取純文字內容
    pages = extract_data["query"]["pages"]

    # print(len(pages)) # 1
    return '\n\n\n'.join([pages[page_id]["extract"] for page_id in pages])
