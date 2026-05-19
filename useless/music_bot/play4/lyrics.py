class 棄用:
    from core.functions import GENIUS_ACCESS_TOKEN
    from lyricsgenius import Genius

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