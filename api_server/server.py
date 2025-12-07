from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import time
import sqlite3
import os
import sys
import uvicorn
from pathlib import Path

# 獲取當前腳本的目錄 (/app/api_server)
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# 獲取專案的根目錄 (/app)
project_root_dir = os.path.abspath(os.path.join(current_script_dir, '..'))
 
# 將專案根目錄加入到 Python 的搜尋路徑中
sys.path.insert(0, project_root_dir)

from core.functions import read_json, current_time, BASE_DIR
from core.setup_log import LOG_CONFIG

app = FastAPI()
templates = Jinja2Templates(directory="templates")
alive = time.time()
app.mount("/assests", StaticFiles(directory="assests"), name="assests")

# Create SQLite database and table
def init_snoymous_messages_db():
    conn = sqlite3.connect('./data/anonymous_messages.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    conn.commit()
    conn.close()

init_snoymous_messages_db()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {'request': request})

@app.get('/api/llm/tools')
async def get_tools():
    data = read_json('./cmds/AIsTwo/data/tools_descrip.json')
    return data

@app.get('/api/image/')
async def get_image_from_path(path: str = Query(..., min_length=5)):
    path = Path(path).resolve()

    if os.path.isfile(path) and path.startswith(BASE_DIR):
        return FileResponse(path)
    else:
        raise HTTPException(404, f'檔案不存在 ({path=}) (使用絕對路徑試試看)')

@app.get('/discord', response_class=RedirectResponse)
async def direct_to_discord_server():
    return RedirectResponse('https://discord.gg/MhtxWJu')

@app.get('/github', response_class=RedirectResponse)
async def direct_to_yinxi_github():
    return RedirectResponse('https://github.com/NotKeKe/Discord-Bot-YinXi')

@app.get('/s_url', response_class=RedirectResponse)
async def short_url():
    return RedirectResponse('https://ke.rf.gd')

@app.get('/test', response_class=FileResponse)
async def test_file_return():
    return FileResponse('./image/discord_embed_author.png')

@app.get('/anonymous', response_class=HTMLResponse)
async def anonymous_messages(request: Request):
    # Retrieve all messages from the database
    conn = sqlite3.connect('./data/anonymous_messages.db')
    c = conn.cursor()
    c.execute('SELECT * FROM messages')
    messages = c.fetchall()
    conn.close()

    # Convert messages to a list of dictionaries
    message_list = []
    for message in messages:
        message_list.append({
            "id": message[0],
            "name": message[1],
            "message": message[2],
            "timestamp": message[3]
        })

    return templates.TemplateResponse("anonymous.html", {"request": request, "messages": message_list})

@app.post('/anonymous', response_class=HTMLResponse)
async def submit_message(request: Request, name: str = Form(...), message: str = Form(...)):
    # Insert the new message into the database
    conn = sqlite3.connect('./data/anonymous_messages.db')
    c = conn.cursor()
    c.execute('INSERT INTO messages (name, message) VALUES (?, ?)', (name, message))
    conn.commit()
    conn.close()

    # Redirect back to the anonymous message board
    return RedirectResponse(url='/anonymous', status_code=303)

@app.get('/ping')
async def check_alive():
    '''Check My bot is alive'''
    if time.time() - alive > 90:
        raise HTTPException(404, 'Discord Bot is offline')
    else:
        return {'status': 'online', 'check_time': current_time()}

uvicorn.run(app, host="0.0.0.0", port=3000, log_level='info')