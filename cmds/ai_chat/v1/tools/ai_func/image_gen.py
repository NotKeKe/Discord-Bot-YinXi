import time
from typing import Tuple

from ...utils.client import AsyncClient

async def image_generate(prompt: str, model: str = 'cogview-3-flash') -> Tuple[str, float]:
    """Generate image by cog view 3 flash model


    Args:
        prompt (str): _description_
        model (str, optional): _description_. Defaults to 'cogview-3-flash'.

    Returns:
        str: _description_: url of image
    """    
    if not model: model = 'cogview-3-flash'
    start_time = time.time()
    client = AsyncClient.zhipu

    resp = await client.images.generate(
        prompt = prompt,
        model=model,
        n=1
    )

    end_time = time.time()

    return resp.data[0].url, end_time - start_time