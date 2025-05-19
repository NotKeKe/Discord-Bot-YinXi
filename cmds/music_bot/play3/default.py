from core.functions import read_json, write_json

personal_list_path = './cmds/data.json/music_personal_list.json'

class save:
    items = {}

    personal_list: dict

    # 代表全部歌曲
    queues = {}

    # 如果ctx.guild.id在looping中，則代表使用者要循環播放音樂
    looping = []

    # 使用前一首，looping，以及預設情況要用到current_playing_index
    current_playing_index = {}

    playing_personal = []

    @classmethod
    def save_item(cls, audio_url, title, length, thumbnail, video_url):
        cls.items = {
            'audio_url': audio_url, 
            'title': title, 
            'length': str(length), 
            'thumbnail': thumbnail, 
            'video_url': video_url
        }

    @classmethod
    def save_info_to_personal_list(cls, user_id):
        # 防呆機制
        user_id = str(user_id)

        if user_id not in cls.personal_list: print('請先初始化陣列'); return
        cls.personal_list[user_id].append(cls.items)
        write_json(cls.personal_list, personal_list_path)
        cls.items = {}

    @classmethod
    def save_info_to_queues(cls, guild_id):
        if guild_id not in cls.queues: print('請先初始化陣列'); return
        cls.queues[guild_id].append(cls.items)
        cls.items = {}

    @classmethod
    def delete_info_for_personal_list(cls, user_id, value):
        user_id = str(user_id)

        if user_id not in cls.personal_list: print('裡面沒有userid'); return
        item = cls.personal_list[user_id].pop(value)

        if not cls.personal_list[user_id]: del cls.personal_list[user_id]

        write_json(cls.personal_list, personal_list_path)
        return item

class init:
    @staticmethod
    def initialize_personal_list(user_id):
        '''
        初始化你要的東西 dict
        '''
        user_id = str(user_id)

        if user_id not in save.personal_list:
            save.personal_list[user_id] = []

    @staticmethod
    def initialize_queues(guild_id):
        '''
        初始化你要的東西 dict
        '''
        if guild_id not in save.queues:
            save.queues[guild_id] = []

    @staticmethod
    def index_dec(id):
        save.current_playing_index[id] -= 1

    @staticmethod
    def index_inc(id):
        save.current_playing_index[id] += 1