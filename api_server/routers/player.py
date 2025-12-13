import os
import uuid
import shutil
from typing import Dict
from httpx import AsyncClient, Limits
import logging
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/player",
    tags=["Player"],
    responses={404: {"description": "Not found"}},
)
logger = logging.getLogger(__name__)

_limit = Limits(max_keepalive_connections=5, max_connections=10)
httpx_client = AsyncClient(limits=_limit)

# 確保目錄存在
MUSIC_DIR = Path(__file__).parent.parent / "static" / "player" / "musics"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

# 2. 設定模板引擎
templates = Jinja2Templates(directory="templates")

# 3. Session 狀態管理 (Multi-tenant)
# 結構: { "guild_id_123": { "uuid": "...", "title": "...", ... } }
class SessionState:
    def __init__(self, guild_id: str):
        self.guild_id = guild_id
        self.uuid = str(uuid.uuid4())
        self.title = "Waiting for Signal..."
        self.subtitle = ""
        self.audio_url = ""
        self.srt_content = ""
        self.current_time = 0
        self.is_paused = False
        self.duration: int = 0

sessions: Dict[str, SessionState] = {}

def get_or_create_session(guild_id: str) -> SessionState:
    if guild_id not in sessions:
        sessions[guild_id] = SessionState(guild_id)
    return sessions[guild_id]

# --- Routes ---

@router.get("/check_song")
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
        'current_time': session.current_time,
        'is_paused': session.is_paused
    }

@router.get("/{guild_id}_{page_uuid}", response_class=HTMLResponse)
async def player_page(request: Request, guild_id: str, page_uuid: str):
    """
    顯示特定 Guild 的播放器頁面。
    URL 範例: http://localhost:8000/player/123456_abcde-1234-uuid
    page_uuid 這裡主要作為連結的一次性或驗證用途，
    但主要邏輯依賴 guild_id 來區分狀態。
    """
    # 這裡將 guild_id 注入到 template 中，讓前端 JS 可以讀取

    if guild_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found, guild_id: {guild_id}")

    return templates.TemplateResponse("player.html", {
        "request": request, 
        "guild_id": guild_id 
    })

@router.post('/update_song')
async def update_song(
    guild_id: str = Form(...),
    title: str = Form(None),
    audio_url: str = Form(...),
    srt: dict = Form(None),
    duration: int = Form(...),
    current_time: int = Form(...),
    is_paused: bool = Form(...),
):
    """
    Discord Bot 或控制端呼叫此接口來更新狀態。
    必須提供 guild_id。
    """
    if guild_id not in sessions:
        parmas_str = f'guild_id: {guild_id}, title: {title}, audio_url: {audio_url}, srt: {srt}, duration: {duration}, current_time: {current_time}, is_paused: {is_paused}'
        raise HTTPException(status_code=404, detail=f"Session not found, with params: {parmas_str}")
    
    session = get_or_create_session(guild_id)
        
    session.audio_url = audio_url
    session.duration = duration
    session.current_time = current_time
    session.is_paused = is_paused

    if title:
        session.title = title
    if srt:
        session.srt_content = srt

    return {"message": "Song updated successfully"}

@router.post("/upload_song")
async def upload_song(
    guild_id: str = Form(...),
    title: str = Form(None),
    audio_url: str = Form(...),
    srt: dict = Form(None),
    duration: int = Form(...),
):
    """
    Discord Bot 或控制端呼叫此接口來創建歌曲。
    必須提供 guild_id。
    """
    try:
        session = get_or_create_session(guild_id)
        
        # 1. 更新 UUID (觸發前端重整)
        session.uuid = str(uuid.uuid4())
        logger.info(f'Created a uuid: {session.uuid}')
        
        # 2. 更新文字資訊
        if title:
            session.title = title
            
        session.audio_url = audio_url
        session.duration = duration

        # 4. 處理 SRT
        if srt:
            session.srt_content = srt

        return {
            "status": "success", 
            "guild_id": guild_id,
            "current_uuid": session.uuid
        }
    except:
        logger.error('upload_song error', exc_info=True)

@router.get("/test")
async def test():
    return sessions