import asyncio
import re
import orjson

from cmds.AIsTwo.base_chat import base_openai_chat

from core.functions import current_time, read_json, write_json

music_PATH = './cmds/data.json/music.json'

class MusicData:
    data = None
    update = False

    example = {
        'recommend': {
            'ctx.author.id': {
                'song': [('title', 'author', 'length', 'video_url'), ('title', 'author', 'length', 'video_url')],
                'recommend': [('title', 'author', 'length', 'video_url')], 
                'update_time': current_time()
            }
        }
    }

    def __init__(self):
        self.data = self.load()
        if not self.data:
            self.data = {
                'recommend': {}
            }
            self.save()

    @classmethod
    def load(cls):
        if not cls.data:
            cls.data = read_json(music_PATH)

    @classmethod
    def save(cls, data=None):
        if data:
            cls.data = data
        cls.update = True

    @classmethod
    def write(cls):
        if not cls.update: return
        write_json(music_PATH, cls.data)
        cls.update = False

class Recommend:
    def __init__(self, music_data: MusicData):
        self.music_data = music_data
    
    async def gener_recommendations(self, userID: str) -> list:
        item: dict = self.music_data.data['recommend'].get(userID, {})
        if not item: return
        songs = item.get('songs', [])
        if not songs: return
        think, result = await asyncio.to_thread(base_openai_chat, str(songs), 'qwen-3-32b', no_extra_system_prompt=True, system_prompt=
'''
接下來使用者會提供他所喜好的歌曲，
格式為一list `[(歌曲標題, 歌曲作者, 歌曲長度, 歌曲連結), (歌曲標題, 歌曲作者, 歌曲長度, 歌曲連結)...]`，
請根據使用者提供的歌曲列表，於判定他喜歡的風格後，在網上搜尋一首或多首符合他喜好的歌曲。
最終請以以下格式進行輸出，確保不包含多餘的文字，如果你感覺你的搜尋結果並不符合使用者的喜好，則一樣要輸出json格式，不過是recommed是空list。如果你所搜尋到的資訊沒有提供的話，請選擇將那一欄輸出為'None'的字串。
請確保嚴格遵守所有規定以及格式。
```json
{
    "recommend": [(歌曲標題, 歌曲作者, 歌曲長度，歌曲連結), (歌曲標題, 歌曲作者, 歌曲長度，歌曲連結)...]
}
```
''')
        data = re.search(r'```json(.*?)```', result, re.DOTALL)
        js = orjson.loads(data.group(1).strip())
        self.music_data.data['recommend'][userID] = {'recommend': js['recommend']}
        self.music_data.save()
        return js.get('recommend', [])
    
    def get_recommendations(self, userID: str) -> list:
        item: dict = self.music_data.data['recommend'].get(userID, {})
        if not item: return []
        return item.get('recommend', [])