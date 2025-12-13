import requests
from pprint import pp

url = 'http://localhost:8000/upload_song'

resp = requests.post(
    url, 
    data={'guild_id': '123456', 'title': 'Test Title', 'subtitle': 'Test Subtitle'},
    files={
        'audio': ('test_music.webm', open('test_music.webm', 'rb')),
        'srt': ('en.srt', open('en.srt', 'rb'))
    }
)
if resp.status_code == 200:
    pp(resp.json())
else:
    print(resp.status_code, resp.text)