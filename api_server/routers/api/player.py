import logging
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import StreamingResponse

from src.player.player import HTTPX_CLIENT, get_player
from src.player.audio_urls import get_audio_url
from src.utils import get_client_ip, security_check

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/player'
)

@router.get("/stream")
async def stream(
    request: Request,
    token: str, # 音樂 token，用於取得 audio url
    guild_id: str,
    uuid: str,
    user_id: str,
    range: str = Header(None)  # 獲取前端瀏覽器發送的 Range header
):
    await security_check(
        params={
            'guild_id': guild_id,
            'uuid': uuid,
            'user_id': user_id,
        },
        to_check={
            'player': True,
            'dc_key': False,
            'user_id': True
        }
    )

    player = get_player(guild_id)
    if not player: 
        logger.error(f'Where is player??? | guild_id: {guild_id} | uuid: {uuid} | user_id: {user_id}')
        raise HTTPException(status_code=500, detail="Unknown error occurred")

    audio_url = get_audio_url(token, guild_id)
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio not found")
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
            logger.info(f'Audio Stream Start, guild_id: {guild_id} | user_id: {user_id} | ip: {get_client_ip(request)}')
            async for chunk in r.aiter_bytes(chunk_size=8192):
                yield chunk
        finally:
            await r.aclose()
            logger.info(f'Audio Stream Stop, guild_id: {guild_id} | user_id: {user_id} | ip: {get_client_ip(request)}') # 也有可能是前端已經接收完了

    # 6. 回傳 StreamingResponse
    # 如果有 Range，狀態碼通常是 206 (Partial Content)，否則 200

    return StreamingResponse(
        content_iterator(),
        status_code=r.status_code,
        headers=resp_headers,
        media_type=r.headers.get("Content-Type", "audio/mpeg")
    )