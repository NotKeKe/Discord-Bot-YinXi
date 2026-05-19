import aiohttp
from cmds.AIsTwo.others.embedding import get_embeddings
from core.functions import DEVICE_IP

async def search(q: str, results_num: int = 3):
    embeddings = await get_embeddings(q)
    url = f'http://{DEVICE_IP}:3001/search'
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={'vector': embeddings, 'top_k': results_num}) as response:
            if not response.status == 200: return f'Error, status_code = {response.status}'
            data = await response.json()

    return data['results']