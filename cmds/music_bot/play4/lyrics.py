from lyricsgenius import Genius
import asyncio
import re

from core.functions import GENIUS_ACCESS_TOKEN

genius = Genius(GENIUS_ACCESS_TOKEN)
# genius.verbose = True

async def search_lyrics(query: str, artist: str) -> str | bool:
    song = await asyncio.to_thread(genius.search_song, query, artist)
    if not song: return False

    lyrics = song.lyrics
    split_lyrics = re.split(r'(?<=Lyrics)', lyrics, maxsplit=1)

    if len(split_lyrics) > 1:
        lyrics_only = split_lyrics[1]
    else:
        lyrics_only = lyrics

    return lyrics_only