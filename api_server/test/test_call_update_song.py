import requests
from pprint import pp

url = 'http://localhost:8000/update_song'

resp = requests.post(
    url, 
    data={'guild_id': '123456', 'current_time': 60},
)
if resp.status_code == 200:
    pp(resp.json())
else:
    print(resp.status_code, resp.text)