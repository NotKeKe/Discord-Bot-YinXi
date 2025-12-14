import os
import shutil
from uuid import uuid4
from typing import Dict
from httpx import AsyncClient, Limits
import logging
from pathlib import Path
from collections import defaultdict
import orjson
import httpx

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from src.url import audio_url_to_token, token_to_audio_url
from src.utils import check_vaild_uuid

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
    def __init__(self, guild_id: str, uuid: str):
        self.guild_id = guild_id
        self.uuid = uuid
        self.session_id = str(uuid4())
        self.title = "Waiting for Signal..."
        self.subtitle = ""
        self.audio_url = ""
        self.srts: dict[str, list] = defaultdict(list)
        self.current_time = 0
        self.is_paused = False
        self.duration: int = 0

sessions: Dict[str, SessionState] = {}

async def get_or_create_session(guild_id: str, uuid: str) -> SessionState | None:
    check = await check_vaild_uuid(guild_id, uuid)
    if not check: return

    if guild_id not in sessions:
        sessions[guild_id] = SessionState(guild_id, uuid)
    
    session = sessions[guild_id]
    if session.uuid != uuid: return # 不合法的 uuid, 請求的 uuid != 該 session 有的 uuid

    return session

# --- Routes ---

@router.get("/check_song")
async def check_song(guild_id: str, lang: str = 'original', session_id: str = ''):
    """
    前端 JS 每秒輪詢的接口。
    必須帶上 ?guild_id=... 參數。
    """
    if guild_id not in sessions:
        # 如果該公會還沒建立過 session，可以回傳預設值或 404
        # 這裡選擇回傳一個空狀態，讓前端保持等待
        return JSONResponse(status_code=404, content={"message": "Session not found"})
    
    session = sessions[guild_id]
    if session_id and session.session_id != session_id:
        return JSONResponse(status_code=404, content={"message": "Session not found"})
    
    # get target srt
    if lang in session.srts:
        target_srt = session.srts[lang]
    elif len(session.srts) > 0:
        # find first lang
        target_srt = session.srts[list(session.srts.keys())[0]]
    else:
        target_srt = ''

    # get stream token
    token = audio_url_to_token(session.audio_url, session.guild_id)
    audio_url = f'/player/stream/{token}'

    return {
        # "uuid": session.uuid,
        'session_id': session.session_id,
        "title": session.title,
        "subtitle": session.subtitle,
        "audio_url": audio_url,
        "srt_content": target_srt,
        'languages': list(session.srts.keys()),
        'current_time': session.current_time,
        'is_paused': session.is_paused
    }

@router.get("/stream/{token}")
async def stream(
    token: str, 
    range: str = Header(None)  # 獲取前端瀏覽器發送的 Range header
):
    audio_url = token_to_audio_url(token)
    req_headers = {}
    if range:
        req_headers["Range"] = range
    
    client = httpx.AsyncClient()
    
    # 建構請求，注意要用 stream=True
    req = client.build_request("GET", audio_url, headers=req_headers)
    
    # 發送請求獲取響應頭 (此時還沒下載 body)
    r = await client.send(req, stream=True)
    
    # 4. 準備回傳給前端的 Headers
    # 這些 Header 告訴瀏覽器這是一個部分內容，以及檔案多大，這讓進度條可以運作
    resp_headers = {
        "Accept-Ranges": "bytes", # 告訴瀏覽器我們支援跳轉
        "Content-Type": r.headers.get("Content-Type", "audio/mpeg"),
    }
    
    if "Content-Length" in r.headers:
        resp_headers["Content-Length"] = r.headers["Content-Length"]
    
    if "Content-Range" in r.headers:
        resp_headers["Content-Range"] = r.headers["Content-Range"]

    # 5. 定義串流生成器
    # 當 FastAPI 傳輸完畢後，確保關閉 httpx client
    async def content_iterator():
        try:
            async for chunk in r.aiter_bytes(chunk_size=8192):
                yield chunk
        finally:
            await r.aclose()
            await client.aclose()

    # 6. 回傳 StreamingResponse
    # 如果有 Range，狀態碼通常是 206 (Partial Content)，否則 200
    return StreamingResponse(
        content_iterator(),
        status_code=r.status_code,
        headers=resp_headers,
        media_type=r.headers.get("Content-Type", "audio/mpeg")
    )

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
    
    session = sessions[guild_id]
    if session.uuid != page_uuid:
        raise HTTPException(status_code=404, detail=f"Invalid page_uuid, guild_id: {guild_id}")

    return templates.TemplateResponse("player.html", {
        "request": request, 
        "guild_id": guild_id 
    })

@router.post('/update_song')
async def update_song(
    guild_id: str = Form(...),
    uuid: str = Form(...),
    title: str = Form(None),
    audio_url: str = Form(...),
    srts: str = Form(''), # type: ignore
    duration: int = Form(...),
    current_time: int = Form(...),
    is_paused: bool = Form(...),
):
    """
    Discord Bot 或控制端呼叫此接口來更新狀態。
    必須提供 guild_id。
    """
    if guild_id not in sessions:
        parmas_str = f'guild_id: {guild_id}, title: {title}, audio_url: {audio_url}, srt: {srts}, duration: {duration}, current_time: {current_time}, is_paused: {is_paused}'
        raise HTTPException(status_code=404, detail=f"Session not found, with params: {parmas_str}")
    
    try:
        srts: dict[str, list] = orjson.loads(srts)
    except:
        raise HTTPException(status_code=400, detail="Invalid srts json format")
    
    session = await get_or_create_session(guild_id, uuid)
    if not session: raise HTTPException(status_code=400, detail="Invalid uuid")
        
    session.audio_url = audio_url
    session.duration = duration
    session.current_time = current_time
    session.is_paused = is_paused
    session.srts = srts

    if title:
        session.title = title

    return {"message": "Song updated successfully"}

@router.post("/upload_song")
async def upload_song(
    guild_id: str = Form(...),
    uuid: str = Form(...),
    title: str = Form(None),
    audio_url: str = Form(...),
    srts: str = Form(None), # type: ignore
    duration: int = Form(...),
):
    """
    Discord Bot 或控制端呼叫此接口來創建歌曲。
    必須提供 guild_id。
    """
    try:
        try:
            srts: dict[str, list] = orjson.loads(srts)
        except:
            raise HTTPException(status_code=400, detail="Invalid srts json format")

        session = await get_or_create_session(guild_id, uuid)
        if not session: raise HTTPException(status_code=400, detail="Invalid uuid")
        
        # 1. 更新 Session ID (觸發前端重整)
        session.session_id = str(uuid4())
        logger.info(f'Created a session: {session.session_id} for guild_id: {guild_id}')
        
        # 2. 更新文字資訊
        if title:
            session.title = title
            
        session.audio_url = audio_url
        session.duration = duration

        # 4. 處理 SRT
        if srts:
            session.srts = srts

        return {
            "status": "success", 
            "guild_id": guild_id,
            "current_uuid": session.uuid
        }
    except HTTPException: ...
    except:
        logger.error('upload_song error', exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.post("/delete_song")
async def delete_song(
    guild_id: str = Form(...), 
    uuid: str = Form(...)
):
    if guild_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session not found, guild_id: {guild_id}")
    
    session = sessions[guild_id]
    if session.uuid != uuid:
        raise HTTPException(status_code=404, detail=f"Invalid uuid, guild_id: {guild_id}")
    
    del sessions[guild_id]
    return {"message": "Song deleted successfully"}

@router.get("/test")
async def test():
    return sessions