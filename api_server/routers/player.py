from uuid import uuid4
import logging
from pathlib import Path
import orjson
from fastapi import APIRouter, Request, Form, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from src.player.player import get_or_create_player, get_player, delete_player, is_player_exist, HTTPX_CLIENT
from src.player.audio_urls import get_audio_url
from src.utils import check_vaild_PLAY_WEBSITE_KEY

router = APIRouter(
    prefix="/player",
    tags=["Player"],
    responses={404: {"description": "Not found"}},
)
logger = logging.getLogger(__name__)

# 確保目錄存在
MUSIC_DIR = Path(__file__).parent.parent / "static" / "player" / "musics"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

# 2. 設定模板引擎
templates = Jinja2Templates(directory="templates")



@router.get('/check_song')
async def check_song(guild_id: str, session_id: str, lang: str = 'original'):
    '''for frontend'''
    if not is_player_exist(guild_id, session_id=session_id or ''):
        raise HTTPException(status_code=404, detail=f"Session not found, guild_id: {guild_id}, session_id: {session_id}")
    
    player = get_player(guild_id)
    if not player: raise HTTPException(status_code=404, detail=f"Cannot found any player, guild_id: {guild_id}, session_id: {session_id}")

    return player.get_state(lang)

@router.get("/stream")
async def stream(
    token: str, # 音樂 token，用於取得 audio url
    guild_id: str,
    session_id: str,
    range: str = Header(None)  # 獲取前端瀏覽器發送的 Range header
):
    if not is_player_exist(guild_id, session_id=session_id):
        return JSONResponse(status_code=404, content={"message": "Session not found"})

    audio_url = get_audio_url(token, guild_id)
    if not audio_url:
        return JSONResponse(status_code=404, content={"message": "Audio not found"})
    req_headers = {}
    if range:
        req_headers["Range"] = range
    
    # 建構請求
    req = HTTPX_CLIENT.build_request("GET", audio_url, headers=req_headers)
    
    # 發送請求獲取響應頭 (此時還沒下載 body)
    r = await HTTPX_CLIENT.send(req, stream=True)
    
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
    '''用於獲取播放器頁面'''
    if not is_player_exist(guild_id, page_uuid):
        raise HTTPException(status_code=404, detail=f"Session not found, guild_id: {guild_id}")

    return templates.TemplateResponse("player.html", {
        "request": request, 
        "guild_id": guild_id 
    })

@router.post('/update_song')
async def update_song(
    guild_id: str = Form(...),
    uuid: str = Form(...),
    title: str | None = Form(None),
    audio_url: str = Form(...),
    srts: str = Form(''), # type: ignore
    duration: int = Form(...),
    current_time: int = Form(...),
    is_paused: bool = Form(...),
):
    '''一個給 discord bot 的端點，用於更新歌曲資訊'''
    if not is_player_exist(guild_id, uuid):
        raise HTTPException(status_code=404, detail=f"Session not found, guild_id: {guild_id}, uuid: {uuid}")
    
    try:
        srts: dict[str, list] = orjson.loads(srts)
    except:
        raise HTTPException(status_code=400, detail="Invalid srts json format")
    
    player = get_player(guild_id)
    if not player: raise HTTPException(status_code=400, detail=f"Cannot found any player, guild_id: {guild_id}, uuid: {uuid}")

    player.update_state(title, audio_url, srts, duration, current_time, is_paused)

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

        player = get_or_create_player(guild_id, uuid)
        
        # 1. 更新 Session ID (觸發前端重整)
        player.session_id = str(uuid4())
        logger.info(f'Created a session: {player.session_id} for guild_id: {guild_id}')
        
        # 2. 更新文字資訊
        player.update_state(title, audio_url, srts, duration, 0, False)

        return {
            "status": "success", 
            "guild_id": guild_id,
            "current_uuid": player.uuid
        }
    except HTTPException: ...
    except:
        logger.error('upload_song error', exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.post("/delete_song")
async def delete_song(
    request: Request,
    guild_id: str = Form(...), 
    uuid: str | None = Form(None),
):
    if not is_player_exist(guild_id, uuid or ''):
        raise HTTPException(status_code=404, detail=f"Session not found, guild_id: {guild_id}")
        
    key = request.headers.get('x-api-key')
    
    player = get_player(guild_id)
    if not player: 
        raise HTTPException(status_code=404, detail=f"Cannot found any player, guild_id: {guild_id}")

    # 沒有 key 就檢查 uuid，有 key 就檢查 key
    if not key:
        if player.uuid != uuid:
            raise HTTPException(status_code=404, detail=f"Invalid uuid, guild_id: {guild_id}, uuid: {uuid}")
    else:
        if not check_vaild_PLAY_WEBSITE_KEY(key):
            raise HTTPException(status_code=404, detail=f"Invalid KEY, guild_id: {guild_id}")
    
    delete_player(guild_id)
    return {"message": "Song deleted successfully"}

# @router.get("/test")
# async def test():
#     from src.player.player import players    
#     return players