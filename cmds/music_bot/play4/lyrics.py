from lyricsgenius import Genius
import asyncio
import re
import aiohttp

from core.functions import async_translate

class 棄用:
    from core.functions import GENIUS_ACCESS_TOKEN

    genius = Genius(GENIUS_ACCESS_TOKEN)
    # genius.verbose = True

    @classmethod
    async def search_lyrics(cls, query: str, artist: str) -> str | bool:
        song = await asyncio.to_thread(cls.genius.search_song, query, artist)
        if not song: return False

        lyrics = song.lyrics
        split_lyrics = re.split(r'(?<=Lyrics)', lyrics, maxsplit=1)

        if len(split_lyrics) > 1:
            lyrics_only = split_lyrics[1]
        else:
            lyrics_only = lyrics

        return lyrics_only
    
def clean_keywords_text(text: str) -> str:
    pattern = r".*[:：].*"

    cleaned = "\n".join(
        line for line in text.splitlines()
        if not re.search(pattern, line)
    )

    text = cleaned.replace('10亿现金激励，千亿流量扶持！', '').replace('本歌曲来自〖飓风计划〗', '').replace('(未经著作权人许可，不得翻唱、翻录或使用)', '')

    text = "\n".join(line.lstrip() for line in text.splitlines())

    return text

def lrc_to_plain_text(lrc_content: str) -> str:  
    # 移除時間標記 [mm:ss.xxx]  
    pattern = r'\[\d+:\d+\.\d+\]'  
    plain_text = re.sub(pattern, '', lrc_content)  

    return plain_text

async def search_lyrics(query: str, artist: str, lrc: bool = False) -> str | bool:
    query = await async_translate(query, 'zh-TW', 'zh-CN')

    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://192.168.31.99:28883/jsonapi', params={'title': query, **({'artist': artist} if artist else {})}) as resp:
            js = await resp.json()

    if not js: return False

    for item in js:
        if not item['cover']: continue
        text = item['lyrics']
        break

    if not lrc:
        text = lrc_to_plain_text(text)
        text = clean_keywords_text(text)

    return text