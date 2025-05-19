# 收集funcs

from datetime import datetime, timezone, timedelta
from discord.ext import commands
import orjson
import ast
import operator
import duckduckgo_search
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import Optional
import sqlite3

from core.functions import read_json, current_time, UnixToReadable
from cmds.AIsTwo.others.func import image_generate, video_generate, image_read
from cmds.AIsTwo.tools import sql_create

# 定義支援的運算
ops = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod
}
# 模仿使用者 (for search)
ua = UserAgent()

func_map = {}

def discord_whereAmI(guild_name:str, channel_name:str) -> str:
    return f"你在 「{guild_name}」的 {channel_name} 頻道當中"

# 尚未連接json檔案 因此取消使用
def weather() -> str:
    WEATHER_PATH = None
    data = read_json(WEATHER_PATH)
    updateTimeUnix = data['UpdateTime']
    updateTime = UnixToReadable(updateTimeUnix)
    result = f"現在時間: {current_time()}, 更新時間: {updateTime}, 查詢結果: {data['Summarize']}"
    return result

def calculate(expression: str) -> str:
    """計算一個包含多個數字的四則運算表達式"""
    try:
        tree = ast.parse(expression, mode='eval')  # 解析表達式為 AST
        result = eval_expr(tree.body)  # 遞迴解析 AST
        if str(result).endswith('.0'):
            return int(result)  # 如果是整數則轉為 int
        else:
            return result
    except Exception:
        return "無效的數學表達式"

def eval_expr(node):
    """遞迴解析 AST (Abstract Syntax Tree)"""
    if isinstance(node, ast.BinOp) and type(node.op) in ops:
        # 如果是運算符節點，遞迴計算左邊與右邊的數字
        return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
    elif isinstance(node, ast.Num):
        # 如果是數字節點，直接返回數字
        return node.n
    else:
        return '沒有計算結果，請自己計算。'
    
def knowledge_base_search(keywords: str) -> str:
    """利用關鍵詞尋找資料庫中的答案 keywords: separated by a space."""
    # 拆分keywords
    tags = [f'\"{tag.strip().lower().replace(",", "，")}\"' for tag in keywords.split()]
    print(tags)

    # 在資料庫中查詢資訊
    connection, cursor = sql_create.knowledge_base()
    cursor.execute(f"SELECT question, answer, source FROM knowledge WHERE tags IN ({', '.join(tags)})")
    rows = cursor.fetchall()
    connection.close()

    if not rows: return ''
    result = []
    for row in rows:
        result.append(f"question: {row[0]}, answer :{row[1]} , link: {row[2]}\n")
    return ''.join(result)

def knowledge_base_save(question: str, answer: str, tags: str, source: str = None):
    '''將知識儲存進知識庫中 tags: separated by a comma.'''
    tags = tags.lower()

    connection, cursor = sql_create.knowledge_base()

    cursor.execute("INSERT INTO knowledge (question, answer, tags, source) VALUES (?, ?, ?, ?)",
               (question, answer, tags, source))
    connection.commit()
    connection.close()

def search(keywords: str, time_range: str = 'year', language: str = 'zh-TW') -> str:
    # 先查資料庫中有沒有對應的資料 再進行搜尋
    # sql_data = knowledge_base_search(keywords)
    # result = [sql_data] if sql_data else []
    result = []
    time_range = 'day' if time_range.lower().strip() not in ('year', 'monuth', 'week', 'day') else time_range.lower().strip()

    url = 'http://192.168.31.99:8080'
    params = {
        'q': keywords,
        'format': 'json',
        'safesearch': 2,
        'time_range': time_range,
        'language': language
    }

    response = requests.get(url, params=params)
    data = orjson.loads(response.content)
    urls = [item['url'] for item in data['results']][:10]

    def scrape_page(url):
        headers = {"User-Agent": 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")

        titleObj = soup.find("title")
        if titleObj is None: return None, None
        title = titleObj.text
        paragraphs = [p.text for p in soup.find_all("p")]
        content = "\n".join(paragraphs)

        return title, content

    
    for url in urls:
        try:
            if url.endswith('.pdf'): continue
            title, content = scrape_page(url)
            if title is None and content is None: continue
            result.append(f"標題: {title}\n內容: {content[:400]}...\n連結: {url}\n")  # 只顯示前200字
        except Exception as e:
            print(f"爬取失敗: {url}, 錯誤: {e}")

    if not result: raise 'No answer'
    return '\n'.join(result)

def wiki_searh(query: str):
    # 先用 search 找到相關的頁面標題
    search_url = "https://zh.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json"
    }

    search_response = requests.get(search_url, params=search_params)
    search_data = search_response.json()

    # 取得第一個搜尋結果的標題
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

    extract_response = requests.get(extract_url, params=extract_params)
    extract_data = extract_response.json()

    # pp(extract_data)

    # 提取純文字內容
    pages = extract_data["query"]["pages"]

    # print(len(pages)) # 1
    return '\n\n\n'.join([pages[page_id]["extract"] for page_id in pages])

if __name__ == '__main__':
    print(current_time())