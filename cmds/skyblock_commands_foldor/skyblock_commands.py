"""
### A simple API wrapper for Hypixel Skyblock.

(c) 2023-present NKA Development Organization
"""
# Imports
import requests
# from json import loads as parse
from orjson import loads as parse
import json
import os
# By NotKeKe
from datetime import datetime

current_directory = os.getcwd()
with open(f"{current_directory}/setting.json", "r") as jfile:
    jdata = json.load(jfile)

# Functions
class Skyblock:
    """Used for accessing the Skyblock API."""
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_uuid(self, player_name: str) -> str:
        """Fetches the UUID of a player based on their username."""
        api_request = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}")
        content = parse(api_request.content)
        if('id' in content): return content['id']
        else: return 'Wrong ID'

    # API Retrieval Commands
    def get_player_info(self, player_name: str) -> str:
        """Fetches data of a specific player, including game stats."""
        player_uuid = self.get_uuid(player_name)
        api_request = requests.get(f"https://api.hypixel.net/player?key={self.api_key}&uuid={player_uuid}").content
        player_data = parse(api_request)
        return player_data["session"]["online"]

    def get_guild_info(self, player_name: str) -> dict:
        """Retrieve a guild by a player."""
        player_uuid = self.get_uuid(player_name)
        api_request = requests.get(f"https://api.hypixel.net/guild?key={self.api_key}&player={player_uuid}").content
        guild_data = parse(api_request)
        return guild_data

    def get_auctions(self, page: int = 0) -> dict:
        """
        Returns a `dict` of the 1000 latest auctions in Skyblock.
        
        Optional args:
        * `page`: View a specific page of auctions.
        """
        api_request = requests.get(f"https://api.hypixel.net/skyblock/auctions?key={self.api_key}&page={page}").content
        auctions = parse(api_request)
        return auctions

    def get_recentgames(self, player_name: str) -> dict:
        """Fetches the recently played games of a specific player."""
        player_uuid = self.get_uuid(player_name)
        api_request = requests.get(f"https://api.hypixel.net/recentgames?key={self.api_key}&uuid={player_uuid}").content
        player_data = parse(api_request)
        return player_data

    def get_player_status(self, player_name: str) -> dict:
        """Fetches the current online status of a specific player."""
        player_uuid = self.get_uuid(player_name)
        api_request = requests.get(f"https://api.hypixel.net/status?key={self.api_key}&uuid={player_uuid}").content
        player_data = parse(api_request)
        return player_data

    def get_player_auctions(self, player_name: str) -> dict:
        """Returns a `dict` of all Skyblock auctions from a particular player."""
        player_uuid = self.get_uuid(player_name)
        api_request = requests.get(f"https://api.hypixel.net/skyblock/auction?key={self.api_key}&player={player_uuid}").content
        player_auctions = parse(api_request)
        return player_auctions

    def get_recently_ended_auctions(self) -> dict:
        """Returns a `dict` of all the auctions that have recently ended within 60 seconds."""
        api_request = requests.get("https://api.hypixel.net/skyblock/auctions_ended").content
        recently_ended_auctions = parse(api_request)
        return recently_ended_auctions

    def get_game_info(self) -> dict:
        """Returns information about Hypixel Games."""
        api_request = requests.get("https://api.hypixel.net/resources/games").content
        games_info = parse(api_request)
        return games_info

    def get_achievements(self) -> dict:
        """Returns a `dict` of all Hypixel achievements."""
        api_request = requests.get("https://api.hypixel.net/resources/achievements").content
        games_info = parse(api_request)
        return games_info

    def get_challenges(self) -> dict:
        """Returns a `dict` of all Hypixel challenges."""
        api_request = requests.get("https://api.hypixel.net/resources/challenges").content
        games_info = parse(api_request)
        return games_info

    def get_quests(self) -> dict:
        """Returns a `dict` of all Hypixel quests."""
        api_request = requests.get("https://api.hypixel.net/resources/quests").content
        games_info = parse(api_request)
        return games_info

    def get_guild_achievements(self) -> dict:
        """Returns a `dict` of all Hypixel Guild achievements."""
        api_request = requests.get("https://api.hypixel.net/resources/guilds/achievements").content
        games_info = parse(api_request)
        return games_info

    def get_vanity_pets(self) -> dict:
        """Returns a `dict` of all Hypixel vanity pets."""
        api_request = requests.get("https://api.hypixel.net/resources/vanity/pets").content
        games_info = parse(api_request)
        return games_info

    def get_vanity_companions(self) -> dict:
        """Returns a `dict` of all Hypixel vanity companions."""
        api_request = requests.get("https://api.hypixel.net/resources/vanity/companions").content
        games_info = parse(api_request)
        return games_info

    def get_news(self) -> dict:
        """Returns a `dict` of the latest Skyblock news from Hypixel."""
        api_request = requests.get(f"https://api.hypixel.net/skyblock/news?key={self.api_key}").content
        news = parse(api_request)
        return news

    def get_bazaar_data(self) -> dict:
        """Returns a `dict` of Skyblock bazaar data."""
        api_request = requests.get(f"https://api.hypixel.net/skyblock/bazaar?key={self.api_key}").content
        bazaar_data = parse(api_request)
        return bazaar_data

    def get_player_profile(self, player_name: str) -> dict:
        """Returns a `dict` of profile data on a player."""
        player_uuid = self.get_uuid(player_name)
        api_request = requests.get(f"https://api.hypixel.net/skyblock/profiles?key={self.api_key}&uuid={player_uuid}").content
        player_profile_data = parse(api_request)
        return player_profile_data

    def get_player_bingo_data(self, player_name: str) -> dict:
        """Returns a `dict` of Bingo data for parcitipated events of the provided player."""
        player_uuid = self.get_uuid(player_name)
        api_request = requests.get(f"https://api.hypixel.net/skyblock/bingo?key={self.api_key}&uuid={player_uuid}").content
        player_bingo_data = parse(api_request)
        return player_bingo_data

    def get_firesales(self) -> dict:
        """Returns a `dict` of all currently active or upcoming Fire Sales for Skyblock."""
        api_request = requests.get("https://api.hypixel.net/skyblock/firesales").content
        firesales_data = parse(api_request)
        return firesales_data

    def get_collections(self) -> dict:
        """Returns a `dict` of information related to Skyblock Collections."""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/collections").content
        collections_data = parse(api_request)
        return collections_data

    def get_skills(self) -> dict:
        """Returns a `dict` of information related to Skyblock Skills."""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/skills").content
        collections_data = parse(api_request)
        return collections_data

    def get_items(self) -> dict:
        """Returns a `dict` of information related to Skyblock items."""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/items").content
        items_data = parse(api_request)
        return items_data

    '''下面兩段程式 因為我也不知道作者在幹嘛 而且還會抱錯，因此註解'''

    # def get_mayor_information(self) -> dict:
    #     """Returns a `dict` of information regarding the current mayor in Skyblock."""
    #     api_request = requests.get("https://api.hypixel.net/resources/skyblock/election").content
    #     mayor_info = parse(api_request)
    #     del mayor_info["current"]
    #     return mayor_info

    # def get_current_election(self) -> dict:
    #     """Returns a `dict` of information regarding the current election in Skyblock."""
    #     api_request = requests.get("https://api.hypixel.net/resources/skyblock/election").content
    #     election_info = parse(api_request)
    #     del election_info["mayor"]
    #     return election_info

    def get_bingo_event(self) -> dict:
        """Returns a `dict` of information regarding the current bingo event and goals in Skyblock."""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/bingo").content
        bingo_data = parse(api_request)
        return bingo_data

    def get_active_network_boosters(self):
        """Returns a `dict` of all of the active network boosters."""
        api_request = requests.get(f"https://api.hypixel.net/boosters?key={self.api_key}").content
        boosters_data = parse(api_request)
        return boosters_data

    def get_current_player_counts(self) -> dict:
        """Returns a `dict` of the current player counts for all game modes."""
        api_request = requests.get(f"https://api.hypixel.net/counts?key={self.api_key}").content
        player_count_data = parse(api_request)
        return player_count_data

    def get_current_leaderboards(self):
        """Returns a `dict` of the current Hypixel leaderboards."""
        api_request = requests.get(f"https://api.hypixel.net/leaderboards?key={self.api_key}").content
        leaderboards_data = parse(api_request)
        return leaderboards_data

    def get_punishment_statistics(self):
        """Returns a `dict` of Hypixel's punishment statistics."""
        api_request = requests.get(f"https://api.hypixel.net/punishmentstats?key={self.api_key}").content
        punishment_stats_data = parse(api_request)
        return punishment_stats_data
    
    # By. NotKeKe

    def get_player_name(self, player_name) -> str:
        """Returns a 'str' of player's name(including uppercase and lowercase)"""
        """回傳(字串)玩家名稱的名稱(有大小跟小寫)"""
        api_request = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}")
        content = parse(api_request.content)
        return content["name"]
    
    def get_username_from_uuid(self, uuid) -> str:
        response = requests.get(f'https://api.mojang.com/user/profiles/{uuid}')

        if response.status_code != 200:
            api_request = requests.get(f"https://api.hypixel.net/player?key={self.api_key}&uuid={uuid}")
            if api_request.status_code != 200: return None
            content = parse(api_request.content)
            result = content['player']['displayname']
        else:
            data = parse(response.content)
            result = data.get("name")
        return result

    def get_mayor(self) -> str:
        """回傳現在的市長、minister、資訊更新時間"""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/election").content
        mayor_info = parse(api_request)
        mayor = mayor_info['mayor']['name']
        minister = mayor_info['mayor']['minister']['name'] if 'minister' in mayor_info['mayor'] else None
        未整理的時間 = datetime.fromtimestamp(mayor_info["lastUpdated"] / 1000)
        lastUpdated = 未整理的時間.strftime("%Y-%m-%d %H:%M:%S")
        return mayor, minister, lastUpdated
    
    def get_mayor_information(self) -> list:
        """回傳市長的增益"""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/election").content
        mayor_info = parse(api_request)
        info = list()
        for i in range(len(mayor_info['mayor']['perks'])):
            info.append(mayor_info['mayor']['perks'][i]['name'])
        return info
    
    def get_minister_information(self) -> str:
        """回傳副市長的增益"""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/election").content
        mayor_info = parse(api_request)
        info = mayor_info['mayor']['minister']['perk']['name'] if 'minister' in mayor_info['mayor'] else None
        return info

    def get_mayor_perks_description(self) -> list:
        """回傳市長的增益描述"""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/election").content
        mayor_info = parse(api_request)
        info = list()
        for i in range(len(mayor_info['mayor']['perks'])):
            info.append(mayor_info['mayor']['perks'][i]['description'])
        return info
    
    def get_minister_perk_description(self) -> str:
        """回傳副市長的增益描述"""
        api_request = requests.get("https://api.hypixel.net/resources/skyblock/election").content
        mayor_info = parse(api_request)
        info = mayor_info['mayor']['minister']['perk']['description'] if 'minister' in mayor_info['mayor'] else None
        return info
    
    def time_conversion(self, un: int) -> str:
        """回傳換算後的時間"""
        # 未整理的時間 = datetime.fromtimestamp(mayor_info["lastUpdated"] / 1000)
        # lastUpdated = 未整理的時間.strftime("%Y-%m-%d %H:%M:%S")
        未整理的時間 = datetime.fromtimestamp(un / 1000)
        time = 未整理的時間.strftime("%Y-%m-%d %H:%M:%S")
        return time
        
    def time_now_disconversion(self) -> int:
        """將現在的時間轉成毫秒並回傳"""
        current_time = datetime.now()
        un = int(current_time.timestamp() * 1000)
        return un
    
    def time_until_new_year_celebration(self):
        """此段代碼由Copilot生成"""
        # Skyblock 中一天的秒數
        SECONDS_PER_SKYBLOCK_DAY = 1200  # 20 分鐘
        # Skyblock 中一年有 124 天
        DAYS_PER_SKYBLOCK_YEAR = 124

        # 當前時間
        now = datetime.now()

        # 計算當前 Skyblock 年份和天數
        skyblock_start_date = datetime(2019, 6, 11)
        days_since_skyblock_start = (now - skyblock_start_date).days
        skyblock_year = days_since_skyblock_start // DAYS_PER_SKYBLOCK_YEAR + 1
        skyblock_day_of_year = days_since_skyblock_start % DAYS_PER_SKYBLOCK_YEAR + 1

        # New Year Celebration 開始時間
        new_year_celebration_start_day = 29 + 3 * 31  # 晚冬第 29 天
        if skyblock_day_of_year > new_year_celebration_start_day:
            skyblock_year += 1
            days_until_new_year_celebration = DAYS_PER_SKYBLOCK_YEAR - skyblock_day_of_year + new_year_celebration_start_day
        else:
            days_until_new_year_celebration = new_year_celebration_start_day - skyblock_day_of_year

        # 將天數換算成秒
        seconds_until_new_year_celebration = days_until_new_year_celebration * SECONDS_PER_SKYBLOCK_DAY

        return seconds_until_new_year_celebration
    
    def format_price(self, price):
        formated_price = "{:,.0f}".format(price)
        return formated_price
    
    


if __name__  == "__main__":
    # while(True):
    #     a = input()
    #     if a == "playerinfo":
    #         player_name = str(input())
    #         Skyblock().get_player_info(player_name=player_name)

    # sb = Skyblock(api_key=jdata["tmp_hypixel_api_key"])

    sb = Skyblock(api_key='e76aab65-dd5c-47eb-8d2c-0ab859e132b8')

    print(sb.get_username_from_uuid('552e9105aa1f47d2ba3f473b0b1d7292'))
    


    # with open("./cmds/skyblock_commands_foldor/tmp.txt", 'wt', encoding="utf-8") as f:
    #     pass

    # with open("./cmds/skyblock_commands_foldor/tmp.txt", 'at', encoding="utf-8") as f:
    #     i = 1
    #     for game in (a['games']):
    #         if not (game == "SPEED_UHC" or game == "TOURNAMENT_LOBBY"):
    #             # f.write(f"discord.SelectOption(label='{game}', value='{i}'),\n")
    #             f.write(f"Choice(name = '{game}', value = '{i}'),\n")
    #             i = i+1
        
