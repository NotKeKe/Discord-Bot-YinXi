from discord import Interaction
from discord.app_commands import Choice
from typing import List
from datetime import datetime
from zoneinfo import ZoneInfo

from core.mongodb import MongoDB_DB
from core.functions import FormatTime, redis_client

async def custom_play_list_autocomplete(inter: Interaction, curr: str) -> List[Choice[str]]:
    coll = MongoDB_DB.music['metas']

    _filter = {
        'type': 'custom_play_list',
        'user_id': inter.user.id,
        **({'list_name': {"$regex": f".*{curr}.*", "$options": "i"}} if curr else {})
    }

    results = []
    format_template = 'Name: "{}" | PlayedTimes: "{}" | LastPlay: "{}"'

    async for meta in coll.find(_filter):
        name = meta['list_name']
        play_times = meta['list_played_times']
        last_play_utc_str = meta["list_last_played_at"]
        if last_play_utc_str != '':
            last_play_utc = datetime.fromisoformat(last_play_utc_str) # utc 0
            last_play_utc8 = last_play_utc.astimezone(ZoneInfo("Asia/Taipei")) # 轉為 utc+8
            last_play = FormatTime(last_play_utc8)
        else:
            last_play = 'Unknown'

        results.append((
            name, # str
            play_times, # int
            last_play # str
        ))

    results.sort(key=lambda x: (-x[1], x[0])) # 先使用播放次數排序(-可以 reverse), 再使用名稱排序

    return [
        Choice(name=format_template.format(name, play_time, last_play), value=name) 
        for name, play_time, last_play in results
    ] # 給使用者顯示的, list_name

async def play_query_autocomplete(inter: Interaction, curr: str) -> List[Choice[str]]:
    '''曾經在 play or add 中使用的 query，最多 10 項'''
    key = f'musics_query:{inter.user.id}'
    results = await redis_client.lrange(key, 0, 9)

    if curr:
        results = [result for result in results if curr.lower().strip() in result.lower().strip()]

    return [Choice(name=result, value=result) for result in results]