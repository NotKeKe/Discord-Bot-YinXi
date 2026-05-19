from datetime import datetime, timezone, timedelta
from discord.ext import commands
import orjson
import ast
import operator
import duckduckgo_search
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from core.functions import read_json, current_time, UnixToReadable
from cmds.AIs.zhipu import image_generate

# 定義支援的運算
ops = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv
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
        tree = ast.parse(expression, mode='eval')
        result = eval_expr(tree.body)
        if str(result).endswith('.0'):
            return int(result)
        else:
            return result
    except Exception:
        raise ValueError("無效的數學表達式")

def eval_expr(node):
    '''
    這是一個歸在calculate底下的func
    '''
    """遞迴解析 AST (Abstract Syntax Tree)"""
    if isinstance(node, ast.BinOp) and type(node.op) in ops:
        return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
    elif isinstance(node, ast.Num):
        return node.n
    else:
        raise ValueError("不支援的運算式")

def search(keywords: str) -> str:
    results = duckduckgo_search.DDGS().text(keywords, max_results=15, region='tw-tzh')
    urls = [res["href"] for res in results]

    def scrape_page(url):
        headers = {"User-Agent": 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.find("title").text
        paragraphs = [p.text for p in soup.find_all("p")]
        content = "\n".join(paragraphs)

        return title, content

    result = []
    for url in urls:
        try:
            title, content = scrape_page(url)
            result.append(f"標題: {title}\n內容: {content[:400]}...\n")  # 只顯示前200字
        except Exception as e:
            print(f"爬取失敗: {url}, 錯誤: {e}")

    if not result: raise 'No answer'
    return '\n'.join(result)

func_map = {
    'current_time': current_time,
    'discord_whereAmI': discord_whereAmI,
    # 'weather': weather,
    'calculate': calculate,
    'search': search,
    'image_generate': image_generate
}

if __name__ == '__main__':
    print(current_time())