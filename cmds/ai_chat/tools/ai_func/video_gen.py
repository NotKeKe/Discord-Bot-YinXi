from datetime import datetime
from typing import Tuple
import base64
from io import BytesIO
from PIL import Image
from zai import ZhipuAiClient
import asyncio

from core.functions import image_to_base64

from ...utils.config import zhipu_KEY

client = ZhipuAiClient(
    api_key=zhipu_KEY
)

def image_size(image_base64) -> str:
    image_data = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_data))

    # 获取圖片大小
    width, height = image.size
    return f'{width}x{height}'

async def video_generate(prompt: str, image_url = None, size=None, fps=60, with_audio: bool=True, duration: int=5) -> Tuple[str, float]:
    imageBase64 = None
    if image_url is not None:
        imageBase64 = await image_to_base64(image_url)
        if size is None:
            size = image_size(imageBase64)

    if size is None:
        size = '1920x1080'


    response = await asyncio.to_thread(
        client.videos.generations,
        model="cogvideox-flash",
        image_url=imageBase64,
        prompt=prompt,  
        quality="quality",
        with_audio=with_audio,
        size=size,
        duration=duration,
        fps=fps
    )

    id = response.id
    # print(f'{id}: {prompt}')
    rn = datetime.now()

    def on_timeout(rn: datetime) -> bool:
        return (datetime.now() - rn).total_seconds() > 60*20

    while True:
        await asyncio.sleep(10)

        try:
            response2 = await asyncio.to_thread(
                client.videos.retrieve_videos_result,
                id=id
            )
            
            passed = (datetime.now() - rn).total_seconds()

            if response2.task_status == 'SUCCESS':
                return response2.video_result[0].url, passed
            elif response2.task_status == 'FAIL':
                return '生成失敗', passed
            
            if on_timeout(rn):
                return 'Timeout (時間超過20分鐘)', passed
        except: return 'API發送失敗', passed