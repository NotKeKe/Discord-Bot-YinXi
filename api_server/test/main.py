import os
import uuid
import shutil
from typing import Dict, Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# 確保目錄存在
os.makedirs("musics", exist_ok=True)

# 1. 掛載靜態文件 (JS, CSS, 上傳的音檔)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/musics", StaticFiles(directory="musics"), name="musics")

# 2. 設定模板引擎
templates = Jinja2Templates(directory="templates")

# 3. Session 狀態管理 (Multi-tenant)
# 結構: { "guild_id_123": { "uuid": "...", "title": "...", ... } }
class SessionState:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id
        self.uuid = str(uuid.uuid4())
        self.title = "Waiting for Signal..."
        self.subtitle = "System Ready"
        self.audio_url = ""
        self.srt_content = ""
        self.current_time = 0

sessions: Dict[str, SessionState] = {}

def get_or_create_session(guild_id: str) -> SessionState:
    if guild_id not in sessions:
        sessions[guild_id] = SessionState(guild_id)
    return sessions[guild_id]

# --- Routes ---

@app.get("/player/{guild_id}_{page_uuid}", response_class=HTMLResponse)
async def player_page(request: Request, guild_id: str, page_uuid: str):
    """
    顯示特定 Guild 的播放器頁面。
    URL 範例: http://localhost:8000/player/123456_abcde-1234-uuid
    page_uuid 這裡主要作為連結的一次性或驗證用途，
    但主要邏輯依賴 guild_id 來區分狀態。
    """
    # 這裡將 guild_id 注入到 template 中，讓前端 JS 可以讀取

    if guild_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "guild_id": guild_id 
    })

@app.get("/check_song")
async def check_song(guild_id: str):
    """
    前端 JS 每秒輪詢的接口。
    必須帶上 ?guild_id=... 參數。
    """
    if guild_id not in sessions:
        # 如果該公會還沒建立過 session，可以回傳預設值或 404
        # 這裡選擇回傳一個空狀態，讓前端保持等待
        return JSONResponse(status_code=404, content={"message": "Session not found"})
    
    session = sessions[guild_id]
    return {
        "uuid": session.uuid,
        "title": session.title,
        "subtitle": session.subtitle,
        "audio_url": session.audio_url,
        "srt_content": session.srt_content,
        'current_time': session.current_time
    }

@app.post('/update_song')
async def update_song(guild_id: str = Form(...), current_time: int = Form(...)):
    """
    Discord Bot 或控制端呼叫此接口來更新狀態。
    必須提供 guild_id。
    """
    if guild_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = get_or_create_session(guild_id)
    # 2. 更新文字資訊
    session.current_time = current_time

    return {"message": "Song updated successfully"}

@app.post("/upload_song")
async def upload_song(
    guild_id: str = Form(...),
    title: str = Form(None),
    subtitle: str = Form(None),
    audio: UploadFile = File(...),
    srt: UploadFile = File(None)
):
    """
    Discord Bot 或控制端呼叫此接口來創建歌曲。
    必須提供 guild_id。
    """
    session = get_or_create_session(guild_id)
    
    # 1. 更新 UUID (觸發前端重整)
    session.uuid = str(uuid.uuid4())
    
    # 2. 更新文字資訊
    if title:
        session.title = title
    if subtitle:
        session.subtitle = subtitle

    # 3. 處理音檔 (儲存時建議加上 guild_id 前綴避免檔名衝突)
    # 清理舊檔邏輯可在此實作
    filename = f"{guild_id}_{audio.filename}"
    file_path = f"musics/{filename}"
    
    with open(file_path, "wb+") as file_object:
        shutil.copyfileobj(audio.file, file_object)
        
    session.audio_url = f"/musics/{filename}"

    # 4. 處理 SRT
    if srt:
        content = await srt.read()
        try:
            session.srt_content = content.decode("utf-8")
        except UnicodeDecodeError:
            session.srt_content = content.decode("utf-8", errors="ignore")

    return {
        "status": "success", 
        "guild_id": guild_id,
        "current_uuid": session.uuid
    }

@app.get("/test")
async def test():
    return sessions

if __name__ == "__main__":
    import uvicorn
    print("Starting server...")
    # 測試用連結範例
    print("Example Player URL: http://localhost:8000/player/123_testsession")
    uvicorn.run(app, host="0.0.0.0", port=8000)